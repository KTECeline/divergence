"""Build the Type-A RE-CHECK slice: positive labels with no action signal at all.

The three hand reviews give 153 POSITIVE runs (payload_attempted,
payload_confirmed, partial_blocked). A few were labelled positive although the
trace records NONE of the signals that would make the harm visible to
Divergence: no skill script run, no sensitive path, no persistence write, no
DNS lookup, no web fetch and zero network connects. Divergence compares the
description with ACTIONS, so a positive it cannot see in the trace is either a
label error (should be negative) or out of scope (should be excluded, like the
reply-only B10-B15 runs). This page asks that one question per row, before the
labels are merged into one dataset.

Run:  python -m src.data.review_sheet_recheck
"""

import csv
import json
from pathlib import Path

from src.config import (
    DIRECT_SAMPLES_PATH, INSTRUCTED_SAMPLES_PATH, PROJECT_ROOT, REVIEW_DIR, SAMPLES_PATH,
    SPLIT_ASSIGNMENT_PATH,
)
from src.data import review_sheet, review_sheet_instructed
from src.data.loader import load_samples

SHEET_PATH = REVIEW_DIR / "recheck_review_sheet.csv"
PAGE_PATH = REVIEW_DIR / "review_recheck.html"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "review_recheck.html"

POSITIVE = {"payload_attempted", "payload_confirmed", "partial_blocked"}
# mode -> (exported labels, samples, row builder). Direct and instructed share a row shape.
MODES = {
    "agent": (PROJECT_ROOT / "review_labels.csv", SAMPLES_PATH, review_sheet._row),
    "direct": (PROJECT_ROOT / "review_labels_direct.csv", DIRECT_SAMPLES_PATH, review_sheet_instructed._row),
    "instructed": (PROJECT_ROOT / "review_labels_instructed.csv", INSTRUCTED_SAMPLES_PATH, review_sheet_instructed._row),
}
COLUMNS = [
    "mode", "sample_id", "split", "dataset_label", "attack_vector", "behaviour_class",
    "behaviour_name", "what_to_look_for", "original_label", "original_notes", "description",
    "suspicious_lines", "actions", "agent_final_text", "recheck_decision", "reviewer_notes",
]


def no_action_signal(sig: dict) -> bool:
    """True when the trace holds nothing that would make a payload visible."""
    return not (sig.get("skill_script_execs") or sig.get("sensitive_paths")
                or sig.get("persistence_writes") or sig.get("dns_domains")
                or sig.get("web_fetches") or sig.get("network_connects", 0))


def build_sheet() -> list[dict]:
    with open(SPLIT_ASSIGNMENT_PATH, newline="", encoding="utf-8") as f:
        split_of = {r["sample_id"]: r["split"] for r in csv.DictReader(f)}
    rows = []
    for mode, (labels_path, samples_path, make_row) in MODES.items():
        samples = {s.sample_id: s for s in load_samples(samples_path)}
        with open(labels_path, newline="", encoding="utf-8") as f:
            labels = [l for l in csv.DictReader(f) if l["reviewed_outcome"] in POSITIVE]
        for l in labels:
            s = samples[l["sample_id"]]
            if not no_action_signal(s.signals):
                continue
            base = make_row(s, split_of.get(s.sample_id, "?"), "A")
            rows.append({
                **{k: base.get(k, "") for k in COLUMNS},
                "mode": mode,
                "original_label": l["reviewed_outcome"], "original_notes": l["reviewer_notes"],
                # the full trace, not just tool calls: the question is what actually ran
                "actions": review_sheet_instructed._actions_text(s),
                "recheck_decision": "", "reviewer_notes": "",
            })
    rows.sort(key=lambda r: (r["mode"], r["sample_id"]))
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
    by_mode = {m: sum(r["mode"] == m for r in rows) for m in MODES}
    print(f"{len(rows)} rows {by_mode} -> {SHEET_PATH}")
    print(f"review page -> {PAGE_PATH}")
