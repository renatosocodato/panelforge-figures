"""Kaplan-Meier survival utility (Greenwood CI inline shim).

Replaces a `lifelines` dep with ~50 LOC. Used by intravital_imaging
beta-pack recipes A.5 (sojourn_survival_per_state) and B.1
(protrusion_commitment_survival), and available to any future recipe
that needs S(t) +/- CI from event-time data.

Reference: Greenwood (1926) for the variance formula, Kalbfleisch &
Prentice (2002) Ch. 1 for the standard exposition. Confidence
intervals are computed on the log-log scale (so they stay in [0, 1]).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

__all__ = ["kaplan_meier"]


def kaplan_meier(
    durations: np.ndarray | list[float],
    censored: np.ndarray | list[bool] | None = None,
    *,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Kaplan-Meier survival estimate with Greenwood CI on log-log scale.

    Parameters
    ----------
    durations : array-like
        Observed event-or-censoring times (>= 0).
    censored : array-like of bool, optional
        True if the observation is right-censored. If None, all
        observations are treated as events.
    alpha : float
        1 - confidence level (default 0.05 -> 95 % CI).

    Returns
    -------
    t : ndarray
        Sorted unique event times (excluding pure-censoring times).
    s : ndarray
        S(t) Kaplan-Meier estimate at each event time.
    ci_lo, ci_hi : ndarray
        95 % CI bounds on log-log scale, clipped to [0, 1].
    """
    d = np.asarray(durations, float)
    if censored is None:
        c = np.zeros_like(d, dtype=bool)
    else:
        c = np.asarray(censored, dtype=bool)
    if d.size == 0:
        return (np.array([]), np.array([]), np.array([]),
                np.array([]))
    # If everyone is censored, no event times to report.
    if c.all():
        return (np.array([]), np.array([]), np.array([]),
                np.array([]))
    # Unique event times only.
    t_event = np.unique(d[~c])
    if t_event.size == 0:
        return (np.array([]), np.array([]), np.array([]),
                np.array([]))
    s = np.zeros_like(t_event)
    cum_log_s = 0.0
    cum_var = 0.0
    var_at = np.zeros_like(t_event)
    for i, ti in enumerate(t_event):
        n_at_risk = int((d >= ti).sum())
        d_ti = int(((d == ti) & (~c)).sum())
        if n_at_risk <= 0 or d_ti <= 0:
            s[i] = float(np.exp(cum_log_s))
            var_at[i] = cum_var
            continue
        if d_ti >= n_at_risk:
            # All remaining fail at this time -> S(t) = 0 from here on.
            s[i] = 0.0
            var_at[i] = cum_var
            cum_log_s = -np.inf
            continue
        cum_log_s += np.log(1.0 - d_ti / n_at_risk)
        denom = n_at_risk * (n_at_risk - d_ti)
        if denom > 0:
            cum_var += d_ti / denom
        s[i] = float(np.exp(cum_log_s))
        var_at[i] = cum_var

    z = float(norm.ppf(1 - alpha / 2))
    ci_lo = np.zeros_like(s)
    ci_hi = np.zeros_like(s)
    for i, si in enumerate(s):
        if si <= 0.0 or si >= 1.0:
            ci_lo[i] = float(np.clip(si, 0.0, 1.0))
            ci_hi[i] = float(np.clip(si, 0.0, 1.0))
            continue
        # Var(log -log S) ~= Var(S) / (S log S)^2; Var(S) ~= S^2 * cum_var.
        v = var_at[i] / (np.log(si) ** 2 + 1e-12)
        se = float(np.sqrt(max(v, 0.0)))
        log_log_s = float(np.log(-np.log(si)))
        lo = float(np.exp(-np.exp(log_log_s + z * se)))
        hi = float(np.exp(-np.exp(log_log_s - z * se)))
        ci_lo[i] = float(np.clip(lo, 0.0, 1.0))
        ci_hi[i] = float(np.clip(hi, 0.0, 1.0))
    return t_event, s, ci_lo, ci_hi
