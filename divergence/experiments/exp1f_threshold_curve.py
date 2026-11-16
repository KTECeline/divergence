"""Experiment 1f: threshold curve for the full pipeline (DESCRIPTIVE ONLY).

Shows how recall, false-alarm rate, precision and F1 of "Divergence (full
pipeline)" would move if the FLAG cut-off were anywhere from 0 to 1, computed
from the saved test probabilities in results/exp1_predictions.csv. No model is
re-scored, refitted or tuned.

This is NOT a retuned operating point. The cut-off stays 0.5, fixed before the
test split was scored (divergence/calibration/logistic_calibrator.py). The test
split has been seen, so a cut-off chosen from this curve would be tuned on test
data, and its figures would be optimistic. Use the curve only to describe how
sensitive the reported 0.5 result is to the cut-off.

Two things to know when reading it:
  * the saved probabilities are rounded to 4 decimals (as the evaluator returns
    them), so a cut-off is resolved to 0.0001;
  * 117 runs give a step curve, and each step is one or a few runs. The CSV
    carries the counts so no step is read as a smooth trend.

Run:  python -m divergence.experiments.exp1f_threshold_curve
Writes results/exp1_threshold_curve.csv and results/figures/exp1_threshold_curve.png.
"""

import numpy as np
import pandas as pd

from divergence.calibration.logistic_calibrator import FLAG_THRESHOLD
from divergence.config import FIGURES_DIR, RESULTS_DIR
from divergence.experiments.exp1_baseline_comparison import MAIN

THRESHOLDS = np.round(np.arange(0.0, 1.0001, 0.01), 2)
BLUE, ORANGE, AQUA, GREY, INK = "#2a78d6", "#eb6834", "#1baf7a", "#52514e", "#0b0b0b"


def threshold_curve(y, prob, thresholds=THRESHOLDS) -> pd.DataFrame:
    """One row per cut-off t, with FLAG = (prob >= t), the evaluator's own rule."""
    y, prob = np.asarray(y), np.asarray(prob, dtype=float)
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    rows = []
    for t in thresholds:
        flag = prob >= t
        tp, fp = int((flag & (y == 1)).sum()), int((flag & (y == 0)).sum())
        recall = tp / n_pos if n_pos else np.nan
        precision = tp / (tp + fp) if tp + fp else np.nan
        f1 = 2 * tp / (2 * tp + fp + (n_pos - tp)) if n_pos else np.nan
        rows.append({"threshold": float(t), "n_flagged": tp + fp, "true_positives": tp, "false_positives": fp,
                     "recall": recall, "false_alarm_rate": fp / n_neg if n_neg else np.nan,
                     "precision": precision, "F1": f1,
                     "is_fixed_operating_point": bool(np.isclose(t, FLAG_THRESHOLD))})
    return pd.DataFrame(rows)


def plot(curve: pd.DataFrame, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.4))
    t = curve["threshold"]
    for col, label, colour in (("recall", "recall", BLUE), ("F1", "F1", AQUA),
                               ("false_alarm_rate", "false-alarm rate", ORANGE)):
        ax.step(t, curve[col], where="post", color=colour, linewidth=2, label=label)
    ax.axvline(FLAG_THRESHOLD, color=GREY, linestyle="--", linewidth=1)
    fixed = curve[curve["is_fixed_operating_point"]].iloc[0]
    for col, colour in (("recall", BLUE), ("F1", AQUA), ("false_alarm_rate", ORANGE)):
        ax.scatter([FLAG_THRESHOLD], [fixed[col]], color=colour, s=45, zorder=3, edgecolor="white", linewidth=1.5)
    ax.annotate(f"fixed cut-off {FLAG_THRESHOLD:.1f} (not tuned)\nrecall {fixed['recall']:.2f} · F1 {fixed['F1']:.2f} · "
                f"false alarms {fixed['false_alarm_rate']:.2f}", (FLAG_THRESHOLD, 1.0), textcoords="offset points",
                xytext=(6, -4), va="top", ha="left", color=GREY, fontsize=9)
    ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="FLAG cut-off on the calibrated probability",
           ylabel="rate on the held-out test split")
    ax.set_title("Descriptive only: sensitivity of the Exp 1 result to the cut-off (117 test runs)\n"
                 "The reported operating point is the pre-set 0.5; this curve was not used to choose it",
                 fontsize=10, color=INK, loc="left")
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="center", bbox_to_anchor=(0.62, 0.42), labelcolor=INK)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    preds = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    y, prob = preds["label"].values, preds[f"{MAIN}|score"].values
    curve = threshold_curve(y, prob)

    # the 0.5 row must be the verdicts Exp 1 already reported, or this is not the same model
    fixed = curve[curve["is_fixed_operating_point"]].iloc[0]
    saved = preds[f"{MAIN}|verdict"].values
    assert fixed["true_positives"] == int((saved[y == 1]).sum()) and fixed["false_positives"] == int(saved[y == 0].sum())

    curve.to_csv(RESULTS_DIR / "exp1_threshold_curve.csv", index=False)
    plot(curve, FIGURES_DIR / "exp1_threshold_curve.png")
    print("DESCRIPTIVE ONLY: the operating point stays at the pre-set cut-off; nothing here is a retuned result.")
    print(curve[np.isclose(curve["threshold"] * 20 % 1, 0)].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
