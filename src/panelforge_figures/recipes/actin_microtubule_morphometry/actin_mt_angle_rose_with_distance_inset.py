"""Actin-MT angle rose with NN-distance inset — polar rose plots
of actin-to-microtubule angle distributions overlaid per condition,
with a Cartesian inset showing nearest-neighbour inter-filament
distance distributions.

Radar family: >=1 polar axis + >=1 filled polygon.
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
from ._shared import BranchOrderEdge

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ActinMTAngleRoseInput(RecipeContract):
    edges: list[BranchOrderEdge] = Field(..., min_length=20)
    n_bins: int = 18                              # rose-petal bin count (180° / n_bins per bin)
    title: str = "Actin-MT angle rose"


def _demo() -> ActinMTAngleRoseInput:
    rng = np.random.default_rng(601)
    edges: list[BranchOrderEdge] = []
    # WT: angle distributed broadly with mode ~45°; NN distance ~ 0.6 um.
    # LI: angle skewed toward 0° (more parallel); NN distance ~ 0.40 um.
    for cond, ang_mu, ang_sd, nn_mu, n in (
        ("WT", 45.0, 28.0, 0.60, 200),
        ("LI", 18.0, 22.0, 0.40, 200),
    ):
        for _ in range(n):
            angle = float(np.clip(np.abs(rng.normal(ang_mu, ang_sd)),
                                  0.0, 90.0))
            nn = float(max(0.05, rng.normal(nn_mu, nn_mu * 0.20)))
            edges.append(BranchOrderEdge(
                cell_id=f"{cond}_x", condition=cond,
                angle_deg=angle, nn_distance_um=nn,
            ))
    return ActinMTAngleRoseInput(edges=edges)


_META = RecipeMetadata(
    name="actin_mt_angle_rose_with_distance_inset",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.radar,
    answers_question=(
        "Per condition, how is the actin-to-microtubule angle "
        "distributed (parallel vs orthogonal), and how does "
        "nearest-neighbour inter-filament distance differ?"
    ),
    required_fields=("edges",),
    optional_fields=("n_bins", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


@register_recipe(
    metadata=_META,
    contract=ActinMTAngleRoseInput,
    demo_contract=_demo,
)
def render(contract: ActinMTAngleRoseInput, ax=None, **_):
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.6, 4.4))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        # Caller gave a cartesian axis — replace with polar.
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)

    AESTHETIC.apply_to_fig(ax.figure)

    # Bin angles into rose petals from 0 to π/2 (data is folded onto
    # half-circle since actin-MT angle is unsigned).
    n_bins = max(4, int(contract.n_bins))
    bin_edges = np.linspace(0, np.pi / 2, n_bins + 1)
    bin_centres = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    conditions = list(dict.fromkeys(e.condition for e in contract.edges))
    bits = []
    max_count = 0
    for cond in conditions:
        cond_angles = np.array([np.deg2rad(e.angle_deg)
                                for e in contract.edges
                                if e.condition == cond])
        if cond_angles.size == 0:
            continue
        counts, _ = np.histogram(cond_angles, bins=bin_edges)
        max_count = max(max_count, counts.max())
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        # Filled rose polygon.
        widths = np.diff(bin_edges)
        ax.bar(bin_centres, counts, width=widths,
               color=colour, alpha=0.45, edgecolor=colour,
               linewidth=0.8, zorder=3, label=cond)
        # Outline polygon over the bars (≥1 filled polygon for the
        # radar family rule).
        polygon_theta = np.concatenate([bin_centres, bin_centres[:1]])
        polygon_r = np.concatenate([counts, counts[:1]])
        ax.fill(polygon_theta, polygon_r,
                color=colour, alpha=0.18, zorder=2)
        # Mode angle for callout.
        mode_idx = int(np.argmax(counts))
        mode_deg = float(np.rad2deg(bin_centres[mode_idx]))
        bits.append(f"{cond}: mode {smart_fmt(mode_deg)} deg")

    ax.set_theta_offset(0.0)
    ax.set_theta_direction(1)
    ax.set_thetalim(0, np.pi / 2)
    ax.set_rlim(0, max_count * 1.15)
    ax.set_xticks(np.deg2rad([0, 30, 45, 60, 90]))
    ax.set_xticklabels(["0 deg\n(parallel)", "30", "45", "60",
                        "90 deg\n(orthogonal)"], fontsize=6.6)
    ax.tick_params(axis="y", labelsize=6.0)
    ax.grid(color="#DDDDDD", lw=0.5)

    # NN-distance inset (Cartesian, lower-left, axes-fraction
    # outside the rose's upper-right quadrant so it doesn't overlap
    # the petals).
    inset = ax.inset_axes([-0.18, -0.18, 0.40, 0.30])
    AESTHETIC.apply_to_ax(inset)
    nn_max = 0.0
    for cond in conditions:
        nn_vals = np.array([e.nn_distance_um for e in contract.edges
                            if e.condition == cond])
        if nn_vals.size == 0:
            continue
        nn_max = max(nn_max, float(nn_vals.max()))
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        # Density via histogram + step plot.
        bins = np.linspace(0, max(nn_vals.max() * 1.05, 1.0), 20)
        counts, edges_ = np.histogram(nn_vals, bins=bins, density=True)
        bin_mids = 0.5 * (edges_[:-1] + edges_[1:])
        inset.fill_between(bin_mids, 0, counts,
                           color=colour, alpha=0.40, zorder=2)
        inset.plot(bin_mids, counts, color=colour, lw=0.9, zorder=3)
    inset.set_xlabel("NN distance (um)", fontsize=6.0)
    inset.set_ylabel("density", fontsize=6.0)
    inset.tick_params(labelsize=5.8)
    inset.grid(color="#EEEEEE", lw=0.4, zorder=0)
    inset.set_axisbelow(True)
    for side in ("top", "right"):
        inset.spines[side].set_visible(False)
    inset.set_title("NN distance inset", fontsize=6.2, pad=2)

    ax.legend(fontsize=6.6, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncols=2, handlelength=1.2)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.4, pad=14,
    )
    return ax
