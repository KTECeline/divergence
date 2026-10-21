"""Build the hand-review sheet that turns provisional outcomes into labels.

Priority A rows are the likely positives, so ALL of them are included: every
malicious run where the rules saw skill code run, risky actions, or nothing
but reads. Priority B rows are fixed-size random samples from the larger
buckets, to measure how precise the rules are (are "declined_security" runs
really declines? does "commands_only" hide payloads?). The error rate found in
a B sample is then applied to the rest of its bucket.

The reviewer fills `reviewed_outcome` (see data/processed/review/README.md).
The agent's final text is shown to the reviewer only; it is never model input.

Run:  python -m src.data.review_sheet
"""

import csv
import json
import random

from src.config import RANDOM_SEED, REVIEW_DIR, SPLIT_ASSIGNMENT_PATH, TRACES_DIR
from src.data.loader import load_samples
from src.data.outcome import final_text

SHEET_PATH = REVIEW_DIR / "outcome_review_sheet.csv"
PRIORITY_A = {"ran_skill_code", "risky_actions_no_skill_code", "read_only"}  # malicious only
PRIORITY_B = {  # (dataset_label, provisional outcome) -> sample size
    (1, "commands_only"): 40,
    (1, "blocked_env"): 15,
    (1, "declined_security"): 15,
    (0, "ran_skill_code"): 8,
    (0, "risky_actions_no_skill_code"): 8,
    (0, "commands_only"): 8,
    (0, "blocked_env"): 8,
    (0, "declined_security"): 8,
}
COLUMNS = [
    "priority", "sample_id", "split", "dataset_label", "attack_vector", "behaviour_class",
    "insertion_strategy", "provisional_outcome", "description", "skill_script_execs",
    "sensitive_paths", "persistence_writes", "dns_domains", "web_fetches", "tool_actions",
    "agent_final_text", "reviewed_outcome", "reviewer_notes",
]


def _row(s, split, priority):
    sig = s.signals
    tools = [f"{a['action']}: {a['target'][:140]}" for a in s.trace if a["source"] == "tool"]
    label, folder = s.sample_id.split("/", 1)
    result = json.loads((TRACES_DIR / "results" / label / f"{folder}.json").read_text(encoding="utf-8"))
    return {
        "priority": priority, "sample_id": s.sample_id, "split": split,
        "dataset_label": "malicious" if s.dataset_label else "benign",
        "attack_vector": s.attack_vector or s.source or "", "behaviour_class": s.behaviour_class or "",
        "insertion_strategy": s.insertion_strategy or "", "provisional_outcome": s.observed_outcome,
        "description": s.description,
        "skill_script_execs": " | ".join(sig.get("skill_script_execs", [])),
        "sensitive_paths": " ".join(sig.get("sensitive_paths", [])),
        "persistence_writes": " ".join(sig.get("persistence_writes", [])),
        "dns_domains": " ".join(sig.get("dns_domains", [])),
        "web_fetches": " ".join(sig.get("web_fetches", [])),
        "tool_actions": "\n".join(tools[:15]) + (f"\n... (+{len(tools) - 15} more)" if len(tools) > 15 else ""),
        "agent_final_text": final_text(result)[:1200],
        "reviewed_outcome": "", "reviewer_notes": "",
    }


def build_sheet(seed: int = RANDOM_SEED) -> list[dict]:
    samples = [s for s in load_samples() if s.description]
    with open(SPLIT_ASSIGNMENT_PATH, newline="", encoding="utf-8") as f:
        split_of = {r["sample_id"]: r["split"] for r in csv.DictReader(f)}
    rng = random.Random(seed)
    rows = [_row(s, split_of[s.sample_id], "A") for s in samples
            if s.dataset_label == 1 and s.observed_outcome in PRIORITY_A]
    for (label, outcome), n in PRIORITY_B.items():
        pool = [s for s in samples if s.dataset_label == label and s.observed_outcome == outcome]
        rows += [_row(s, split_of[s.sample_id], "B") for s in rng.sample(pool, min(n, len(pool)))]
    rows.sort(key=lambda r: (r["priority"], r["dataset_label"] != "malicious", r["provisional_outcome"], r["sample_id"]))
    return rows


if __name__ == "__main__":
    rows = build_sheet()
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    with open(SHEET_PATH, "w", newline="", encoding="utf-8-sig") as f:  # -sig: Excel/Numbers read UTF-8
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    n_a = sum(r["priority"] == "A" for r in rows)
    print(f"{len(rows)} rows ({n_a} priority A, {len(rows) - n_a} priority B) -> {SHEET_PATH}")
