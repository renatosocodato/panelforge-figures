"""Tests for `core/multiverse_specification_utility` (Wave 1 inline shim).

Verifies that the per-spec ROBUST / FRAGILE / NON_SIG
classification + sort-order index behave as documented under
several mocked specification grids.
"""

from __future__ import annotations

import numpy as np

from panelforge_figures.core import (
    MULTIVERSE_OUTCOME_CLASSES,
    multiverse_audit,
)


def test_multiverse_returns_two_outputs_with_correct_shape() -> None:
    eff = np.array([0.05, 0.30, -0.40, 0.02])
    classes, order = multiverse_audit(eff)
    assert classes.shape == (4,)
    assert order.shape == (4,)


def test_multiverse_class_labels_in_official_set() -> None:
    eff = np.array([0.05, 0.30, -0.40, 0.02])
    classes, _ = multiverse_audit(eff)
    for c in classes:
        assert c in MULTIVERSE_OUTCOME_CLASSES


def test_multiverse_below_threshold_classified_non_sig() -> None:
    eff = np.array([0.05, 0.02, -0.04, 0.10])  # all |eff| <= 0.10
    classes, _ = multiverse_audit(eff, threshold=0.10)
    assert all(c == "NON_SIG" for c in classes)


def test_multiverse_robust_when_ci_excludes_rope() -> None:
    eff = np.array([0.40, -0.50, 0.30])
    lo = np.array([0.30, -0.60, 0.20])
    hi = np.array([0.50, -0.40, 0.40])
    classes, _ = multiverse_audit(
        eff, ci_lo=lo, ci_hi=hi, threshold=0.10, rope=(-0.10, 0.10),
    )
    assert all(c == "ROBUST" for c in classes)


def test_multiverse_fragile_when_ci_overlaps_rope() -> None:
    """|effect| > threshold but the CI dips into the ROPE band."""
    eff = np.array([0.30])
    lo = np.array([-0.05])  # overlaps rope (-0.10, 0.10)
    hi = np.array([0.65])
    classes, _ = multiverse_audit(
        eff, ci_lo=lo, ci_hi=hi, threshold=0.10, rope=(-0.10, 0.10),
    )
    assert classes[0] == "FRAGILE"


def test_multiverse_sort_order_ascending() -> None:
    eff = np.array([0.30, -0.40, 0.05, 0.10])
    _, order = multiverse_audit(eff)
    sorted_eff = eff[order]
    assert np.all(np.diff(sorted_eff) >= 0)


def test_multiverse_no_ci_collapses_fragile_into_robust() -> None:
    """Without CIs, |effect| > threshold falls into ROBUST (no
    ROPE-overlap test possible)."""
    eff = np.array([0.30, -0.40, 0.05])
    classes, _ = multiverse_audit(eff, threshold=0.10)
    assert classes[0] == "ROBUST"
    assert classes[1] == "ROBUST"
    assert classes[2] == "NON_SIG"
