"""Significant-but-biologically-negligible classification bar.

Flags metrics where p < 0.05 but Cohen's |d| < 0.2 — the audit class that
catches statistical-significance-without-effect-size traps.
"""

from __future__ import annotations

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class SigNegligibleEntry(RecipeContract):
    metric_name: str
    p_value: float
    effect_size_d: float


class SigNegligibleInput(RecipeContract):
    entries: list[SigNegligibleEntry]
    negligible_threshold: float = 0.2
    title: str = "Significant but biologically negligible"


def _demo() -> SigNegligibleInput:
    return SigNegligibleInput(
        entries=[
            SigNegligibleEntry(metric_name="coloc_costes_p", p_value=0.003, effect_size_d=0.14),
            SigNegligibleEntry(metric_name="actin_branch_density", p_value=0.012, effect_size_d=0.18),
            SigNegligibleEntry(metric_name="mt_endpoints", p_value=0.024, effect_size_d=0.11),
            SigNegligibleEntry(metric_name="zone_contact_fraction", p_value=0.041, effect_size_d=0.07),
            SigNegligibleEntry(metric_name="morph_spread_idx", p_value=0.018, effect_size_d=0.16),
        ],
        title="Significant (p<0.05) AND biologically negligible (|d|<0.2): 5 metrics",
    )


_META = RecipeMetadata(
    name="significant_negligible_classification_bar",
    modality="meta_and_diagnostic",
    family=RecipeFamily.sobol_bar,
    answers_question="Which significant metrics carry effect sizes too small to matter biologically?",
    required_fields=("entries",),
    optional_fields=("negligible_threshold", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("equivalence_forest_with_tost_bounds",),
)


@register_recipe(metadata=_META, contract=SigNegligibleInput, demo_contract=_demo)
def render(contract: SigNegligibleInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(8.0, 5.0))
    AESTHETIC.apply_to_ax(ax)

    entries = sorted(contract.entries, key=lambda e: e.p_value)
    if not entries:
        ax.text(0.5, 0.5, "No significant-but-negligible metrics found",
                ha="center", va="center", fontsize=9.6, transform=ax.transAxes)
        ax.set_title(contract.title, fontsize=9.6)
        return ax

    y = np.arange(len(entries))[::-1]
    abs_d = [abs(e.effect_size_d) for e in entries]
    ax.barh(y, abs_d, color="#aaaaaa", edgecolor="#666", linewidth=0.5)
    ax.axvline(contract.negligible_threshold, color="#c0392b", ls="--", lw=1.2,
               label=f"|d| = {contract.negligible_threshold:.1f} negligible bound")
    ax.set_yticks(y)
    ax.set_yticklabels([e.metric_name.replace("_", " ")[:38] for e in entries],
                       fontsize=8.4)
    for i, (yi, e) in enumerate(zip(y, entries)):
        ax.text(abs_d[i] + 0.005, yi, f"p={e.p_value:.3g}",
                va="center", fontsize=7.0, color="#444")
    ax.set_xlabel("|Cohen d|")
    ax.set_title(f"{contract.title} (n={len(entries)})",
                 fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=8.4, frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    return ax
