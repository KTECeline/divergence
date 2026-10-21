"""Unit tests for the leakage-free split."""

import pytest

from src.data.schema import SkillSample
from src.data.splitter import assign_splits, check_no_leakage, leakage_groups


def _s(i, group, desc, label=0, vector=None):
    return SkillSample(sample_id=f"x/{i}", skill_name=str(i), description=desc, trace=[],
                       dataset_label=label, attack_vector=vector, group_key=group)


def _samples():
    out = []
    for i in range(100):
        out.append(_s(i, f"base:b{i}", f"benign skill {i}"))
        out.append(_s(1000 + i, f"base:m{i}", f"malicious skill {i}", 1, "CI" if i % 2 else "PI"))
    # variants of one base skill, and two folders with the same description
    out += [_s(5000, "base:b1", "variant of b1", 1, "CI"), _s(5001, "base:other", "benign skill 2")]
    return out


def test_identical_descriptions_share_a_group():
    s = _samples()
    g = dict(zip((x.sample_id for x in s), leakage_groups(s)))
    assert g["x/5001"] == g["x/2"]          # same description
    assert g["x/5000"] == g["x/1"]          # same group_key


def test_split_has_no_leakage_and_expected_sizes():
    s = _samples()
    splits = assign_splits(s, seed=0)
    check_no_leakage(s, splits)
    n = len(s)
    assert abs(splits.count("held_out_test") / n - 0.4) < 0.08
    assert abs(splits.count("calibration") / n - 0.2) < 0.08


def test_check_no_leakage_catches_a_leak():
    s = [_s(1, "base:a", "d1"), _s(2, "base:a", "d2")]
    with pytest.raises(AssertionError):
        check_no_leakage(s, ["finetune", "held_out_test"])
