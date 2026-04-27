"""Aligned vs unaligned velocity split — split violin per condition
showing per-step velocity when heading is cue-aligned (cos > 0) vs
unaligned (cos < 0).

Split-violin family: >=2 violin bodies + >=1 median marker.
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

_ALIGNED_COLOR = "#26A69A"   # teal
_UNALIGNED_COLOR = "#EF5350"  # coral


class AlignedVelocityRow(RecipeContract):
    v_um_per_min: float
    cos_theta_c: float
    condition: str


class AlignedVsUnalignedSplitInput(RecipeContract):
    rows: list[AlignedVelocityRow] = Field(..., min_length=10)
    alignment_cut: float = 0.0
    title: str = "Aligned vs unaligned velocity"


def _demo() -> AlignedVsUnalignedSplitInput:
    rng = np.random.default_rng(3091)
    rows: list[AlignedVelocityRow] = []
    # Aligned cells move ~30 % faster.
    for cond, factor in (("control", 1.30), ("DISC1", 1.10)):
        for _ in range(300):
            cos = float(rng.uniform(-1, 1))
            v_base = float(rng.gamma(shape=2.5, scale=1.2))
            if cos > 0:
                v = v_base * factor
            else:
                v = v_base
            rows.append(AlignedVelocityRow(
                v_um_per_min=v, cos_theta_c=cos, condition=cond,
            ))
    return AlignedVsUnalignedSplitInput(rows=rows)


_META = RecipeMetadata(
    name="aligned_vs_unaligned_velocity_split",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per condition, are tip steps faster when the heading is "
        "cue-aligned (cos > 0) vs unaligned (cos < 0)?"
    ),
    required_fields=("rows",),
    optional_fields=("alignment_cut", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("chemotaxis_index_trajectory",),
)


@register_recipe(
    metadata=_META,
    contract=AlignedVsUnalignedSplitInput,
    demo_contract=_demo,
)
def render(contract: AlignedVsUnalignedSplitInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    conditions = list(dict.fromkeys(r.condition for r in contract.rows))
    positions = np.arange(len(conditions))

    def _draw_half(vals, pos, colour, side):
        if vals.size < 2:
            return
        parts = ax.violinplot([vals], positions=[pos], widths=0.78,
                              showmeans=False, showmedians=False,
                              showextrema=False)
        for pc in parts["bodies"]:
            pc.set_facecolor(colour)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.55)
            v = pc.get_paths()[0].vertices
            if side == "left":
                v[:, 0] = np.clip(v[:, 0], -np.inf, pos)
            else:
                v[:, 0] = np.clip(v[:, 0], pos, np.inf)

    medians_aligned: dict[str, float] = {}
    medians_unaligned: dict[str, float] = {}
    for pos, cond in zip(positions, conditions):
        rows = [r for r in contract.rows if r.condition == cond]
        aligned_vals = np.array([
            r.v_um_per_min for r in rows
            if r.cos_theta_c > contract.alignment_cut
        ])
        unaligned_vals = np.array([
            r.v_um_per_min for r in rows
            if r.cos_theta_c <= contract.alignment_cut
        ])
        _draw_half(aligned_vals, pos, _ALIGNED_COLOR, "left")
        _draw_half(unaligned_vals, pos, _UNALIGNED_COLOR, "right")
        if aligned_vals.size >= 4:
            med_a = float(np.median(aligned_vals))
            ax.scatter([pos - 0.15], [med_a], s=22,
                       facecolor="white", edgecolor="black",
                       linewidth=0.7, zorder=6)
            medians_aligned[cond] = med_a
        if unaligned_vals.size >= 4:
            med_u = float(np.median(unaligned_vals))
            ax.scatter([pos + 0.15], [med_u], s=22,
                       facecolor="white", edgecolor="black",
                       linewidth=0.7, zorder=6)
            medians_unaligned[cond] = med_u

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel("v (um/min)")
    ax.set_xlabel("condition")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=_ALIGNED_COLOR, edgecolor="#333333",
              alpha=0.55, label="aligned (cos > 0)"),
        Patch(facecolor=_UNALIGNED_COLOR, edgecolor="#333333",
              alpha=0.55, label="unaligned (cos < 0)"),
    ]
    ax.legend(handles=handles, fontsize=6.6, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=2, handlelength=1.0)

    bits = []
    for cond in conditions:
        a = medians_aligned.get(cond)
        u = medians_unaligned.get(cond)
        if a and u and u > 0:
            bits.append(f"{cond}: aligned/unaligned = {smart_fmt(a/u)}x")
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
