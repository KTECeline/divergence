"""Experiment 1: baseline comparison + McNemar's test. Build order item 12.

Compares DivergenceEvaluator against the non-trained baselines (AGT-only,
behaviour-only) plus text-only and a mode-only diagnostic, on the held-out
test split ONLY. The same run also scores the component ablations (Exp 2 / 2b
preview: score alone, flags alone, pretrained encoder, AGT-visible actions only),
since they need the same frozen models. Writes results/exp1_results.csv and
results/exp1_predictions.csv.

LLM-as-judge is not included yet (src/baselines/llm_as_judge.py is a stub;
it will run on local Ollama).

Nothing here is tuned on the test split: every model and threshold comes from
the fine-tune / calibration splits.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.baselines import agt_only, behaviour_only
from src.baselines.text_only import TextOnlyBaseline
from src.calibration.logistic_calibrator import FLAG_THRESHOLD, feature_row
from src.config import RANDOM_SEED, RESULTS_DIR, VERDICT_FLAG
from src.data.merge_labels import load_labelled_dataset
from src.embedding.encoder import Encoder
from src.embedding.similarity import consistency_scores
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, point_metrics
from src.evaluator.agt_adapter import agt_visible
from src.evaluator.divergence_evaluator import DivergenceEvaluator
from src.preprocessing.structural_flags import compute_structural_flags
from src.preprocessing.trace_to_text import trace_to_enriched_text

MAIN = "Divergence (full pipeline)"
# name -> role in the report: the system, a baseline to beat, or a component ablation
ROLES = {
    MAIN: "system",
    "AGT-only (rule policy on audit log)": "baseline",
    "Behaviour-only (rules, no description)": "baseline",
    "Text-only (description TF-IDF)": "baseline",
    "Mode-only (diagnostic)": "baseline",
    "Divergence on AGT-visible actions only": "ablation",
    "Fine-tuned score only": "ablation",
    "Flags only (any flag)": "ablation",
    "Pretrained encoder + flags": "ablation",
}


def _group(r) -> str:
    return r["group_key"] or r["sample_id"]


def _calibrated(X_cal, y_cal, X_test) -> np.ndarray:
    """Logistic regression fitted on the calibration split, as notebook 06 did for the full pipeline."""
    m = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED).fit(X_cal, y_cal)
    return m.predict_proba(X_test)[:, 1]


def run_systems(test, ft, cal, evaluator: DivergenceEvaluator | None = None):
    """Score every system on the test runs. Returns (per-run predictions, Divergence results)."""
    ev = evaluator or DivergenceEvaluator()
    y_cal = np.array([r["label"] for r in cal])
    out = {}  # name -> (score for ranking, 0/1 verdict, probability or None)

    results = ev.evaluate_batch([(r["description"], r["trace"]) for r in test])
    p = np.array([res.probability for res in results])
    out[MAIN] = (p, np.array([res.verdict == VERDICT_FLAG for res in results], int), p)

    vis = ev.evaluate_batch([(r["description"], agt_visible(r["trace"])) for r in test])
    p = np.array([res.probability for res in vis])
    out["Divergence on AGT-visible actions only"] = (p, (p >= FLAG_THRESHOLD).astype(int), p)

    for name, mod in [("AGT-only (rule policy on audit log)", agt_only),
                      ("Behaviour-only (rules, no description)", behaviour_only)]:
        s = np.array([mod.score(r) for r in test])
        out[name] = (s, (s > 0).astype(int), None)

    p = TextOnlyBaseline().fit(ft + cal).predict_proba(test)
    out["Text-only (description TF-IDF)"] = (p, (p >= 0.5).astype(int), p)

    rate = pd.DataFrame(ft + cal).groupby("mode")["label"].mean()
    p = np.array([rate[r["mode"]] for r in test])
    out["Mode-only (diagnostic)"] = (p, (p >= 0.5).astype(int), p)

    # component ablations, each recalibrated on the calibration split
    def scores_with(enc, rows):
        return consistency_scores(enc.encode([r["description"] for r in rows]),
                                  enc.encode([trace_to_enriched_text(r["trace"]) for r in rows]))
    flags = lambda rows: np.array([compute_structural_flags(r["description"], r["trace"]).as_list() for r in rows], float)
    f_cal, f_test = flags(cal), flags(test)
    s_cal, s_test = scores_with(ev.encoder, cal), np.array([res.consistency_score for res in results])
    p = _calibrated(s_cal[:, None], y_cal, s_test[:, None])
    out["Fine-tuned score only"] = (p, (p >= FLAG_THRESHOLD).astype(int), p)
    s = f_test.sum(1)
    out["Flags only (any flag)"] = (s, (s > 0).astype(int), None)
    pre = Encoder()
    p = _calibrated(np.column_stack([scores_with(pre, cal), f_cal]), y_cal,
                    np.column_stack([scores_with(pre, test), f_test]))
    out["Pretrained encoder + flags"] = (p, (p >= FLAG_THRESHOLD).astype(int), p)

    preds = pd.DataFrame({"sample_id": [r["sample_id"] for r in test], "mode": [r["mode"] for r in test],
                          "group": [_group(r) for r in test], "label": [r["label"] for r in test],
                          "dataset_label": [r["dataset_label"] for r in test]})
    for name in ROLES:
        score, verdict, _ = out[name]
        preds[f"{name}|score"], preds[f"{name}|verdict"] = score, verdict
    return preds, results


def summarise(preds: pd.DataFrame, n_boot: int = 2000) -> pd.DataFrame:
    """One row per system: point metrics, group-bootstrap 95% CIs, McNemar vs Divergence."""
    y, groups = preds["label"].values, preds["group"].values
    rows = []
    for name, role in ROLES.items():
        s, v = preds[f"{name}|score"].values, preds[f"{name}|verdict"].values
        is_prob = name not in ("AGT-only (rule policy on audit log)", "Behaviour-only (rules, no description)",
                               "Flags only (any flag)")
        m = point_metrics(y, s, v, s if is_prob else None)
        ci = group_bootstrap_ci(y, s, v, groups, n_boot=n_boot)
        row = {"system": name, "role": role, **m,
               "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1], "F1_lo": ci["F1"][0], "F1_hi": ci["F1"][1]}
        if name != MAIN:
            t = mcnemar_test(y, preds[f"{MAIN}|verdict"].values, v)
            row.update({"divergence_right_only": t["A_right_B_wrong"], "baseline_right_only": t["A_wrong_B_right"],
                        "mcnemar_p": t["p_value"]})
        rows.append(row)
    return pd.DataFrame(rows).set_index("system")


def within_mode_auc(preds: pd.DataFrame) -> pd.DataFrame:
    """AUC inside each execution mode, which removes the mode confound (POS rate differs by mode)."""
    table = {}
    for name in ROLES:
        table[name] = {m: point_metrics(g["label"], g[f"{name}|score"], g[f"{name}|verdict"])["AUC"]
                       for m, g in preds.groupby("mode")}
    t = pd.DataFrame(table).T
    t["mean of modes"] = t.mean(axis=1)
    return t


def main() -> None:
    test = load_labelled_dataset(("held_out_test",))
    ft, cal = load_labelled_dataset(("finetune",)), load_labelled_dataset(("calibration",))
    preds, _ = run_systems(test, ft, cal)
    RESULTS_DIR.mkdir(exist_ok=True)
    preds.to_csv(RESULTS_DIR / "exp1_predictions.csv", index=False)
    summary = summarise(preds)
    summary.to_csv(RESULTS_DIR / "exp1_results.csv")
    print(summary.round(3).to_string())


if __name__ == "__main__":
    main()
