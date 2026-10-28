"""Experiment 1d: capability-overlap baseline on the locked test split.

Adds src/baselines/capability_overlap.py to the Exp 1 comparison: same test
runs, same metrics, group-bootstrap CI and McNemar vs Divergence (read from
results/exp1_predictions.csv, so the main model is not re-scored). Nothing is
fitted, so nothing can be tuned on the test split. Also reports AUC within
each mode, as Exp 1 does, to remove the mode confound.

Writes results/exp1_capability_overlap.csv.
"""

import numpy as np
import pandas as pd

from src.baselines import capability_overlap
from src.config import RESULTS_DIR
from src.data.merge_labels import load_labelled_dataset
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, paired_auc_delta_ci, point_metrics
from src.experiments.exp1_baseline_comparison import MAIN

NAME = "Capability overlap (declared vs observed)"


def main() -> None:
    test = load_labelled_dataset(("held_out_test",))
    keys = [(r["sample_id"], r["mode"]) for r in test]
    e1 = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv").set_index(["sample_id", "mode"]).loc[keys]
    y, groups, modes = e1["label"].values, e1["group"].values, e1.index.get_level_values("mode")
    s = np.array([capability_overlap.score(r) for r in test])
    v = np.array([capability_overlap.predict(r) for r in test])

    rows = []
    for name, score, verdict in ((MAIN, e1[f"{MAIN}|score"].values, e1[f"{MAIN}|verdict"].values), (NAME, s, v)):
        m = point_metrics(y, score, verdict)
        ci = group_bootstrap_ci(y, score, verdict, groups)
        row = {"system": name, **m, "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1],
               **{f"AUC_{md}": point_metrics(y[modes == md], score[modes == md], verdict[modes == md])["AUC"]
                  for md in ("direct", "instructed")}}
        if name == NAME:
            t = mcnemar_test(y, e1[f"{MAIN}|verdict"].values, verdict)
            d, lo, hi = paired_auc_delta_ci(y, s, e1[f"{MAIN}|score"].values, groups)
            row.update({"divergence_right_only": t["A_right_B_wrong"], "baseline_right_only": t["A_wrong_B_right"],
                        "mcnemar_p": t["p_value"], "divergence_AUC_gain": d, "gain_lo": lo, "gain_hi": hi})
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS_DIR / "exp1_capability_overlap.csv", index=False)
    print(out.round(3).T.to_string())


if __name__ == "__main__":
    main()
