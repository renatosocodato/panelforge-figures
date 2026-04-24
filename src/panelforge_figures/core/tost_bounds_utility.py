"""Two-one-sided-test (TOST) equivalence utilities.

Used by biophysics_scaling beta-pack recipes (A.1, B.1, B.4, and any
future equivalence-bounded forest). The utility is modality-agnostic:
it takes float CIs + float bounds, so recipes can pass either a
`TostZone` sub-contract object (duck-typed .lower / .upper) or the
raw numbers.

Two entry points:

- `classify_outcome(ci_lo, ci_hi, lower, upper)` → one of
  ``"significant"`` | ``"null_accepting"`` | ``"equivocal"``.
  Rule:
    * ``significant``     — CI does not straddle the null (0) and lies
                             entirely outside the equivalence zone
                             on either side
    * ``null_accepting``  — CI lies entirely inside the equivalence zone
    * ``equivocal``       — CI straddles an equivalence bound
- `tost_band_patch(ax, lower, upper, orientation="y", **kw)` draws a
  shaded band spanning the equivalence zone on the given axes.

Both are thin by design so recipes remain free to style the band in
whatever way best fits their layout.
"""

from __future__ import annotations

from typing import Any, Literal

OutcomeClass = Literal["significant", "null_accepting", "equivocal"]


def _unpack_bounds(lower: Any, upper: Any = None) -> tuple[float, float]:
    """Accept either `(lower_float, upper_float)` or a TostZone-like object.

    If `upper` is None, `lower` is expected to expose `.lower` and `.upper`
    attributes.
    """
    if upper is None:
        return float(lower.lower), float(lower.upper)
    return float(lower), float(upper)


def classify_outcome(
    ci_lo: float,
    ci_hi: float,
    lower: Any,
    upper: Any = None,
) -> OutcomeClass:
    """Classify an effect's CI against a TOST equivalence zone.

    Parameters
    ----------
    ci_lo, ci_hi : float
        Lower and upper bounds of the effect's confidence interval.
    lower, upper : float or TostZone-like
        Either pass two floats (equivalence bounds), or a single object
        exposing ``.lower`` and ``.upper``.

    Returns
    -------
    One of ``"significant"``, ``"null_accepting"``, ``"equivocal"``.
    """
    lo, hi = _unpack_bounds(lower, upper)
    if ci_lo > ci_hi:
        ci_lo, ci_hi = ci_hi, ci_lo
    if lo > hi:
        lo, hi = hi, lo
    # Null-accepting: CI fully inside the zone.
    if lo <= ci_lo and ci_hi <= hi:
        return "null_accepting"
    # Significant: CI lies entirely outside the zone on one side and
    # does not straddle 0 (i.e. the sign is preserved).
    if ci_hi < lo or ci_lo > hi:
        return "significant"
    # Anything else — CI straddles a bound.
    return "equivocal"


def tost_band_patch(
    ax,
    lower: Any,
    upper: Any = None,
    orientation: str = "y",
    color: str = "#D0D0D0",
    alpha: float = 0.45,
    zorder: int = 1,
    label: str | None = None,
):
    """Shade the TOST equivalence zone on an axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    lower, upper : float or TostZone-like
        Bounds of the equivalence zone. Same dispatch as `classify_outcome`.
    orientation : {"y", "x"}
        ``"y"`` → vertical band (extends in y, spans lo..hi in x); used
        for forests where effect sizes are plotted on the x-axis.
        ``"x"`` → horizontal band; used when the effect is on the y-axis.
    color, alpha, zorder, label : forwarded to `axvspan` / `axhspan`.
    """
    lo, hi = _unpack_bounds(lower, upper)
    if lo > hi:
        lo, hi = hi, lo
    if orientation == "y":
        return ax.axvspan(lo, hi, color=color, alpha=alpha,
                          zorder=zorder, label=label, lw=0)
    if orientation == "x":
        return ax.axhspan(lo, hi, color=color, alpha=alpha,
                          zorder=zorder, label=label, lw=0)
    raise ValueError(
        f"orientation must be 'y' or 'x', got {orientation!r}"
    )


__all__ = ["classify_outcome", "tost_band_patch", "OutcomeClass"]
