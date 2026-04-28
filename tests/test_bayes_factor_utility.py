"""Tests for `core/bayes_factor_utility` (Wave 1 inline shim).

Verifies that the BIC-derived Bayes-factor approximation behaves
correctly: equal BICs → BF=1; alternative-favouring delta → BF<1;
null-favouring delta → BF>1; threshold classification matches
the Wagenmakers / Kass-Raftery tier table.
"""

from __future__ import annotations

import math

import pytest

from panelforge_figures.core import (
    BF_THRESHOLDS,
    bf_from_bic,
    classify_bf_threshold,
)


def test_bf_equal_bics_returns_one() -> None:
    assert bf_from_bic(100.0, 100.0) == pytest.approx(1.0)


def test_bf_alt_better_than_null_below_one() -> None:
    """Alternative model has lower BIC -> data favour H1 -> BF_01 < 1."""
    bf = bf_from_bic(bic_alt=90.0, bic_null=100.0)
    assert bf < 1.0
    # exp(-5) ~ 0.0067
    assert bf == pytest.approx(math.exp(-5.0), rel=1e-6)


def test_bf_null_better_than_alt_above_one() -> None:
    """Null model has lower BIC -> data favour H0 -> BF_01 > 1."""
    bf = bf_from_bic(bic_alt=110.0, bic_null=100.0)
    assert bf > 1.0
    assert bf == pytest.approx(math.exp(5.0), rel=1e-6)


def test_bf_extreme_delta_clamps_finite() -> None:
    """Massive BIC differences must not overflow."""
    bf_high = bf_from_bic(bic_alt=10_000.0, bic_null=100.0)
    bf_low = bf_from_bic(bic_alt=100.0, bic_null=10_000.0)
    assert math.isfinite(bf_high)
    assert math.isfinite(bf_low)
    assert bf_high > 1e100
    assert bf_low < 1e-100


def test_classify_bf_threshold_tiers() -> None:
    assert classify_bf_threshold(0.5) == "favours_alt"
    assert classify_bf_threshold(2.0) == "anecdotal"
    assert classify_bf_threshold(5.0) == "moderate"
    assert classify_bf_threshold(15.0) == "strong"
    assert classify_bf_threshold(50.0) == "decisive"


def test_classify_bf_threshold_boundary_inclusive_lower() -> None:
    """Exactly at the lower boundary, the higher tier kicks in."""
    assert classify_bf_threshold(BF_THRESHOLDS["moderate"]) == "moderate"
    assert classify_bf_threshold(BF_THRESHOLDS["strong"]) == "strong"
    assert classify_bf_threshold(BF_THRESHOLDS["decisive"]) == "decisive"
