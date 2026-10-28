"""Experiment 6: held-out category generalisation. Build order item 16.

Tests whether the model learns divergence as a concept or memorises known
attack vocabulary. Two settings:

  6a. Leave-one-behaviour-class-out: one fold per behaviour class B1-B9; train
      without that class, test only on it. B10-B15 have no positive runs (their
      effect is in the agent's reply, not its actions) and are skipped.
  6b. Cross attack vector: train on Code Injection, test on Prompt Injection,
      and the reverse. Mixed is excluded from both sides, since it contains
      both vectors and would leak the held-out one.

Reference ("seen"): 5-fold group cross-validation with the same protocol, so
each class / vector is scored once by models that DID see it in training. The
gap seen -> held-out is the generalisation cost.

Protocol, identical in every fold: the training rows are split by skill group
into a fine-tune part (2/3) and a calibration part (1/3); the encoder is
fine-tuned (epochs = 12, as chosen for the main model in notebook 05), the
logistic calibrator is fitted on the calibration part, FLAG at 0.5. Every row
whose skill group appears in the held-out set is removed from training, so no
variant of a held-out skill is seen.

These are NEW models trained on the pooled labelled runs (all three splits);
the locked main model and its test split result are not touched or re-tuned.
Held-out sets are malicious-skill runs only, so negatives are few in some
classes: recall is the main figure, AUC only when both sides have 3+ runs.

Writes results/exp6_holdout.csv and results/exp6_predictions.csv.
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from src.baselines import behaviour_only
from src.calibration.logistic_calibrator import FLAG_THRESHOLD, LogisticCalibrator, feature_row
from src.config import PRETRAINED_EMBEDDING_MODEL, RANDOM_SEED, RESULTS_DIR
from src.data.merge_labels import load_labelled_dataset
from src.embedding.finetune_setfit import finetune, score
from src.preprocessing.structural_flags import compute_structural_flags

EPOCHS = 12
CLASSES = [f"B{i}" for i in range(1, 10)]
CLASS_NAMES = {"B1": "Data Exfiltration", "B2": "Credential Theft", "B3": "Remote Code Execution",
               "B4": "Malware Delivery", "B5": "Persistence", "B6": "Reverse Shell", "B7": "Ransomware",
               "B8": "Resource Abuse", "B9": "Privilege Escalation"}


def group(r: dict) -> str:
    return r["group_key"] or r["sample_id"]


def features(rows: list[dict], scores: np.ndarray) -> np.ndarray:
    return np.array([feature_row(s, compute_structural_flags(r["description"], r["trace"]))
                     for r, s in zip(rows, scores)])


def train_and_predict(train: list[dict], test: list[dict], pretrained: SentenceTransformer, seed: int = RANDOM_SEED):
    """Fine-tune + calibrate on `train` (group split 2:1), return test probabilities for both encoders."""
    y = np.array([r["label"] for r in train])
    inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
    ft_idx, cal_idx = next(inner.split(np.zeros(len(train)), y, [group(r) for r in train]))
    ft, cal = [train[i] for i in ft_idx], [train[i] for i in cal_idx]
    model, _ = finetune(ft, epochs=EPOCHS, seed=seed)
    out = {}
    for name, enc in (("divergence", model), ("pretrained_flags", pretrained)):
        c = LogisticCalibrator()
        c.fit(features(cal, score(enc, cal)), y[cal_idx])
        out[name] = c.predict_proba(features(test, score(enc, test)))
    return out


def held_out_folds(rows: list[dict]) -> list[tuple[str, str, list[int]]]:
    folds = [("6a class", c, [i for i, r in enumerate(rows) if r["behaviour_class"] == c]) for c in CLASSES]
    folds += [("6b vector", f"train {a} -> test {b}", [i for i, r in enumerate(rows) if r["attack_vector"] == b])
              for a, b in (("CI", "PI"), ("PI", "CI"))]
    return folds


def metrics(y: np.ndarray, prob: np.ndarray, verdict: np.ndarray) -> dict:
    pos, neg = y == 1, y == 0
    return {"recall": verdict[pos].mean() if pos.any() else np.nan,
            "false_alarm_rate": verdict[neg].mean() if neg.any() else np.nan,
            "AUC": roc_auc_score(y, prob) if pos.sum() >= 3 and neg.sum() >= 3 else np.nan}


def main() -> None:
    rows = load_labelled_dataset()
    y = np.array([r["label"] for r in rows])
    pretrained = SentenceTransformer(PRETRAINED_EMBEDDING_MODEL, device="cpu")
    beh = np.array([behaviour_only.predict(r) for r in rows])

    # reference: every row scored once by a model that saw its class / vector
    seen = np.full(len(rows), np.nan)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    for k, (tr, te) in enumerate(cv.split(np.zeros(len(rows)), y, [group(r) for r in rows]), 1):
        print(f"reference CV fold {k}/5", flush=True)
        seen[te] = train_and_predict([rows[i] for i in tr], [rows[i] for i in te], pretrained)["divergence"]

    results, preds = [], []
    for setting, name, test_idx in held_out_folds(rows):
        test_groups = {group(rows[i]) for i in test_idx}
        excluded = {"MIXED", name.split()[3]} if setting.startswith("6b") else set()
        train = [r for i, r in enumerate(rows) if group(r) not in test_groups
                 and (r["behaviour_class"] != name if setting.startswith("6a") else r["attack_vector"] not in excluded)]
        print(f"{setting} {name}: train {len(train)}, test {len(test_idx)}", flush=True)
        test = [rows[i] for i in test_idx]
        p = train_and_predict(train, test, pretrained)
        yt = y[test_idx]
        row = {"setting": setting, "held_out": name, "behaviour": CLASS_NAMES.get(name, ""), "n_train": len(train),
               "n_test": len(test_idx), "n_pos": int(yt.sum()), "n_neg": int((1 - yt).sum())}
        for sysname, prob in (("divergence_heldout", p["divergence"]), ("divergence_seen", seen[test_idx]),
                              ("pretrained_flags_heldout", p["pretrained_flags"])):
            row.update({f"{sysname}_{k}": v for k, v in metrics(yt, prob, (prob >= FLAG_THRESHOLD).astype(int)).items()})
        row.update({f"behaviour_only_{k}": v for k, v in metrics(yt, beh[test_idx], beh[test_idx]).items()})
        results.append(row)
        preds += [{"setting": setting, "held_out": name, "sample_id": rows[i]["sample_id"], "mode": rows[i]["mode"],
                   "label": int(y[i]), "prob_heldout": float(ph), "prob_seen": float(seen[i]),
                   "prob_pretrained_flags": float(pp)}
                  for i, ph, pp in zip(test_idx, p["divergence"], p["pretrained_flags"])]

    # overall reference figures, for the report's comparison with the random split
    v = (seen >= FLAG_THRESHOLD).astype(int)
    results.append({"setting": "reference", "held_out": "5-fold group CV, all runs", "n_test": len(rows),
                    "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
                    **{f"divergence_seen_{k}": val for k, val in metrics(y, seen, v).items()}})
    out = pd.DataFrame(results)
    out.to_csv(RESULTS_DIR / "exp6_holdout.csv", index=False)
    pd.DataFrame(preds).to_csv(RESULTS_DIR / "exp6_predictions.csv", index=False)
    cols = ["setting", "held_out", "behaviour", "n_test", "n_pos", "n_neg",
            "divergence_seen_recall", "divergence_heldout_recall", "pretrained_flags_heldout_recall",
            "behaviour_only_recall", "divergence_seen_false_alarm_rate", "divergence_heldout_false_alarm_rate",
            "divergence_seen_AUC", "divergence_heldout_AUC"]
    print(out[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
