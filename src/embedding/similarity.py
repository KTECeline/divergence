"""Cosine similarity scoring between description and enriched-trace vectors
(pipeline Step 4). Returns the semantic consistency score in [0, 1].

Cosine lies in [-1, 1]; it is rescaled as (1 + cos) / 2 rather than clipped,
so the ordering of scores (all that ranking metrics and the calibration layer
use) is unchanged. 1 = description and behaviour point the same way.
"""

import numpy as np


def consistency_score(vector_a, vector_b) -> float:
    """cosine_similarity(Vector_A, Vector_B) -> score in [0, 1]."""
    a, b = np.asarray(vector_a, dtype=float), np.asarray(vector_b, dtype=float)
    cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
    return float((1 + cos) / 2)


def consistency_scores(vectors_a: np.ndarray, vectors_b: np.ndarray) -> np.ndarray:
    """Row-wise consistency_score for two (n, d) arrays of paired vectors."""
    a = vectors_a / np.linalg.norm(vectors_a, axis=1, keepdims=True)
    b = vectors_b / np.linalg.norm(vectors_b, axis=1, keepdims=True)
    return (1 + np.sum(a * b, axis=1)) / 2
