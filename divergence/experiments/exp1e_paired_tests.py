"""Experiment 1e: paired significance tests on the Exp 1 test predictions.

Three follow-ups to Exp 1, read from results/exp1_predictions.csv (no model is
re-scored, refitted or tuned):

1. Paired PR-AUC (and ROC-AUC) difference, Divergence minus each comparison
   system, with a group-bootstrap 95% interval. Single-system intervals that
   overlap can still hide a consistent paired gain; this tests the gain itself.
2. False alarms on the negative (label 0) runs only: the false-alarm-rate
   difference with a group-bootstrap interval, plus exact McNemar on the
   negatives' paired verdicts. McNemar treats runs as independent although
   modes of one skill share a group, so the bootstrap interval is the primary
   result and McNemar is reported alongside it.
3. The same pair of tests on the positive (label 1) runs only, so the cost side
   is shown next to the benefit side: attacks only Divergence catches against
   attacks only the comparison catches, and the recall difference (Divergence
   minus comparison; negative = Divergence misses more).

Run:  python -m divergence.experiments.exp1e_paired_tests
Writes results/exp1_paired_tests.csv.
"""

import numpy as np
import pandas as pd

from divergence.config import RANDOM_SEED, RESULTS_DIR
from divergence.experiments.exp1_baseline_comparison import MAIN
from divergence.metrics import mcnemar_test, paired_auc_delta_ci

COMPARE = ["Pretrained encoder + flags", "Flags only (any flag)",
           "Behaviour-only (rules, no description)", "AGT-only (rule policy on audit log)",
           "Fine-tuned score only"]


def fa_delta_ci(verdict_a, verdict_b, groups, n_boot: int = 2000, level: float = 0.95,
                seed: int = RANDOM_SEED) -> tuple[float, float, float]:
    """FLAG rate of b minus FLAG rate of a on the same runs, resampling skill groups.

    On the negative runs this is FA(b) - FA(a); on the positive runs it is
    recall(b) - recall(a). Returns (delta, lo, hi)."""
    a, b, groups = map(np.asarray, (verdict_a, verdict_b, groups))
    uniq = np.unique(groups)
    members = {g: np.where(groups == g)[0] for g in uniq}
    rng = np.random.default_rng(seed)
    deltas = [b[idx].mean() - a[idx].mean() for idx in
              (np.concatenate([members[g] for g in rng.choice(uniq, size=len(uniq), replace=True)])
               for _ in range(n_boot))]
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return float(b.mean() - a.mean()), *map(float, np.percentile(deltas, [lo, hi]))


def main() -> None:
    p = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    y, groups = p["label"].values, p["group"].values
    neg, pos = y == 0, y == 1
    main_s, main_v = p[f"{MAIN}|score"].values, p[f"{MAIN}|verdict"].values
    rows = []
    for name in COMPARE:
        s, v = p[f"{name}|score"].values, p[f"{name}|verdict"].values
        # delta = Divergence minus comparison (positive = Divergence better)
        pr = paired_auc_delta_ci(y, s, main_s, groups, metric="PR_AUC")
        roc = paired_auc_delta_ci(y, s, main_s, groups, metric="AUC")
        fa = fa_delta_ci(main_v[neg], v[neg], groups[neg])  # comparison FA minus Divergence FA
        t = mcnemar_test(y[neg], main_v[neg], v[neg])
        rec = fa_delta_ci(v[pos], main_v[pos], groups[pos])  # Divergence recall minus comparison recall
        tp = mcnemar_test(y[pos], main_v[pos], v[pos])       # "right" on a positive = the attack was flagged
        rows.append({"comparison": name,
                     "PR_AUC_delta": pr[0], "PR_AUC_delta_lo": pr[1], "PR_AUC_delta_hi": pr[2],
                     "AUC_delta": roc[0], "AUC_delta_lo": roc[1], "AUC_delta_hi": roc[2],
                     "n_negatives": int(neg.sum()),
                     "FA_divergence": float(main_v[neg].mean()), "FA_comparison": float(v[neg].mean()),
                     "FA_reduction": fa[0], "FA_reduction_lo": fa[1], "FA_reduction_hi": fa[2],
                     "neg_divergence_right_only": t["A_right_B_wrong"],
                     "neg_comparison_right_only": t["A_wrong_B_right"], "neg_mcnemar_p": t["p_value"],
                     "n_positives": int(pos.sum()),
                     "recall_divergence": float(main_v[pos].mean()), "recall_comparison": float(v[pos].mean()),
                     "recall_delta": rec[0], "recall_delta_lo": rec[1], "recall_delta_hi": rec[2],
                     "pos_divergence_caught_only": tp["A_right_B_wrong"],
                     "pos_comparison_caught_only": tp["A_wrong_B_right"], "pos_mcnemar_p": tp["p_value"]})
    out = pd.DataFrame(rows).set_index("comparison")
    out.to_csv(RESULTS_DIR / "exp1_paired_tests.csv")
    print(out.round(3).T.to_string())


if __name__ == "__main__":
    main()
