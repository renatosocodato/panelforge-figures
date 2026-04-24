"""Tests for `core.tost_bounds_utility` — classify_outcome + tost_band_patch."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from panelforge_figures.core import classify_outcome, tost_band_patch


class _FakeZone:
    """Duck-typed TostZone-like object for utility-dispatch tests."""

    def __init__(self, lower: float, upper: float) -> None:
        self.lower = lower
        self.upper = upper


# --- classify_outcome ------------------------------------------------------


def test_classify_null_accepting_fully_inside():
    # CI [-0.1, 0.1] fully inside [-0.2, 0.2] -> null_accepting.
    assert classify_outcome(-0.1, 0.1, -0.2, 0.2) == "null_accepting"


def test_classify_significant_above_zone():
    # CI [0.3, 0.5] lies entirely above the zone upper -> significant.
    assert classify_outcome(0.3, 0.5, -0.2, 0.2) == "significant"


def test_classify_significant_below_zone():
    # CI [-0.9, -0.4] lies entirely below the zone lower -> significant.
    assert classify_outcome(-0.9, -0.4, -0.2, 0.2) == "significant"


def test_classify_equivocal_straddles_upper():
    # CI [0.1, 0.3] straddles the upper bound -> equivocal.
    assert classify_outcome(0.1, 0.3, -0.2, 0.2) == "equivocal"


def test_classify_equivocal_straddles_lower():
    # CI [-0.3, -0.1] straddles the lower bound -> equivocal.
    assert classify_outcome(-0.3, -0.1, -0.2, 0.2) == "equivocal"


def test_classify_accepts_zone_object():
    # Duck-typed object with .lower / .upper.
    zone = _FakeZone(-0.2, 0.2)
    assert classify_outcome(-0.1, 0.1, zone) == "null_accepting"
    assert classify_outcome(0.3, 0.5, zone) == "significant"


def test_classify_handles_swapped_ci():
    # CI passed with lo > hi should be auto-normalized.
    assert classify_outcome(0.1, -0.1, -0.2, 0.2) == "null_accepting"


def test_classify_handles_swapped_bounds():
    # Bounds with lower > upper should be auto-normalized.
    assert classify_outcome(-0.1, 0.1, 0.2, -0.2) == "null_accepting"


def test_classify_edge_exactly_on_bound():
    # CI exactly sharing an edge with the zone -> null_accepting
    # (bounds are inclusive).
    assert classify_outcome(-0.2, 0.2, -0.2, 0.2) == "null_accepting"


# --- tost_band_patch -------------------------------------------------------


def test_tost_band_patch_y_orientation():
    fig, ax = plt.subplots()
    tost_band_patch(ax, -0.2, 0.2, orientation="y")
    # axvspan → one Polygon added to ax.patches.
    assert any(p.get_xy() is not None for p in ax.patches)
    plt.close(fig)


def test_tost_band_patch_x_orientation():
    fig, ax = plt.subplots()
    tost_band_patch(ax, -0.2, 0.2, orientation="x")
    assert any(p.get_xy() is not None for p in ax.patches)
    plt.close(fig)


def test_tost_band_patch_accepts_zone_object():
    fig, ax = plt.subplots()
    zone = _FakeZone(-0.2, 0.2)
    tost_band_patch(ax, zone, orientation="y")
    assert any(p.get_xy() is not None for p in ax.patches)
    plt.close(fig)


def test_tost_band_patch_rejects_bad_orientation():
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        tost_band_patch(ax, -0.2, 0.2, orientation="diagonal")
    plt.close(fig)
