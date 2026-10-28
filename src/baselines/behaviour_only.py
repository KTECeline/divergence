"""Baseline: behaviour-only (non-trained). Build order item 11.

Uses the observed action trace alone, ignoring the declared description: the
same three structural rules, run with an EMPTY description, so every network
contact, credential read or risky action type counts as undeclared. This is a
"flag anything risky" detector. Divergence beating it means the description
matters; it is the direct test of "malicious behaviour != inconsistent
behaviour" (106 of the 159 negatives are malicious skills).
"""

from src.preprocessing.structural_flags import compute_structural_flags


def score(sample) -> int:
    """How many of the three rules fire on the behaviour alone (0-3); used for ranking."""
    return sum(compute_structural_flags("", sample["trace"]).as_list())


def predict(sample) -> int:
    return int(score(sample) > 0)
