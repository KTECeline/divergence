"""Unit tests for SKILL.md parsing and split-group keys."""

from src.data.loader import group_key, parse_skill_md, split_frontmatter


def test_normal_frontmatter():
    name, desc, body, src = parse_skill_md("---\nname: demo\ndescription: Does a thing.\n---\n# Demo\n")
    assert (name, desc, src) == ("demo", "Does a thing.", "frontmatter")
    assert body.startswith("# Demo")


def test_missing_opening_dashes():
    front, body = split_frontmatter("name: demo\ndescription: x\n---\nbody")
    assert "description: x" in front and body == "body"


def test_horizontal_rule_is_not_frontmatter():
    text = "# Title\n\nThis skill watches a charger status page.\n\n---\n\nMore."
    name, desc, _, src = parse_skill_md(text)
    assert src == "first_paragraph"
    assert desc == "This skill watches a charger status page."


def test_generator_marker_stripped():
    text = ("---\nname: x\ndescription: Real description here.\n---\nbody\n"
            "=== END ORIGINAL SKILL.md ===\n## Setup\nrun this")
    _, desc, body, _ = parse_skill_md(text)
    assert "ORIGINAL SKILL.md" not in body
    assert desc == "Real description here."


def test_group_keys_tie_variants_together():
    assert group_key("webapp-testing__CI_B8", "GENERATED") == group_key("webapp-testing", None)
    assert group_key("wallet-tracker-zih4w", "WILD") == group_key("wallet-tracker-bf3bs", "WILD")
    assert group_key("a", None) != group_key("b", None)
