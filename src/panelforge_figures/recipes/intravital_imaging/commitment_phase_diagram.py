"""Commitment phase diagram — 2-D heatmap of P(commit | L, v_bar)
fitted via the GAM utility, with overlaid iso-prob contours,
fitted 0.5 boundary, and per-protrusion scatter (committed vs not).

Heatmap family: >=1 imshow / pcolormesh.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    fit_phase_boundary,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PhaseDiagramRow(RecipeContract):
    L_um: float
    v_bar_um_per_min: float
    committed: bool


class CommitmentPhaseDiagramInput(RecipeContract):
    per_protrusion: list[PhaseDiagramRow] = Field(..., min_length=20)
    grid_resolution: tuple[int, int] = (40, 40)
    iso_prob_levels: list[float] = Field(
        default_factory=lambda: [0.25, 0.5, 0.75],
    )
    cmap: str = "cividis"
    title: str = "Commitment phase diagram"


def _demo() -> CommitmentPhaseDiagramInput:
    rng = np.random.default_rng(3021)
    n = 200
    L = np.exp(rng.uniform(np.log(2.0), np.log(20.0), n))
    v_bar = np.exp(rng.uniform(np.log(0.5), np.log(8.0), n))
    score = L * v_bar
    p = 1.0 / (1.0 + np.exp(-(np.log(score) - np.log(30.0))))
    committed = (rng.random(n) < p).tolist()
    rows = [PhaseDiagramRow(L_um=float(li), v_bar_um_per_min=float(vi),
                            committed=bool(ci))
            for li, vi, ci in zip(L, v_bar, committed)]
    return CommitmentPhaseDiagramInput(per_protrusion=rows)


_META = RecipeMetadata(
    name="commitment_phase_diagram",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Where on (L, v_bar) phase space does protrusion commitment "
        "happen, and what is the fitted boundary?"
    ),
    required_fields=("per_protrusion",),
    optional_fields=(
        "grid_resolution", "iso_prob_levels", "cmap", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("protrusion_commitment_survival",),
)


@register_recipe(
    metadata=_META,
    contract=CommitmentPhaseDiagramInput,
    demo_contract=_demo,
)
def render(contract: CommitmentPhaseDiagramInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    L = np.array([r.L_um for r in contract.per_protrusion], float)
    v = np.array([r.v_bar_um_per_min for r in contract.per_protrusion], float)
    c = np.array([r.committed for r in contract.per_protrusion], bool)

    nx, ny = contract.grid_resolution
    X, Y, P = fit_phase_boundary(L, v, c, n_grid_x=nx, n_grid_y=ny)

    # Heatmap (cividis, low-saturation).
    mesh = ax.pcolormesh(X, Y, P, cmap=contract.cmap, shading="auto",
                         alpha=0.85, zorder=1, vmin=0, vmax=1)
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("P(commit | L, v_bar)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Iso-prob contours (black solid).
    cs = ax.contour(X, Y, P, levels=contract.iso_prob_levels,
                    colors="#222222", linewidths=0.8, zorder=4)
    ax.clabel(cs, inline=True, fontsize=6.4, fmt="%.2f")

    # Per-protrusion scatter: committed = filled coral, not = hollow slate.
    ax.scatter(L[c], v[c], s=22, marker="o",
               facecolor="#EF5350", edgecolor="white", linewidth=0.5,
               alpha=0.85, zorder=5, label="committed")
    ax.scatter(L[~c], v[~c], s=22, marker="o",
               facecolor="none", edgecolor="#37474F", linewidth=0.7,
               alpha=0.85, zorder=5, label="not committed")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("protrusion length L (um)")
    ax.set_ylabel("mean velocity v_bar (um/min)")
    # Park the legend below the axes so it cannot collide with the
    # iso-prob contour labels (which always sit somewhere inside the
    # plotting area and shift with the data).
    ax.legend(fontsize=6.6, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncols=2, handlelength=1.0)

    n_total = len(contract.per_protrusion)
    n_committed = int(c.sum())
    ax.set_title(
        f"{contract.title}  ·  n = {n_total}  ·  "
        f"committed {n_committed} ({smart_fmt(100 * n_committed / n_total)} %)",
        fontsize=8.2, pad=4,
    )
    return ax
