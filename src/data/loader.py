"""Build one SkillSample per sandbox run and save them to samples.jsonl.

Sources:
  * vendor/MalSkillBench/Dataset/Skills/<malware|benign>/<skill>/SKILL.md
    -> name and description (what a user is shown before installing);
  * malware/_source_inventory.txt -> taxonomy (vector / behaviour / insertion);
  * data/raw/traces/batch_out/ (Stage 2) -> the run's raw evidence, normalised
    by src/preprocessing/normalise_trace.py.

Run:  python -m src.data.loader
"""

import csv
import json
import re
from pathlib import Path

import yaml

from src.config import INVENTORY_PATH, SAMPLES_PATH, SKILLS_DIR, TRACES_DIR, TRACES_SUMMARY_PATH
from src.data.outcome import SCRIPT_EXT, provisional_outcome, signals
from src.data.schema import SkillSample
from src.preprocessing.normalise_trace import attribution_coverage, normalise

# e.g. "GENERATED  boot-persistence  <-  generated_malicious/PI/B5/full_camouflage_2026…"
INV_RE = re.compile(r"^(GENERATED|WILD|TEST)\s+(.+?)\s+<-\s+(\S+)")
SUFFIX_RE = re.compile(r"__(CI|PI|MIXED)_B\d+$")
WILD_FAMILY_RE = re.compile(r"-[a-z0-9]{4,12}$")
YAML_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:(\s|$)")
# MalSkillBench's generator left "=== END ORIGINAL SKILL.md ===" (and BEGIN)
# lines in 888 of 3,945 malicious SKILL.md files and in no benign one: a free
# label giveaway for anything that reads the body. Stripped before parsing.
GENERATOR_MARKER_RE = re.compile(r"^=== (?:BEGIN|END) ORIGINAL SKILL\.md.*===[ \t]*\n?", re.MULTILINE)


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, dict]:
    """name -> {source, vector, behaviour, insertion}; taxonomy only for GENERATED."""
    inv = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = INV_RE.match(line)
        if not m:
            continue
        src, name, origin = m.groups()
        parts = origin.split("/")
        tax = {"vector": None, "behaviour": None, "insertion": None}
        if src == "GENERATED" and len(parts) >= 4:
            tax = {"vector": parts[1], "behaviour": parts[2],
                   "insertion": re.sub(r"_\d{8}_\d{6}.*$", "", parts[3])}
        inv.setdefault(name, {"source": src, **tax})
    return inv


def group_key(name: str, source: str | None) -> str:
    """Split-grouping key. Generated variants share a base name with each other
    and with the benign skill they were made from; wild samples share a family
    prefix (the random suffix is dropped)."""
    if source == "WILD":
        return "wild:" + WILD_FAMILY_RE.sub("", name)
    return "base:" + SUFFIX_RE.sub("", name)


def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter, body). Handles a normal `---` block, one missing its
    opening `---` (the sandbox entrypoint repairs the same case), repeated
    `---` lines, and no frontmatter at all (a later `---` is then a horizontal
    rule, not a frontmatter end)."""
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    i, opened = 0, False
    while i < len(lines) and lines[i].strip() in ("", "---"):
        opened = opened or lines[i].strip() == "---"
        i += 1
    if i >= len(lines) or not YAML_KEY_RE.match(lines[i]):
        return "", "".join(lines[i:]) if opened else text
    for j in range(i, len(lines)):
        if lines[j].strip() == "---":
            return "".join(lines[i:j]), "".join(lines[j + 1:])
    return "", text


def first_paragraph(body: str, max_words: int = 80) -> str:
    """First prose paragraph of a markdown body (skips headings, code, lists)."""
    in_code = False
    for block in re.split(r"\n\s*\n", body):
        lines = []
        for line in block.splitlines():
            t = line.strip()
            if t.startswith("```"):
                in_code = not in_code
                continue
            if in_code or not t or t.startswith(("#", "|", "- [", "<!--", "---")):
                continue
            lines.append(t.lstrip(">*- ").strip())
        text = " ".join(lines)
        if len(text.split()) >= 5:
            words = re.sub(r"[*_`]", "", text).split()
            return " ".join(words[:max_words])
    return ""


def parse_skill_md(text: str) -> tuple[str, str, str, str]:
    """(name, description, body, description_source) from a SKILL.md,
    tolerant of broken frontmatter. description_source is "frontmatter" or
    "first_paragraph" (fallback when the frontmatter has no description)."""
    front, body = split_frontmatter(GENERATOR_MARKER_RE.sub("", text))
    meta = {}
    try:
        loaded = yaml.safe_load(front) if front else None
        if isinstance(loaded, dict):
            meta = loaded
    except yaml.YAMLError:
        pass
    name = str(meta.get("name") or "").strip()
    desc = str(meta.get("description") or "").strip()
    if not desc:  # malformed YAML: fall back to the raw line
        dm = re.search(r"^description:\s*['\"]?(.+?)['\"]?\s*$", front, re.MULTILINE)
        desc = dm.group(1).strip() if dm else ""
    if not name:
        nm = re.search(r"^name:\s*['\"]?([^'\"\n]+)", front, re.MULTILINE)
        name = nm.group(1).strip() if nm else ""
    source = "frontmatter"
    if not desc:
        # a truncated generator file can leave markdown inside the "frontmatter"
        desc, source = first_paragraph(body) or first_paragraph(front), "first_paragraph"
    return name, " ".join(desc.split()), body, source


def build_samples(traces_dir: Path = TRACES_DIR, skills_dir: Path = SKILLS_DIR) -> list[SkillSample]:
    inv = load_inventory()
    with open(traces_dir / "summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    samples = []
    for row in rows:
        label, folder = row["label"], row["skill"]
        skill_dir = skills_dir / label / folder
        name, desc, body, desc_source = parse_skill_md((skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        result = json.loads((traces_dir / "results" / label / f"{folder}.json").read_text(encoding="utf-8"))
        actions = normalise(result)
        script_files = {p.name for p in skill_dir.rglob("*") if p.is_file() and p.name.endswith(SCRIPT_EXT)}
        sig = signals(result, actions, script_files)
        tax = inv.get(folder, {}) if label == "malware" else {}
        samples.append(SkillSample(
            sample_id=f"{label}/{folder}",
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
            observed_outcome=provisional_outcome(sig),
            signals=sig,
            timed_out=row.get("timed_out") == "True",
            metadata={
                "folder": folder,
                "skill_md_body": body,
                "description_source": desc_source,
                "agent_model": row.get("model"),
                "trigger": row.get("trigger"),
                "duration_s": float(row.get("duration_s") or 0),
                "attribution_coverage": round(attribution_coverage(result), 3),
                "batch_outcome_v1": row.get("observed_outcome"),  # batch_run.py heuristic, superseded
            },
        ))
    return samples


def save_samples(samples: list[SkillSample], path: Path = SAMPLES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")


def load_samples(path: Path = SAMPLES_PATH) -> list[SkillSample]:
    with open(path, encoding="utf-8") as f:
        return [SkillSample.from_dict(json.loads(line)) for line in f if line.strip()]


if __name__ == "__main__":
    out = build_samples()
    save_samples(out)
    print(f"{len(out)} samples -> {SAMPLES_PATH}")
