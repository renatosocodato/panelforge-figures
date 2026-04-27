"""Transfer-entropy utility (symbolic-binning inline shim).

Discrete approximation of Schreiber (2000) transfer entropy:

    TE(X -> Y) = H(Y_{t+1} | Y_t) - H(Y_{t+1} | Y_t, X_t)

For continuous time series we discretise each stream into `n_bins`
quantile bins, then estimate joint / conditional entropies from the
empirical contingency table. ~60 LOC, no scikit-learn / pyentropy
dep.

Used by intravital_imaging beta-pack recipe C.10
(`transfer_entropy_state_to_velocity_matrix`). Generic enough to be
called between any two scalar series (state stream, velocity stream,
length-rate stream, biosensor stream, etc.).
"""

from __future__ import annotations

import numpy as np

__all__ = ["transfer_entropy"]


def transfer_entropy(
    source: np.ndarray | list[float],
    target: np.ndarray | list[float],
    *,
    n_bins: int = 4,
    lag: int = 1,
) -> float:
    """Estimate TE(source -> target) by symbolic binning.

    Parameters
    ----------
    source, target : array-like, shape (T,)
        Two scalar time series sampled on a common time grid.
    n_bins : int
        Number of quantile bins per stream (default 4).
    lag : int
        Time lag (in samples) between source / target's past and the
        target's future (default 1).

    Returns
    -------
    te : float
        Estimated transfer entropy in nats. >= 0; near zero means the
        source's past adds no predictive information about the
        target's future beyond the target's own past.
    """
    s = np.asarray(source, float).ravel()
    t = np.asarray(target, float).ravel()
    n = min(s.size, t.size)
    if n < lag + 2:
        return 0.0
    s = s[:n]
    t = t[:n]

    # Quantile-bin each stream into 0..n_bins-1.
    def _bin(x: np.ndarray, k: int) -> np.ndarray:
        # Edges from quantiles, drop dups.
        q = np.quantile(x, np.linspace(0, 1, k + 1))
        q = np.unique(q)
        # If degenerate (all values equal), fall back to a single bin.
        if q.size < 2:
            return np.zeros_like(x, dtype=int)
        # `right=False` -> (q[i-1], q[i]] except first bin; clip to [0, k-1].
        idx = np.clip(np.searchsorted(q, x, side="right") - 1, 0, q.size - 2)
        return idx.astype(int)

    sb = _bin(s, n_bins)
    tb = _bin(t, n_bins)

    # Build the joint distribution P(Y_{t+1}, Y_t, X_t).
    y_fut = tb[lag:]
    y_past = tb[: -lag] if lag > 0 else tb
    x_past = sb[: -lag] if lag > 0 else sb

    # Collapse to single-axis indices for fast histogramming.
    K = max(sb.max(), tb.max()) + 1
    flat = (y_fut * K + y_past) * K + x_past
    bins = np.bincount(flat, minlength=K ** 3).astype(float)
    P = bins.reshape(K, K, K)
    P /= max(P.sum(), 1e-12)

    # Marginalise.
    P_yp_xp = P.sum(axis=0)               # P(Y_t, X_t)
    P_yf_yp = P.sum(axis=2)               # P(Y_{t+1}, Y_t)
    P_yp = P_yp_xp.sum(axis=1)            # P(Y_t)

    # TE = sum P(yf, yp, xp) log [P(yf | yp, xp) / P(yf | yp)]
    eps = 1e-12
    te = 0.0
    for yf in range(K):
        for yp in range(K):
            for xp in range(K):
                p_joint = P[yf, yp, xp]
                if p_joint < eps:
                    continue
                p_cond_with_x = p_joint / max(P_yp_xp[yp, xp], eps)
                p_cond_no_x = P_yf_yp[yf, yp] / max(P_yp[yp], eps)
                if p_cond_with_x < eps or p_cond_no_x < eps:
                    continue
                te += p_joint * np.log(p_cond_with_x / p_cond_no_x)
    return float(max(te, 0.0))
