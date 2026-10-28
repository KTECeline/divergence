"""Experiment 2: ablation study. Build order item 13.

Removes or swaps one component at a time to measure what each contributes:

  * trace text: enriched templates vs the flat "<action> <target>" baseline
    (src/preprocessing/trace_to_text.py), plus the flat text with the sandbox
    artefacts the enriched text hides (the sinkhole IP every domain resolves
    to, tool-config reads such as /etc/hosts) removed, to test whether flat
    text gains from cues that exist only in this sandbox;
  * encoder: pretrained vs SetFit-style fine-tuned (the delta itself, with a
    paired interval, is Exp 2b);
  * calibrator features: consistency score alone, score + the 3 structural
    flags, the flags alone, and the full model with each flag left out.

Same protocol as the main model for every variant: encoders are fine-tuned on
the fine-tune split only (12 epochs, as chosen for the main model in notebook
05; the flat text gets the same budget and is not tuned separately), the
logistic calibrator is refitted on the calibration split, FLAG at 0.5, and the
test split is only scored. The enriched fine-tuned encoder is the saved main
model, so the full configuration reproduces Exp 1's Divergence row.

Ablations explain the frozen design; none of them is used to change it.
Writes results/exp2_ablation_results.csv and results/exp2_predictions.csv.
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics import roc_auc_score

from src.calibration.logistic_calibrator import FLAG_THRESHOLD, LogisticCalibrator
from src.config import FINETUNED_EMBEDDING_DIR, PRETRAINED_EMBEDDING_MODEL, RESULTS_DIR
from src.data.merge_labels import load_labelled_dataset
from src.embedding.finetune_setfit import finetune, score
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, point_metrics
from src.experiments.exp1_baseline_comparison import MAIN
from src.preprocessing.structural_flags import StructuralFlags, compute_structural_flags
from src.preprocessing.trace_to_text import (SINKHOLE_IP, TOOL_CONFIG_READS, trace_to_enriched_text,
                                             trace_to_flat_text)

EPOCHS = 12


def flat_masked_text(trace: list[dict]) -> str:
    """Flat text without the sandbox artefacts: connections to the sinkhole IP (the DNS lookup before
    them still names the real host) and the config files tools read by themselves."""
    return trace_to_flat_text([a for a in trace
                               if not (a["action"] == "network_connect" and a["target"].startswith(SINKHOLE_IP))
                               and not (a["action"] == "file_read" and TOOL_CONFIG_READS.search(a["target"]))])


TEXTS = {"enriched": trace_to_enriched_text, "flat": trace_to_flat_text, "flat-masked": flat_masked_text}
FULL = "enriched | fine-tuned | score + 3 flags"   # = the main model


def flag_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([compute_structural_flags(r["description"], r["trace"]).as_list() for r in rows], float)


def calibrate(X_cal, y_cal, X_test) -> np.ndarray:
    c = LogisticCalibrator(feature_names=tuple(f"x{i}" for i in range(X_cal.shape[1])))
    c.fit(X_cal, y_cal)
    return c.predict_proba(X_test)


def main() -> None:
    ft, cal, test = (load_labelled_dataset((s,)) for s in ("finetune", "calibration", "held_out_test"))
    y_cal, y_test = np.array([r["label"] for r in cal]), np.array([r["label"] for r in test])
    groups = [r["group_key"] or r["sample_id"] for r in test]
    f_cal, f_test = flag_matrix(cal), flag_matrix(test)
    exp1 = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    main_v = exp1.set_index(["sample_id", "mode"]).loc[[(r["sample_id"], r["mode"]) for r in test],
                                                         f"{MAIN}|verdict"].values

    pretrained = SentenceTransformer(PRETRAINED_EMBEDDING_MODEL, device="cpu")
    encoders = {("enriched", "pretrained"): pretrained, ("flat", "pretrained"): pretrained,
                ("flat-masked", "pretrained"): pretrained,
                ("enriched", "fine-tuned"): SentenceTransformer(str(FINETUNED_EMBEDDING_DIR), device="cpu")}
    for text in ("flat", "flat-masked"):
        print(f"fine-tuning on {text} text", flush=True)
        encoders[(text, "fine-tuned")], _ = finetune(ft, text_fn=TEXTS[text], epochs=EPOCHS)

    variants = {}  # name -> (component, test probabilities, calibration-split score AUC or nan)
    for (text, enc_name), enc in encoders.items():
        s_cal, s_test = score(enc, cal, TEXTS[text]), score(enc, test, TEXTS[text])
        val = roc_auc_score(y_cal, -s_cal)  # score alone, on a split no fitted encoder has seen
        variants[f"{text} | {enc_name} | score only"] = (
            "text x encoder", calibrate(s_cal[:, None], y_cal, s_test[:, None]), val)
        variants[f"{text} | {enc_name} | score + 3 flags"] = (
            "text x encoder", calibrate(np.column_stack([s_cal, f_cal]), y_cal, np.column_stack([s_test, f_test])), val)
        if (text, enc_name) == ("enriched", "fine-tuned"):
            for k, flag in enumerate(StructuralFlags.NAMES):
                keep = [j for j in range(f_cal.shape[1]) if j != k]
                variants[f"{FULL} minus {flag}"] = (
                    "leave one flag out",
                    calibrate(np.column_stack([s_cal, f_cal[:, keep]]), y_cal,
                              np.column_stack([s_test, f_test[:, keep]])), np.nan)
    variants["3 flags only (calibrated, no description score)"] = (
        "no semantic score", calibrate(f_cal, y_cal, f_test), np.nan)

    rows, preds = [], {"sample_id": [r["sample_id"] for r in test], "mode": [r["mode"] for r in test],
                       "group": groups, "label": y_test}
    for name, (component, prob, val) in variants.items():
        verdict = (prob >= FLAG_THRESHOLD).astype(int)
        m = point_metrics(y_test, prob, verdict, prob)
        ci = group_bootstrap_ci(y_test, prob, verdict, groups)
        t = mcnemar_test(y_test, main_v, verdict)
        rows.append({"variant": name, "component": component, "val_score_AUC": val, **m,
                     "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1],
                     "verdicts_differ_from_main": int((verdict != main_v).sum()), "mcnemar_p_vs_main": t["p_value"]})
        preds[f"{name}|prob"] = prob

    out = pd.DataFrame(rows)
    out.to_csv(RESULTS_DIR / "exp2_ablation_results.csv", index=False)
    pd.DataFrame(preds).to_csv(RESULTS_DIR / "exp2_predictions.csv", index=False)
    cols = ["variant", "val_score_AUC", "AUC", "AUC_lo", "AUC_hi", "F1", "precision", "recall",
            "false_alarm_rate", "Brier", "verdicts_differ_from_main", "mcnemar_p_vs_main"]
    print(out[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
