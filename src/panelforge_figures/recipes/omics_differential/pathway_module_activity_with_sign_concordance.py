"""Pathway-module activity with sign-concordance — sex × genotype ×
module heatmap (manuscript Fig 4G layout) with sign-concordance
glyphs ('+' / '−' / blank, Helvetica-safe ASCII) overlaid in cell
corners marking proteome-vs-phospho agreement per cell.

Matrix family: >=1 imshow OR >=4 cell patches.
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
from ._shared import ModuleConcordanceCell


class PathwayModuleSignConcordanceInput(RecipeContract):
    cells: list[ModuleConcordanceCell] = Field(..., min_length=4)
    module_order: list[str] | None = None
    condition_order: list[str] | None = None
    title: str = "Pathway-module activity with sign-concordance"


def _demo() -> PathwayModuleSignConcordanceInput:
    rng = np.random.default_rng(817)
    # Match the manuscript Fig 4G layout: 4 conditions × 7 modules
    # showing sex-asymmetric remodelling.
    modules = [
        "CDC42_GEF", "RAC_GEF", "CDC42_GAP", "RAC_GAP",
        "ARP2/3", "WASP", "FORMIN",
    ]
    conditions = ["F-CTL", "F-CKO", "M-CTL", "M-CKO"]
    # Manuscript-anchored values: female CKO CDC42_GEF -2.22,
    # RAC_GEF +1.58, etc.
    score_table = {
        ("CDC42_GEF", "F-CTL"): -0.65, ("CDC42_GEF", "F-CKO"): -2.22,
        ("CDC42_GEF", "M-CTL"): +0.65, ("CDC42_GEF", "M-CKO"): -0.71,
        ("RAC_GEF",   "F-CTL"): +0.40, ("RAC_GEF",   "F-CKO"): +1.58,
        ("RAC_GEF",   "M-CTL"): -0.40, ("RAC_GEF",   "M-CKO"): -0.10,
        ("CDC42_GAP", "F-CTL"): +0.20, ("CDC42_GAP", "F-CKO"): -0.40,
        ("CDC42_GAP", "M-CTL"): +0.10, ("CDC42_GAP", "M-CKO"): +0.20,
        ("RAC_GAP",   "F-CTL"): -0.10, ("RAC_GAP",   "F-CKO"): -0.30,
        ("RAC_GAP",   "M-CTL"): -0.20, ("RAC_GAP",   "M-CKO"): -0.40,
        ("ARP2/3",    "F-CTL"): +0.40, ("ARP2/3",    "F-CKO"): -1.80,
        ("ARP2/3",    "M-CTL"): +0.30, ("ARP2/3",    "M-CKO"): +2.88,
        ("WASP",      "F-CTL"): +0.10, ("WASP",      "F-CKO"): -0.76,
        ("WASP",      "M-CTL"): +0.20, ("WASP",      "M-CKO"): -1.96,
        ("FORMIN",    "F-CTL"): +0.05, ("FORMIN",    "F-CKO"): -0.35,
        ("FORMIN",    "M-CTL"): +0.10, ("FORMIN",    "M-CKO"): -0.42,
    }
    cells: list[ModuleConcordanceCell] = []
    for mod in modules:
        for cond in conditions:
            score = float(score_table.get((mod, cond), 0.0)
                          + rng.normal(0, 0.04))
            # Concordance: agree if F-CKO and M-CKO have same sign,
            # else disagree.  Tag agree on the *-CKO cells only.
            if cond.endswith("CKO"):
                f_score = score_table.get((mod, "F-CKO"), 0.0)
                m_score = score_table.get((mod, "M-CKO"), 0.0)
                concordance = "agree" if np.sign(f_score) == np.sign(m_score) else "disagree"
            else:
                concordance = "neutral"
            cells.append(ModuleConcordanceCell(
                module=mod, condition=cond,
                signed_score=score,
                sign_concordance=concordance,
            ))
    return PathwayModuleSignConcordanceInput(
        cells=cells,
        module_order=modules, condition_order=conditions,
    )


_META = RecipeMetadata(
    name="pathway_module_activity_with_sign_concordance",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across sex × genotype conditions and GEF / GAP / Effector "
        "modules, where do CKO conditions show sign-concordant "
        "remodelling between sexes vs sex-asymmetric divergence?"
    ),
    required_fields=("cells",),
    optional_fields=("module_order", "condition_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("pathway_module_activity_heatmap",
                              "module_concordance_signed_heatmap"),
)


@register_recipe(
    metadata=_META,
    contract=PathwayModuleSignConcordanceInput,
    demo_contract=_demo,
)
def render(contract: PathwayModuleSignConcordanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

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
    Z = np.zeros((n_rows, n_cols))
    glyph = np.empty((n_rows, n_cols), dtype=object)
    for c in contract.cells:
        if c.module in modules and c.condition in conditions:
            i = modules.index(c.module)
            j = conditions.index(c.condition)
            Z[i, j] = float(c.signed_score)
            if c.sign_concordance == "agree":
                glyph[i, j] = "+" if c.signed_score >= 0 else "−"
            elif c.sign_concordance == "disagree":
                glyph[i, j] = "−" if c.signed_score < 0 else "+"
            else:
                glyph[i, j] = ""

    v_abs = max(0.5, float(np.abs(Z).max()))
    im = ax.imshow(Z, cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
                   aspect="auto", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("centred module-state score", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell annotations + concordance glyph corner.
    for i in range(n_rows):
        for j in range(n_cols):
            v = Z[i, j]
            txt_color = "white" if abs(v) > 0.55 * v_abs else "#222222"
            ax.text(j, i, f"{smart_fmt(v)}",
                    ha="center", va="center", fontsize=6.6,
                    color=txt_color, zorder=4)
            # Concordance glyph: small tag in upper-right corner of
            # the cell — only meaningful on -CKO columns.
            if glyph[i, j]:
                ax.text(j + 0.34, i - 0.34, glyph[i, j],
                        ha="center", va="center", fontsize=8.6,
                        color=txt_color, fontweight="bold",
                        zorder=4)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(modules, fontsize=6.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Tally agree vs disagree on -CKO columns.
    cko_cells = [c for c in contract.cells if c.condition.endswith("CKO")]
    n_agree = sum(1 for c in cko_cells if c.sign_concordance == "agree")
    n_disagree = sum(1 for c in cko_cells
                     if c.sign_concordance == "disagree")
    ax.set_title(
        f"{contract.title}  ·  CKO sign-concordance: "
        f"{n_agree // 2} agree / "
        f"{n_disagree // 2} disagree (per module)",
        fontsize=8.2, pad=4,
    )
    return ax
