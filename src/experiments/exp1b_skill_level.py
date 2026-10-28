"""Experiment 1b: skill-level results from the Exp 1 run-level predictions.

The install decision is per SKILL, while the model scores single runs. The rule,
fixed before this was computed (src/evaluator/agt_installer.py): a skill is
FLAGged if ANY of its runs is flagged, and its score is the highest run score.
This reads results/exp1_predictions.csv; nothing is refitted or re-scored, and
the test split is not used to choose anything.

Two ground truths are reported:
  * divergence (primary, the claim): the skill diverges if ANY of its runs was
    labelled POS by the reviewer.
  * malicious (secondary, context only): MalSkillBench's malicious/benign label.
    Malicious skills whose runs matched their description are NOT expected to be
    flagged, so recall here is a lower bound, not the system's target.

Caveat: in the labelled dataset direct and instructed modes cover different
skills, so almost every test skill has a single run, and the skill-level figures
mostly repeat the run-level ones. The live demo (sandbox/demo_pipeline.py) is
where several modes per skill are actually exercised.

Writes results/exp1_skill_level.csv and results/exp1_skill_predictions.csv.
"""

import pandas as pd

from src.config import RESULTS_DIR
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, point_metrics
from src.experiments.exp1_baseline_comparison import MAIN, ROLES


def skill_predictions(preds: pd.DataFrame) -> pd.DataFrame:
    """One row per skill: max score and any-flag verdict for every system."""
    agg = {"group": "first", "label": "max", "dataset_label": "first",
           "mode": lambda s: "+".join(sorted(s)), "sample_id": "size"}
    for name in ROLES:
        agg[f"{name}|score"] = "max"
        agg[f"{name}|verdict"] = "max"  # 0/1, so max == any
    return (preds.groupby("sample_id").agg(agg).rename(columns={"sample_id": "n_runs", "mode": "modes"})
            .reset_index())


def summarise_skills(skills: pd.DataFrame, truth: str, n_boot: int = 2000) -> pd.DataFrame:
    y, groups = skills[truth].values, skills["group"].values
    rows = []
    for name, role in ROLES.items():
        s, v = skills[f"{name}|score"].values, skills[f"{name}|verdict"].values
        m = point_metrics(y, s, v)  # no Brier: the max of run probabilities is not calibrated
        ci = group_bootstrap_ci(y, s, v, groups, n_boot=n_boot)
        row = {"truth": truth, "system": name, "role": role, **m,
               "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1], "F1_lo": ci["F1"][0], "F1_hi": ci["F1"][1]}
        if name != MAIN:
            t = mcnemar_test(y, skills[f"{MAIN}|verdict"].values, v)
            row.update({"divergence_right_only": t["A_right_B_wrong"], "baseline_right_only": t["A_wrong_B_right"],
                        "mcnemar_p": t["p_value"]})
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    preds = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    skills = skill_predictions(preds)
    skills.to_csv(RESULTS_DIR / "exp1_skill_predictions.csv", index=False)
    summary = pd.concat([summarise_skills(skills, "label"), summarise_skills(skills, "dataset_label")])
    summary.to_csv(RESULTS_DIR / "exp1_skill_level.csv", index=False)

    print(f"{len(preds)} runs -> {len(skills)} skills ({(skills.n_runs > 1).sum()} with more than one run), "
          f"{skills.group.nunique()} groups")
    print(skills.modes.value_counts().to_string())
    cols = ["system", "AUC", "AUC_lo", "AUC_hi", "F1", "precision", "recall", "accuracy", "false_alarm_rate",
            "mcnemar_p"]
    for truth, title in (("label", "truth = divergence (any run POS)"), ("dataset_label", "truth = malicious")):
        print(f"\n== {title} ==")
        print(summary[summary.truth == truth][cols].round(3).to_string(index=False))
    multi = skills[skills.n_runs > 1]
    print("\nSkills with several runs (where 'flag if any' can matter):")
    print(multi[["sample_id", "modes", "label", "dataset_label", f"{MAIN}|verdict"]].to_string(index=False))
    for sid in multi.sample_id:
        r = preds[preds.sample_id == sid][["mode", "label", f"{MAIN}|score", f"{MAIN}|verdict"]]
        print(f"  {sid}:\n{r.to_string(index=False)}")


if __name__ == "__main__":
    main()
