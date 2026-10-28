"""Experiment 2b: fine-tuning delta. Build order item 13.

Measures the improvement from SetFit-style fine-tuning over the pretrained
encoder, for each trace text and with / without the structural flags. Reads
the per-run probabilities Exp 2 saved (run exp2_ablation first), so no model
is retrained here. Each delta is AUC(fine-tuned) - AUC(pretrained) on the same
test runs, with a PAIRED group-bootstrap interval: an interval that excludes 0
means fine-tuning helped on these runs, even where the two single-system
intervals overlap. Verdict changes at the 0.5 cut-off are reported alongside.

A second table compares trace texts the same paired way (flat and flat with
sandbox artefacts masked, each minus enriched; fine-tuned encoders only).

Writes results/exp2b_finetune_delta.csv and results/exp2b_text_delta.csv.
"""

import numpy as np
import pandas as pd

from src.calibration.logistic_calibrator import FLAG_THRESHOLD
from src.config import RESULTS_DIR
from src.evaluation.metrics import mcnemar_test, paired_auc_delta_ci, point_metrics


def main() -> None:
    preds = pd.read_csv(RESULTS_DIR / "exp2_predictions.csv")
    y, groups = preds["label"].values, preds["group"].values
    rows = []
    for text in ("enriched", "flat", "flat-masked"):
        for feats in ("score only", "score + 3 flags"):
            pre, fin = (preds[f"{text} | {e} | {feats}|prob"].values for e in ("pretrained", "fine-tuned"))
            v_pre, v_fin = (pre >= FLAG_THRESHOLD).astype(int), (fin >= FLAG_THRESHOLD).astype(int)
            d, lo, hi = paired_auc_delta_ci(y, pre, fin, groups)
            m_pre, m_fin = point_metrics(y, pre, v_pre), point_metrics(y, fin, v_fin)
            t = mcnemar_test(y, v_pre, v_fin)
            rows.append({"text": text, "features": feats, "AUC_pretrained": m_pre["AUC"], "AUC_finetuned": m_fin["AUC"],
                         "AUC_delta": d, "AUC_delta_lo": lo, "AUC_delta_hi": hi,
                         "F1_pretrained": m_pre["F1"], "F1_finetuned": m_fin["F1"],
                         "FA_pretrained": m_pre["false_alarm_rate"], "FA_finetuned": m_fin["false_alarm_rate"],
                         "verdicts_changed": int((v_pre != v_fin).sum()),
                         "finetuned_right_only": t["A_wrong_B_right"], "pretrained_right_only": t["A_right_B_wrong"],
                         "mcnemar_p": t["p_value"]})
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS_DIR / "exp2b_finetune_delta.csv", index=False)
    print(out.round(3).to_string(index=False))

    rows = []
    for feats in ("score only", "score + 3 flags"):
        base = preds[f"enriched | fine-tuned | {feats}|prob"].values
        for text in ("flat", "flat-masked"):
            d, lo, hi = paired_auc_delta_ci(y, base, preds[f"{text} | fine-tuned | {feats}|prob"].values, groups)
            rows.append({"features": feats, "comparison": f"{text} minus enriched",
                         "AUC_delta": d, "AUC_delta_lo": lo, "AUC_delta_hi": hi})
    text = pd.DataFrame(rows)
    text.to_csv(RESULTS_DIR / "exp2b_text_delta.csv", index=False)
    print(text.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
