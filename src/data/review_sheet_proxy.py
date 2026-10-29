"""Build the Exp 5a DISCLOSURE slice: does each positive's description admit the harm?

The POS label says a harmful step is in the trace; it does not say the
description hid it. Divergence measures intent-behaviour mismatch, so the
labels only measure that if the positives' descriptions do NOT disclose the
harmful step. This page asks that one question for every POSITIVE test run
listed in proxy_labelling_sheet.csv (written by exp5_control_experiments).

The sheet itself is never edited: re-running Exp 5 rewrites it blank. Labels
export to review_labels_proxy.csv in the project root, like the other slices.

Run:  python -m src.data.review_sheet_proxy
"""

import csv
import json
from pathlib import Path

from src.config import REVIEW_DIR, SKILLS_DIR
from src.data.control_sets import CONTROLS_DIR
from src.data.review_sheet import BEHAVIOURS, suspicious_lines

SOURCE_PATH = CONTROLS_DIR / "proxy_labelling_sheet.csv"
PAGE_PATH = REVIEW_DIR / "review_proxy.html"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "review_proxy.html"


def build_rows() -> list[dict]:
    with open(SOURCE_PATH, newline="", encoding="utf-8") as f:
        sheet = list(csv.DictReader(f))
    rows = []
    for r in sheet:
        label, folder = r["sample_id"].split("/", 1)
        name, look = BEHAVIOURS.get(r["behaviour_class"], ("", "unknown (wild sample): use the suspicious lines"))
        rows.append({
            "sample_id": r["sample_id"], "mode": r["mode"],
            "attack_vector": r["attack_vector"], "behaviour_class": r["behaviour_class"],
            "behaviour_name": name, "what_to_look_for": look,
            "description": r["description"],
            # the trace exactly as Divergence's test run saw it (format_trace)
            "actions": r["actions"],
            "suspicious_lines": suspicious_lines(SKILLS_DIR / label / folder),
        })
    return rows


if __name__ == "__main__":
    rows = build_rows()
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    PAGE_PATH.write_text(TEMPLATE_PATH.read_text(encoding="utf-8").replace("__ROWS__", data), encoding="utf-8")
    by_mode = {m: sum(r["mode"] == m for r in rows) for m in sorted({r["mode"] for r in rows})}
    print(f"{len(rows)} rows {by_mode} from {SOURCE_PATH}")
    print(f"review page -> {PAGE_PATH}")
