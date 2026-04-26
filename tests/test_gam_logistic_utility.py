"""Tests for `core.gam_logistic_utility` — fit_phase_boundary shim."""

from __future__ import annotations

import numpy as np

from panelforge_figures.core import fit_phase_boundary


def _make_synthetic_phase_data(n: int = 200, seed: int = 0):
    """Generate (L, v_bar, committed) where committed ~ logistic(L*v_bar)."""
    rng = np.random.default_rng(seed)
    L = np.exp(rng.uniform(np.log(2.0), np.log(20.0), n))
    v_bar = np.exp(rng.uniform(np.log(0.5), np.log(8.0), n))
    # True boundary: L * v_bar > 30 => committed.
    score = L * v_bar
    p = 1.0 / (1.0 + np.exp(-(np.log(score) - np.log(30.0))))
    committed = rng.random(n) < p
    return L, v_bar, committed


def test_fit_phase_boundary_returns_correct_shapes():
    L, v_bar, committed = _make_synthetic_phase_data()
    X, Y, P = fit_phase_boundary(L, v_bar, committed,
                                 n_grid_x=30, n_grid_y=30)
    assert X.shape == (30, 30)
    assert Y.shape == (30, 30)
    assert P.shape == (30, 30)


def test_fit_phase_boundary_p_in_unit_interval():
    L, v_bar, committed = _make_synthetic_phase_data()
    _, _, P = fit_phase_boundary(L, v_bar, committed)
    assert (P >= 0).all() and (P <= 1).all()


def test_fit_phase_boundary_recovers_monotone_trend():
    """Increasing L and v_bar should both increase P(committed)."""
    L, v_bar, committed = _make_synthetic_phase_data(n=300, seed=1)
    X, Y, P = fit_phase_boundary(L, v_bar, committed)
    # P at the high-L, high-v corner should exceed P at the low-L,
    # low-v corner.
    p_low = float(P[0, 0])
    p_high = float(P[-1, -1])
    assert p_high > p_low + 0.20, (
        f"expected high-L/high-v P to exceed low-L/low-v by >0.20, "
        f"got P_low={p_low:.3f}, P_high={p_high:.3f}"
    )


def test_fit_phase_boundary_high_purity_against_truth():
    """Predicted classes should match ground truth on >70 % of training points."""
    L, v_bar, committed = _make_synthetic_phase_data(n=400, seed=2)
    X, Y, P = fit_phase_boundary(L, v_bar, committed)
    # Look up predicted P at each training point via nearest-grid.
    purity_count = 0
    for li, vi, ci in zip(L, v_bar, committed):
        # Find nearest grid cell.
        ix = int(np.argmin(np.abs(X[0, :] - li)))
        iy = int(np.argmin(np.abs(Y[:, 0] - vi)))
        pred = P[iy, ix] >= 0.5
        if pred == bool(ci):
            purity_count += 1
    purity = purity_count / L.size
    assert purity > 0.70, f"expected >70 % purity, got {purity:.2%}"


def test_fit_phase_boundary_handles_all_committed():
    """All-committed input should produce P near 1 everywhere."""
    L = np.linspace(2.0, 20.0, 30)
    v_bar = np.linspace(0.5, 8.0, 30)
    LL, VV = np.meshgrid(L, v_bar)
    L_flat = LL.ravel()
    V_flat = VV.ravel()
    committed = np.ones(L_flat.size, dtype=bool)
    _, _, P = fit_phase_boundary(L_flat, V_flat, committed)
    assert P.mean() > 0.85


def test_fit_phase_boundary_log_axes_default():
    """Default log_axes=True works on skewed feature distributions."""
    L, v_bar, committed = _make_synthetic_phase_data()
    X, Y, P = fit_phase_boundary(L, v_bar, committed, log_axes=True)
    # Grid spans original (linear) ranges.
    assert X.min() == X[0, 0]
    assert Y.min() == Y[0, 0]
    assert X.max() == X[0, -1] or X.max() == X[-1, -1]
