import json, sys, collections
from pathlib import Path
sys.path.insert(0, "."); sys.path.insert(0, sys.argv[1])
import divergence.preprocessing.normalise_trace as nt
from dns_impact_lib import patched, orig
from divergence.evaluator.divergence_evaluator import DivergenceEvaluator
ev = DivergenceEvaluator()
MODE_DIR = {"agent": "batch_out", "direct": "direct_out", "instructed": "instructed_out"}
rows = [json.loads(l) for l in open("data/processed/labelled_dataset.jsonl")]
for split in ("held_out_test", "calibration", "finetune"):
    cm = {"old": collections.Counter(), "new": collections.Counter()}; flips = []
    for r in rows:
        if r["split"] != split: continue
        res = json.loads((Path("data/raw/traces") / MODE_DIR[r["mode"]] / "results" / f"{r['sample_id']}.json").read_text())
        nt._os_events = patched; new = nt.normalise(res); nt._os_events = orig
        vo = ev.evaluate(r["description"], r["trace"]).verdict
        vn = ev.evaluate(r["description"], new).verdict
        for k, v in (("old", vo), ("new", vn)):
            cm[k][("TP" if v == "FLAG" else "FN") if r["label"] else ("FP" if v == "FLAG" else "TN")] += 1
        if vo != vn: flips.append((r["sample_id"], r["mode"], r["label"], vo, "->", vn))
    print(f"== {split}: old {dict(cm['old'])}  new {dict(cm['new'])}")
    for f in flips: print("   ", f)
