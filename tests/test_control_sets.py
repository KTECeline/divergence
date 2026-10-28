"""Exp 5 control-set builders (no model needed)."""

import csv

from src.data.control_sets import build_proxy_labelling_sheet, build_swapped_description_set


def rows(n):
    return [{"sample_id": f"benign/s{i}", "mode": "direct", "group_key": f"g{i // 2}", "label": i % 2,
             "description": f"desc {i}", "trace": [], "attack_vector": None, "behaviour_class": None}
            for i in range(n)]


def test_swap_never_keeps_a_description_from_the_same_group():
    r = rows(8)
    sw = build_swapped_description_set(r, seed=42)
    assert [s["original_description"] for s in sw] == [x["description"] for x in r]
    donor_group = {x["sample_id"]: x["group_key"] for x in r}
    assert all(donor_group[s["donor"]] != s["group_key"] for s in sw)
    assert sorted(s["description"] for s in sw) == sorted(x["description"] for x in r)  # a permutation
    assert sw == build_swapped_description_set(r, seed=42)                              # seeded


def test_proxy_sheet_has_only_positive_runs(tmp_path):
    path = tmp_path / "sheet.csv"
    assert build_proxy_labelling_sheet(rows(6), path) == 3
    with open(path) as f:
        sheet = list(csv.DictReader(f))
    assert len(sheet) == 3 and sheet[0]["discloses_harmful_behaviour"] == ""
