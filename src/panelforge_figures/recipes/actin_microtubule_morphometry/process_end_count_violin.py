"""Terminal-tip counts per cell — split violin by primary / higher-order ends."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ProcessEndCountInput(RecipeContract):
    end_counts_by_condition: dict[str, dict[str, list[float]]] = Field(
        ..., description="condition → {'primary': [...], 'higher_order': [...]} counts"
    )
    title: str = "Terminal-tip counts"


def _demo() -> ProcessEndCountInput:
    rng = np.random.default_rng(707)
    out: dict[str, dict[str, list[float]]] = {}
    for cond, prim_mu, higher_mu in [
        ("control", 2.4, 9.5),
        ("mutant",  3.1, 4.8),
        ("rescue",  2.6, 8.2),
    ]:
        out[cond] = {
            "primary":      rng.poisson(prim_mu, 54).tolist(),
            "higher_order": rng.poisson(higher_mu, 54).tolist(),
        }
    return ProcessEndCountInput(end_counts_by_condition=out)


_META = RecipeMetadata(
    name="process_end_count_violin",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does the per-cell number of terminal tips distribute across "
        "conditions, split by primary vs. higher-order ends?"
    ),
    required_fields=("end_counts_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("branch_point_count_raincloud",),
)


@register_recipe(
    metadata=_META,
    contract=ProcessEndCountInput,
    demo_contract=_demo,
)
def render(contract: ProcessEndCountInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.end_counts_by_condition.keys())
    positions = list(range(len(conditions)))

    # Split violin: two violins per position, one mirrored to the left,
    # one to the right, colour-coded by end-type.
    color_primary = palette.pick("actin") if "actin" in palette.semantic else palette[0]
    color_higher = palette.pick("microtubule") if "microtubule" in palette.semantic else palette[1]

    def _draw_half(vals: np.ndarray, pos: float, color: str, side: str):
        parts = ax.violinplot([vals], positions=[pos], widths=0.88,
                              showmeans=False, showmedians=False, showextrema=False)
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.55)
            v = pc.get_paths()[0].vertices
            if side == "left":
                v[:, 0] = np.clip(v[:, 0], -np.inf, pos)
            else:
                v[:, 0] = np.clip(v[:, 0], pos, np.inf)

    for pos, cond in zip(positions, conditions):
        prim = np.asarray(contract.end_counts_by_condition[cond]["primary"], float)
        higher = np.asarray(contract.end_counts_by_condition[cond]["higher_order"], float)
        _draw_half(prim, pos, color_primary, "left")
        _draw_half(higher, pos, color_higher, "right")
        # Median markers at the centerline for each side.
        for vals, x_off, outline in [(prim, -0.08, color_primary),
                                      (higher, 0.08, color_higher)]:
            if vals.size < 4:
                continue
            q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
            ax.plot([pos + x_off, pos + x_off], [q1, q3],
                    color="black", lw=2.2, zorder=5, solid_capstyle="butt")
            ax.scatter([pos + x_off], [med], s=28, facecolor="white",
                       edgecolor="black", linewidth=0.9, zorder=6)

    # Legend via proxy patches.
    from matplotlib.patches import Patch
    ax.legend(
        handles=[
            Patch(facecolor=color_primary, edgecolor="#333333", alpha=0.55,
                  label="primary"),
            Patch(facecolor=color_higher, edgecolor="#333333", alpha=0.55,
                  label="higher-order"),
        ],
        fontsize=6.8, frameon=False, loc="upper left", handlelength=1.2,
    )

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel("terminal-tip count per cell")
    # Header medians — primary / higher-order for each condition.
    medians = []
    for cond in conditions:
        prim_med = float(np.median(contract.end_counts_by_condition[cond]["primary"]))
        high_med = float(np.median(contract.end_counts_by_condition[cond]["higher_order"]))
        medians.append(f"{cond}: {smart_fmt(prim_med)} / {smart_fmt(high_med)}")
    ax.set_title(
        f"{contract.title}  ·  primary / higher-order medians  "
        f"·  {'  ·  '.join(medians)}",
        fontsize=8.4, pad=4,
    )
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
