"""Unit tests for the logistic calibration layer (build order item 9)."""

import json

import numpy as np

from src.calibration.logistic_calibrator import FEATURES, LogisticCalibrator, feature_row
from src.preprocessing.structural_flags import StructuralFlags


def fitted():
    rng = np.random.default_rng(0)
    y = np.array([0, 1] * 20)
    X = np.column_stack([np.where(y == 1, 0.4, 0.8) + rng.normal(0, 0.1, 40), y, np.zeros(40), y])
    cal = LogisticCalibrator()
    cal.fit(X, y)
    return cal, X


def test_feature_row_order_matches_names():
    flags = StructuralFlags(True, False, True)
    assert feature_row(0.31, flags) == [0.31, 1.0, 0.0, 1.0]
    assert FEATURES == ("consistency_score", "flag_unmentioned_domain",
                        "flag_credential_access", "flag_undeclared_action_type")


def test_low_score_and_flags_mean_suspicious():
    cal, _ = fitted()
    p_bad, p_good = cal.predict_proba([[0.3, 1, 0, 1], [0.9, 0, 0, 0]])
    assert p_bad > 0.5 > p_good
    w = cal.coefficients()
    assert w["consistency_score"] < 0 and w["flag_unmentioned_domain"] > 0


def test_json_round_trip_is_exact_and_not_a_pickle(tmp_path):
    cal, X = fitted()
    path = tmp_path / "calibration_model.json"
    cal.save(path)
    assert json.loads(path.read_text())["feature_names"] == list(FEATURES)
    assert np.allclose(LogisticCalibrator.load(path).predict_proba(X), cal.predict_proba(X))
