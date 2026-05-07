"""Overlap-juxtaposition quantification — per-cell scatter linking
polymer-overlap (actin-MT colocalization) to territory-juxtaposition
(zone abutment); per-condition LOWESS-style fit lines highlight the
shared manifold.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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
from ._shared import OverlapJuxtapositionCell

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class OverlapJuxtapositionInput(RecipeContract):
    cells: list[OverlapJuxtapositionCell] = Field(..., min_length=4)
    title: str = "Overlap × juxtaposition quantification"


def _demo() -> OverlapJuxtapositionInput:
    rng = np.random.default_rng(705)
    cells: list[OverlapJuxtapositionCell] = []
    # WT: low overlap, low juxtaposition.  LI: shifted up-and-right.
    for cond, ov_mu, jx_mu, n in (
        ("WT", 0.30, 0.25, 12),
        ("LI", 0.55, 0.50, 12),
    ):
        for k in range(n):
            ov = float(np.clip(rng.normal(ov_mu, 0.08), 0, 1))
            # Juxtaposition correlates with overlap on a shared manifold.
            jx = float(np.clip(0.7 * ov + rng.normal(0, 0.08)
                               + (jx_mu - 0.7 * ov_mu), 0, 1))
            cells.append(OverlapJuxtapositionCell(
                cell_id=f"{cond}_{k:02d}", condition=cond,
                polymer_overlap=ov,
                territory_juxtaposition=jx,
            ))
    return OverlapJuxtapositionInput(cells=cells)


_META = RecipeMetadata(
    name="overlap_juxtaposition_quantification",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per cell, do polymer-overlap (actin-MT colocalization) and "
        "territory-juxtaposition (zone abutment) co-vary on a shared "
        "condition-independent manifold, or do conditions occupy "
        "distinct regions?"
    ),
    required_fields=("cells",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("colocalization_vs_morphology_correlation",),
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
    contract=OverlapJuxtapositionInput,
    demo_contract=_demo,
)
def render(contract: OverlapJuxtapositionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    overlaps = np.array([c.polymer_overlap for c in contract.cells])
    juxtas = np.array([c.territory_juxtaposition for c in contract.cells])
    conditions_arr = [c.condition for c in contract.cells]
    conditions = list(dict.fromkeys(conditions_arr))

    # Per-condition scatter + LOWESS-style running median fit line.
    bits = []
    for cond in conditions:
        mask = np.array([c == cond for c in conditions_arr])
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        xs = overlaps[mask]
        ys = juxtas[mask]
        ax.scatter(xs, ys, s=44, color=colour,
                   edgecolor="white", linewidth=0.6, alpha=0.85,
                   zorder=5, label=cond)
        # Running-median fit (windowed; >=5 points per window).
        order = np.argsort(xs)
        if xs.size >= 5:
            window = max(5, xs.size // 4)
            xs_sorted = xs[order]
            ys_sorted = ys[order]
            running_med = np.array([
                np.median(ys_sorted[max(0, k - window // 2):
                                    min(xs.size, k + window // 2 + 1)])
                for k in range(xs.size)
            ])
            ax.plot(xs_sorted, running_med,
                    color=colour, lw=1.4, alpha=0.85, zorder=6)
        bits.append(f"{cond}: median overlap = "
                    f"{smart_fmt(float(np.median(xs)))}")

    ax.set_xlabel("polymer overlap (actin-MT colocalization)")
    ax.set_ylabel("territory juxtaposition")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.4)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
