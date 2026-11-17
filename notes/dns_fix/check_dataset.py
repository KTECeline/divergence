"""Redo check: the regenerated dataset still has the locked shape, and AGT parity holds for every run.

Run from the repo root:  .venv/bin/python notes/dns_fix/check_dataset.py
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from agentmesh.governance.audit import AuditLog

from divergence.evaluator.agt_adapter import check_parity, record_trial
from divergence.preprocessing.normalise_trace import normalise

MODE_DIR = {"agent": "batch_out", "direct": "direct_out", "instructed": "instructed_out"}
rows = [json.loads(l) for l in open("data/processed/labelled_dataset.jsonl", encoding="utf-8")]
labels = collections.Counter(r["label"] for r in rows)
splits = collections.Counter((r["split"], r["label"]) for r in rows)
print(f"runs: {len(rows)}  POS {labels[1]}  NEG {labels[0]}   (locked: 308, POS 149, NEG 159)")
for s in ("finetune", "calibration", "held_out_test"):
    print(f"  {s:14} POS {splits[(s, 1)]:3}  NEG {splits[(s, 0)]:3}")

stale = bad = 0
for r in rows:
    res = json.loads((Path("data/raw/traces") / MODE_DIR[r["mode"]] / "results" / f"{r['sample_id']}.json").read_text())
    stale += normalise(res) != r["trace"]
    entries, os_events = record_trial(AuditLog(), "did:dvg:check", res)
    ok, msg = check_parity(res, entries, os_events)
    if not ok:
        bad += 1
        print("  parity FAILED:", r["sample_id"], r["mode"], msg)
print(f"stored trace != normalise(raw): {stale}   (must be 0)")
print(f"AGT parity failures: {bad}   (must be 0)")
ok = len(rows) == 308 and labels[1] == 149 and labels[0] == 159 and stale == 0 and bad == 0
print("OK" if ok else "NOT OK")
sys.exit(0 if ok else 1)
