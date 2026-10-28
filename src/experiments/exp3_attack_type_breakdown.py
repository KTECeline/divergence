"""Experiment 3: attack-type breakdown. Build order item 14.

Performance broken down across the MalSkillBench taxonomy: attack vector
(Code Injection / Prompt Injection / Mixed), behaviour class (B1-B15),
insertion strategy, sample source (generated / wild / benign) and execution
mode. Wild malicious skills carry no vector, class or strategy in the
benchmark; they get their own "wild" cell rather than being dropped.

Two views, because the test split alone leaves most cells with a handful of runs:
  A. locked test split (117 runs): the frozen main model, scored once in Exp 1,
     beside the baselines (behaviour-only, AGT-only, LLM judge qwen2.5:7b);
  B. all 308 labelled runs, each scored out-of-fold by 5-fold group
     cross-validation (same protocol and seed as Exp 6's reference CV):
     new models, more runs per cell, but not the locked model.
Per cell: recall on POS runs (Wilson 95% interval), false-alarm rate on NEG
runs, and AUC when both sides have 3+ runs. Cells under 5 runs are kept but
marked small; read them as examples, not rates.

Writes results/exp3_attack_breakdown.csv (+ exp3_cv_predictions.csv, a cache
of view B's out-of-fold probabilities).
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from statsmodels.stats.proportion import proportion_confint

from src.baselines import behaviour_only
from src.calibration.logistic_calibrator import FLAG_THRESHOLD
from src.config import PRETRAINED_EMBEDDING_MODEL, RANDOM_SEED, RESULTS_DIR
from src.data.loader import load_inventory
from src.data.merge_labels import load_labelled_dataset
from src.experiments.exp1_baseline_comparison import MAIN
from src.experiments.exp6_holdout_generalisation import CLASS_NAMES, group, train_and_predict

SMALL = 5
EXTRA_CLASS_NAMES = {"B10": "Role Hijack", "B11": "Safety Bypass", "B12": "Instruction Override",
                     "B13": "System Prompt Leak", "B14": "Goal Hijacking", "B15": "Content Manipulation"}
CV_CACHE = RESULTS_DIR / "exp3_cv_predictions.csv"


def taxonomy(rows: list[dict]) -> pd.DataFrame:
    """One row per run: the cells it belongs to. Benign / wild runs get their own cell in every dimension."""
    inv = load_inventory()
    out = []
    for r in rows:
        name = r["sample_id"].split("/", 1)[1]
        source = "benign" if r["dataset_label"] == 0 else inv.get(name, {}).get("source", "?").lower()
        fill = source if source in ("benign", "wild") else None
        out.append({"sample_id": r["sample_id"], "mode": r["mode"], "label": r["label"], "source": source,
                    "attack_vector": r["attack_vector"] or fill,
                    "behaviour_class": r["behaviour_class"] or fill,
                    "insertion_strategy": (inv.get(name, {}).get("insertion") if source == "generated" else None) or fill})
    return pd.DataFrame(out)


def cell_metrics(y: np.ndarray, prob: np.ndarray, verdict: np.ndarray) -> dict:
    pos, neg = y == 1, y == 0
    k, n = int(verdict[pos].sum()), int(pos.sum())
    lo, hi = proportion_confint(k, n, method="wilson") if n else (np.nan, np.nan)
    return {"recall": k / n if n else np.nan, "recall_lo": lo, "recall_hi": hi,
            "false_alarm_rate": verdict[neg].mean() if neg.any() else np.nan,
            "AUC": roc_auc_score(y, prob) if pos.sum() >= 3 and neg.sum() >= 3 else np.nan}


def cv_predictions(rows: list[dict]) -> np.ndarray:
    """Out-of-fold Divergence probability for every run (cached; ~6 min to build)."""
    if CV_CACHE.exists():
        c = pd.read_csv(CV_CACHE).set_index(["sample_id", "mode"])
        return c.loc[[(r["sample_id"], r["mode"]) for r in rows], "prob"].values
    y = np.array([r["label"] for r in rows])
    prob = np.full(len(rows), np.nan)
    pretrained = SentenceTransformer(PRETRAINED_EMBEDDING_MODEL, device="cpu")
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    for k, (tr, te) in enumerate(cv.split(np.zeros(len(rows)), y, [group(r) for r in rows]), 1):
        print(f"CV fold {k}/5", flush=True)
        prob[te] = train_and_predict([rows[i] for i in tr], [rows[i] for i in te], pretrained)["divergence"]
    pd.DataFrame({"sample_id": [r["sample_id"] for r in rows], "mode": [r["mode"] for r in rows],
                  "prob": prob}).to_csv(CV_CACHE, index=False)
    return prob


def breakdown(view: str, tax: pd.DataFrame, systems: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[dict]:
    names = {**CLASS_NAMES, **EXTRA_CLASS_NAMES}
    out = []
    for dim in ("attack_vector", "behaviour_class", "insertion_strategy", "source", "mode"):
        for cell, idx in tax.groupby(tax[dim].fillna("?")).groups.items():
            idx = np.asarray(list(idx))
            y = tax["label"].values[idx]
            row = {"view": view, "dimension": dim, "cell": cell, "name": names.get(cell, ""), "n": len(idx),
                   "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()), "small": len(idx) < SMALL}
            for sysname, (prob, verdict) in systems.items():
                row.update({f"{sysname}|{k}": v for k, v in cell_metrics(y, prob[idx], verdict[idx]).items()})
            out.append(row)
    return out


def main() -> None:
    rows = load_labelled_dataset()
    test = [r for r in rows if r["split"] == "held_out_test"]
    beh = lambda rs: np.array([behaviour_only.score(r) for r in rs])

    # A. locked test split, predictions from Exp 1 / 1c
    keys = [(r["sample_id"], r["mode"]) for r in test]
    e1 = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv").set_index(["sample_id", "mode"]).loc[keys]
    judge = pd.read_csv(RESULTS_DIR / "exp1_llm_judge_predictions.csv").set_index(["sample_id", "mode"]).loc[keys]
    pick = lambda df, name: (df[f"{name}|score"].values, df[f"{name}|verdict"].values.astype(int))
    systems_a = {"Divergence": pick(e1, MAIN),
                 "Behaviour-only": pick(e1, "Behaviour-only (rules, no description)"),
                 "AGT-only": pick(e1, "AGT-only (rule policy on audit log)"),
                 "LLM judge (qwen2.5:7b)": pick(judge, "qwen2.5:7b")}
    results = breakdown("A. test split (locked model)", taxonomy(test), systems_a)

    # B. all runs, out-of-fold
    p = cv_predictions(rows)
    b = beh(rows)
    systems_b = {"Divergence": (p, (p >= FLAG_THRESHOLD).astype(int)), "Behaviour-only": (b, (b > 0).astype(int))}
    results += breakdown("B. all runs (5-fold CV)", taxonomy(rows), systems_b)

    out = pd.DataFrame(results)
    out.to_csv(RESULTS_DIR / "exp3_attack_breakdown.csv", index=False)
    cols = ["view", "dimension", "cell", "n", "n_pos", "n_neg", "Divergence|recall", "Behaviour-only|recall",
            "Divergence|false_alarm_rate", "Behaviour-only|false_alarm_rate", "Divergence|AUC"]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(out[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
