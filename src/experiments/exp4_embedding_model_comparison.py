"""Experiment 4: embedding model comparison (core, per the APU CSDA guideline:
build several models and justify the choice).

Four sentence encoders, each used pretrained and SetFit-style fine-tuned, all
through the SAME pipeline and splits as the main model:
fine-tune split -> encoder fine-tuning (epochs = 12, as chosen for the main
model in notebook 05; the same for every encoder so none gets extra tuning),
calibration split -> logistic calibrator (score + 3 flags), test split -> scored once.

Selection rule, fixed before the run: an encoder is chosen on the CALIBRATION
split (AUC of its consistency score alone, which no fitted parameter has seen;
the fine-tuning never touches that split), with model size and encoding time as
tie-breakers for deployment. Test-split figures are reported for every encoder
but are never used to choose one; the main model stays all-MiniLM-L6-v2 unless
the validation rule says otherwise, and that is reported, not acted on silently.

Writes results/exp4_embedding_models.csv and results/exp4_predictions.csv.
"""

import time

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics import roc_auc_score

from src.calibration.logistic_calibrator import FLAG_THRESHOLD, LogisticCalibrator
from src.config import RESULTS_DIR
from src.data.merge_labels import load_labelled_dataset
from src.embedding.finetune_setfit import finetune, score
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, point_metrics
from src.experiments.exp1_baseline_comparison import MAIN
from src.experiments.exp6_holdout_generalisation import features

EPOCHS = 12
ENCODERS = {  # name -> parameters (millions), for the size criterion
    "sentence-transformers/all-MiniLM-L6-v2": 22,
    "sentence-transformers/all-MiniLM-L12-v2": 33,
    "sentence-transformers/all-mpnet-base-v2": 110,
    "BAAI/bge-small-en-v1.5": 33,
}


def main() -> None:
    ft, cal, test = (load_labelled_dataset((s,)) for s in ("finetune", "calibration", "held_out_test"))
    y_cal, y_test = np.array([r["label"] for r in cal]), np.array([r["label"] for r in test])
    groups = [r["group_key"] or r["sample_id"] for r in test]
    exp1 = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    main_v = exp1.set_index(["sample_id", "mode"]).loc[[(r["sample_id"], r["mode"]) for r in test],
                                                         f"{MAIN}|verdict"].values

    rows, preds = [], {"sample_id": [r["sample_id"] for r in test], "mode": [r["mode"] for r in test],
                       "label": y_test}
    for name, params in ENCODERS.items():
        for variant in ("pretrained", "fine-tuned"):
            print(f"{name} [{variant}]", flush=True)
            t0 = time.time()
            if variant == "pretrained":
                enc = SentenceTransformer(name, device="cpu")
            else:
                enc, _ = finetune(ft, epochs=EPOCHS, base=name)
            train_s = time.time() - t0
            s_cal = score(enc, cal)
            t0 = time.time()
            s_test = score(enc, test)
            ms_per_run = (time.time() - t0) / len(test) * 1000
            c = LogisticCalibrator()
            c.fit(features(cal, s_cal), y_cal)
            prob = c.predict_proba(features(test, s_test))
            verdict = (prob >= FLAG_THRESHOLD).astype(int)
            m = point_metrics(y_test, prob, verdict, prob)
            ci = group_bootstrap_ci(y_test, prob, verdict, groups)
            t = mcnemar_test(y_test, main_v, verdict)
            rows.append({"encoder": name, "variant": variant, "params_M": params,
                         "val_score_AUC": roc_auc_score(y_cal, -s_cal),        # selection criterion
                         "test_score_AUC": roc_auc_score(y_test, -s_test),
                         **{f"test_{k}": v for k, v in m.items()},
                         "test_AUC_lo": ci["AUC"][0], "test_AUC_hi": ci["AUC"][1],
                         "mcnemar_p_vs_main": t["p_value"], "ms_per_run": ms_per_run, "train_s": train_s,
                         "score_weight": c.coefficients().get("consistency_score", np.nan)})
            preds[f"{name}|{variant}|prob"] = prob

    out = pd.DataFrame(rows)
    best = out.sort_values(["val_score_AUC", "params_M", "ms_per_run"], ascending=[False, True, True]).iloc[0]
    out["selected_by_validation"] = (out.encoder == best.encoder) & (out.variant == best.variant)
    out.to_csv(RESULTS_DIR / "exp4_embedding_models.csv", index=False)
    pd.DataFrame(preds).to_csv(RESULTS_DIR / "exp4_predictions.csv", index=False)
    cols = ["encoder", "variant", "params_M", "val_score_AUC", "test_score_AUC", "test_AUC", "test_AUC_lo",
            "test_AUC_hi", "test_F1", "test_accuracy", "test_false_alarm_rate", "mcnemar_p_vs_main", "ms_per_run",
            "train_s", "score_weight", "selected_by_validation"]
    print(out[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
