"""Metrics shared by the experiments: point metrics, group bootstrap intervals,
McNemar's test.

The test split holds several runs of the same skill (agent / direct /
instructed modes share a skill group), and those runs are not independent. The
confidence intervals therefore resample skill GROUPS, not single runs; resampling
runs would make the intervals too narrow.
"""

import numpy as np
from sklearn.metrics import brier_score_loss, precision_recall_fscore_support, roc_auc_score
from statsmodels.stats.contingency_tables import mcnemar

from src.config import RANDOM_SEED


def point_metrics(y, score, verdict, prob=None) -> dict:
    """AUC ranks by `score` (higher = more suspicious); F1/P/R/accuracy use the 0/1 `verdict`;
    Brier only when `score` is a real probability."""
    y, verdict = np.asarray(y), np.asarray(verdict)
    p, r, f1, _ = precision_recall_fscore_support(y, verdict, average="binary", zero_division=0)
    out = {"AUC": roc_auc_score(y, score) if 0 < y.sum() < len(y) else np.nan,
           "F1": f1, "precision": p, "recall": r, "accuracy": float((verdict == y).mean()),
           "false_alarm_rate": float(verdict[y == 0].mean()) if (y == 0).any() else np.nan}
    if prob is not None:
        out["Brier"] = brier_score_loss(y, prob)
    return out


def group_bootstrap_ci(y, score, verdict, groups, n_boot: int = 2000, level: float = 0.95,
                       seed: int = RANDOM_SEED) -> dict[str, tuple[float, float]]:
    """Percentile intervals for AUC and F1, resampling skill groups with replacement."""
    y, score, verdict, groups = map(np.asarray, (y, score, verdict, groups))
    uniq = np.unique(groups)
    members = {g: np.where(groups == g)[0] for g in uniq}
    rng = np.random.default_rng(seed)
    aucs, f1s = [], []
    for _ in range(n_boot):
        idx = np.concatenate([members[g] for g in rng.choice(uniq, size=len(uniq), replace=True)])
        yb = y[idx]
        if 0 < yb.sum() < len(yb):
            aucs.append(roc_auc_score(yb, score[idx]))
        f1s.append(precision_recall_fscore_support(yb, verdict[idx], average="binary", zero_division=0)[2])
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return {"AUC": tuple(np.percentile(aucs, [lo, hi])), "F1": tuple(np.percentile(f1s, [lo, hi]))}


def mcnemar_test(y, verdict_a, verdict_b) -> dict:
    """Exact McNemar's test on the runs where exactly one system is right.

    b = A right, B wrong; c = A wrong, B right. A small p-value means the two
    systems' error rates differ by more than chance.
    """
    y, a, b_ = map(np.asarray, (y, verdict_a, verdict_b))
    ra, rb = a == y, b_ == y
    table = [[int((ra & rb).sum()), int((ra & ~rb).sum())], [int((~ra & rb).sum()), int((~ra & ~rb).sum())]]
    res = mcnemar(table, exact=True)
    return {"A_right_B_wrong": table[0][1], "A_wrong_B_right": table[1][0], "p_value": float(res.pvalue)}


def paired_auc_delta_ci(y, score_a, score_b, groups, n_boot: int = 2000, level: float = 0.95,
                        seed: int = RANDOM_SEED) -> tuple[float, float, float]:
    """AUC(b) - AUC(a) on the same runs, with a group-bootstrap interval.

    Both systems are scored on every resample, so the interval reflects the
    difference itself; two overlapping single-system intervals can still hide
    a consistent gain. Returns (delta, lo, hi).
    """
    y, a, b, groups = map(np.asarray, (y, score_a, score_b, groups))
    uniq = np.unique(groups)
    members = {g: np.where(groups == g)[0] for g in uniq}
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_boot):
        idx = np.concatenate([members[g] for g in rng.choice(uniq, size=len(uniq), replace=True)])
        if 0 < y[idx].sum() < len(idx):
            deltas.append(roc_auc_score(y[idx], b[idx]) - roc_auc_score(y[idx], a[idx]))
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return float(roc_auc_score(y, b) - roc_auc_score(y, a)), *map(float, np.percentile(deltas, [lo, hi]))
