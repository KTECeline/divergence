"""Experiment 7 live demo: Divergence as a pre-install check inside AGT's marketplace.

For each skill:
  1. The skill is published to an AGT PluginRegistry as a signed manifest whose
     `description` is the SKILL.md description (AGT's signature check stays ON).
  2. Its sandbox trial runs are read: direct (if the skill ships scripts) and
     instructed, plus agent with --with-agent. They come from the SAME sandbox
     and runners as the dataset (sandbox/demo_trial.sh captures new ones in the VM).
  3. Each run's tool calls are recorded in AGT's Merkle-chained AuditLog; the
     sandbox's OS events are attributed to them (agt_adapter.record_trial).
  4. Parity check: the trace rebuilt from AGT's log must equal the dataset's
     normalise() trace, i.e. the evaluator sees exactly what it was trained on.
  5. DivergencePluginInstaller.assess() scores every run; FLAG if any run flags.
  6. install(): a FLAG stops the install (DivergenceEscalation, AGT decision
     "escalate") until a human approves; an ALLOW proceeds to AGT's own checks.

Run on the Mac (models + AGT live in .venv):
    .venv/bin/python sandbox/demo_pipeline.py --skill malware/<folder> --skill benign/<folder>
    # fresh VM captures copied to data/raw/traces/demo/:
    .venv/bin/python sandbox/demo_pipeline.py --traces-root data/raw/traces/demo --skill malware/<folder>
"""

import argparse
import json
import re
import shutil
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore", category=DeprecationWarning)

from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402
from agentmesh.governance.audit import AuditLog  # noqa: E402
from agentmesh.marketplace.manifest import PluginManifest, PluginType  # noqa: E402
from agentmesh.marketplace.registry import PluginRegistry  # noqa: E402
from agentmesh.marketplace.signing import PluginSigner  # noqa: E402

from src.config import DATA_DIR, RESULTS_DIR, SKILLS_DIR  # noqa: E402
from src.data.loader import parse_skill_md  # noqa: E402
from src.evaluator.agt_adapter import check_parity, record_trial  # noqa: E402
from src.evaluator.agt_installer import DivergenceEscalation, DivergencePluginInstaller, TrialRun  # noqa: E402

MODE_DIRS = {"direct": "direct_out", "instructed": "instructed_out", "agent": "batch_out"}
AUTHOR = "demo-publisher"
DEMO_DIR = RESULTS_DIR / "demo"


def plugin_name(folder: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", folder)


def trial_runs(traces_root: Path, label: str, folder: str, modes: list[str], audit_log: AuditLog):
    """TrialRuns for every mode that has a captured result, after the parity check."""
    runs, parity = [], {}
    for mode in modes:
        f = traces_root / MODE_DIRS[mode] / "results" / label / f"{folder}.json"
        if not f.exists():
            continue
        result = json.loads(f.read_text(encoding="utf-8"))
        entries, os_events = record_trial(audit_log, f"did:dvg:trial:{mode}:{plugin_name(folder)}", result,
                                          trace_id=f"{label}/{folder}/{mode}")
        ok, msg = check_parity(result, entries, os_events)
        parity[mode] = msg
        if not ok:
            raise SystemExit(f"PARITY FAILED for {label}/{folder} [{mode}]: {msg}")
        runs.append(TrialRun(mode, entries, os_events))
    return runs, parity


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", action="append", required=True, help="<label>/<folder>, repeatable")
    ap.add_argument("--traces-root", type=Path, default=DATA_DIR / "raw" / "traces")
    ap.add_argument("--with-agent", action="store_true", help="also use the aligned-agent run if captured")
    ap.add_argument("--approve", action="store_true", help="show the human-approval path for flagged skills")
    args = ap.parse_args()
    modes = ["direct", "instructed"] + (["agent"] if args.with_agent else [])

    # a fresh marketplace for the demo: registry, publisher key, plugin directory
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    (DEMO_DIR / "plugins").mkdir(parents=True)
    registry = PluginRegistry(DEMO_DIR / "registry.json")
    signer = PluginSigner(ed25519.Ed25519PrivateKey.generate())
    audit_log = AuditLog()
    # one AuditLog for the trial runs AND the installer's decisions, so the exported chain holds both
    installer = DivergencePluginInstaller(DEMO_DIR / "plugins", registry, {AUTHOR: signer.public_key},
                                          audit_log=audit_log)

    report = {}
    for sid in args.skill:
        label, folder = sid.split("/", 1)
        _, description, _, _ = parse_skill_md((SKILLS_DIR / label / folder / "SKILL.md").read_text(
            encoding="utf-8", errors="replace"))
        name = plugin_name(folder)
        registry.register(signer.sign(PluginManifest(name=name, version="1.0.0", description=description,
                                                     author=AUTHOR, plugin_type=PluginType.INTEGRATION)))
        runs, parity = trial_runs(args.traces_root, label, folder, modes, audit_log)
        print("=" * 100)
        print(f"{sid}\n  declared: {description[:160]}")
        print(f"  trial runs: {', '.join(r.mode for r in runs) or 'none'}   parity: {parity}")
        if not runs:
            print("  no captured trial runs: run sandbox/demo_trial.sh in the VM first")
            continue
        assessment = installer.assess(name, runs)
        print(assessment.summary())
        try:
            path = installer.install(name)
            outcome = f"INSTALLED by AGT -> {path.relative_to(DEMO_DIR.parent.parent)}"
        except DivergenceEscalation:
            outcome = "BLOCKED: escalated to a human reviewer (AGT decision: escalate)"
            if args.approve:
                installer.approve(name, reviewer="did:dvg:reviewer:demo")
                path = installer.install(name)
                outcome += f" -> approved -> INSTALLED by AGT -> {path.relative_to(DEMO_DIR.parent.parent)}"
        print(f"\n>>> {outcome}")
        report[sid] = {"parity": parity, "outcome": outcome, **assessment.to_agt_evidence()}

    ok, err = audit_log.verify_integrity()
    export = audit_log.export()
    print("=" * 100)
    print(f"AGT audit log: {export['entry_count']} entries, Merkle chain valid: {ok}{'' if ok else ' ' + str(err)}")
    (DEMO_DIR / "demo_report.json").write_text(json.dumps(report, indent=1))
    (DEMO_DIR / "agt_audit_log.json").write_text(json.dumps(export, default=str, indent=1))
    print(f"saved {DEMO_DIR.relative_to(DEMO_DIR.parent.parent)}/demo_report.json and agt_audit_log.json")


if __name__ == "__main__":
    main()
