"""Option B: an install request runs the sandbox trial itself (Lima is faked here)."""

import io
import json
import subprocess
import tarfile
import warnings

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

warnings.filterwarnings("ignore", category=DeprecationWarning)
from agentmesh.governance.audit import AuditLog  # noqa: E402
from agentmesh.marketplace import MarketplaceError  # noqa: E402
from agentmesh.marketplace.manifest import PluginManifest, PluginType  # noqa: E402
from agentmesh.marketplace.registry import PluginRegistry  # noqa: E402
from agentmesh.marketplace.signing import PluginSigner  # noqa: E402

from divergence.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller  # noqa: E402
from divergence.evaluator.trial_runner import (  # noqa: E402
    CANDIDATE_LABEL, CapturedTraceRunner, LimaTrialRunner, TrialError, load_trial_runs,
)
from tests.test_evaluator import DESC, evaluator  # noqa: E402
from tests.test_normalise_trace import _result  # noqa: E402

FOLDER = "md-tables"


def _skill(tmp_path, folder=FOLDER):
    d = tmp_path / "skills" / folder
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {folder}\ndescription: {DESC}\n---\nbody\n")
    (d / "scripts" / "run.py").write_text("print('hi')\n")
    return d


def _packed_traces(folder, modes=("direct", "instructed")):
    """What demo_trial.sh packs: <mode>_out/results/candidate/<folder>.json."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for mode in modes:
            data = json.dumps(_result()).encode()
            info = tarfile.TarInfo(f"./{mode}_out/results/{CANDIDATE_LABEL}/{folder}.json")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class FakeLima:
    """Stands in for subprocess.run(['limactl', ...]); records every call."""

    def __init__(self, status="Running", fail_on=None):
        self.calls, self.status, self.fail_on = [], status, fail_on
        self.uploaded = {}

    def __call__(self, args, **kw):
        self.calls.append(args)
        out, rc = "", 0
        if args[1] == "list":
            out = self.status
        elif args[1] == "shell":
            script = args[-1]
            out = "/home/u.linux" if "printf" in script else "== direct ==\n== instructed ==\npacked\n"
            if self.fail_on and self.fail_on in script:
                rc = 1
        elif args[1] == "copy":
            src, dst = args[2], args[3]
            if src.startswith("dvg-lab:"):  # VM -> Mac: the packed traces
                with open(dst, "wb") as f:
                    f.write(_packed_traces(FOLDER))
            else:
                self.uploaded[dst] = open(src, "rb").read()
        return subprocess.CompletedProcess(args, rc, out, "boom" if rc else "")

    def shell_scripts(self):
        return [c[-1] for c in self.calls if c[1] == "shell"]


def test_lima_runner_drives_the_vm_and_loads_traces(tmp_path):
    fake = FakeLima()
    runner = LimaTrialRunner(local_root=tmp_path / "trials", run=fake)
    trial = runner.run("md-tables", _skill(tmp_path), AuditLog())

    assert [r.mode for r in trial.runs] == ["direct", "instructed"]
    assert all(m.startswith("identical") for m in trial.parity.values())
    # the skill and the repo's demo_trial.sh went into a fresh per-trial folder in the VM
    dests = sorted(fake.uploaded)
    assert dests[0].startswith("dvg-lab:/home/u.linux/dvg/trials/md-tables-")
    assert dests[0].endswith("/demo_trial.sh") and dests[1].endswith("/skill.tgz")
    names = tarfile.open(fileobj=io.BytesIO(fake.uploaded[dests[1]])).getnames()
    assert "./SKILL.md" in names and "./scripts/run.py" in names
    run_script = fake.shell_scripts()[-1]
    assert f"Dataset/Skills/{CANDIDATE_LABEL}/{FOLDER}" in run_script
    assert "DVG_DEMO_OUT=" in run_script and f"{CANDIDATE_LABEL}/{FOLDER}" in run_script
    assert "--with-agent" not in run_script
    assert (trial.traces_root / "sandbox_log.txt").exists()


def test_vm_not_running_is_a_clear_error(tmp_path):
    runner = LimaTrialRunner(local_root=tmp_path, run=FakeLima(status="Stopped"))
    with pytest.raises(TrialError, match="limactl start"):
        runner.run("md-tables", _skill(tmp_path), AuditLog())


def test_sandbox_failure_surfaces(tmp_path):
    runner = LimaTrialRunner(local_root=tmp_path, run=FakeLima(fail_on="demo_trial.sh"))
    with pytest.raises(TrialError, match="command failed"):
        runner.run("md-tables", _skill(tmp_path), AuditLog())


def test_rejects_non_skill_and_unsafe_names(tmp_path):
    runner = LimaTrialRunner(local_root=tmp_path, run=FakeLima())
    with pytest.raises(TrialError, match="SKILL.md"):
        runner.run("x", tmp_path, AuditLog())
    with pytest.raises(TrialError, match="unsafe"):
        runner.run("x", _skill(tmp_path, folder="bad;rm -rf"), AuditLog())


def test_captured_runner_is_option_a(tmp_path):
    with tarfile.open(fileobj=io.BytesIO(_packed_traces(FOLDER))) as tar:
        tar.extractall(tmp_path / "t", filter="data")
    trial = CapturedTraceRunner(tmp_path / "t", CANDIDATE_LABEL).run("md-tables", tmp_path / FOLDER, AuditLog())
    assert [r.mode for r in trial.runs] == ["direct", "instructed"]
    assert load_trial_runs(tmp_path / "t", "malware", FOLDER, ["direct"], AuditLog()).runs == []


def _installer(tmp_path, runner, intercept):
    signer = PluginSigner(ed25519.Ed25519PrivateKey.generate())
    registry = PluginRegistry(tmp_path / "registry.json")
    registry.register(signer.sign(PluginManifest(name="md-tables", version="1.0.0", description=DESC,
                                                 author="pub", plugin_type=PluginType.INTEGRATION)))
    return DivergencePluginInstaller(tmp_path / "plugins", registry, {"pub": signer.public_key},
                                     evaluator=evaluator(intercept=intercept), trial_runner=runner)


def test_request_install_runs_trial_then_escalates(tmp_path):
    # the fake calibrator's intercept forces FLAG / ALLOW; scoring itself is tested in test_evaluator
    inst = _installer(tmp_path, LimaTrialRunner(local_root=tmp_path / "trials", run=FakeLima()), intercept=50.0)
    with pytest.raises(DivergenceEscalation):
        inst.request_install("md-tables", _skill(tmp_path))
    assert inst.trials["md-tables"].runs and not (tmp_path / "plugins" / "md-tables").exists()
    events = [e["event_type"] for e in inst.audit_log.export()["entries"]]
    assert events[-1] == "divergence_assessment" and "divergence_assessment" not in events[:-1]
    inst.approve("md-tables", reviewer="did:dvg:reviewer")
    assert inst.install("md-tables").exists()
    assert inst.audit_log.verify_integrity()[0]


def test_request_install_allows_and_installs(tmp_path):
    inst = _installer(tmp_path, LimaTrialRunner(local_root=tmp_path / "trials", run=FakeLima()), intercept=-50.0)
    assert inst.request_install("md-tables", _skill(tmp_path)).exists()
    assert inst.assessments["md-tables"].verdict == "ALLOW"


def test_request_install_needs_runner_and_known_skill(tmp_path):
    with pytest.raises(MarketplaceError, match="trial_runner"):
        _installer(tmp_path / "a", None, 0.0).request_install("md-tables", _skill(tmp_path))
    fake = FakeLima()
    with pytest.raises(MarketplaceError):
        _installer(tmp_path / "b", LimaTrialRunner(run=fake), 0.0).request_install("unknown", _skill(tmp_path))
    assert fake.calls == []  # no sandbox run spent on an unregistered skill
