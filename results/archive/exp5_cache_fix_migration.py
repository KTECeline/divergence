"""One-off, run once on 2026-11-14: re-key the qwen2.5:7b judge answers of Exp 5's controls.

Old key: `sample_id|mode|swap` / `sample_id|mode|disclosed` (no description, the bug).
New key: exp5_control_experiments.judge_key, which ends in a hash of the description.

An old answer is copied to its new key ONLY for the description it was really given for:
  * the 19 benign runs' `|swap` answers were given for the "5b swapped (benign skills)"
    descriptions (that set is judged first; the cache file's order confirms it);
  * the other 43 negative runs' `|swap` answers, for the "all negative runs" descriptions;
  * the 55 `|disclosed` answers, for the disclosed descriptions.
The 19 benign runs under their "all negative runs" donor description get NO entry, so
the next Exp 5 run asks the judge about them for the first time. Old lines are kept;
nothing reads those keys any more. No model is called here.

    python results/archive/exp5_cache_fix_migration.py
"""

import json

from divergence.baselines.llm_as_judge import CACHE_DIR
from divergence.config import RANDOM_SEED
from divergence.data.control_sets import build_disclosed_payload_set, build_swapped_description_set
from divergence.experiments.exp5_control_experiments import JUDGE, judge_key
from divergence.labelling.merge_labels import load_labelled_dataset

path = CACHE_DIR / "qwen2.5_7b.jsonl"
records = {}
for line in path.read_text(encoding="utf-8").splitlines():
    rec = json.loads(line)
    records[rec["key"]] = rec

test = load_labelled_dataset(("held_out_test",))
benign = [r for r in test if r["dataset_label"] == 0]
negatives = [r for r in test if r["label"] == 0]
pairs = [(r, "swap") for r in build_swapped_description_set(benign, RANDOM_SEED)]
pairs += [(r, "swap") for r in build_swapped_description_set(negatives, RANDOM_SEED) if r["dataset_label"] == 1]
pairs += [(r, "disclosed") for r in build_disclosed_payload_set(test)]

added = 0
with open(path, "a", encoding="utf-8") as f:
    for r, tag in pairs:
        old, new = f"{r['sample_id']}|{r['mode']}|{tag}", judge_key(r, tag)
        if new in records:
            continue
        src = records[old]
        assert src["model"] == JUDGE
        rec = {"key": new, "model": src["model"], "prompt_version": src["prompt_version"], "raw": src["raw"],
               "migrated_from": old}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        records[new] = rec
        added += 1
print(f"{added} answers re-keyed ({len(pairs)} description-verified pairs); "
      f"{len(negatives) - len(pairs) + len(benign) + len([r for r in test if r['label'] == 1])} left for the judge")
