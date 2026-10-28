"""Experiment 1c: the LLM-as-judge baseline, on the held-out test split.

Local Ollama models (free) judge every test run from its description and
normalised trace (src/baselines/llm_as_judge.py). The judge rows are scored with
the same metrics, group bootstrap and McNemar's test as Exp 1, against the
frozen Divergence predictions in results/exp1_predictions.csv.

    .venv/bin/python -m src.experiments.exp1c_llm_judge --model qwen2.5:7b --model llama3.1:8b
    # smoke test (JSON validity only, fine-tune split, no metrics):
    .venv/bin/python -m src.experiments.exp1c_llm_judge --model qwen2.5:7b --smoke 8

Writes results/exp1_llm_judge.csv (one row per judge) and
results/exp1_llm_judge_predictions.csv.
"""

import argparse
import time

import pandas as pd

from src.baselines.llm_as_judge import PROMPT_VERSION, LLMJudge
from src.config import RESULTS_DIR
from src.data.merge_labels import load_labelled_dataset
from src.evaluation.metrics import group_bootstrap_ci, mcnemar_test, point_metrics
from src.experiments.exp1_baseline_comparison import MAIN


def run_judge(judge: LLMJudge, rows: list[dict]) -> pd.DataFrame:
    out, t0 = [], time.time()
    for i, r in enumerate(rows, 1):
        rec = judge.judge(f"{r['sample_id']}|{r['mode']}", r["description"], r["trace"])
        out.append({"sample_id": r["sample_id"], "mode": r["mode"], "score": rec["score"],
                    "verdict": rec["verdict"], "parse_ok": rec["parse_ok"], "reason": rec["reason"]})
        if i % 10 == 0 or i == len(rows):
            print(f"  {judge.model}: {i}/{len(rows)} ({time.time() - t0:.0f}s)", flush=True)
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--smoke", type=int, default=0, help="only check JSON on N fine-tune runs")
    args = ap.parse_args()

    if args.smoke:
        rows = load_labelled_dataset(("finetune",))[:: max(1, 200 // args.smoke)][: args.smoke]
        for model in args.model:
            df = run_judge(LLMJudge(model), rows)
            print(df[["sample_id", "mode", "verdict", "score", "parse_ok", "reason"]].to_string(index=False))
        return

    preds = pd.read_csv(RESULTS_DIR / "exp1_predictions.csv")
    rows = load_labelled_dataset(("held_out_test",))
    y, groups, main_v = preds["label"].values, preds["group"].values, preds[f"{MAIN}|verdict"].values
    summary, merged = [], preds[["sample_id", "mode", "group", "label", "dataset_label", f"{MAIN}|verdict"]].copy()
    for model in args.model:
        df = run_judge(LLMJudge(model), rows)
        df = preds[["sample_id", "mode"]].merge(df, on=["sample_id", "mode"], how="left", validate="one_to_one")
        s, v = df["score"].values, df["verdict"].values
        m = point_metrics(y, s, v)
        ci = group_bootstrap_ci(y, s, v, groups)
        t = mcnemar_test(y, main_v, v)
        within = {f"AUC_{mode}": point_metrics(g["label"], df.loc[g.index, "score"], df.loc[g.index, "verdict"])["AUC"]
                  for mode, g in preds.groupby("mode")}
        summary.append({"system": f"LLM-as-judge ({model})", "role": "baseline", "prompt": PROMPT_VERSION, **m,
                        "AUC_lo": ci["AUC"][0], "AUC_hi": ci["AUC"][1], "F1_lo": ci["F1"][0], "F1_hi": ci["F1"][1],
                        "divergence_right_only": t["A_right_B_wrong"], "baseline_right_only": t["A_wrong_B_right"],
                        "mcnemar_p": t["p_value"], "parse_failures": int((~df["parse_ok"]).sum()), **within})
        merged[f"{model}|score"], merged[f"{model}|verdict"], merged[f"{model}|reason"] = s, v, df["reason"]
    summary = pd.DataFrame(summary)
    summary.to_csv(RESULTS_DIR / "exp1_llm_judge.csv", index=False)
    merged.to_csv(RESULTS_DIR / "exp1_llm_judge_predictions.csv", index=False)
    print(summary.drop(columns=["role", "prompt"]).round(3).T.to_string())


if __name__ == "__main__":
    main()
