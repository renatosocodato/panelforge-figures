"""Multiverse robustness classification bar — per-specification
ROBUST / FRAGILE / NON_SIG verdict bar with stacked composition
fractions and tally callouts.

Matrix family: >=1 imshow OR >=4 cell patches.
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
from ._shared import MultiverseSpec

_CLASS_COLOR = {
    "ROBUST": "#2E7D32",      # green
    "FRAGILE": "#FB8C00",     # amber
    "NON_SIG": "#9E9E9E",     # grey
}


class MultiverseClassificationInput(RecipeContract):
    specs: list[MultiverseSpec] = Field(..., min_length=4)
    title: str = "Multiverse robustness classification"


def _demo() -> MultiverseClassificationInput:
    rng = np.random.default_rng(804)
    specs: list[MultiverseSpec] = []
    for k in range(12):
        # 7 ROBUST, 3 FRAGILE, 2 NON_SIG.
        if k < 7:
            cls = "ROBUST"
            eff = float(rng.normal(0.45, 0.05))
        elif k < 10:
            cls = "FRAGILE"
            eff = float(rng.normal(0.30, 0.08))
        else:
            cls = "NON_SIG"
            eff = float(rng.normal(0.05, 0.04))
        specs.append(MultiverseSpec(
            spec_id=f"S{k:02d}",
            spec_label=f"spec {k:02d}",
            effect_size=eff,
            ci_lo=eff - 0.18, ci_hi=eff + 0.18,
            classification=cls,
        ))
    return MultiverseClassificationInput(specs=specs)


_META = RecipeMetadata(
    name="multiverse_robustness_classification_bar",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across analytical specifications, what fraction are "
        "ROBUST / FRAGILE / NON_SIG, and how does the verdict "
        "stack up as a single composition bar?"
    ),
    required_fields=("specs",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("multiverse_specification_curve",),
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
    contract=MultiverseClassificationInput,
    demo_contract=_demo,
)
def render(contract: MultiverseClassificationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.specs)

    # Tally per class.
    tally = {"ROBUST": 0, "FRAGILE": 0, "NON_SIG": 0}
    for s in contract.specs:
        if s.classification in tally:
            tally[s.classification] += 1
    fractions = {k: v / n for k, v in tally.items()}

    # Top half: per-spec coloured cell strip showing each spec
    # individually as a cell patch.
    strip_y = 0.55
    strip_h = 0.30
    cell_w = 0.85 / n
    pad_left = 0.07
    for i, s in enumerate(contract.specs):
        x_lo = pad_left + i * cell_w
        colour = _CLASS_COLOR.get(s.classification, "#888888")
        ax.add_patch(mpatches.Rectangle(
            (x_lo, strip_y), cell_w * 0.92, strip_h,
            transform=ax.transAxes,
            facecolor=colour, edgecolor="white",
            linewidth=0.6, zorder=3,
        ))

    # Spec-id ticks below cell strip.
    for i, s in enumerate(contract.specs):
        x_lo = pad_left + i * cell_w + cell_w * 0.46
        ax.text(x_lo, strip_y - 0.04, s.spec_id,
                transform=ax.transAxes,
                ha="center", va="top", fontsize=5.6,
                color="#666666", rotation=70, zorder=4)

    # Bottom half: stacked composition bar (one row, three coloured
    # blocks) with fraction labels.
    bar_y = 0.18
    bar_h = 0.18
    cur_x = pad_left
    bar_w = 0.85
    for cls in ("ROBUST", "FRAGILE", "NON_SIG"):
        frac = fractions[cls]
        if frac <= 0:
            continue
        block_w = bar_w * frac
        colour = _CLASS_COLOR[cls]
        ax.add_patch(mpatches.Rectangle(
            (cur_x, bar_y), block_w, bar_h,
            transform=ax.transAxes,
            facecolor=colour, edgecolor="white",
            linewidth=0.6, zorder=3,
        ))
        # Inline label.
        ax.text(cur_x + block_w / 2, bar_y + bar_h / 2,
                f"{cls}\n{tally[cls]}/{n}  "
                f"({smart_fmt(frac * 100)}%)",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=5.6 if block_w < 0.15 else 6.4,
                color="white", fontweight="bold", zorder=4)
        cur_x += block_w

    # Strip + bar group labels.
    ax.text(0.04, strip_y + strip_h / 2,
            "per-spec",
            transform=ax.transAxes,
            ha="right", va="center", fontsize=6.6,
            color="#444444", fontweight="bold")
    ax.text(0.04, bar_y + bar_h / 2,
            "composition",
            transform=ax.transAxes,
            ha="right", va="center", fontsize=6.6,
            color="#444444", fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    bits = "  ".join(
        f"{cls}: {tally[cls]} ({smart_fmt(fractions[cls] * 100)}%)"
        for cls in ("ROBUST", "FRAGILE", "NON_SIG")
    )
    ax.set_title(
        f"{contract.title}  ·  n = {n} specs  ·  {bits}",
        fontsize=8.2, pad=8,
    )
    return ax
