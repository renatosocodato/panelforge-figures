"""Tests for `core.km_survival_utility` — Kaplan-Meier with Greenwood CI."""

from __future__ import annotations

import numpy as np

from panelforge_figures.core import kaplan_meier


def test_km_no_censoring_basic_step_decrease():
    durations = [1.0, 2.0, 3.0, 4.0, 5.0]
    t, s, lo, hi = kaplan_meier(durations)
    assert len(t) == 5
    # S(t) drops by 1/N at each step: 0.8, 0.6, 0.4, 0.2, 0.
    np.testing.assert_allclose(s, [0.8, 0.6, 0.4, 0.2, 0.0], atol=1e-9)


def test_km_handles_censoring():
    # 5 events, 3 censored. Risk-set sizes at event times: 8, 6, 4, 3, 1.
    # (At t=3, the censored-at-2.5 has already left the risk set.)
    durations = [1.0, 2.0, 3.0, 4.0, 5.0, 1.5, 2.5, 4.5]
    censored = [False, False, False, False, False, True, True, True]
    t, s, _, _ = kaplan_meier(durations, censored)
    expected = [
        7 / 8,                          # 1: n_risk=8, d=1 -> 7/8 = 0.875
        7 / 8 * 5 / 6,                  # 2: n_risk=6, d=1 -> 0.7292
        7 / 8 * 5 / 6 * 3 / 4,          # 3: n_risk=4, d=1 -> 0.5469
        7 / 8 * 5 / 6 * 3 / 4 * 2 / 3,  # 4: n_risk=3, d=1 -> 0.3646
        0.0,                             # 5: n_risk=1, d=1 -> 0
    ]
    np.testing.assert_allclose(s, expected, atol=1e-6)


def test_km_handles_tied_events():
    durations = [1.0, 1.0, 2.0, 3.0]
    t, s, _, _ = kaplan_meier(durations)
    assert len(t) == 3
    np.testing.assert_allclose(t, [1.0, 2.0, 3.0])
    # At t=1: 2 deaths out of 4 -> S(1) = 0.5; t=2: 1/2 -> 0.25; t=3: 0.
    np.testing.assert_allclose(s, [0.5, 0.25, 0.0], atol=1e-9)


def test_km_ci_bounds_contain_estimate():
    durations = list(np.random.default_rng(0).gamma(2, 2, 60))
    t, s, lo, hi = kaplan_meier(durations)
    assert ((lo <= s) & (s <= hi)).all() or (s == 0).any()


def test_km_ci_stays_in_unit_interval():
    durations = list(np.random.default_rng(0).exponential(3, 50))
    t, s, lo, hi = kaplan_meier(durations)
    assert (lo >= 0).all() and (lo <= 1).all()
    assert (hi >= 0).all() and (hi <= 1).all()


def test_km_empty_input_returns_empty_arrays():
    t, s, lo, hi = kaplan_meier([])
    assert t.size == 0
    assert s.size == 0


def test_km_all_censored_returns_empty():
    t, s, _, _ = kaplan_meier([1.0, 2.0, 3.0],
                              censored=[True, True, True])
    assert t.size == 0
