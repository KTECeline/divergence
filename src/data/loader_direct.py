"""Build one SkillSample per direct-execution run -> samples_direct.jsonl.

Direct runs (Stage 3, sandbox/direct_exec) execute the skill's OWN documented
commands with no agent, so payloads fire without the agent's refusal. This
loader mirrors src/data/loader.py but reads data/raw/traces/direct_out/ and
tags every sample execution_mode="direct". Only the 573 skills that ship
runnable scripts have a direct run; the rest are agent-only.

Each direct sample keeps the SAME sample_id (and therefore the same split) as
its Stage 2 counterpart, so nothing leaks across the train/test boundary just
because a skill was run a second way.

Run:  python -m src.data.loader_direct
"""

import csv
import json

from src.config import (
    DIRECT_SAMPLES_PATH, DIRECT_TRACES_DIR, SKILLS_DIR, SPLIT_ASSIGNMENT_PATH,
)
from src.data.loader import group_key, load_inventory, parse_skill_md
from src.data.outcome import SCRIPT_EXT, provisional_outcome_direct, signals
from src.data.schema import SkillSample
from src.preprocessing.normalise_trace import attribution_coverage, normalise


def _split_map() -> dict[str, str]:
    with open(SPLIT_ASSIGNMENT_PATH, newline="", encoding="utf-8") as f:
        return {r["sample_id"]: r["split"] for r in csv.DictReader(f)}


def build_direct_samples() -> list[SkillSample]:
    inv = load_inventory()
    split_of = _split_map()
    with open(DIRECT_TRACES_DIR / "summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    samples = []
    for row in rows:
        label, folder = row["label"], row["skill"]
        skill_dir = SKILLS_DIR / label / folder
        name, desc, body, desc_source = parse_skill_md(
            (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        result = json.loads((DIRECT_TRACES_DIR / "results" / label / f"{folder}.json").read_text(encoding="utf-8"))
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
            execution_mode="direct",
            observed_outcome=provisional_outcome_direct(sig, actions),
            signals=sig,
            timed_out=str(row.get("timed_out")).lower() == "true",
            metadata={
                "folder": folder,
                "skill_md_body": body,
                "description_source": desc_source,
                "split": split_of.get(sample_id, "unassigned"),
                "duration_s": float(row.get("duration_s") or 0),
                "n_scripts": int(row.get("n_scripts") or 0),
                "attribution_coverage": round(attribution_coverage(result), 3),
                "run_error": row.get("error") or "",
            },
        ))
    return samples


def save_direct_samples(samples: list[SkillSample]) -> None:
    DIRECT_SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DIRECT_SAMPLES_PATH, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import collections

    out = build_direct_samples()
    save_direct_samples(out)
    n_mal = sum(s.dataset_label == 1 for s in out)
    oc = collections.Counter(s.observed_outcome for s in out if s.dataset_label == 1)
    print(f"{len(out)} direct samples ({n_mal} malware, {len(out) - n_mal} benign) -> {DIRECT_SAMPLES_PATH}")
    print("malware provisional outcomes:", dict(oc))
