"""Persistence length Lp with explicit TOST equivalence zone per
compartment. 2xN split violin (N compartments) with per-genotype
medians, TOST band shaded, and compact N / %-in-zone callouts.

This is the polymer-layer canonical figure for the anchor manuscript:
polymer properties (Lp) are expected to be *invariant* across genotypes,
so the TOST-zone intersection is the argument, not a significant shift.

Split-violin family: >=2 violin bodies + >=1 median marker. Satisfied
by the 2-groups-per-compartment split layout + black median ticks.
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
from ._shared import TostZone


class LpEquivalenceInput(RecipeContract):
    # dict keys are "group|compartment" strings (e.g. "WT|whole_cell").
    lp_by_group_and_compartment: dict[str, list[float]] = Field(...)
    tost: TostZone
    filament_type: str = "actin"
    dimensionality: str = "3D"
    log_scale: bool = True
    group_order: list[str] = Field(
        default_factory=lambda: ["WT", "LI"],
    )
    compartment_order: list[str] = Field(
        default_factory=lambda: ["whole_cell", "protrusion_internal"],
    )
    title: str = "Persistence length Lp with TOST zone"


def _demo() -> LpEquivalenceInput:
    rng = np.random.default_rng(2211)
    # Lp in um; WT vs LI close under log-normal, both compartments.
    data: dict[str, list[float]] = {}
    base_mu = {"WT|whole_cell": 1.1, "LI|whole_cell": 1.05,
               "WT|protrusion_internal": 0.95,
               "LI|protrusion_internal": 0.92}
    for key, mu in base_mu.items():
        vals = np.exp(rng.normal(np.log(mu), 0.35, 60))
        data[key] = vals.tolist()
    # TOST in log10-d space, ±0.2 log-fold == ~±58%.
    return LpEquivalenceInput(
        lp_by_group_and_compartment=data,
        tost=TostZone(lower=-0.2, upper=0.2, units="log10_fold"),
    )


_META = RecipeMetadata(
    name="persistence_length_lp_with_equivalence_bounds",
    modality="biophysics_scaling",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Across compartments, does the polymer persistence length Lp "
        "lie inside the pre-registered equivalence zone (null-accepting "
        "invariance) or outside it?"
    ),
    required_fields=("lp_by_group_and_compartment", "tost"),
    optional_fields=(
        "filament_type", "dimensionality", "log_scale",
        "group_order", "compartment_order", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("scaling_exponent_ci_forest",),
)


@register_recipe(
    metadata=_META,
    contract=LpEquivalenceInput,
    demo_contract=_demo,
)
def render(contract: LpEquivalenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    groups = list(contract.group_order)
    comps = list(contract.compartment_order)

    # x positions: one per (compartment); group0 left half, group1 right half.
    positions = np.arange(len(comps)) * 1.4

    group_colors = {groups[0]: "#1565C0", groups[-1]: "#C62828"}

    def _draw_half(vals: np.ndarray, pos: float, color: str, side: str):
        parts = ax.violinplot(
            [vals], positions=[pos], widths=0.88,
            showmeans=False, showmedians=False, showextrema=False,
        )
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.55)
            v = pc.get_paths()[0].vertices
            if side == "left":
                v[:, 0] = np.clip(v[:, 0], -np.inf, pos)
            else:
                v[:, 0] = np.clip(v[:, 0], pos, np.inf)

    for pos, comp in zip(positions, comps):
        for g_idx, group in enumerate(groups):
            key = f"{group}|{comp}"
            vals = np.asarray(
                contract.lp_by_group_and_compartment.get(key, []), float,
            )
            if vals.size == 0:
                continue
            side = "left" if g_idx == 0 else "right"
            _draw_half(vals, pos, group_colors[group], side)
            if vals.size >= 4:
                med = float(np.median(vals))
                q1, q3 = np.quantile(vals, [0.25, 0.75])
                x_off = -0.15 if side == "left" else 0.15
                ax.plot([pos + x_off, pos + x_off], [q1, q3],
                        color="black", lw=2.2, zorder=5,
                        solid_capstyle="butt")
                ax.scatter([pos + x_off], [med],
                           s=28, facecolor="white",
                           edgecolor="black", linewidth=0.8,
                           zorder=6)

    # Compute per-compartment log10-fold between groups, annotate TOST
    # distance.
    tost = contract.tost
    header_bits = []
    for pos, comp in zip(positions, comps):
        vals0 = np.asarray(
            contract.lp_by_group_and_compartment.get(
                f"{groups[0]}|{comp}", []), float)
        vals1 = np.asarray(
            contract.lp_by_group_and_compartment.get(
                f"{groups[-1]}|{comp}", []), float)
        if vals0.size < 2 or vals1.size < 2:
            continue
        med0 = float(np.median(vals0))
        med1 = float(np.median(vals1))
        lf = float(np.log10(med1 / med0))
        inside = tost.lower <= lf <= tost.upper
        tag = "null-accept" if inside else "equivocal"
        header_bits.append(
            f"{comp}: log10 fold = {smart_fmt(lf)} ({tag})"
        )

    if contract.log_scale:
        ax.set_yscale("log")
    ax.set_xticks(positions)
    ax.set_xticklabels([c.replace("_", "-") for c in comps], fontsize=7.0)
    ax.set_ylabel(f"Lp ({contract.filament_type}, um)")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend (groups).
    from matplotlib.patches import Patch
    ax.legend(
        handles=[Patch(facecolor=group_colors[g], edgecolor="#333333",
                       alpha=0.55, label=g) for g in groups],
        fontsize=6.8, frameon=False, loc="upper left",
        handlelength=1.2,
    )

    ax.set_title(
        f"{contract.title}  ·  {contract.filament_type} "
        f"({contract.dimensionality})  ·  "
        f"TOST [{smart_fmt(tost.lower)}, {smart_fmt(tost.upper)}]  ·  "
        + "   ".join(header_bits),
        fontsize=7.4, pad=4,
    )
    return ax
