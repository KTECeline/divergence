"""Build the INSTRUCTED-mode review slice: validate the prose-instruction payloads.

Instructed runs (a complying, low-refusal agent TOLD to run each skill's
documented workflow) give 114 malware runs the agent-rule calls a payload
(ran_skill_code or risky_actions_no_skill_code). That is provisional, so a
person checks them: is it a TRUE prose-instruction payload, or incidental (the
agent legitimately read the skill's own config / called a declared API)?

All instructed skills are malicious and PROSE-ONLY (no script). The benign
confound is already covered by the direct review, so this slice has no benign
rows; instead priority B samples the `commands_only` runs (the agent ran but
tripped nothing — did the rule miss a payload?) and includes every refusal
(did the compliant prompt still get declined?).

Run:  python -m src.data.review_sheet_instructed
"""

import csv
import json
import random
from pathlib import Path

from src.config import (
    INSTRUCTED_SAMPLES_PATH, RANDOM_SEED, REVIEW_DIR, SKILLS_DIR, SPLIT_ASSIGNMENT_PATH,
)
from src.data.loader import load_samples
from src.data.review_sheet import BEHAVIOURS, suspicious_lines

SHEET_PATH = REVIEW_DIR / "instructed_review_sheet.csv"
PAGE_PATH = REVIEW_DIR / "review_instructed.html"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "review_instructed.html"

# priority A = the candidate positives to validate (all 114 revealed payloads);
# B = did the rule miss anything, and did the compliant prompt still get refused?
A_SAMPLE = {
    (1, "risky_actions_no_skill_code"): 999,  # all: read secret / persistence / phoned out
    (1, "ran_skill_code"): 999,               # all: ran the skill's own code
}
B_SAMPLE = {
    (1, "commands_only"): 30,          # ran commands but nothing tripped: missed payload?
    (1, "read_only"): 15,              # only read: missed payload?
    (1, "declined_security"): 999,     # all refusals: did the compliant prompt still fail?
    (1, "blocked_env"): 999,
}
COLUMNS = [
    "priority", "sample_id", "split", "dataset_label", "attack_vector", "behaviour_class",
    "behaviour_name", "what_to_look_for", "provisional_outcome", "description",
    "suspicious_lines", "skill_script_execs", "sensitive_paths", "persistence_writes",
    "dns_domains", "network_connects", "actions", "reviewed_outcome", "reviewer_notes",
]


def _actions_text(s) -> str:
    """What the agent did, in order, as the reviewer sees them."""
    lines = [f"{a['action']}: {a['target'][:140]}"
             + ("" if a["status"] == "ok" else f"  [{a['status']}]")
             for a in s.trace]
    head = lines[:40]
    return "\n".join(head) + (f"\n... (+{len(lines) - 40} more)" if len(lines) > 40 else "")


def _row(s, split, priority):
    sig = s.signals
    label, folder = s.sample_id.split("/", 1)
    return {
        "priority": priority, "sample_id": s.sample_id, "split": split,
        "dataset_label": "malicious" if s.dataset_label else "benign",
        "attack_vector": s.attack_vector or s.source or "", "behaviour_class": s.behaviour_class or "",
        "behaviour_name": BEHAVIOURS.get(s.behaviour_class or "", ("", ""))[0],
        "what_to_look_for": BEHAVIOURS.get(s.behaviour_class or "", ("", "unknown (wild sample): use the suspicious lines"))[1]
        if s.dataset_label else "benign: is the flagged action legitimate for this skill?",
        "provisional_outcome": s.observed_outcome, "description": s.description,
        "suspicious_lines": suspicious_lines(SKILLS_DIR / label / folder) if s.dataset_label else "",
        "skill_script_execs": " | ".join(sig.get("skill_script_execs", [])),
        "sensitive_paths": " ".join(sig.get("sensitive_paths", [])),
        "persistence_writes": " ".join(sig.get("persistence_writes", [])),
        "dns_domains": " ".join(sig.get("dns_domains", [])),
        "network_connects": sig.get("network_connects", 0),
        "actions": _actions_text(s),
        "reviewed_outcome": "", "reviewer_notes": "",
    }


def build_sheet(seed: int = RANDOM_SEED) -> list[dict]:
    samples = [s for s in load_samples(INSTRUCTED_SAMPLES_PATH) if s.description]
    with open(SPLIT_ASSIGNMENT_PATH, newline="", encoding="utf-8") as f:
        split_of = {r["sample_id"]: r["split"] for r in csv.DictReader(f)}
    rng = random.Random(seed)

    def pick(spec, priority):
        rows = []
        for (lbl, outcome), n in spec.items():
            pool = [s for s in samples if s.dataset_label == lbl and s.observed_outcome == outcome]
            rows += [_row(s, split_of.get(s.sample_id, "?"), priority)
                     for s in rng.sample(pool, min(n, len(pool)))]
        return rows

    rows = pick(A_SAMPLE, "A") + pick(B_SAMPLE, "B")
    rows.sort(key=lambda r: (r["priority"], r["provisional_outcome"], r["sample_id"]))
    return rows


if __name__ == "__main__":
    rows = build_sheet()
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    with open(SHEET_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    PAGE_PATH.write_text(TEMPLATE_PATH.read_text(encoding="utf-8").replace("__ROWS__", data), encoding="utf-8")
    n_a = sum(r["priority"] == "A" for r in rows)
    print(f"{len(rows)} rows ({n_a} priority A, {len(rows) - n_a} priority B) -> {SHEET_PATH}")
    print(f"review page -> {PAGE_PATH}")
