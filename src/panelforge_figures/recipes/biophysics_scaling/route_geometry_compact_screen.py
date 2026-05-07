"""Route geometry compact screen — perturbation × route geometric-
scalar `imshow` heatmap with per-cell numeric annotations and
disrupted-route flagging.

Each cell encodes one perturbation × route geometry value (mean
route length, mean curvature, etc.). Cells flagged as `is_disrupted`
get a hatched overlay and a red border to surface manuscript-
threshold breakers across the screen at a glance.

Matrix family: >=1 imshow OR >=4 cell patches. Satisfied by the
imshow of the perturbation × route grid.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import RouteGeometryRow


class RouteGeometryCompactScreenInput(RecipeContract):
    rows: list[RouteGeometryRow] = Field(..., min_length=4)
    value_label: str = "geometry score"
    title: str = "Route geometry compact screen"


def _demo() -> RouteGeometryCompactScreenInput:
    rng = np.random.default_rng(831)
    perturbations = [
        "MR-CKO", "Vav-KO", "Tiam-KO", "Trio-KO", "WT-vehicle", "WT-rescue",
    ]
    routes = ["PIP3", "Rho", "Rac", "Cdc42", "lipid"]
    # Manuscript F6E values: MR-CKO has weakest geometric signal across
    # all routes (≤0.30); WT-vehicle highest (≥0.75).
    base = {
        "MR-CKO":     0.22,
        "Vav-KO":     0.45,
        "Tiam-KO":    0.55,
        "Trio-KO":    0.60,
        "WT-vehicle": 0.78,
        "WT-rescue":  0.68,
    }
    rows: list[RouteGeometryRow] = []
    threshold = 0.35
    for p in perturbations:
        for r in routes:
            v = base[p] + rng.normal(0.0, 0.06)
            v = float(np.clip(v, 0.0, 1.0))
            rows.append(RouteGeometryRow(
                perturbation=p, route=r, value=v,
                is_disrupted=v < threshold,
            ))
    return RouteGeometryCompactScreenInput(rows=rows)


_META = RecipeMetadata(
    name="route_geometry_compact_screen",
    modality="biophysics_scaling",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across multiple Cdc42-pathway perturbations and route "
        "geometries (PIP3 / Rho / Rac / Cdc42 / lipid), which "
        "perturbation × route cells fall below the manuscript "
        "disruption threshold?"
    ),
    required_fields=("rows",),
    optional_fields=("value_label", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("phase_diagram_by_genotype",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=RouteGeometryCompactScreenInput,
    demo_contract=_demo,
)
def render(contract: RouteGeometryCompactScreenInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Build (n_perturbations × n_routes) value + disruption grids.
    perturbations: list[str] = []
    routes: list[str] = []
    for r in contract.rows:
        if r.perturbation not in perturbations:
            perturbations.append(r.perturbation)
        if r.route not in routes:
            routes.append(r.route)
    grid = np.full((len(perturbations), len(routes)), np.nan, float)
    disrupted = np.zeros_like(grid, bool)
    for r in contract.rows:
        i = perturbations.index(r.perturbation)
        j = routes.index(r.route)
        grid[i, j] = r.value
        disrupted[i, j] = r.is_disrupted

    # imshow on the cividis ramp (manuscript geometry-score convention).
    im = ax.imshow(grid, cmap="cividis", vmin=0.0, vmax=1.0,
                   aspect="auto", zorder=2)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label(contract.value_label, fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Per-cell numeric + disruption-flag overlay.
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid[i, j]
            text_colour = "white" if v < 0.5 else "#222222"
            ax.text(j, i, smart_fmt(v),
                    ha="center", va="center",
                    fontsize=6.6, color=text_colour, fontweight="bold",
                    zorder=4)
            if disrupted[i, j]:
                ax.add_patch(mpatches.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1,
                    facecolor="none", edgecolor="#C62828",
                    linewidth=1.3, hatch="///", zorder=5,
                ))

    ax.set_xticks(range(len(routes)))
    ax.set_xticklabels(routes, fontsize=7.0)
    ax.set_yticks(range(len(perturbations)))
    ax.set_yticklabels(perturbations, fontsize=7.0)
    ax.set_xlabel("route geometry")
    ax.set_ylabel("perturbation")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Title summary: total disrupted cells.
    n_disrupted = int(disrupted.sum())
    n_total = grid.size
    ax.set_title(
        f"{contract.title}  ·  {n_disrupted}/{n_total} cells "
        f"flagged disrupted  ·  threshold = 0.35",
        fontsize=8.2, pad=4,
    )

    # Legend.
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor="none", edgecolor="#C62828", hatch="///",
              linewidth=1.3, label="disrupted (< 0.35)"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncols=1, handlelength=1.6)
    return ax
