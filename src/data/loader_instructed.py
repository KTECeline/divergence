"""Build one SkillSample per instructed-agent run -> samples_instructed.jsonl.

Instructed runs (Stage 3, sandbox/instructed_agent) re-run the ~361 action-
producing malicious PROSE-ONLY skills (no runnable script, no payload under the
aligned agent, not reply-only) with a low-refusal, tool-capable model and a
compliant sandbox-analysis prompt. This is the ONLY mode that can surface a
prose-instruction payload — one that becomes real actions only when an agent
reads SKILL.md and follows it. It is a POSITIVE-DATA SOURCE, not the deployment
reality; the aligned run stays the realistic set and labels still come from the
hand review, never from which mode produced the trace.

Unlike direct mode, these ARE agent runs (tool calls present), so this loader
uses the AGENT outcome rules (provisional_outcome) exactly like loader.py, and
reads the same trace shape. Each sample keeps the SAME sample_id (hence the same
frozen split) as its Stage 2 counterpart, so nothing leaks across train/test
just because a skill was observed a third way.

Run:  python -m src.data.loader_instructed
"""

import csv
import json

from src.config import (
    INSTRUCTED_SAMPLES_PATH, INSTRUCTED_TRACES_DIR, SKILLS_DIR, SPLIT_ASSIGNMENT_PATH,
)
from src.data.loader import group_key, load_inventory, parse_skill_md
from src.data.outcome import SCRIPT_EXT, provisional_outcome, signals
from src.data.schema import SkillSample
from src.preprocessing.normalise_trace import attribution_coverage, normalise

# Buckets that mean the compliant agent actually produced risky behaviour, i.e.
# a prose-instruction payload was revealed (vs still refusing / doing nothing).
PAYLOAD_BUCKETS = ("ran_skill_code", "risky_actions_no_skill_code")


def _split_map() -> dict[str, str]:
    with open(SPLIT_ASSIGNMENT_PATH, newline="", encoding="utf-8") as f:
        return {r["sample_id"]: r["split"] for r in csv.DictReader(f)}


def build_instructed_samples() -> list[SkillSample]:
    inv = load_inventory()
    split_of = _split_map()
    with open(INSTRUCTED_TRACES_DIR / "summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    samples = []
    for row in rows:
        label, folder = row["label"], row["skill"]
        skill_dir = SKILLS_DIR / label / folder
        name, desc, body, desc_source = parse_skill_md(
            (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        result = json.loads((INSTRUCTED_TRACES_DIR / "results" / label / f"{folder}.json").read_text(encoding="utf-8"))
        actions = normalise(result)
        script_files = {p.name for p in skill_dir.rglob("*") if p.is_file() and p.name.endswith(SCRIPT_EXT)}
        sig = signals(result, actions, script_files)
        tax = inv.get(folder, {}) if label == "malware" else {}
        sample_id = f"{label}/{folder}"
        samples.append(SkillSample(
            sample_id=sample_id,
            skill_name=name or folder,
            description=desc,
            trace=actions,
            dataset_label=1 if label == "malware" else 0,
            source=tax.get("source"),
            attack_vector=tax.get("vector"),
            behaviour_class=tax.get("behaviour"),
            insertion_strategy=tax.get("insertion"),
            group_key=group_key(folder, tax.get("source")),
            has_scripts=(skill_dir / "scripts").is_dir(),
            execution_mode="agent_instructed",
            observed_outcome=provisional_outcome(sig),
            signals=sig,
            timed_out=str(row.get("timed_out")).lower() == "true",
            metadata={
                "folder": folder,
                "skill_md_body": body,
                "description_source": desc_source,
                "split": split_of.get(sample_id, "unassigned"),
                "agent_model": row.get("model"),
                "duration_s": float(row.get("duration_s") or 0),
                "exit_code": row.get("exit_code") or "",
                "attribution_coverage": round(attribution_coverage(result), 3),
                "run_error": row.get("error") or "",
            },
        ))
    return samples


def save_instructed_samples(samples: list[SkillSample]) -> None:
    INSTRUCTED_SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTRUCTED_SAMPLES_PATH, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import collections

    out = build_instructed_samples()
    save_instructed_samples(out)
    oc = collections.Counter(s.observed_outcome for s in out)
    revealed = sum(oc.get(b, 0) for b in PAYLOAD_BUCKETS)
    declined = oc.get("declined_security", 0) + oc.get("blocked_env", 0)
    print(f"{len(out)} instructed samples -> {INSTRUCTED_SAMPLES_PATH}")
    print("outcomes:", dict(oc))
    print(f"payload revealed (ran_skill_code + risky_actions): {revealed}/{len(out)}")
    print(f"still refused / blocked: {declined}/{len(out)}")
