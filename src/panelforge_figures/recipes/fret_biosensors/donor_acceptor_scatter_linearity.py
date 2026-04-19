"""Donor / acceptor linearity — sensor-validation scatter with OLS fit and R²."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class DALinearityInput(RecipeContract):
    donor: list[float] = Field(..., description="per-pixel or per-ROI donor intensities")
    acceptor: list[float] = Field(..., description="matched acceptor intensities")
    condition_labels: list[str] | None = Field(
        None, description="optional per-point condition (drives point color)"
    )
    title: str = "Donor / acceptor linearity"


def _demo() -> DALinearityInput:
    rng = np.random.default_rng(601)
    # A well-behaved FRET pair: acceptor = 0.82 * donor + noise, with a
    # broad dynamic range.
    n = 3200
    donor = rng.uniform(120, 2400, n)
    acceptor = 0.82 * donor + rng.normal(0, 35, n)
    # Sprinkle a few mild outliers below the line (saturated pixels).
    outlier_idx = rng.choice(n, size=60, replace=False)
    acceptor[outlier_idx] -= rng.uniform(80, 180, 60)
    return DALinearityInput(
        donor=donor.tolist(),
        acceptor=acceptor.tolist(),
    )


_META = RecipeMetadata(
    name="donor_acceptor_scatter_linearity",
    modality="fret_biosensors",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Does the donor / acceptor intensity pair behave linearly across "
        "the dynamic range, as required for FRET-ratio interpretability?"
    ),
    required_fields=("donor", "acceptor"),
    optional_fields=("condition_labels", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("donor_acceptor_dual_channel",),
)


@register_recipe(
    metadata=_META,
    contract=DALinearityInput,
    demo_contract=_demo,
)
def render(contract: DALinearityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    d = np.asarray(contract.donor, dtype=float)
    a = np.asarray(contract.acceptor, dtype=float)
    mask = np.isfinite(d) & np.isfinite(a)
    d, a = d[mask], a[mask]

    # Density-weighted alpha so the central mass reads without over-plotting.
    alpha = density_alpha(d, a, alpha_min=0.08, alpha_max=0.75)
    accent = (palette.pick("donor") if "donor" in palette.semantic
              else palette[0])
    ax.scatter(d, a, s=6, color=accent, alpha=alpha,
               edgecolor="none", zorder=3)

    # OLS fit + 95% CI band.
    slope, intercept = np.polyfit(d, a, 1)
    xfit = np.linspace(float(d.min()), float(d.max()), 200)
    yfit = slope * xfit + intercept
    # Residuals → SE of prediction (simple textbook approximation).
    resid = a - (slope * d + intercept)
    sigma = float(np.sqrt(np.mean(resid ** 2)))
    ci = 1.96 * sigma
    ax.fill_between(xfit, yfit - ci, yfit + ci,
                    color=accent, alpha=0.14, linewidth=0, zorder=2,
                    label="95% CI (± 1.96 σ)")
    ax.plot(xfit, yfit, color="#111111", lw=1.1, zorder=4,
            label=f"OLS fit (slope = {smart_fmt(float(slope))})")

    # R² — simple 1 − SSE/SST.
    sse = float(np.sum(resid ** 2))
    sst = float(np.sum((a - a.mean()) ** 2))
    r_squared = 1.0 - sse / sst if sst > 0 else float("nan")

    # Ideal 1:1 reference.
    lo = float(min(d.min(), a.min()))
    hi = float(max(d.max(), a.max()))
    ax.plot([lo, hi], [lo, hi], color="#888888", lw=0.6, ls=":",
            zorder=1, label="$y = x$")

    ax.text(
        0.04, 0.96,
        f"n = {d.size}\n"
        f"slope = {smart_fmt(float(slope))}\n"
        f"intercept = {smart_fmt(float(intercept))}\n"
        f"R² = {smart_fmt(float(r_squared))}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    ax.set_xlabel("donor intensity (a.u.)")
    ax.set_ylabel("acceptor intensity (a.u.)")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
