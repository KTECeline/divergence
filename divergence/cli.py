"""`divergence` command line: the plugin's two ways in.

  divergence evaluate   bring your own trace: score a skill description against a
                        trace you already have (no sandbox, nothing executed)
  divergence install    Option B: one install request -> sandbox trial -> Divergence
                        -> AGT install, or escalate to a human

Examples:
  divergence evaluate --skill-md path/to/SKILL.md --trace run.json
  divergence evaluate --description "Formats markdown tables" --trace agt_audit_log.json \\
                      --os-events os_events.json
  divergence install --skill-dir path/to/skill            # needs the Lima sandbox
  divergence install --skill-dir path/to/skill --traces-root captured/   # trials captured earlier

`--trace` accepts: a raw sandbox run result (what the trial runners write), an
exported AGT AuditLog ({"entries": [...]}), a list of AGT audit entries, or an
already-normalised Divergence trace.

Exit codes: 0 = ALLOW / installed, 1 = FLAG / blocked (evaluate: only with
--fail-on-flag), 3 = the sandbox trial failed, 4 = the trained model wasn't found.
"""

import argparse
import json
import re
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)


def plugin_name(folder: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", folder)


def _description(args) -> str:
    from divergence.data.loader import parse_skill_md
    if args.description:
        return args.description
    _, description, _, _ = parse_skill_md(Path(args.skill_md).read_text(encoding="utf-8", errors="replace"))
    return description


def load_trace(path: Path) -> list:
    """Any supported trace file -> something DivergenceEvaluator.evaluate() accepts."""
    from divergence.preprocessing.normalise_trace import normalise
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "entries" in data:  # AuditLog.export()
        return data["entries"]
    if isinstance(data, dict):  # raw sandbox run result (agent_json / process_events / ...)
        return normalise(data)
    if isinstance(data, list):  # AGT entries or a normalised trace (the evaluator tells them apart)
        return data
    raise SystemExit(f"unsupported trace file: {path}")


def cmd_evaluate(args) -> int:
    from divergence.evaluator.divergence_evaluator import DivergenceEvaluator
    os_events = json.loads(Path(args.os_events).read_text()) if args.os_events else None
    result = DivergenceEvaluator().evaluate(_description(args), load_trace(args.trace), os_events)
    print(result.to_json() if args.json else result.reasoning)
    return 1 if (args.fail_on_flag and result.verdict == "FLAG") else 0


def cmd_install(args) -> int:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from agentmesh.marketplace.manifest import PluginManifest, PluginType
    from agentmesh.marketplace.registry import PluginRegistry
    from agentmesh.marketplace.signing import PluginSigner

    from divergence.config import RESULTS_DIR, IS_DEV_CHECKOUT, SKILLS_DIR
    from divergence.data.loader import parse_skill_md
    from divergence.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller
    from divergence.evaluator.trial_runner import CapturedTraceRunner, LimaTrialRunner, TrialError

    if args.skill:  # <label>/<folder> shorthand: MalSkillBench in the research repo only
        if not IS_DEV_CHECKOUT:
            raise SystemExit("--skill needs the research repo's MalSkillBench copy; use --skill-dir")
        skill_dir = SKILLS_DIR / args.skill
    else:
        skill_dir = Path(args.skill_dir).resolve()
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"no SKILL.md in {skill_dir}")
    _, description, _, _ = parse_skill_md((skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
    name = plugin_name(skill_dir.name)

    if args.traces_root:
        label = args.label or (args.skill.split("/", 1)[0] if args.skill else "candidate")
        runner = CapturedTraceRunner(args.traces_root, label, with_agent=args.with_agent)
    else:
        runner = LimaTrialRunner(args.vm, with_agent=args.with_agent)

    out_root = Path(args.out) if args.out else (RESULTS_DIR / "install" if IS_DEV_CHECKOUT else Path("divergence_installs"))
    run_dir = out_root / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
    (run_dir / "plugins").mkdir(parents=True)
    # A fresh demo marketplace: in a real one the publisher signs the manifest; here a demo key does.
    author = "demo-publisher"
    registry = PluginRegistry(run_dir / "registry.json")
    signer = PluginSigner(ed25519.Ed25519PrivateKey.generate())
    registry.register(signer.sign(PluginManifest(name=name, version="1.0.0", description=description,
                                                 author=author, plugin_type=PluginType.INTEGRATION)))
    installer = DivergencePluginInstaller(run_dir / "plugins", registry, {author: signer.public_key},
                                          trial_runner=runner)

    print("=" * 100)
    print(f"install request: {name}\n  from: {skill_dir}\n  declared: {description[:160]}")
    print(f"  trial runner: {type(runner).__name__}"
          + ("" if args.traces_root else f" (VM {args.vm}; this takes a few minutes)"), flush=True)
    t0, code = time.monotonic(), 0
    try:
        path = installer.request_install(name, skill_dir)
        outcome = f"INSTALLED by AGT -> {path}"
        print(installer.assessments[name].summary())
    except DivergenceEscalation as e:
        print(e.assessment.summary())
        outcome, code = "BLOCKED: escalated to a human reviewer (AGT decision: escalate)", 1
        if args.approve:
            installer.approve(name, reviewer="did:dvg:reviewer:demo")
            outcome += f" -> approved -> INSTALLED by AGT -> {installer.install(name)}"
            code = 0
    except TrialError as e:
        print(f"sandbox trial failed: {e}", file=sys.stderr)
        return 3

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
    return code


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="divergence", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    ev = sub.add_parser("evaluate", help="score a description against a trace you already have")
    d = ev.add_mutually_exclusive_group(required=True)
    d.add_argument("--description", help="the skill's declared description")
    d.add_argument("--skill-md", type=Path, help="read the description from a SKILL.md")
    ev.add_argument("--trace", type=Path, required=True, help="trace file (see formats above)")
    ev.add_argument("--os-events", type=Path, help="sandbox OS events per AGT entry (with an AGT log)")
    ev.add_argument("--json", action="store_true", help="print the full result object as JSON")
    ev.add_argument("--fail-on-flag", action="store_true", help="exit code 1 on FLAG (for CI)")
    ev.set_defaults(func=cmd_evaluate)

    ins = sub.add_parser("install", help="Option B: sandbox trial -> Divergence -> AGT install / escalate")
    s = ins.add_mutually_exclusive_group(required=True)
    s.add_argument("--skill-dir", type=Path, help="a skill folder containing a SKILL.md")
    s.add_argument("--skill", help="<label>/<folder> inside MalSkillBench (research repo only)")
    ins.add_argument("--vm", default="dvg-lab", help="Lima VM that runs the sandbox")
    ins.add_argument("--with-agent", action="store_true", help="also run the aligned agent")
    ins.add_argument("--approve", action="store_true", help="show the human-approval path if flagged")
    ins.add_argument("--traces-root", type=Path, help="use trials captured earlier instead of the VM")
    ins.add_argument("--label", help="label folder under --traces-root (default: candidate)")
    ins.add_argument("--out", type=Path, help="where to write the report and AGT audit log")
    ins.set_defaults(func=cmd_install)
    return ap


def main(argv: list[str] | None = None) -> int:
    from divergence.model_store import ModelNotFound
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ModelNotFound as e:
        print(f"divergence: model not found: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
