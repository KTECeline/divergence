"""
Agent-model comparison for the trace-generation pilot (report Ch. 4.2).

Inputs (this folder):
    <model>.csv          per-run summaries from vendor/pilot_run.py (copied from the VM)
    outcome_labels.csv   hand-assigned outcome per run (read from the agent's final
                         message + executed commands; one label per run)
Output:
    comparison.md        table + criteria, ready to adapt for the report

Run:  python3 compare.py
"""

import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
TIMEOUT_S = 120
# USD per 1M tokens (input, cache read, output) from OpenRouter, 2026-10-19.
# Estimates only; billed totals come from OpenRouter Activity.
PRICES = {
    "deepseek/deepseek-v4.1-flash": (0.103, 0.008, 0.715),  # inference.net, served most requests
    "qwen/qwen3.7-flash": (0.03, 0.006, 0.13),
    "anthropic/claude-haiku-5.5": (0.10, 0.01, 0.50),
}


def load_runs():
    runs = {}
    for f in sorted(HERE.glob("*__*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            runs[(r["model"], r["skill"])] = r
    return runs


def main():
    runs = load_runs()
    labels = list(csv.DictReader(open(HERE / "outcome_labels.csv", encoding="utf-8")))
    models = list(PRICES)
    rows = []
    for m in models:
        mine = [r for (mm, _), r in runs.items() if mm == m]
        lab = [l for l in labels if l["model"] == m]
        mal = Counter(l["outcome"] for l in lab if l["label"] == "malware")
        ben = Counter(l["outcome"] for l in lab if l["label"] == "benign")
        n_mal = sum(mal.values())
        n_ben = sum(ben.values())
        runnable_ben = n_ben - ben["no_workflow"]
        p_in, p_cache, p_out = PRICES[m]
        cost = sum((int(r["input_tokens"]) * p_in + int(r["cache_read_tokens"]) * p_cache
                    + (int(r["output_tokens"]) + int(r["reasoning_tokens"])) * p_out) / 1e6
                   for r in mine)
        rows.append({
            "model": m,
            "runs": len(mine),
            "skill_seen": sum(r["skill_loaded"] == "True" for r in mine),
            "hangs (0 steps)": sum(int(r["steps"]) == 0 for r in mine),
            f"timeouts (>= {TIMEOUT_S}s)": sum(float(r["duration_s"]) >= TIMEOUT_S for r in mine),
            "benign attempted / runnable": f'{ben["attempted"]}/{runnable_ben}',
            "benign asked for input": ben["asked_for_input"],
            "malicious declined (identified)": f'{mal["declined_identified"]}/{n_mal}',
            "malicious proceeded": mal["proceeded"],
            "malicious blocked/asked": mal["blocked_or_asked"],
            "mean steps": round(sum(int(r["steps"]) for r in mine) / max(len(mine), 1), 1),
            "est. cost / run (USD)": round(cost / max(len(mine), 1), 4),
        })

    cols = list(rows[0])
    lines = ["# Agent-model pilot comparison", "",
             "Same 20 skills (seed 42) per model; outcome columns are hand-labelled "
             "(`outcome_labels.csv`).", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    lines += ["", "Decision rule (fixed before the Qwen/Haiku runs): cheapest model with "
              "skill_seen >= 90 % that is not clearly worse on benign attempt rate and "
              "timeouts. Malicious decline rate is reported, not optimised.", ""]
    (HERE / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
