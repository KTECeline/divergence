"""Option B: one install request -> sandbox trial -> Divergence -> AGT install / escalate.

    .venv/bin/python sandbox/install_skill.py --skill malware/<folder>
    .venv/bin/python sandbox/install_skill.py --skill-dir /path/to/any/skill-folder
    # options: --with-agent (aligned-agent run too, costs a little), --approve (human
    #          approval path for a flagged skill), --vm dvg-lab,
    #          --traces-root DIR (Option A: use trials captured earlier, no VM)

What happens, with nothing done by hand in the VM:
  1. The skill is published to a fresh AGT PluginRegistry as a signed manifest whose
     `description` is its SKILL.md description (AGT's signature check stays ON).
     In a real marketplace the publisher signs; here a demo publisher key does.
  2. installer.request_install() asks the trial runner for observed behaviour:
     LimaTrialRunner copies the skill into the sealed VM, runs sandbox/demo_trial.sh
     (same sandbox, images and runners as the dataset), copies the traces back.
  3. The trial's tool calls are recorded in AGT's Merkle-chained AuditLog, parity
     is checked against normalise(), and Divergence scores every run.
  4. FLAG -> DivergenceEscalation (AGT decision "escalate"), nothing is installed
     unless --approve; ALLOW -> AGT's own install checks run and the skill installs.

Needs: the dvg-lab VM running (`limactl start dvg-lab`) with ~/dvg set up as in
sandbox/setup_notes.md. The instructed run calls OpenRouter from inside the VM.
"""

import argparse
import json
import re
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore", category=DeprecationWarning)

from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402
from agentmesh.marketplace.manifest import PluginManifest, PluginType  # noqa: E402
from agentmesh.marketplace.registry import PluginRegistry  # noqa: E402
from agentmesh.marketplace.signing import PluginSigner  # noqa: E402

from src.config import RESULTS_DIR, SKILLS_DIR  # noqa: E402
from src.data.loader import parse_skill_md  # noqa: E402
from src.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller  # noqa: E402
from src.evaluator.trial_runner import CapturedTraceRunner, LimaTrialRunner, TrialError  # noqa: E402

AUTHOR = "demo-publisher"
OUT_DIR = RESULTS_DIR / "install"


def plugin_name(folder: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", folder)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--skill", help="<label>/<folder> inside MalSkillBench Dataset/Skills")
    src.add_argument("--skill-dir", type=Path, help="any skill folder containing a SKILL.md")
    ap.add_argument("--vm", default="dvg-lab")
    ap.add_argument("--with-agent", action="store_true", help="also run the aligned agent")
    ap.add_argument("--approve", action="store_true", help="show the human-approval path if flagged")
    ap.add_argument("--traces-root", type=Path,
                    help="Option A: read trials captured earlier from here instead of running the VM")
    args = ap.parse_args()

    skill_dir = (SKILLS_DIR / args.skill) if args.skill else args.skill_dir.resolve()
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"no SKILL.md in {skill_dir}")
    _, description, _, _ = parse_skill_md((skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
    name = plugin_name(skill_dir.name)

    if args.traces_root:
        label = args.skill.split("/", 1)[0] if args.skill else "candidate"
        runner = CapturedTraceRunner(args.traces_root, label, with_agent=args.with_agent)
    else:
        runner = LimaTrialRunner(args.vm, with_agent=args.with_agent)

    run_dir = OUT_DIR / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
    (run_dir / "plugins").mkdir(parents=True)
    registry = PluginRegistry(run_dir / "registry.json")
    signer = PluginSigner(ed25519.Ed25519PrivateKey.generate())
    registry.register(signer.sign(PluginManifest(name=name, version="1.0.0", description=description,
                                                 author=AUTHOR, plugin_type=PluginType.INTEGRATION)))
    installer = DivergencePluginInstaller(run_dir / "plugins", registry, {AUTHOR: signer.public_key},
                                          trial_runner=runner)

    print("=" * 100)
    print(f"install request: {name}\n  from: {skill_dir}\n  declared: {description[:160]}")
    print(f"  trial runner: {type(runner).__name__}"
          + ("" if args.traces_root else f" (VM {args.vm}; this takes a few minutes)"), flush=True)
    t0 = time.monotonic()
    try:
        path = installer.request_install(name, skill_dir)
        outcome = f"INSTALLED by AGT -> {path}"
    except DivergenceEscalation as e:
        print(e.assessment.summary())
        outcome = "BLOCKED: escalated to a human reviewer (AGT decision: escalate)"
        if args.approve:
            installer.approve(name, reviewer="did:dvg:reviewer:demo")
            outcome += f" -> approved -> INSTALLED by AGT -> {installer.install(name)}"
    except TrialError as e:
        raise SystemExit(f"sandbox trial failed: {e}")
    else:
        print(installer.assessments[name].summary())

    trial = installer.trials.get(name)
    print(f"\n  trial runs: {', '.join(r.mode for r in trial.runs)}   parity: {trial.parity}"
          f"   ({time.monotonic() - t0:.0f}s, traces in {trial.traces_root})")
    print(f"\n>>> {outcome}")

    ok, err = installer.audit_log.verify_integrity()
    export = installer.audit_log.export()
    print(f"AGT audit log: {export['entry_count']} entries, Merkle chain valid: {ok}{'' if ok else ' ' + str(err)}")
    report = {"skill": name, "skill_dir": str(skill_dir), "outcome": outcome, "parity": trial.parity,
              "traces_root": str(trial.traces_root), **installer.assessments[name].to_agt_evidence()}
    (run_dir / "install_report.json").write_text(json.dumps(report, indent=1))
    (run_dir / "agt_audit_log.json").write_text(json.dumps(export, default=str, indent=1))
    print(f"saved {run_dir}/install_report.json and agt_audit_log.json")


if __name__ == "__main__":
    main()
