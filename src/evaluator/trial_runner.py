"""Trial runners: get the observed behaviour Divergence needs BEFORE a skill is installed.

A brand-new skill has never run, so it has no trace. A trial runner executes the
skill in an isolated sandbox, captures its trace, and hands it back as TrialRuns
recorded in AGT's AuditLog. DivergencePluginInstaller.request_install() calls one,
so a single install request goes: trial run -> trace -> Divergence -> ALLOW / ESCALATE.

Two runners share the same interface, `run(name, skill_dir, audit_log) -> Trial`:

  LimaTrialRunner      Option B. Drives the sealed Lima VM from the Mac: copies the
                       skill in, runs sandbox/demo_trial.sh (the SAME sandbox, images
                       and runners that built the dataset), copies the traces back.
  CapturedTraceRunner  Option A / "bring your own trace". Reads trial runs that were
                       already captured (e.g. by running demo_trial.sh by hand).

Both turn the raw runner output into TrialRuns the same way (load_trial_runs):
AGT AuditLog entries + strace OS events, with the parity check that the trace
rebuilt from AGT's log equals the dataset's normalise() trace.

Limits (stated, not hidden): only behaviour that fires during the trial is seen
(time bombs / trigger-gated payloads are missed); an empty trace means "nothing
observed", not "safe"; the instructed mode calls an LLM and costs a little.
"""

import json
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.config import DATA_DIR, PROJECT_ROOT
from src.evaluator.agt_adapter import check_parity, record_trial
from src.evaluator.agt_installer import TrialRun

MODE_DIRS = {"direct": "direct_out", "instructed": "instructed_out", "agent": "batch_out"}
CANDIDATE_LABEL = "candidate"  # skills under install review; never a dataset label
TRIALS_DIR = DATA_DIR / "raw" / "traces" / "trials"
DEMO_TRIAL_SH = PROJECT_ROOT / "sandbox" / "demo_trial.sh"


class TrialError(RuntimeError):
    """The sandbox trial could not be run or its output could not be read."""


@dataclass
class Trial:
    runs: list[TrialRun]
    parity: dict[str, str] = field(default_factory=dict)  # mode -> parity message
    traces_root: Path | None = None                       # where the raw runner output lives
    log: str = ""                                         # sandbox console output


def load_trial_runs(traces_root: Path, label: str, folder: str, modes: list[str], audit_log,
                    agent_name: str | None = None) -> Trial:
    """TrialRuns for every mode with a captured result, recorded in `audit_log`, parity-checked."""
    agent_name = agent_name or folder
    runs, parity = [], {}
    for mode in modes:
        f = Path(traces_root) / MODE_DIRS[mode] / "results" / label / f"{folder}.json"
        if not f.exists():
            continue
        result = json.loads(f.read_text(encoding="utf-8"))
        entries, os_events = record_trial(audit_log, f"did:dvg:trial:{mode}:{agent_name}", result,
                                          trace_id=f"{label}/{folder}/{mode}")
        ok, msg = check_parity(result, entries, os_events)
        if not ok:
            raise TrialError(f"parity failed for {label}/{folder} [{mode}]: {msg}")
        parity[mode] = msg
        runs.append(TrialRun(mode, entries, os_events))
    return Trial(runs, parity, Path(traces_root))


def _modes(with_agent: bool) -> list[str]:
    return ["direct", "instructed"] + (["agent"] if with_agent else [])


class CapturedTraceRunner:
    """Option A: trial runs already captured under `traces_root` (same layout as data/raw/traces/)."""

    def __init__(self, traces_root: Path, label: str, *, with_agent: bool = False):
        self.traces_root, self.label, self.with_agent = Path(traces_root), label, with_agent

    def run(self, name: str, skill_dir: Path, audit_log) -> Trial:
        return load_trial_runs(self.traces_root, self.label, Path(skill_dir).name,
                               _modes(self.with_agent), audit_log, agent_name=name)


class LimaTrialRunner:
    """Option B: run the skill's trial in the sealed Lima VM, automatically, per install request.

    Steps (all over Lima's SSH connection; the VM has no shared folders):
      1. pack the skill folder on the Mac
      2. copy it + the repo's demo_trial.sh into a fresh ~/dvg/trials/<id>/ in the VM
      3. unpack it as MalSkillBench/Dataset/Skills/candidate/<folder>, run demo_trial.sh
         with DVG_DEMO_OUT/DVG_DEMO_PACK pointing at the fresh trial folder
      4. copy the packed traces back to data/raw/traces/trials/<id>/ and load them
    """

    def __init__(self, vm: str = "dvg-lab", *, with_agent: bool = False, timeout_s: int = 1800,
                 local_root: Path = TRIALS_DIR, limactl: str = "limactl", run=subprocess.run):
        self.vm, self.with_agent, self.timeout_s = vm, with_agent, timeout_s
        self.local_root, self.limactl, self._run = Path(local_root), limactl, run

    # -- subprocess helpers ---------------------------------------------------------------
    def _call(self, args: list[str], timeout: int = 120) -> str:
        try:
            p = self._run(args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise TrialError(f"timed out after {timeout}s: {' '.join(args[:3])} ...") from e
        except FileNotFoundError as e:
            raise TrialError(f"{self.limactl} not found: Option B needs Lima and the dvg-lab VM") from e
        if p.returncode != 0:
            raise TrialError(f"command failed ({p.returncode}): {' '.join(args[:3])} ...\n"
                             f"{(p.stdout or '')[-2000:]}{(p.stderr or '')[-2000:]}")
        return p.stdout or ""

    def _shell(self, script: str, timeout: int = 120) -> str:
        return self._call([self.limactl, "shell", "--workdir", "/tmp", self.vm,
                           "bash", "-lc", script], timeout)

    def _copy(self, src: str, dst: str) -> None:
        self._call([self.limactl, "copy", src, dst], timeout=300)

    # -- the trial ------------------------------------------------------------------------
    def run(self, name: str, skill_dir: Path, audit_log) -> Trial:
        skill_dir = Path(skill_dir)
        if not (skill_dir / "SKILL.md").is_file():
            raise TrialError(f"{skill_dir} is not a skill folder (no SKILL.md)")
        folder = skill_dir.name
        if not re.fullmatch(r"[A-Za-z0-9._-]+", folder):
            raise TrialError(f"unsafe skill folder name: {folder!r}")
        trial_id = f"{folder}-{time.strftime('%Y%m%d-%H%M%S')}"

        status = self._call([self.limactl, "list", "--format", "{{.Status}}", self.vm]).strip()
        if status != "Running":
            raise TrialError(f"VM {self.vm} is {status or 'missing'}: start it with `limactl start {self.vm}`")
        home = self._shell('printf %s "$HOME"').strip()
        remote = f"{home}/dvg/trials/{trial_id}"
        skill_root = f"{home}/dvg/MalSkillBench/Dataset/Skills/{CANDIDATE_LABEL}/{folder}"

        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "skill.tgz"
            with tarfile.open(pkg, "w:gz") as tar:
                tar.add(skill_dir, arcname=".")
            self._shell(f"mkdir -p {shlex.quote(remote)}")
            self._copy(str(pkg), f"{self.vm}:{remote}/skill.tgz")
            self._copy(str(DEMO_TRIAL_SH), f"{self.vm}:{remote}/demo_trial.sh")

        q = shlex.quote
        script = "\n".join([
            "set -euo pipefail",
            f"rm -rf {q(skill_root)} && mkdir -p {q(skill_root)}",
            f"tar -xzf {q(remote + '/skill.tgz')} -C {q(skill_root)}",
            'source "$HOME/dvg/.venv/bin/activate"',
            'cd "$HOME/dvg/MalSkillBench"',
            f"DVG_DEMO_OUT={q(remote + '/out')} DVG_DEMO_PACK={q(remote + '/out.tgz')} "
            f"bash {q(remote + '/demo_trial.sh')} {q(CANDIDATE_LABEL + '/' + folder)}"
            + (" --with-agent" if self.with_agent else ""),
        ])
        log = self._shell(script, timeout=self.timeout_s)

        local = self.local_root / trial_id
        local.mkdir(parents=True, exist_ok=True)
        self._copy(f"{self.vm}:{remote}/out.tgz", str(local / "out.tgz"))
        with tarfile.open(local / "out.tgz") as tar:
            tar.extractall(local, filter="data")  # output came from a VM that ran untrusted code
        (local / "sandbox_log.txt").write_text(log, encoding="utf-8")

        trial = load_trial_runs(local, CANDIDATE_LABEL, folder, _modes(self.with_agent), audit_log,
                                agent_name=name)
        trial.log = log
        return trial
