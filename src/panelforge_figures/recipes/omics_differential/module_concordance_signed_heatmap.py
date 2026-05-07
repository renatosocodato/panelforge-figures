"""Module concordance signed heatmap — module × condition signed-
score heatmap with sign-concordance overlay (`+` / `-` / blank
glyphs, Helvetica-safe ASCII) showing where modules agree across
proteome and phosphoproteome layers.

Matrix family: >=1 imshow OR >=4 cell patches.
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
from ._shared import ModuleConcordanceCell


class ModuleConcordanceInput(RecipeContract):
    cells: list[ModuleConcordanceCell] = Field(..., min_length=4)
    module_order: list[str] | None = None
    condition_order: list[str] | None = None
    title: str = "Module concordance signed heatmap"


def _demo() -> ModuleConcordanceInput:
    rng = np.random.default_rng(812)
    modules = [
        "CDC42_GEF", "RAC_GEF", "RHO_GEF",
        "CDC42_GAP", "RAC_GAP", "RHO_GAP",
        "ARP2/3", "WASP", "FORMIN",
        "MOTOR_AXIN", "TRAFFICKING", "POLARITY",
    ]
    conditions = ["F-CKO", "M-CKO"]
    cells: list[ModuleConcordanceCell] = []
    # Per the manuscript: 5/12 modules show sign-concordance (~42%).
    concordant_modules = ["CDC42_GEF", "ARP2/3", "WASP",
                          "MOTOR_AXIN", "POLARITY"]
    for mod in modules:
        for cond in conditions:
            score = float(rng.normal(0, 0.8))
            if mod in concordant_modules:
                # Force same sign across conditions for concordant ones.
                if cond == "F-CKO":
                    score = float(abs(score) if mod in ("ARP2/3", "WASP") else -abs(score))
                else:
                    score = float(abs(score) if mod in ("ARP2/3", "WASP") else -abs(score))
                concordance = "agree"
            else:
                concordance = "disagree"
            cells.append(ModuleConcordanceCell(
                module=mod, condition=cond,
                signed_score=score,
                sign_concordance=concordance,
            ))
    return ModuleConcordanceInput(
        cells=cells,
        module_order=modules, condition_order=conditions,
    )


_META = RecipeMetadata(
    name="module_concordance_signed_heatmap",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across GEF / GAP / Effector modules and CKO conditions, "
        "which modules show sign-concordance between proteome and "
        "phosphoproteome layers?"
    ),
    required_fields=("cells",),
    optional_fields=("module_order", "condition_order", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("annotated_cluster_heatmap",),
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
    contract=ModuleConcordanceInput,
    demo_contract=_demo,
)
def render(contract: ModuleConcordanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Resolve orders.
    if contract.module_order is None:
        modules: list[str] = []
        for c in contract.cells:
            if c.module not in modules:
                modules.append(c.module)
    else:
        modules = list(contract.module_order)
    if contract.condition_order is None:
        conditions: list[str] = []
        for c in contract.cells:
            if c.condition not in conditions:
                conditions.append(c.condition)
    else:
        conditions = list(contract.condition_order)

    n_rows = len(modules)
    n_cols = len(conditions)

    # Build the score matrix.
    Z = np.zeros((n_rows, n_cols))
    glyph = np.empty((n_rows, n_cols), dtype=object)
    for c in contract.cells:
        if c.module not in modules or c.condition not in conditions:
            continue
        i = modules.index(c.module)
        j = conditions.index(c.condition)
        Z[i, j] = float(c.signed_score)
        if c.sign_concordance == "agree":
            glyph[i, j] = "+" if c.signed_score >= 0 else "-"
        elif c.sign_concordance == "disagree":
            glyph[i, j] = ""
        else:
            glyph[i, j] = ""

    v_abs = max(0.5, float(np.abs(Z).max()))
    im = ax.imshow(Z, cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
                   aspect="auto", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("signed centred score", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell annotations: signed score + concordance glyph.
    for i in range(n_rows):
        for j in range(n_cols):
            v = Z[i, j]
            txt_color = "white" if abs(v) > 0.55 * v_abs else "#222222"
            ax.text(j, i, f"{smart_fmt(v)}",
                    ha="center", va="center", fontsize=6.4,
                    color=txt_color, zorder=4)
            # Concordance glyph in upper-right corner of cell.
            if glyph[i, j]:
                ax.text(j + 0.32, i - 0.32, glyph[i, j],
                        ha="center", va="center", fontsize=8.4,
                        color=txt_color, fontweight="bold",
                        zorder=4)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(modules, fontsize=6.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    n_concordant = sum(
        1 for c in contract.cells if c.sign_concordance == "agree"
    ) // n_cols    # one count per module
    ax.set_title(
        f"{contract.title}  ·  {n_concordant}/{n_rows} modules "
        f"sign-concordant",
        fontsize=8.2, pad=4,
    )
    return ax
