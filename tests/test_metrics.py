import numpy as np

from src.evaluation.metrics import paired_auc_delta_ci


def test_paired_delta_is_zero_for_identical_scores():
    y = np.array([0, 1] * 10)
    s = np.linspace(0, 1, 20)
    d, lo, hi = paired_auc_delta_ci(y, s, s, groups=np.arange(20) // 2, n_boot=200)
    assert d == lo == hi == 0.0


def test_paired_delta_interval_excludes_zero_for_a_clear_gain():
    rng = np.random.default_rng(0)
    y = np.array([0, 1] * 30)
    weak = rng.random(60)                        # chance-level ranking
    strong = y + rng.normal(0, 0.3, 60)          # near-perfect ranking
    d, lo, hi = paired_auc_delta_ci(y, weak, strong, groups=np.arange(60), n_boot=500)
    assert d > 0.3 and lo > 0 and lo <= d <= hi
