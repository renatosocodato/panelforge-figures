"""Reproducibility correlogram — replicate × replicate Pearson r
matrix with lower-triangle numeric labels and block-structure detection.
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


class CorrelogramInput(RecipeContract):
    replicate_names: list[str] = Field(..., min_length=3)
    correlation_matrix: list[list[float]] = Field(
        ...,
        description="symmetric n × n Pearson r matrix",
    )
    group_membership: list[str] | None = Field(
        None,
        description="optional group label per replicate (for row-strip)",
    )
    title: str = "Replicate correlogram"


def _demo() -> CorrelogramInput:
    rng = np.random.default_rng(733)
    n = 8
    names = [f"rep {i + 1:02d}" for i in range(n)]
    groups = ["A"] * 3 + ["B"] * 3 + ["C"] * 2
    # Generate block-structured correlation matrix.
    R = np.eye(n)
    for i in range(n):
        for j in range(n):
            if i != j:
                if groups[i] == groups[j]:
                    R[i, j] = rng.uniform(0.85, 0.96)
                else:
                    R[i, j] = rng.uniform(0.45, 0.65)
    R = (R + R.T) / 2
    np.fill_diagonal(R, 1.0)
    return CorrelogramInput(
        replicate_names=names,
        correlation_matrix=R.tolist(),
        group_membership=groups,
    )


_META = RecipeMetadata(
    name="reproducibility_correlogram",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Pairwise, how correlated are replicate runs, and do they "
        "cluster into block groups?"
    ),
    required_fields=("replicate_names", "correlation_matrix"),
    optional_fields=("group_membership", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("replication_retrospective_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=CorrelogramInput,
    demo_contract=_demo,
)
def render(contract: CorrelogramInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    names = contract.replicate_names
    R = np.asarray(contract.correlation_matrix, float)
    n = R.shape[0]

    im = ax.imshow(R, cmap="RdBu_r", vmin=-1.0, vmax=1.0,
                   aspect="equal", interpolation="nearest",
                   zorder=2)

    ax.set_xticks(range(n))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=6.6)
    ax.set_yticks(range(n))
    ax.set_yticklabels(names, fontsize=6.6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label("Pearson r", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Lower-triangle numeric labels.
    for i in range(n):
        for j in range(n):
            if j > i:
                continue
            r = R[i, j]
            ax.text(j, i, smart_fmt(r),
                    ha="center", va="center", fontsize=6.4,
                    color=("white" if abs(r) > 0.55 else "#222222"),
                    zorder=4)

    # Group strip on the left edge if provided.
    if contract.group_membership is not None:
        groups = contract.group_membership
        unique = list(dict.fromkeys(groups))
        group_colors = ["#6FA8DC", "#E06666", "#93C47D", "#C27BA0", "#FFD966"]
        gmap = {g: group_colors[i % len(group_colors)]
                for i, g in enumerate(unique)}
        import matplotlib.patches as mpatches
        strip_x = -1.2
        for i, g in enumerate(groups):
            ax.add_patch(mpatches.Rectangle(
                (strip_x, i - 0.5), 0.6, 1.0,
                facecolor=gmap[g], edgecolor="white", linewidth=0.4,
                clip_on=False, zorder=3,
            ))
        # Group legend below axes.
        patches = [
            mpatches.Patch(facecolor=gmap[g], edgecolor="white",
                           label=f"group {g}")
            for g in unique
        ]
        ax.legend(handles=patches, fontsize=6.6, frameon=False,
                  loc="upper center", bbox_to_anchor=(0.5, -0.14),
                  ncols=len(unique), handlelength=1.0)

    # Summary: mean within-group vs between-group r.
    if contract.group_membership is not None:
        within, between = [], []
        for i in range(n):
            for j in range(n):
                if i >= j:
                    continue
                if groups[i] == groups[j]:
                    within.append(R[i, j])
                else:
                    between.append(R[i, j])
        w = float(np.mean(within)) if within else np.nan
        b = float(np.mean(between)) if between else np.nan
        ax.set_title(
            f"{contract.title}  ·  mean within-group r = {smart_fmt(w)}, "
            f"between r = {smart_fmt(b)}",
            fontsize=7.4, pad=4,
        )
    else:
        ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
