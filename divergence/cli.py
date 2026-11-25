"""`divergence` command line: the plugin's two ways in.

  divergence evaluate   bring your own trace: score a skill description against a
                        trace you already have (no sandbox, nothing executed)
  divergence install    Option B: one install request -> sandbox trial -> Divergence
                        -> AGT install, or escalate to a human
  divergence setup-sandbox   one time: build the sealed Lima VM that `install` runs
                        skills in (needs Lima and an OpenRouter key)

Examples:
  divergence evaluate --skill-md path/to/SKILL.md --trace run.json
  divergence evaluate --description "Formats markdown tables" --trace agt_audit_log.json \\
                      --os-events os_events.json
  divergence setup-sandbox                                # once; 10 to 20 minutes
  divergence install --skill-dir path/to/skill            # needs the Lima sandbox
  divergence install --skill-dir path/to/skill --traces-root captured/   # trials captured earlier

`--trace` accepts: a raw sandbox run result (what the trial runners write), an
exported AGT AuditLog ({"entries": [...]}), a list of AGT audit entries, or an
already-normalised Divergence trace.

Exit codes (1 means FLAG and nothing else, so a script can rely on it):
  0  ALLOW / installed
  1  FLAG / blocked (evaluate: only with --fail-on-flag)
  2  invalid input: a trace, description or argument that cannot be read. No verdict.
  3  the sandbox trial failed or produced no run (timeout, or the agent's LLM calls
     failed: bad key, no credit), or setup-sandbox failed. No verdict.
  4  the trained model wasn't found
  5  unexpected error. No verdict. (DIVERGENCE_DEBUG=1 shows the traceback.)
  6  install only: blocked by AGT's own install checks (signature, dependencies,
     restricted imports), whatever Divergence said. AGT's reason is printed.

A run with no observable actions is announced first, before the verdict: nothing
was observed during the trial, which is not evidence the skill is safe.

An unreadable trace is an error, never an ALLOW: a pre-install check must not pass
a skill because its evidence could not be read.
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

EXIT_OK, EXIT_FLAG, EXIT_INPUT, EXIT_TRIAL, EXIT_MODEL, EXIT_ERROR, EXIT_AGT = 0, 1, 2, 3, 4, 5, 6
NOTHING_OBSERVED = "nothing was observed during the trial; this is not evidence the skill is safe"
# what marks a JSON object as a raw sandbox run result (the trial runners' output)
RAW_RESULT_KEYS = ("agent_json", "process_events", "file_events", "network_events")


class InputError(Exception):
    """Something the user passed cannot be used; reported in one line with exit code 2."""


def plugin_name(folder: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", folder)


def _read_text(path: Path, what: str, errors: str = "strict") -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors=errors)
    except FileNotFoundError:
        raise InputError(f"{what} not found: {path}") from None
    except (OSError, UnicodeDecodeError) as e:
        raise InputError(f"cannot read {what} {path}: {e}") from None


def _read_json(path: Path, what: str):
    text = _read_text(path, what)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise InputError(f"{what} {path} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})") from None


def _skill_description(skill_md: Path) -> str:
    from divergence.data.loader import parse_skill_md
    _, description, _, _ = parse_skill_md(_read_text(skill_md, "SKILL.md", errors="replace"))
    if not description.strip():
        raise InputError(f"{skill_md} has no description to compare the behaviour against")
    return description


def _description(args) -> str:
    if args.description is None:
        return _skill_description(args.skill_md)
    if not args.description.strip():
        raise InputError("--description is empty: there is nothing to compare the behaviour against")
    return args.description


def _check_raw_result(data: dict, path: Path) -> None:
    if data.get("agent_json") is not None and not isinstance(data["agent_json"], dict):
        raise InputError(f"trace file {path}: 'agent_json' must be an object, got {type(data['agent_json']).__name__}")
    for key in RAW_RESULT_KEYS[1:]:
        events = data.get(key)
        if events is not None and not (isinstance(events, list) and all(isinstance(e, dict) for e in events)):
            raise InputError(f"trace file {path}: '{key}' must be a list of objects")


def load_trace(path: Path) -> list:
    """Any supported trace file -> something DivergenceEvaluator.evaluate() accepts.

    Raises InputError for a file that is missing, is not JSON, or is JSON of no known
    trace shape. The entries themselves are checked by the evaluator's adapter
    (TraceFormatError), which also covers traces passed in from Python.
    """
    from divergence.evaluator.trial_runner import run_failure
    from divergence.preprocessing.normalise_trace import normalise
    data = _read_json(path, "trace file")
    if isinstance(data, dict) and "entries" in data:  # AuditLog.export()
        if not isinstance(data["entries"], list):
            raise InputError(f"trace file {path}: 'entries' must be a list, got {type(data['entries']).__name__}")
        return data["entries"]
    if isinstance(data, dict):  # raw sandbox run result (agent_json / process_events / ...)
        if not any(k in data for k in RAW_RESULT_KEYS):
            raise InputError(f"trace file {path}: the JSON object is neither an AGT AuditLog export (no 'entries') "
                             f"nor a sandbox run result (none of {', '.join(RAW_RESULT_KEYS)})")
        _check_raw_result(data, path)
        failure = run_failure(data)
        if failure:
            raise InputError(f"trace file {path} is not usable evidence: {failure}")
        try:
            return normalise(data)
        except Exception as e:  # a result file whose inner structure is not the sandbox's
            raise InputError(f"trace file {path}: not a readable sandbox run result "
                             f"({type(e).__name__}: {e})") from None
    if isinstance(data, list):  # AGT entries or a normalised trace (the evaluator tells them apart)
        return data
    raise InputError(f"trace file {path}: expected a JSON list or object, got {type(data).__name__}")


def _nothing_observed(result) -> bool:
    from divergence.evaluator.divergence_evaluator import EMPTY_TRACE_TEXT
    return result.trace_text == EMPTY_TRACE_TEXT


def _fresh_run_dir(out_root: Path, name: str) -> Path:
    """A new folder for this install run. The name is stamped to the second, so a
    second run of the same skill within that second gets a -2, -3, ... suffix."""
    base = f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
    for n in range(1, 1000):
        run_dir = out_root / (base if n == 1 else f"{base}-{n}")
        try:
            run_dir.mkdir(parents=True)
            return run_dir
        except FileExistsError:
            continue
    raise InputError(f"could not create a new run folder under {out_root}")


def cmd_evaluate(args) -> int:
    from divergence.evaluator.divergence_evaluator import DivergenceEvaluator
    description, trace = _description(args), load_trace(args.trace)   # bad input fails before the model loads
    os_events = _read_json(args.os_events, "OS events file") if args.os_events else None
    if os_events is not None and not isinstance(os_events, list):
        raise InputError(f"OS events file {args.os_events}: expected a JSON list, got {type(os_events).__name__}")
    result = DivergenceEvaluator().evaluate(description, trace, os_events)
    if _nothing_observed(result):  # said first, before any verdict; with --json on stderr so stdout stays JSON
        print(f"NOTICE: {NOTHING_OBSERVED}\n", file=sys.stderr if args.json else sys.stdout)
    print(result.to_json() if args.json else result.reasoning)
    return EXIT_FLAG if (args.fail_on_flag and result.verdict == "FLAG") else EXIT_OK


def cmd_install(args) -> int:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from agentmesh.exceptions import MarketplaceError as AgentMeshMarketplaceError
    from agentmesh.marketplace import MarketplaceError
    from agentmesh.marketplace.manifest import PluginManifest, PluginType
    from agentmesh.marketplace.registry import PluginRegistry
    from agentmesh.marketplace.signing import PluginSigner

    from divergence.config import RESULTS_DIR, IS_DEV_CHECKOUT, SKILLS_DIR
    from divergence.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller
    from divergence.evaluator.trial_runner import CapturedTraceRunner, LimaTrialRunner, TrialError

    if args.skill:  # <label>/<folder> shorthand: MalSkillBench in the research repo only
        if not IS_DEV_CHECKOUT:
            raise InputError("--skill needs the research repo's MalSkillBench copy; use --skill-dir")
        skill_dir = SKILLS_DIR / args.skill
    else:
        skill_dir = Path(args.skill_dir).resolve()
    if not (skill_dir / "SKILL.md").is_file():
        raise InputError(f"no SKILL.md in {skill_dir}")
    description = _skill_description(skill_dir / "SKILL.md")
    name = plugin_name(skill_dir.name)

    if args.traces_root:
        label = args.label or (args.skill.split("/", 1)[0] if args.skill else "candidate")
        runner = CapturedTraceRunner(args.traces_root, label, with_agent=args.with_agent)
    else:
        runner = LimaTrialRunner(args.vm, with_agent=args.with_agent)

    out_root = Path(args.out) if args.out else (RESULTS_DIR / "install" if IS_DEV_CHECKOUT else Path("divergence_installs"))
    run_dir = _fresh_run_dir(out_root, name)
    (run_dir / "plugins").mkdir()
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
    t0, code, shown = time.monotonic(), EXIT_OK, False

    def show(assessment) -> None:
        nonlocal shown
        if shown:
            return
        shown = True
        for mode, r in assessment.runs.items():  # said first, before any verdict
            if _nothing_observed(r):
                print(f"NOTICE ({mode} run): {NOTHING_OBSERVED}")
        print(assessment.summary())

    try:
        try:
            path = installer.request_install(name, skill_dir)
            show(installer.assessments[name])
            outcome = f"INSTALLED by AGT -> {path}"
        except DivergenceEscalation as e:
            show(e.assessment)
            outcome, code = "BLOCKED: escalated to a human reviewer (AGT decision: escalate)", EXIT_FLAG
            if args.approve:
                installer.approve(name, reviewer="did:dvg:reviewer:demo")
                outcome += f" -> approved -> INSTALLED by AGT -> {installer.install(name)}"
                code = EXIT_OK
    except TrialError as e:
        print(f"divergence: sandbox trial failed: {e}", file=sys.stderr)
        return EXIT_TRIAL
    except (MarketplaceError, AgentMeshMarketplaceError) as e:
        # AGT's own install checks refused the skill (signature, dependencies, restricted imports).
        # An expected outcome of an installer, and not Divergence's verdict: its own exit code.
        print(f"divergence: blocked by AGT: {e}", file=sys.stderr)
        if name not in installer.assessments:
            return EXIT_AGT
        verdict = installer.assessments[name].verdict
        show(installer.assessments[name])
        outcome, code = f"BLOCKED by AGT: {e} (Divergence verdict: {verdict})", EXIT_AGT

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


def cmd_setup_sandbox(args) -> int:
    """Run the bundled sandbox/setup_sandbox.sh; it talks to the terminal itself (hidden key prompt)."""
    import shutil
    import subprocess

    from divergence.sandbox_files import setup_script
    script = setup_script()
    if not script.is_file():
        raise InputError(f"sandbox setup script not found at {script}: reinstall divergence-agt")
    if shutil.which("bash") is None:
        raise InputError("bash not found: the sandbox setup needs macOS or Linux")
    argv = ["bash", str(script), "--vm", args.vm]
    if args.check:
        argv.append("--check")
    if args.rekey:
        argv.append("--rekey")
    rc = subprocess.run(argv).returncode  # inherits stdin/stdout so the key prompt works
    if rc != 0:
        print(f"divergence: sandbox setup failed (exit {rc}); re-run it to resume, finished steps are skipped",
              file=sys.stderr)
        return EXIT_TRIAL
    return EXIT_OK


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

    st = sub.add_parser("setup-sandbox", help="one time: build the sealed Lima VM that `install` uses")
    st.add_argument("--vm", default="dvg-lab", help="name of the Lima VM to create or check")
    st.add_argument("--check", action="store_true", help="only re-run the isolation checks")
    st.add_argument("--rekey", action="store_true", help="replace the OpenRouter key held by the proxy")
    st.set_defaults(func=cmd_setup_sandbox)
    return ap


def main(argv: list[str] | None = None) -> int:
    from divergence.evaluator.agt_adapter import TraceFormatError
    from divergence.model_store import ModelNotFound
    args = build_parser().parse_args(argv)  # argparse itself exits 2 on bad arguments
    try:
        return args.func(args)
    except ModelNotFound as e:
        print(f"divergence: model not found: {e}", file=sys.stderr)
        return EXIT_MODEL
    except InputError as e:
        print(f"divergence: invalid input: {e}", file=sys.stderr)
        return EXIT_INPUT
    except TraceFormatError as e:
        print(f"divergence: invalid input: trace is not readable, nothing was scored: {e}", file=sys.stderr)
        return EXIT_INPUT
    except Exception as e:  # never let a crash exit 1: that code means FLAG
        if os.environ.get("DIVERGENCE_DEBUG"):
            raise
        print(f"divergence: unexpected error, no verdict was produced ({type(e).__name__}: {e}). "
              "Set DIVERGENCE_DEBUG=1 for the traceback.", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
