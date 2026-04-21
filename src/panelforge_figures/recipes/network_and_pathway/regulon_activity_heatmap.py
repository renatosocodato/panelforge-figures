"""TF-regulon activity heatmap — regulon × sample."""

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


class RegulonHeatmapInput(RecipeContract):
    regulon_names: list[str] = Field(..., min_length=3)
    sample_names: list[str] = Field(..., min_length=3)
    activity: list[list[float]] = Field(
        ..., description="n_regulons × n_samples activity (z-scored)"
    )
    sample_groups: list[str] | None = None
    title: str = "TF-regulon activity"


def _demo() -> RegulonHeatmapInput:
    rng = np.random.default_rng(821)
    regulons = ["NFkB", "IRF3", "STAT1", "STAT3", "FOXO3",
                "HIF1A", "NFE2L2", "PPARG", "MYC", "TP53"]
    samples = [f"s{i:02d}" for i in range(15)]
    n_r, n_s = len(regulons), len(samples)
    A = rng.normal(0, 0.6, (n_r, n_s))
    grp_b = list(range(5, 10))
    grp_c = list(range(10, 15))
    A[:3, grp_b] += 1.2     # NFkB / IRF3 / STAT1 up in LPS
    A[5:7, grp_c] += 1.0    # HIF1A / NFE2L2 up in rescue
    A[8, grp_b] -= 0.8      # MYC down in LPS
    return RegulonHeatmapInput(
        regulon_names=regulons,
        sample_names=samples,
        activity=A.tolist(),
        sample_groups=(["ctrl"] * 5 + ["LPS"] * 5 + ["rescue"] * 5),
    )


_META = RecipeMetadata(
    name="regulon_activity_heatmap",
    modality="network_and_pathway",
    family=RecipeFamily.heatmap,
    answers_question=(
        "How does each TF-regulon's activity score vary across "
        "samples / conditions?"
    ),
    required_fields=("regulon_names", "sample_names", "activity"),
    optional_fields=("sample_groups", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("module_eigengene_heatmap",),
)


@register_recipe(
    metadata=_META,
    contract=RegulonHeatmapInput,
    demo_contract=_demo,
)
def render(contract: RegulonHeatmapInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    regulons = contract.regulon_names
    samples = contract.sample_names
    A = np.asarray(contract.activity, float)
    n_r, n_s = A.shape
    v_hi = float(max(abs(A).max(), 1e-9))

    cmap = mpl.colormaps["RdBu_r"]
    im = ax.imshow(A, cmap=cmap, vmin=-v_hi, vmax=v_hi,
                   aspect="auto", interpolation="nearest")
    ax.set_xticks(range(n_s))
    ax.set_xticklabels(samples, rotation=45, ha="right", fontsize=6.2)
    ax.set_yticks(range(n_r))
    ax.set_yticklabels(regulons, fontsize=6.8)

    # Condition strip below.
    if contract.sample_groups is not None:
        groups = contract.sample_groups
        unique = list(dict.fromkeys(groups))
        group_colors = ["#6FA8DC", "#E06666", "#93C47D", "#C27BA0",
                        "#FFD966"][: len(unique)]
        gmap = {g: c for g, c in zip(unique, group_colors)}
        strip_y = n_r + 0.4
        for si, g in enumerate(groups):
            ax.add_patch(mpatches.Rectangle(
                (si - 0.5, strip_y), 1.0, 0.5,
                facecolor=gmap[g], edgecolor="white", linewidth=0.3,
                clip_on=False, zorder=3,
            ))
        pos_by: dict[str, list[int]] = {}
        for si, g in enumerate(groups):
            pos_by.setdefault(g, []).append(si)
        for g, xs in pos_by.items():
            ax.text(float(np.mean(xs)), strip_y + 0.90, g,
                    ha="center", va="bottom", fontsize=6.4,
                    color="#333333", fontweight="bold",
                    clip_on=False)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("activity (z)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    top_i, top_j = np.unravel_index(int(np.argmax(A)), A.shape)
    bot_i, bot_j = np.unravel_index(int(np.argmin(A)), A.shape)
    ax.set_title(
        f"{contract.title}  ·  top: {regulons[top_i]} in {samples[top_j]} "
        f"({smart_fmt(float(A[top_i, top_j]))})  ·  "
        f"bottom: {regulons[bot_i]} ({smart_fmt(float(A[bot_i, bot_j]))})",
        fontsize=8.4, pad=4,
    )
    return ax
