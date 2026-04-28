"""Bayes factor utility (BIC-derived approximation inline shim).

Replaces a `BayesFactor` (R) / `JASP` dep with ~40 LOC of pure
numpy. Used by factorial_design_companion beta-pack recipe W1.1
(`bayes_factor_arrow_plot`) and reusable across any null-
acceptance audit.

Algorithm: Bayesian Information Criterion (BIC) approximates the
log marginal likelihood under each model. The Bayes factor in
favour of the null vs alternative is approximately
`BF_01 = exp((BIC_alt - BIC_null) / 2)`. Higher BF_01 means the
data favour the null.

Reference: Wagenmakers (2007), "A practical solution to the
pervasive problems of p-values"; Kass & Raftery (1995) Table for
threshold interpretation.
"""

from __future__ import annotations

import math

__all__ = [
    "bf_from_bic",
    "classify_bf_threshold",
    "BF_THRESHOLDS",
]


# Wagenmakers / Kass-Raftery threshold table for BF_01:
#   BF_01 < 1     -> data favour H1 (alternative); evidence "anecdotal" or stronger AGAINST null
#   1 ≤ BF_01 < 3 -> "anecdotal"  evidence FOR null
#   3 ≤ BF_01 < 10 -> "moderate"  evidence FOR null
#   10 ≤ BF_01 < 30 -> "strong"   evidence FOR null
#   BF_01 ≥ 30 -> "decisive" evidence FOR null
BF_THRESHOLDS: dict[str, float] = {
    "anecdotal": 1.0,
    "moderate": 3.0,
    "strong": 10.0,
    "decisive": 30.0,
}


def bf_from_bic(bic_alt: float, bic_null: float) -> float:
    """Compute approximate BF_01 (favouring null over alternative) from BICs.

    Parameters
    ----------
    bic_alt : float
        BIC of the alternative model (smaller BIC = better fit).
    bic_null : float
        BIC of the null model.

    Returns
    -------
    bf_01 : float
        Bayes factor in favour of the null vs alternative.  >= 0;
        values > 1 favour the null.

    Notes
    -----
    Uses the BIC approximation
        BF_01 ≈ exp((BIC_alt - BIC_null) / 2).
    """
    delta = float(bic_alt) - float(bic_null)
    # Clamp to avoid overflow in exp(); BIC differences > ~700 produce
    # numerically infinite BFs anyway, which is fine to cap.
    delta = max(min(delta, 700.0), -700.0)
    return float(math.exp(delta / 2.0))


def classify_bf_threshold(bf_01: float) -> str:
    """Classify a BF_01 value into the Wagenmakers / Kass-Raftery tier.

    Parameters
    ----------
    bf_01 : float
        Bayes factor in favour of the null over the alternative.

    Returns
    -------
    tier : str
        One of:
            "favours_alt"   — BF_01 < 1 (evidence against null)
            "anecdotal"     — 1 ≤ BF_01 < 3
            "moderate"      — 3 ≤ BF_01 < 10
            "strong"        — 10 ≤ BF_01 < 30
            "decisive"      — BF_01 ≥ 30
    """
    if bf_01 < BF_THRESHOLDS["anecdotal"]:
        return "favours_alt"
    if bf_01 < BF_THRESHOLDS["moderate"]:
        return "anecdotal"
    if bf_01 < BF_THRESHOLDS["strong"]:
        return "moderate"
    if bf_01 < BF_THRESHOLDS["decisive"]:
        return "strong"
    return "decisive"
