"""Multiverse specification-curve utility (inline shim).

Pure-numpy specification-curve sensitivity analysis. Used by
cdc42_factorial_companion beta-pack recipes W1.4
(`multiverse_robustness_classification_bar`) and W1.5
(`multiverse_specification_curve`).

Algorithm: given an enumeration of analytical specifications
(e.g. preprocessing × model-form × censoring rule combinations)
and the per-spec effect-size estimate (and optional CI), classify
each specification as ROBUST / FRAGILE / NON_SIG against a
threshold + ROPE band, and emit the sorted effect-size grid for
specification-curve display.

Reference: Steegen et al. (2016), "Increasing transparency through
a multiverse analysis"; Simonsohn et al. (2020), "Specification
curve analysis".
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "multiverse_audit",
    "MULTIVERSE_OUTCOME_CLASSES",
]


# Three-way classification used by W1.4 + W1.5 demos.
MULTIVERSE_OUTCOME_CLASSES: tuple[str, ...] = (
    "ROBUST",     # |effect| > threshold AND CI excludes ROPE
    "FRAGILE",    # |effect| > threshold BUT CI overlaps ROPE
    "NON_SIG",    # |effect| <= threshold
)


def multiverse_audit(
    effect_sizes: np.ndarray | list[float],
    ci_lo: np.ndarray | list[float] | None = None,
    ci_hi: np.ndarray | list[float] | None = None,
    *,
    threshold: float = 0.10,
    rope: tuple[float, float] = (-0.10, 0.10),
) -> tuple[np.ndarray, np.ndarray]:
    """Classify each specification as ROBUST / FRAGILE / NON_SIG and
    return the sort-order index for specification-curve display.

    Parameters
    ----------
    effect_sizes : array-like, shape (n_specs,)
        Per-specification effect-size estimate.
    ci_lo, ci_hi : array-like, shape (n_specs,) or None
        Per-specification 95 % CI bounds.  If either is None, the
        FRAGILE class collapses into ROBUST whenever |effect| >
        threshold (no ROPE-overlap test possible without CIs).
    threshold : float
        Magnitude cutoff for considering an effect "real".
        Defaults to 0.10 (Cohen's d small-effect convention).
    rope : (float, float)
        Region of practical equivalence; CIs that overlap this
        band downgrade ROBUST → FRAGILE.

    Returns
    -------
    classifications : ndarray of str, shape (n_specs,)
        One of "ROBUST" / "FRAGILE" / "NON_SIG" per spec.
    sort_order : ndarray of int, shape (n_specs,)
        Indices that would sort `effect_sizes` ascending — useful
        for plotting the specification curve.
    """
    eff = np.asarray(effect_sizes, float)
    n = eff.size
    classifications = np.empty(n, dtype=object)
    rope_lo, rope_hi = float(rope[0]), float(rope[1])

    if ci_lo is not None:
        lo = np.asarray(ci_lo, float)
    else:
        lo = None
    if ci_hi is not None:
        hi = np.asarray(ci_hi, float)
    else:
        hi = None

    for i in range(n):
        if abs(eff[i]) <= threshold:
            classifications[i] = "NON_SIG"
            continue
        # |effect| > threshold; check CI vs ROPE if available.
        if lo is None or hi is None:
            classifications[i] = "ROBUST"
            continue
        ci_overlaps_rope = not (hi[i] < rope_lo or lo[i] > rope_hi)
        classifications[i] = "FRAGILE" if ci_overlaps_rope else "ROBUST"

    sort_order = np.argsort(eff)
    return classifications, sort_order
