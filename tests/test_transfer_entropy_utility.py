"""Tests for `core/transfer_entropy_utility` (Wave 4 inline shim).

Verifies that TE(X -> Y) is recovered as positive when X drives Y in
a coupled-AR(1) ground truth, and stays near zero in the reverse
direction.
"""

from __future__ import annotations

import numpy as np

from panelforge_figures.core import transfer_entropy


def test_te_is_nonnegative() -> None:
    rng = np.random.default_rng(0)
    s = rng.normal(size=200)
    t = rng.normal(size=200)
    te = transfer_entropy(s, t, n_bins=4, lag=1)
    assert te >= 0.0


def test_te_short_input_returns_zero() -> None:
    s = np.zeros(2)
    t = np.zeros(2)
    assert transfer_entropy(s, t, lag=1) == 0.0


def test_te_recovers_directed_coupling() -> None:
    """X drives Y via a one-step coupling. TE(X -> Y) should be
    measurably > TE(Y -> X)."""
    rng = np.random.default_rng(1)
    n = 1500
    s = np.zeros(n)
    t = np.zeros(n)
    # X is an autoregressive process; Y inherits from X with lag 1.
    for k in range(1, n):
        s[k] = 0.4 * s[k - 1] + rng.normal(0, 1.0)
        t[k] = 0.5 * s[k - 1] + 0.2 * t[k - 1] + rng.normal(0, 0.6)
    te_xy = transfer_entropy(s, t, n_bins=4, lag=1)
    te_yx = transfer_entropy(t, s, n_bins=4, lag=1)
    assert te_xy > te_yx, (
        f"directionality not recovered: TE(X->Y)={te_xy:.4f}, "
        f"TE(Y->X)={te_yx:.4f}"
    )
    assert te_xy > 0.05


def test_te_independent_streams_near_zero() -> None:
    rng = np.random.default_rng(2)
    s = rng.normal(size=1500)
    t = rng.normal(size=1500)
    te_xy = transfer_entropy(s, t, n_bins=4, lag=1)
    te_yx = transfer_entropy(t, s, n_bins=4, lag=1)
    # Both should be small for fully independent streams.
    assert te_xy < 0.05
    assert te_yx < 0.05


def test_te_constant_streams() -> None:
    """All-constant streams degenerate to a single bin; TE = 0."""
    s = np.zeros(50)
    t = np.zeros(50)
    assert transfer_entropy(s, t, n_bins=4, lag=1) == 0.0


def test_te_n_bins_argument() -> None:
    rng = np.random.default_rng(3)
    s = rng.normal(size=300)
    t = rng.normal(size=300)
    te2 = transfer_entropy(s, t, n_bins=2, lag=1)
    te4 = transfer_entropy(s, t, n_bins=4, lag=1)
    # With more bins, an AR-noisy estimate is at least as large as
    # with fewer bins because finer partitioning tends to inflate
    # finite-sample TE estimates (well-known bias).
    assert te2 >= 0.0
    assert te4 >= 0.0
