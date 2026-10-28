"""Unit tests for the cosine consistency score (pipeline Step 4)."""

import numpy as np

from src.embedding.similarity import consistency_score, consistency_scores


def test_score_range_endpoints():
    v = np.array([1.0, 0.0])
    assert consistency_score(v, v) == 1.0
    assert consistency_score(v, -v) == 0.0
    assert consistency_score(v, np.array([0.0, 1.0])) == 0.5


def test_batch_matches_single():
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=(5, 8)), rng.normal(size=(5, 8))
    assert np.allclose(consistency_scores(a, b), [consistency_score(x, y) for x, y in zip(a, b)])
