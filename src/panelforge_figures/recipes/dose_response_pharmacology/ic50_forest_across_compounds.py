"""IC50 forest — compounds ranked by IC50 with 95% CIs in log-molar space."""

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


class CompoundRow(RecipeContract):
    name: str
    ic50: float
    ci_lo: float
    ci_hi: float
    mechanism: str = "signaling"


class IC50ForestInput(RecipeContract):
    compounds: list[CompoundRow] = Field(..., min_length=2)
    reference_line: float | None = None
    title: str = "IC50 across compounds"


def _demo() -> IC50ForestInput:
    return IC50ForestInput(
        compounds=[
            CompoundRow(name="CompoundA", ic50=8e-9, ci_lo=5e-9, ci_hi=12e-9, mechanism="signaling"),
            CompoundRow(name="CompoundB", ic50=42e-9, ci_lo=28e-9, ci_hi=62e-9, mechanism="signaling"),
            CompoundRow(name="CompoundC", ic50=180e-9, ci_lo=120e-9, ci_hi=260e-9, mechanism="metabolic"),
            CompoundRow(name="CompoundD", ic50=620e-9, ci_lo=410e-9, ci_hi=920e-9, mechanism="metabolic"),
            CompoundRow(name="CompoundE", ic50=2.1e-6, ci_lo=1.4e-6, ci_hi=3.2e-6, mechanism="cytoskeletal"),
            CompoundRow(name="CompoundF", ic50=9.5e-6, ci_lo=6.4e-6, ci_hi=14.1e-6, mechanism="other"),
        ],
        reference_line=100e-9,
        title="IC50 panel (nM–μM)",
    )


_META = RecipeMetadata(
    name="ic50_forest_across_compounds",
    modality="dose_response_pharmacology",
    family=RecipeFamily.coef_forest,
    answers_question="How do compounds rank by IC50 across a chemical series?",
    required_fields=("compounds",),
    optional_fields=("reference_line", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("hill_fit_with_ci",),
)


@register_recipe(metadata=_META, contract=IC50ForestInput, demo_contract=_demo)
def render(contract: IC50ForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Sort most potent (lowest IC50) to top.
    rows = sorted(contract.compounds, key=lambda r: r.ic50)
    y = np.arange(len(rows))[::-1]

    for yi, r in zip(y, rows):
        color = (
            palette.pick(r.mechanism)
            if r.mechanism in palette.semantic
            else palette[0]
        )
        ax.plot([r.ci_lo, r.ci_hi], [yi, yi], color=color, lw=1.1, zorder=2)
        for x_end in (r.ci_lo, r.ci_hi):
            ax.plot([x_end, x_end], [yi - 0.17, yi + 0.17],
                    color=color, lw=1.1, zorder=2)
        ax.scatter([r.ic50], [yi], s=32, color=color,
                   edgecolor="white", linewidth=0.9, zorder=3)

    if contract.reference_line is not None:
        ax.axvline(contract.reference_line, color="#D32F2F", lw=0.8, ls="--", zorder=1)
        ax.text(contract.reference_line, len(rows) - 0.4,
                f"ref = {smart_fmt(contract.reference_line * 1e9)} nM",
                ha="center", va="bottom", fontsize=6.4, color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="none", alpha=0.92))

    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([r.name for r in rows], fontsize=7.2)
    ax.set_xlabel(r"IC$_{50}$ (M, log scale)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Per-row numeric label to the right.
    xhi = max(r.ci_hi for r in rows)
    ax.set_xlim(None, xhi * 3)
    for yi, r in zip(y, rows):
        ax.text(r.ci_hi * 1.08, yi,
                f"{smart_fmt(r.ic50 * 1e9)} nM",
                va="center", ha="left",
                fontsize=6.6, color="#222222")

    # Mechanism legend (compact, marker-based for Helvetica-safe glyphs).
    from matplotlib.lines import Line2D
    mechs = sorted({r.mechanism for r in rows})
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=(palette.pick(m) if m in palette.semantic else palette[0]),
               markeredgecolor="white", markersize=6,
               label=m)
        for m in mechs
    ]
    ax.legend(handles=proxies, loc="upper left",
              fontsize=6.4, frameon=True, framealpha=0.92,
              edgecolor="#BBBBBB", borderpad=0.4, handlelength=1.0,
              ncol=min(len(mechs), 2))
    ax.grid(axis="x", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
