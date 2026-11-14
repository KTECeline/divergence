"""Experiment 5a: proxy validity. Is a positive run really undisclosed behaviour?

The positive class was built from observed harmful actions (hand review), but the
research question is about divergence: behaviour the description does NOT
declare. 5a checks that gap by hand. Every positive test run (55) was labelled
`discloses_harmful_behaviour` = no / partial / yes: does the skill's own
description tell a user about the harmful step seen in its actions?
(Labels: labels/review_labels_proxy.csv, exported from data/processed/review/review_proxy.html.)

Analysis, fixed before looking at the verdicts. Reads saved predictions only:
nothing is fitted, no model or judge is called, the test split is not re-scored.

  1. Proxy validity: share of "no" (fully undisclosed), Wilson 95% CI; also "no"+"partial".
     Breakdown by mode, attack vector and behaviour class.
  2. Verdicts by disclosure: FLAG rate of Divergence, behaviour-only rules and the
     qwen2.5:7b judge in each group. A divergence detector should flag "no" runs and
     tend to pass "yes" runs; a maliciousness detector flags all of them.
  3. Label-noise sensitivity of Exp 1: a "yes" run is, by the divergence definition,
     consistent, so its POS label is proxy noise. Exp 1 metrics are recomputed with
     (a) the original labels, (b) "yes" runs excluded, (c) "yes" relabelled NEG,
     (d) "yes" and "partial" relabelled NEG (upper bound on the noise).

Writes results/exp5a_proxy_validity.csv, results/exp5a_by_group.csv,
results/exp5a_sensitivity.csv, results/exp5a_runs.csv.
"""

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.stats.proportion import proportion_confint

from divergence.config import LABELS_DIR, RESULTS_DIR
from divergence.data.control_sets import CONTROLS_DIR
from divergence.metrics import group_bootstrap_ci, point_metrics

LABELS_PATH = LABELS_DIR / "review_labels_proxy.csv"
SHEET_PATH = CONTROLS_DIR / "proxy_labelling_sheet.csv"
JUDGE = "qwen2.5:7b"
SYSTEMS = {  # name -> (score column, verdict column), from the saved Exp 1 predictions
    "Divergence": ("Divergence (full pipeline)|score", "Divergence (full pipeline)|verdict"),
    "Behaviour-only": ("Behaviour-only (rules, no description)|score", "Behaviour-only (rules, no description)|verdict"),
    f"LLM judge ({JUDGE})": (f"{JUDGE}|score", f"{JUDGE}|verdict"),
}
ORDER = ["no", "partial", "yes"]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(all 117 test runs with every system's predictions, the 55 labelled positive runs)."""
    preds = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    judge = pd.read_csv(RESULTS_DIR / "exp1_llm_judge_predictions.csv")[
        ["sample_id", "mode", f"{JUDGE}|score", f"{JUDGE}|verdict"]]
    test = preds.merge(judge, on=["sample_id", "mode"], how="left", validate="one_to_one")

    labels = pd.read_csv(LABELS_PATH)[["sample_id", "mode", "discloses_harmful_behaviour", "labeller_notes"]]
    sheet = pd.read_csv(SHEET_PATH)[["sample_id", "mode", "attack_vector", "behaviour_class"]]
    pos = labels.merge(sheet, on=["sample_id", "mode"], how="left", validate="one_to_one")
    pos = pos.merge(test, on=["sample_id", "mode"], how="left", validate="one_to_one")

    # integrity: exactly the test split's positive runs, each labelled once, all three values valid
    test_pos = test[test["label"] == 1][["sample_id", "mode"]]
    assert len(pos) == len(test_pos) == len(pos.drop_duplicates(["sample_id", "mode"])), "label/test mismatch"
    assert set(map(tuple, pos[["sample_id", "mode"]].values)) == set(map(tuple, test_pos.values))
    assert pos["discloses_harmful_behaviour"].isin(ORDER).all() and (pos["label"] == 1).all()
    test = test.merge(labels[["sample_id", "mode", "discloses_harmful_behaviour"]],
                      on=["sample_id", "mode"], how="left")
    return test, pos


def share(k: int, n: int) -> dict:
    lo, hi = proportion_confint(k, n, method="wilson")
    return {"k": k, "n": n, "share": k / n, "ci_lo": lo, "ci_hi": hi}


def proxy_validity(pos: pd.DataFrame) -> pd.DataFrame:
    d = pos["discloses_harmful_behaviour"]
    rows = [{"measure": f"disclosure = {v}", **share(int((d == v).sum()), len(d))} for v in ORDER]
    rows.append({"measure": "undisclosed or partial (no + partial)", **share(int(d.isin(["no", "partial"]).sum()), len(d))})
    return pd.DataFrame(rows)


def by_group(pos: pd.DataFrame) -> pd.DataFrame:
    out = []
    for col in ("mode", "attack_vector", "behaviour_class"):
        for val, g in pos.groupby(pos[col].fillna("unlabelled (wild)")):
            d = g["discloses_harmful_behaviour"]
            out.append({"breakdown": col, "value": val, "n": len(g),
                        **{f"n_{v}": int((d == v).sum()) for v in ORDER},
                        "share_no": float((d == "no").mean())})
    for name, (_, vcol) in SYSTEMS.items():  # FLAG rate per disclosure group
        for v in ORDER:
            g = pos[pos["discloses_harmful_behaviour"] == v]
            out.append({"breakdown": f"FLAG rate: {name}", "value": v, "n": len(g),
                        "flag_rate": float(g[vcol].mean()) if len(g) else np.nan,
                        "n_flagged": int(g[vcol].sum())})
        no, yes = pos[pos.discloses_harmful_behaviour == "no"][vcol], pos[pos.discloses_harmful_behaviour == "yes"][vcol]
        table = [[int(no.sum()), int(len(no) - no.sum())], [int(yes.sum()), int(len(yes) - yes.sum())]]
        out.append({"breakdown": f"FLAG rate: {name}", "value": "Fisher exact p (no vs yes)",
                    "n": len(no) + len(yes), "fisher_p": float(fisher_exact(table)[1])})
    return pd.DataFrame(out)


def sensitivity(test: pd.DataFrame) -> pd.DataFrame:
    d = test["discloses_harmful_behaviour"]
    variants = {
        "(a) original labels": (test, test["label"]),
        "(b) 'yes' runs excluded": (test[d != "yes"], test.loc[d != "yes", "label"]),
        "(c) 'yes' relabelled NEG": (test, test["label"].where(d != "yes", 0)),
        "(d) 'yes'+'partial' relabelled NEG": (test, test["label"].where(~d.isin(["yes", "partial"]), 0)),
    }
    rows = []
    for vname, (df, y) in variants.items():
        for sname, (scol, vcol) in SYSTEMS.items():
            m = point_metrics(y.values, df[scol].values, df[vcol].values)
            ci = group_bootstrap_ci(y.values, df[scol].values, df[vcol].values, df["group"].values)
            rows.append({"variant": vname, "system": sname, "n": len(df), "n_pos": int(y.sum()), **m,
                         "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1],
                         "F1_lo": ci["F1"][0], "F1_hi": ci["F1"][1]})
    return pd.DataFrame(rows)


def main() -> None:
    test, pos = load()
    pv, grp, sens = proxy_validity(pos), by_group(pos), sensitivity(test)
    pv.to_csv(RESULTS_DIR / "exp5a_proxy_validity.csv", index=False)
    grp.to_csv(RESULTS_DIR / "exp5a_by_group.csv", index=False)
    sens.to_csv(RESULTS_DIR / "exp5a_sensitivity.csv", index=False)
    keep = ["sample_id", "mode", "attack_vector", "behaviour_class", "discloses_harmful_behaviour",
            "labeller_notes"] + [c for _, cs in SYSTEMS.items() for c in cs]
    pos[keep].to_csv(RESULTS_DIR / "exp5a_runs.csv", index=False)

    pd.set_option("display.width", 200)
    print("1. Proxy validity (55 positive test runs)\n", pv.round(3).to_string(index=False))
    comp = grp[grp.breakdown.isin(["mode", "attack_vector", "behaviour_class"])]
    print("\n   by group\n", comp[["breakdown", "value", "n", "n_no", "n_partial", "n_yes", "share_no"]]
          .round(2).to_string(index=False))
    fr = grp[grp.breakdown.str.startswith("FLAG")]
    print("\n2. FLAG rate by disclosure\n", fr[["breakdown", "value", "n", "n_flagged", "flag_rate", "fisher_p"]]
          .round(3).to_string(index=False))
    print("\n3. Exp 1 label-noise sensitivity\n",
          sens[["variant", "system", "n", "n_pos", "AUC", "AUC_lo", "AUC_hi", "F1", "recall", "false_alarm_rate"]]
          .round(3).to_string(index=False))
    print("\n   the 'yes' / 'partial' runs\n",
          pos[pos.discloses_harmful_behaviour != "no"][["sample_id", "mode", "discloses_harmful_behaviour",
                                                        "Divergence (full pipeline)|score",
                                                        "Divergence (full pipeline)|verdict",
                                                        f"{JUDGE}|verdict"]].to_string(index=False))


if __name__ == "__main__":
    main()
