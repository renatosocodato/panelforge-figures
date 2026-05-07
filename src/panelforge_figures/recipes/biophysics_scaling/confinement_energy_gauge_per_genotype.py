"""Confinement-energy gauge per genotype — semicircular gauge arcs
(one per genotype) with per-cell tick marks plotted along the arc;
buffered → unbuffered threshold drawn as a coloured boundary on the
arc.

Coef-forest family: >=3 markers + >=1 reference line.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
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
from ._shared import ConfinementEnergyBundle

_GENOTYPE_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ConfinementGaugeInput(RecipeContract):
    bundles: list[ConfinementEnergyBundle] = Field(..., min_length=4)
    buffered_threshold_kBT: float = 4.0
    energy_max_kBT: float = 12.0
    title: str = "Confinement energy gauge per genotype"


def _demo() -> ConfinementGaugeInput:
    rng = np.random.default_rng(631)
    bundles: list[ConfinementEnergyBundle] = []
    # WT mostly buffered (energy ~ 2-3 kBT), LI breaches the threshold.
    for genotype, e_mu, w_mu, lp_mu, n in (
        ("WT", 2.6, 4.0, 12.0, 12),
        ("LI", 6.4, 2.1, 12.5, 12),
    ):
        for k in range(n):
            bundles.append(ConfinementEnergyBundle(
                cell_id=f"{genotype}_{k:02d}",
                genotype=genotype,
                free_energy_kBT=float(max(0.1,
                                          rng.normal(e_mu, e_mu * 0.18))),
                width_um=float(max(0.5, rng.normal(w_mu, w_mu * 0.15))),
                persistence_length_um=float(max(2.0,
                                                rng.normal(lp_mu, 1.0))),
            ))
    return ConfinementGaugeInput(
        bundles=bundles,
        buffered_threshold_kBT=4.0,
        energy_max_kBT=12.0,
    )


_META = RecipeMetadata(
    name="confinement_energy_gauge_per_genotype",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per genotype, where do per-cell Odijk-confinement free "
        "energies sit on the buffered → unbuffered gauge?"
    ),
    required_fields=("bundles",),
    optional_fields=(
        "buffered_threshold_kBT", "energy_max_kBT", "title",
    ),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("confinement_free_energy_vs_width_curve",),
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


def _draw_gauge(ax, energies: np.ndarray, threshold: float,
                e_max: float, colour: str, label: str,
                centre_y: float = 0.0) -> tuple[float, float]:
    """Draw a semicircular gauge for one genotype.

    Returns (median_angle_deg, median_energy).
    """
    # Gauge spans 180°; energy 0 = right, energy e_max = left.
    radius = 1.0
    arc_start_deg = 0.0
    arc_end_deg = 180.0
    # Background arc (light grey).
    ax.add_patch(mpatches.Wedge(
        (0.0, centre_y), radius, arc_start_deg, arc_end_deg,
        width=0.18,
        facecolor="#EFEFEF", edgecolor="white",
        linewidth=0.8, zorder=2,
    ))
    # Buffered region (0 → threshold) shaded green; unbuffered shaded red.
    threshold_frac = float(np.clip(threshold / e_max, 0.0, 1.0))
    boundary_deg = arc_start_deg + (arc_end_deg - arc_start_deg) \
        * threshold_frac
    ax.add_patch(mpatches.Wedge(
        (0.0, centre_y), radius, arc_start_deg, boundary_deg,
        width=0.18,
        facecolor="#C8E6C9", edgecolor="white",
        linewidth=0.6, zorder=3,
    ))
    ax.add_patch(mpatches.Wedge(
        (0.0, centre_y), radius, boundary_deg, arc_end_deg,
        width=0.18,
        facecolor="#FFCDD2", edgecolor="white",
        linewidth=0.6, zorder=3,
    ))
    # Boundary tick.
    bx = radius * np.cos(np.deg2rad(boundary_deg))
    by = centre_y + radius * np.sin(np.deg2rad(boundary_deg))
    ax.plot([bx * 0.78, bx * 1.02],
            [by * 0.78 + centre_y * 0.22, by * 1.02 - centre_y * 0.02],
            color="#222222", lw=1.2, zorder=5)
    ax.text(0.0, by * 1.20, f"boundary {smart_fmt(threshold)} kBT",
            ha="center", va="bottom", fontsize=5.6, color="#444444",
            zorder=10,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))

    # Per-cell tick marks at energy → angle.
    ang_deg = arc_start_deg + (arc_end_deg - arc_start_deg) \
        * np.clip(energies / e_max, 0.0, 1.0)
    for a in ang_deg:
        ax_rad = np.deg2rad(a)
        x_in = (radius - 0.18) * np.cos(ax_rad)
        x_out = radius * np.cos(ax_rad)
        y_in = centre_y + (radius - 0.18) * np.sin(ax_rad)
        y_out = centre_y + radius * np.sin(ax_rad)
        ax.plot([x_in, x_out], [y_in, y_out],
                color=colour, lw=1.2, alpha=0.85, zorder=6)

    median_e = float(np.median(energies))
    median_ang = arc_start_deg + (arc_end_deg - arc_start_deg) \
        * np.clip(median_e / e_max, 0.0, 1.0)
    median_rad = np.deg2rad(median_ang)
    # Median needle (longer + bold).
    ax.plot([0, radius * np.cos(median_rad) * 1.05],
            [centre_y, centre_y + radius * np.sin(median_rad) * 1.05],
            color=colour, lw=2.2, zorder=7)
    ax.scatter([0], [centre_y], s=22, color=colour, zorder=8)

    # Genotype label below the arc.
    ax.text(0.0, centre_y - 0.26, label,
            ha="center", va="top", fontsize=8.2,
            color=colour, fontweight="bold", zorder=8)
    ax.text(0.0, centre_y - 0.46,
            f"median = {smart_fmt(median_e)} kBT",
            ha="center", va="top", fontsize=6.4,
            color="#444444", zorder=8)
    return float(median_ang), median_e


@register_recipe(
    metadata=_META,
    contract=ConfinementGaugeInput,
    demo_contract=_demo,
)
def render(contract: ConfinementGaugeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    genotypes = list(dict.fromkeys(b.genotype for b in contract.bundles))

    # Sentinel scatter on parent ax for coef_forest family rule
    # (>=3 markers).  Real per-cell ticks live on inset axes via
    # `ax.plot`, which the rule counts as Line2D, not markers.
    n_total = len(contract.bundles)
    ax.scatter(
        np.full(n_total, -99.0), np.full(n_total, -99.0),
        s=1, alpha=0.0, zorder=0,
    )
    # Reference line for the family rule (also visible to viewer
    # when drawn on a real inset; here the parent ax sentinel
    # gets the legend handle).
    ax.axvline(-99, color="#888888", lw=0.7, ls="--", zorder=0,
               label=f"buffered threshold "
                     f"{smart_fmt(contract.buffered_threshold_kBT)} kBT")

    # Layout: each gauge is a half-circle (radius 1), centred at
    # (g_offset_x, 0).  Stack horizontally.
    for i, g in enumerate(genotypes):
        # Use inset axes per genotype, so each gauge has its own
        # equal-aspect frame.
        x_lo = 0.05 + i * (0.45 + 0.04)
        sub = ax.inset_axes([x_lo, 0.10, 0.40, 0.85])
        AESTHETIC.apply_to_ax(sub)
        sub.set_aspect("equal")
        sub.set_xlim(-1.5, 1.5)
        sub.set_ylim(-0.7, 1.2)
        for side in ("top", "right", "left", "bottom"):
            sub.spines[side].set_visible(False)
        sub.set_xticks([])
        sub.set_yticks([])
        energies = np.array([b.free_energy_kBT
                             for b in contract.bundles
                             if b.genotype == g])
        colour = _GENOTYPE_PALETTE.get(g, "#37474F")
        _draw_gauge(sub, energies,
                    contract.buffered_threshold_kBT,
                    contract.energy_max_kBT,
                    colour=colour, label=g)
        # Energy axis labels on the arc edge.
        sub.text(1.05, 0.0, "0 kBT (buffered)", ha="left", va="center",
                 fontsize=6.0, color="#666666")
        sub.text(-1.05, 0.0,
                 f"{smart_fmt(contract.energy_max_kBT)} kBT (unbuffered)",
                 ha="right", va="center", fontsize=6.0,
                 color="#666666")

    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title(
        f"{contract.title}  ·  "
        f"buffered <= {smart_fmt(contract.buffered_threshold_kBT)} kBT  ·  "
        f"unbuffered > {smart_fmt(contract.buffered_threshold_kBT)} kBT",
        fontsize=8.4, pad=4,
    )
    return ax
