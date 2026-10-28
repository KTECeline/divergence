"""Experiment 5: inconsistency vs maliciousness controls. Build order item 15.

Tests whether Divergence detects intent-behaviour divergence or just
maliciousness. All on the held-out test split; nothing is fitted or tuned:

  5a. Proxy validity: a hand-labelling sheet of the positive runs (does the
      description disclose the harmful step?). Labelled by hand, not here.
  5b. Swapped description: a benign run's trace with another skill's
      description. Benign but inconsistent -> ideal verdict FLAG.
      (secondary: every negative test run, benign or malicious skill)
  5c. Disclosed payload: a positive run's trace with a description rewritten to
      state what it did. Malicious but consistent -> ideal verdict ALLOW.

Each control is compared, run by run, with the SAME trace under its original
description, so only the description changes. If 5c stays mostly flagged, the
model is detecting maliciousness, and the report's claims must be narrowed.

Systems: Divergence, the description-blind behaviour-only rules (unchanged by
construction: the reference for "ignores the description"), and the strongest
LLM judge (qwen2.5:7b).

Writes results/exp5_controls.csv and results/exp5_control_predictions.csv.
"""

import numpy as np
import pandas as pd
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint

from src.baselines import behaviour_only
from src.baselines.llm_as_judge import LLMJudge
from src.config import RANDOM_SEED, RESULTS_DIR, VERDICT_FLAG
from src.data.control_sets import (build_disclosed_payload_set, build_proxy_labelling_sheet,
                                   build_swapped_description_set)
from src.data.merge_labels import load_labelled_dataset
from src.evaluator.divergence_evaluator import DivergenceEvaluator
from src.preprocessing.structural_flags import compute_structural_flags

JUDGE = "qwen2.5:7b"


def score(rows: list[dict], evaluator: DivergenceEvaluator, judge: LLMJudge, tag: str) -> pd.DataFrame:
    """Every system's verdict on each (description, trace) pair."""
    results = evaluator.evaluate_batch([(r["description"], r["trace"]) for r in rows])
    out = []
    for r, res in zip(rows, results):
        key = f"{r['sample_id']}|{r['mode']}" + ("" if tag == "original" else f"|{tag}")
        j = judge.judge(key, r["description"], r["trace"])
        flags = compute_structural_flags(r["description"], r["trace"])
        out.append({"sample_id": r["sample_id"], "mode": r["mode"], "condition": tag,
                    "div_prob": res.probability, "div_consistency": res.consistency_score,
                    "div_flag": int(res.verdict == VERDICT_FLAG), "div_flags": ",".join(res.structural_flags),
                    "flag_unmentioned_domain": int(flags.flag_unmentioned_domain),
                    "flag_credential_access": int(flags.flag_credential_access),
                    "flag_undeclared_action_type": int(flags.flag_undeclared_action_type),
                    "behaviour_only_flag": int(behaviour_only.predict(r)),
                    "judge_flag": j["verdict"], "judge_prob": j["score"], "description": r["description"]})
    return pd.DataFrame(out)


def compare(name: str, orig: pd.DataFrame, ctrl: pd.DataFrame, ideal: int) -> list[dict]:
    """FLAG rate before/after, Wilson 95% CI, exact McNemar on the paired verdicts."""
    rows = []
    for sys_col, sys_name in (("div_flag", "Divergence"), ("behaviour_only_flag", "Behaviour-only"),
                              ("judge_flag", f"LLM judge ({JUDGE})")):
        a, b = orig[sys_col].values, ctrl[sys_col].values
        n, k = len(b), int(b.sum())
        lo, hi = proportion_confint(k, n, method="wilson")
        table = [[int(((a == 1) & (b == 1)).sum()), int(((a == 1) & (b == 0)).sum())],
                 [int(((a == 0) & (b == 1)).sum()), int(((a == 0) & (b == 0)).sum())]]
        rows.append({"control": name, "system": sys_name, "n": n, "ideal_verdict": "FLAG" if ideal else "ALLOW",
                     "flag_rate_original": a.mean(), "flag_rate_control": b.mean(),
                     "flag_rate_control_lo": lo, "flag_rate_control_hi": hi,
                     "correct_on_control": float((b == ideal).mean()),
                     "flipped_to_flag": table[1][0], "flipped_to_allow": table[0][1],
                     "mcnemar_p": float(mcnemar(table, exact=True).pvalue)})
    rows[0].update({"mean_prob_original": orig["div_prob"].mean(), "mean_prob_control": ctrl["div_prob"].mean(),
                    "mean_consistency_original": orig["div_consistency"].mean(),
                    "mean_consistency_control": ctrl["div_consistency"].mean()})
    return rows


def main() -> None:
    test = load_labelled_dataset(("held_out_test",))
    evaluator, judge = DivergenceEvaluator(), LLMJudge(JUDGE)

    n_sheet = build_proxy_labelling_sheet(test)
    print(f"5a: proxy labelling sheet with {n_sheet} positive runs -> data/processed/controls/proxy_labelling_sheet.csv")

    benign = [r for r in test if r["dataset_label"] == 0]
    negatives = [r for r in test if r["label"] == 0]
    sets = {
        "5b swapped (benign skills)": (benign, build_swapped_description_set(benign, RANDOM_SEED), 1),
        "5b swapped (all negative runs)": (negatives, build_swapped_description_set(negatives, RANDOM_SEED), 1),
        "5c disclosed payload": ([r for r in test if r["label"] == 1], build_disclosed_payload_set(test), 0),
    }
    summary, preds = [], []
    for name, (orig_rows, ctrl_rows, ideal) in sets.items():
        print(f"{name}: {len(ctrl_rows)} runs", flush=True)
        tag = "swap" if "swapped" in name else "disclosed"
        orig, ctrl = score(orig_rows, evaluator, judge, "original"), score(ctrl_rows, evaluator, judge, tag)
        ctrl["control_set"] = orig["control_set"] = name
        ctrl["donor"] = [r.get("donor", "") for r in ctrl_rows]
        summary += compare(name, orig, ctrl, ideal)
        preds += [orig, ctrl]
        if "disclosed" in name:  # manipulation check: did the rewrite name every host the trace contacted?
            still = ctrl["flag_unmentioned_domain"].values == 1
            print(f"  disclosed descriptions still missing a contacted host: {still.sum()}/{len(ctrl)}")
    summary = pd.DataFrame(summary)
    summary.to_csv(RESULTS_DIR / "exp5_controls.csv", index=False)
    pd.concat(preds).to_csv(RESULTS_DIR / "exp5_control_predictions.csv", index=False)
    cols = ["control", "system", "n", "ideal_verdict", "flag_rate_original", "flag_rate_control",
            "flag_rate_control_lo", "flag_rate_control_hi", "correct_on_control", "mcnemar_p"]
    print(summary[cols].round(3).to_string(index=False))
    print(summary.dropna(subset=["mean_prob_original"])[["control", "mean_prob_original", "mean_prob_control",
                                                         "mean_consistency_original", "mean_consistency_control"]]
          .round(3).to_string(index=False))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
