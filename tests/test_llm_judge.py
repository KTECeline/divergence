"""LLM-as-judge baseline: prompt formatting and answer parsing (no model needed)."""

from src.baselines.llm_as_judge import MAX_LINES, format_trace, parse


def test_parse_valid_and_broken_answers():
    assert parse('{"divergent": true, "probability": 85, "reason": "sends data"}') == \
        {"verdict": 1, "score": 0.85, "reason": "sends data", "parse_ok": True}
    assert parse('Sure! {"divergent": false, "probability": 10}')["verdict"] == 0
    bad = parse("I cannot decide")
    assert bad["parse_ok"] is False and bad["score"] == 0.5 and bad["verdict"] == 0
    assert parse('{"divergent": true, "probability": 400}')["score"] == 1.0
    broken = parse('{"divergent": true, "probability": 85, "reason": "ran `curl -s "http://x"` here"}')
    assert broken["parse_ok"] and broken["verdict"] == 1 and broken["score"] == 0.85


def test_format_trace_collapses_repeats_and_caps_length():
    a = {"source": "process", "tool": "script", "action": "dns_lookup", "target": "x.example", "status": "ok"}
    assert format_trace([a, a, a]).splitlines()[1] == "  (previous line repeated 2 more times)"
    assert format_trace([]) == "(no observable actions)"
    many = [{**a, "target": f"h{i}.example"} for i in range(MAX_LINES + 5)]
    assert format_trace(many).splitlines()[-1] == "... 5 more actions not shown"
