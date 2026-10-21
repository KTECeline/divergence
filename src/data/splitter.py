"""Split the runs into fine-tune / calibration / held-out test, with no leakage.

Viva priority #1: near-duplicates must not straddle splits. Two runs land in
the same group (and so the same split) if they share
  * a group_key — generated variants of one base skill (`x`, `x__CI_B4`,
    `x__PI_B10`) and the benign skill they were made from; or wild samples of
    one family (`wallet-tracker-zih4w`, `wallet-tracker-bf3bs`); or
  * an identical description — different folders, same declared intent.
Groups are merged with union-find, then assigned with StratifiedGroupKFold
(5 folds, stratified on dataset_label x source/vector): folds 0-1 fine-tune,
fold 2 calibration, folds 3-4 held-out test (40/20/40).

The split is made on groups and dataset labels only, BEFORE the observed-
behaviour labels are finalised, so changing the labels later (after the hand
review) can never move a run between splits.

Run:  python -m src.data.splitter
"""

import csv
import json
from collections import Counter

from sklearn.model_selection import StratifiedGroupKFold

from src.config import (
    CALIBRATION_SPLIT_PATH, FINETUNE_SPLIT_PATH, HELD_OUT_TEST_SPLIT_PATH,
    RANDOM_SEED, SPLIT_ASSIGNMENT_PATH, SPLIT_FOLDS,
)
from src.data.schema import SkillSample

SPLIT_PATHS = {
    "finetune": FINETUNE_SPLIT_PATH,
    "calibration": CALIBRATION_SPLIT_PATH,
    "held_out_test": HELD_OUT_TEST_SPLIT_PATH,
}


def leakage_groups(samples: list[SkillSample]) -> list[str]:
    """One merged group id per sample (union of group_key and identical description)."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for s in samples:
        find("g:" + s.group_key)
        desc = " ".join(s.description.lower().split())
        if desc:
            union("g:" + s.group_key, "d:" + desc)
    return [find("g:" + s.group_key) for s in samples]


def stratum(s: SkillSample) -> str:
    if s.dataset_label == 0:
        return "benign/scripts" if s.has_scripts else "benign/plain"
    return f"malware/{s.attack_vector or s.source or 'unknown'}"


def assign_splits(samples: list[SkillSample], seed: int = RANDOM_SEED) -> list[str]:
    """Split name per sample, same order as samples."""
    groups = leakage_groups(samples)
    y = [stratum(s) for s in samples]
    fold_of = [0] * len(samples)
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    for k, (_, test_idx) in enumerate(sgkf.split(samples, y, groups)):
        for i in test_idx:
            fold_of[i] = k
    by_fold = {f: name for name, folds in SPLIT_FOLDS.items() for f in folds}
    return [by_fold[f] for f in fold_of]


def check_no_leakage(samples: list[SkillSample], splits: list[str]) -> None:
    """Raise if any merged group, group_key or description spans two splits."""
    for key_fn, what in ((lambda s: s.group_key, "group_key"),
                         (lambda s: " ".join(s.description.lower().split()), "description")):
        seen: dict[str, str] = {}
        for s, sp in zip(samples, splits):
            k = key_fn(s)
            if not k:
                continue
            if seen.setdefault(k, sp) != sp:
                raise AssertionError(f"leak: {what} {k[:60]!r} in {seen[k]} and {sp}")


def make_splits(samples: list[SkillSample], seed: int = RANDOM_SEED) -> list[str]:
    """Create, check and persist the three leakage-free splits.

    Runs without a description (a broken generator file) are dropped here,
    since Divergence has nothing to compare their trace against."""
    kept = [s for s in samples if s.description]
    dropped = [s.sample_id for s in samples if not s.description]
    splits = assign_splits(kept, seed)
    check_no_leakage(kept, splits)
    groups = leakage_groups(kept)

    SPLIT_ASSIGNMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPLIT_ASSIGNMENT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "split", "leakage_group", "group_key", "stratum"])
        for s, sp, g in zip(kept, splits, groups):
            w.writerow([s.sample_id, sp, g, s.group_key, stratum(s)])
        for sid in dropped:
            w.writerow([sid, "excluded_no_description", "", "", ""])
    for name, path in SPLIT_PATHS.items():
        with open(path, "w", encoding="utf-8") as f:
            for s, sp in zip(kept, splits):
                if sp == name:
                    f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    return splits


if __name__ == "__main__":
    from src.data.loader import load_samples

    samples = load_samples()
    kept = [s for s in samples if s.description]
    splits = make_splits(samples)
    print(f"{len(kept)} runs split, {len(samples) - len(kept)} excluded (no description)")
    print(f"leakage groups: {len(set(leakage_groups(kept)))} (from {len({s.group_key for s in kept})} group_keys)")
    for name in SPLIT_PATHS:
        c = Counter(stratum(s) for s, sp in zip(kept, splits) if sp == name)
        print(f"  {name:14} {sum(c.values()):5}  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
