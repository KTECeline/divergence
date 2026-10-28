"""Baseline: capability overlap (non-trained, no embedding).

Turns both sides into a set of capability categories and compares the sets:
  declared = categories the description has vocabulary for (the same word lists
             the structural flags use);
  observed = categories the trace performed (network, credential reads,
             persistence, mass deletion, privilege change, encoded payload,
             remote shell; the same trace parsing as the flags).
Score = 1 - Jaccard(declared, observed), higher = less overlap; verdict FLAG
when the trace used any capability the description does not declare.

It reads the description, unlike behaviour-only, but only at category level:
no host names, no semantic similarity. Divergence beating it is the direct
test of "does the embedding (and host-level matching) add anything over a
plain declared-vs-observed comparison?".
"""

from src.preprocessing.structural_flags import CREDENTIAL_WORDS, DECLARES, _mentions, _observed

CATEGORIES = tuple(DECLARES) + ("credentials",)


def declared(description: str) -> set[str]:
    words = {**DECLARES, "credentials": CREDENTIAL_WORDS}
    return {c for c in CATEGORIES if _mentions(description, words[c])}


def observed(trace: list[dict]) -> set[str]:
    seen = _observed(trace)
    return set(seen["kinds"]) | ({"credentials"} if seen["credential_reads"] else set())


def score(sample) -> float:
    d, o = declared(sample["description"]), observed(sample["trace"])
    if not d | o:
        return 0.0
    return 1 - len(d & o) / len(d | o)


def predict(sample) -> int:
    return int(bool(observed(sample["trace"]) - declared(sample["description"])))
