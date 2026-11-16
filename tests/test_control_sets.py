"""Exp 5 control-set builders (no model needed)."""

import csv

from divergence.data.control_sets import build_proxy_labelling_sheet, build_swapped_description_set


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


# --- Exp 5: the judge's answer cache must be keyed on the description that was judged ---------

def test_judge_cache_never_shares_an_answer_between_two_descriptions(tmp_path, monkeypatch):
    """The same run appears in both swapped sets with different donor descriptions (the 2026-11-14 bug)."""
    import divergence.baselines.llm_as_judge as lj
    from divergence.experiments.exp5_control_experiments import judge_key

    run = {"sample_id": "benign/a", "mode": "direct", "trace": []}
    first, second = {**run, "description": "Tracks parcels."}, {**run, "description": "Solves chess puzzles."}
    assert judge_key(first, "swap") != judge_key(second, "swap")
    assert judge_key(first, "swap") == judge_key(dict(first), "swap")               # same text -> same entry
    assert judge_key(first, "swap") != judge_key(first, "disclosed")
    assert judge_key(first, "original") == "benign/a|direct"                        # Exp 1c's key, unchanged

    asked = []

    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": '{"divergent": false, "probability": 10, "reason": "ok"}'}}

    def post(url, **kw):
        asked.append(kw["json"]["messages"][1]["content"])
        return Reply()

    monkeypatch.setattr(lj.requests, "post", post)
    judge = lj.LLMJudge("fake-model", cache_dir=tmp_path)
    for r in (first, second, first, second):
        judge.judge(judge_key(r, "swap"), r["description"], r["trace"])
    assert len(asked) == 2 and "Tracks parcels." in asked[0] and "Solves chess puzzles." in asked[1]
    again = lj.LLMJudge("fake-model", cache_dir=tmp_path)                           # reloaded from disk
    again.judge(judge_key(second, "swap"), second["description"], second["trace"])
    assert len(asked) == 2
