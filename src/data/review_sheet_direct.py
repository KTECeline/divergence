"""Build the DIRECT-mode review slice: validate the rule-flagged payloads.

Direct runs (no agent) give ~241 malware runs the rule calls `payload_signal`.
That is a provisional rule, so a person checks a sample of them to estimate how
many are TRUE payloads vs incidental (a skill reading its own config, a benign
API call). Benign `payload_signal` runs are all included, because they are the
confound the whole project is about (a benign skill legitimately touching the
network), and a sample of the "nothing flagged" malware is included to catch
payloads the rule missed.

The reviewer answers one question per row: is this a real payload? Labels and
the local page are in data/processed/review/ (review_direct.html).

Run:  python -m src.data.review_sheet_direct
"""

import csv
import json
import random

from src.config import (
    DIRECT_SAMPLES_PATH, RANDOM_SEED, REVIEW_DIR, SKILLS_DIR, SPLIT_ASSIGNMENT_PATH,
)
from src.data.loader import load_samples
from src.data.review_sheet import BEHAVIOURS, suspicious_lines
from pathlib import Path

SHEET_PATH = REVIEW_DIR / "direct_review_sheet.csv"
PAGE_PATH = REVIEW_DIR / "review_direct.html"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "review_direct.html"

# priority A = the candidate positives to validate; B = confound + missed payloads
A_SAMPLE = {(1, "payload_signal"): 80, (1, "ran_skill_code"): 25}
B_SAMPLE = {
    (0, "payload_signal"): 999,      # ALL benign payload_signal: the confound
    (1, "ran_no_signal"): 15,        # malware that ran but tripped nothing: did we miss it?
    (1, "no_execution"): 10,         # malware that did not run: why?
    (0, "ran_skill_code"): 12,       # benign control
}
COLUMNS = [
    "priority", "sample_id", "split", "dataset_label", "attack_vector", "behaviour_class",
    "behaviour_name", "what_to_look_for", "provisional_outcome", "description",
    "suspicious_lines", "skill_script_execs", "sensitive_paths", "persistence_writes",
    "dns_domains", "network_connects", "actions", "reviewed_outcome", "reviewer_notes",
]


def _actions_text(s) -> str:
    """The skill's own actions, in order, as the reviewer sees them."""
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
    samples = [s for s in load_samples(DIRECT_SAMPLES_PATH) if s.description]
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
    rows.sort(key=lambda r: (r["priority"], r["dataset_label"] != "malicious",
                             r["provisional_outcome"], r["sample_id"]))
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
