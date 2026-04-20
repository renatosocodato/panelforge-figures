"""Latin hypercube sample coverage — scatter matrix with marginal histograms.

Not a sensitivity index — a *sampling-design* diagnostic. Shows whether
the LHS design achieves space-filling coverage across all parameter
pairs, with marginal histograms on the diagonal and an overall
Centered L2 discrepancy callout.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class LHSCoverageInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=2)
    samples: list[list[float]] = Field(
        ..., description="n_samples × n_parameters, in [0, 1] unit cube"
    )
    discrepancy: float | None = Field(
        None, description="Centered L2 discrepancy of the design"
    )
    title: str = "LHS parameter-space coverage"


def _demo() -> LHSCoverageInput:
    rng = np.random.default_rng(211)
    n_params = 4
    n_samples = 64
    # Proper LHS construction for a space-filling demo.
    cuts = np.linspace(0, 1, n_samples + 1)
    u = rng.uniform(cuts[:-1, None], cuts[1:, None], size=(n_samples, n_params))
    for j in range(n_params):
        rng.shuffle(u[:, j])
    names = ["k_on", "V_max", "Km", "D"]
    # Centered L2 discrepancy (Hickernell 1998) — lightweight approximation.
    n = n_samples
    t = u - 0.5
    s1 = (1 + 0.5 * np.abs(t) - 0.5 * t ** 2).prod(axis=1).sum()
    s2 = 0.0
    for i in range(n):
        for j in range(n):
            s2 += (1 + 0.5 * np.abs(t[i]) + 0.5 * np.abs(t[j])
                   - 0.5 * np.abs(t[i] - t[j])).prod()
    cd2 = (13 / 12) ** n_params - 2 * s1 / n + s2 / (n ** 2)
    return LHSCoverageInput(
        parameter_names=names,
        samples=u.tolist(),
        discrepancy=float(np.sqrt(abs(cd2))),
    )


_META = RecipeMetadata(
    name="lhs_parameter_space_coverage",
    modality="sensitivity_analysis",
    family=RecipeFamily.matrix,
    answers_question=(
        "Does the Latin-hypercube sample actually cover the joint "
        "parameter space, or are there gaps / clustering?"
    ),
    required_fields=("parameter_names", "samples"),
    optional_fields=("discrepancy", "title"),
    file_format_hints=("parquet", "csv"),
    alternatives_in_modality=("parameter_scan_2d_contour",),
)


@register_recipe(
    metadata=_META,
    contract=LHSCoverageInput,
    demo_contract=_demo,
)
def render(contract: LHSCoverageInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 5.0))
    AESTHETIC.apply_to_ax(ax)

    U = np.asarray(contract.samples, float)
    n_samples, n_params = U.shape
    names = contract.parameter_names
    assert len(names) == n_params

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]

    # Lay out a small scatter-matrix inside the host ax via patches + polygons.
    # Cell bounds in axis coords: i = row (y, top-to-bottom), j = col (x, L-to-R).
    margin = 0.06
    cell = (1 - 2 * margin) / n_params
    # Outer frame so the matrix is visible even before points.
    ax.add_patch(mpatches.Rectangle(
        (margin, margin), 1 - 2 * margin, 1 - 2 * margin,
        facecolor="none", edgecolor="#888888", linewidth=0.5,
        transform=ax.transAxes, zorder=1,
    ))
    for j in range(n_params + 1):
        ax.plot([margin + j * cell, margin + j * cell],
                [margin, 1 - margin],
                transform=ax.transAxes, color="#DDDDDD", lw=0.4, zorder=1)
    for i in range(n_params + 1):
        ax.plot([margin, 1 - margin],
                [margin + i * cell, margin + i * cell],
                transform=ax.transAxes, color="#DDDDDD", lw=0.4, zorder=1)

    # Per-cell draw.
    for i in range(n_params):
        for j in range(n_params):
            x0 = margin + j * cell
            y0 = 1 - margin - (i + 1) * cell    # top-row = first parameter
            inset_w = cell * 0.86
            inset_h = cell * 0.86
            ix0 = x0 + cell * 0.07
            iy0 = y0 + cell * 0.07

            if i == j:
                # Marginal histogram.
                bins = np.linspace(0, 1, 11)
                h, _ = np.histogram(U[:, j], bins=bins)
                h_norm = h / max(h.max(), 1)
                for b in range(len(bins) - 1):
                    w = (bins[b + 1] - bins[b]) * inset_w
                    left = ix0 + bins[b] * inset_w
                    bar_h = h_norm[b] * inset_h
                    color = cmap(0.30 + 0.5 * bins[b])
                    ax.add_patch(mpatches.Rectangle(
                        (left, iy0), w, bar_h,
                        facecolor=color, edgecolor="white", linewidth=0.3,
                        transform=ax.transAxes, zorder=3,
                    ))
                # Parameter name bold in cell upper-right.
                ax.text(ix0 + inset_w - 0.004, iy0 + inset_h - 0.004,
                        names[j], ha="right", va="top",
                        fontsize=7.4, fontweight="bold",
                        color="#111111", transform=ax.transAxes, zorder=4)
            else:
                # Off-diagonal scatter (xj, xi).
                xs = ix0 + U[:, j] * inset_w
                ys = iy0 + U[:, i] * inset_h
                ax.scatter(xs, ys, s=6.5, color="#1F77B4", alpha=0.70,
                           edgecolor="white", linewidth=0.25,
                           transform=ax.transAxes, zorder=3)
                if j == 0:
                    ax.text(ix0 - 0.006, iy0 + inset_h / 2,
                            names[i], ha="right", va="center",
                            fontsize=6.8, color="#333333",
                            transform=ax.transAxes)
                if i == n_params - 1:
                    ax.text(ix0 + inset_w / 2, iy0 - 0.006,
                            names[j], ha="center", va="top",
                            fontsize=6.8, color="#333333",
                            transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    disc_str = (f"  ·  √CD² = {smart_fmt(contract.discrepancy)}"
                if contract.discrepancy is not None else "")
    ax.set_title(f"{contract.title}  ·  n = {n_samples}{disc_str}",
                 fontsize=9.0, pad=4)
    return ax
