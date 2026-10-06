"""Unit tests for DivergenceEvaluator (build order item 16)."""

from src.evaluator.divergence_evaluator import DivergenceResult


def test_result_object_shape():
    result = DivergenceResult(
        consistency_score=0.31,
        structural_flags=["flag_unmentioned_domain"],
        verdict="FLAG",
        reasoning="Low semantic alignment between stated purpose and observed behaviour.",
    )
    assert 0.0 <= result.consistency_score <= 1.0
    assert result.verdict in ("ALLOW", "FLAG")
