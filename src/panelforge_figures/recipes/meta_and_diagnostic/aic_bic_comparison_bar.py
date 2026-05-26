"""AIC/BIC comparison bar — side-by-side info-criterion ranking across models.

Best (lowest) criterion highlighted; rest in neutral color.
"""

from __future__ import annotations

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ModelICEntry(RecipeContract):
    model_name: str
    AIC: float
    BIC: float


class AICBICInput(RecipeContract):
    models: list[ModelICEntry]
    title: str = "AIC / BIC model comparison"
    best_color: str = "#e67e22"
    other_color: str = "#5b8aa4"


def _demo() -> AICBICInput:
    return AICBICInput(
        models=[
            ModelICEntry(model_name="A", AIC=-38.9, BIC=-36.6),
            ModelICEntry(model_name="B", AIC=-42.3, BIC=-38.8),
            ModelICEntry(model_name="C", AIC=-41.1, BIC=-36.4),
            ModelICEntry(model_name="D", AIC=-40.0, BIC=-34.2),
        ],
        title="AIC/BIC across Odijk model variants (lower = better)",
    )


_META = RecipeMetadata(
    name="aic_bic_comparison_bar",
    modality="meta_and_diagnostic",
    family=RecipeFamily.sobol_bar,
    answers_question="Which model variant is preferred by AIC vs BIC?",
    required_fields=("models",),
    optional_fields=("title", "best_color", "other_color"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("competing_model_residual_panels",),
)


@register_recipe(metadata=_META, contract=AICBICInput, demo_contract=_demo)
def render(contract: AICBICInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")

    if len(contract.models) == 0:
        ax.text(0.5, 0.5, "No models supplied", ha="center", va="center")
        return ax

    names = [m.model_name for m in contract.models]
    aics = np.asarray([m.AIC for m in contract.models])
    bics = np.asarray([m.BIC for m in contract.models])
    best_aic = int(np.argmin(aics))
    best_bic = int(np.argmin(bics))

    # Two side-by-side subplots via inset axes
    gs = fig.add_gridspec(1, 2, wspace=0.25, left=0.08, right=0.97,
                          top=0.86, bottom=0.10)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1], sharey=ax1)
    AESTHETIC.apply_to_ax(ax1)
    AESTHETIC.apply_to_ax(ax2)

    x = np.arange(len(names))
    aic_colors = [contract.best_color if i == best_aic else contract.other_color for i in range(len(names))]
    bic_colors = [contract.best_color if i == best_bic else contract.other_color for i in range(len(names))]

    ax1.bar(x, aics, color=aic_colors, edgecolor="#23416b", linewidth=0.5)
    for i, v in enumerate(aics):
        ax1.text(i, v + 0.2, f"{v:.1f}", ha="center", fontsize=8.4, color="#444")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax1.set_ylabel("Information criterion (lower better)")
    ax1.set_title("AIC", fontsize=9.6)
    ax1.spines[["top", "right"]].set_visible(False)

    ax2.bar(x, bics, color=bic_colors, edgecolor="#23416b", linewidth=0.5)
    for i, v in enumerate(bics):
        ax2.text(i, v + 0.2, f"{v:.1f}", ha="center", fontsize=8.4, color="#444")
    ax2.set_xticks(x)
    ax2.set_xticklabels(names)
    ax2.set_title("BIC", fontsize=9.6)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle(contract.title, fontsize=9.6, color="#2c3e50", y=0.97)
    return ax
