"""Exp 1e (paired tests) and Exp 1f (threshold curve): the arithmetic, on tiny hand-checkable inputs."""

import numpy as np
import pytest

from divergence.experiments.exp1e_paired_tests import fa_delta_ci
from divergence.experiments.exp1f_threshold_curve import threshold_curve
from divergence.metrics import mcnemar_test


def test_rate_delta_is_b_minus_a_with_an_interval_around_it():
    a, b = np.array([0, 0, 1, 1]), np.array([1, 1, 1, 1])
    delta, lo, hi = fa_delta_ci(a, b, groups=np.arange(4), n_boot=300)
    assert delta == 0.5 and 0.0 <= lo <= delta <= hi <= 1.0
    assert fa_delta_ci(a, a, groups=np.arange(4), n_boot=100) == (0.0, 0.0, 0.0)


def test_runs_of_one_skill_group_are_resampled_together():
    # two groups, each internally identical: every resample is all-0, all-1 or the 50/50 mix
    a, b, groups = np.zeros(4, int), np.array([1, 1, 0, 0]), np.array(["g1", "g1", "g2", "g2"])
    _, lo, hi = fa_delta_ci(a, b, groups, n_boot=300)
    assert (lo, hi) == (0.0, 1.0)


def test_mcnemar_on_positives_counts_attacks_only_one_system_caught():
    y = np.ones(6, int)                       # positives only: "right" means the attack was flagged
    divergence = np.array([1, 1, 1, 0, 0, 0])
    comparison = np.array([1, 0, 0, 1, 1, 1])
    t = mcnemar_test(y, divergence, comparison)
    assert (t["A_right_B_wrong"], t["A_wrong_B_right"]) == (2, 3)


def test_exact_mcnemar_p_value_matches_the_binomial_by_hand():
    # 12 runs where only A is right, 0 where only B is: two-sided exact p = 2 * 0.5 ** 12
    y, a, b = np.zeros(12, int), np.zeros(12, int), np.ones(12, int)
    assert mcnemar_test(y, a, b)["p_value"] == pytest.approx(2 * 0.5 ** 12)


def test_threshold_curve_rows_by_hand():
    y, prob = [0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9]
    c = threshold_curve(y, prob).set_index("threshold")
    assert c.loc[0.0, ["recall", "false_alarm_rate"]].tolist() == [1.0, 1.0]        # everything flagged
    half = c.loc[0.5]                                                              # flags 0.6 (NEG) and 0.9 (POS)
    assert (half.true_positives, half.false_positives) == (1, 1)
    assert (half.recall, half.false_alarm_rate, half.precision, half.F1) == (0.5, 0.5, 0.5, 0.5)
    last = c.loc[1.0]                                                              # nothing flagged
    assert last.n_flagged == 0 and np.isnan(last.precision) and last.F1 == 0.0


def test_threshold_curve_marks_only_the_fixed_cut_off_and_uses_the_evaluators_rule():
    c = threshold_curve([0, 1], [0.5, 0.5])
    assert c[c.is_fixed_operating_point].threshold.tolist() == [0.5]
    assert c.set_index("threshold").loc[0.5, "n_flagged"] == 2                      # FLAG at p >= cut-off
    assert c.recall.is_monotonic_decreasing and c.false_alarm_rate.is_monotonic_decreasing
