"""Module × sample activity-score heatmap — pathway-module summary grammar.

Summarises each sample's activity in each pathway module (via a
gene-set score like GSVA or singscore). Different from
`annotated_cluster_heatmap` (gene × sample) — this operates at the
module-level summary. Row annotations tag module type (metabolic,
immune, signalling, …); column annotations tag condition group.
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


class ModuleActivityInput(RecipeContract):
    module_names: list[str] = Field(..., min_length=3)
    sample_names: list[str] = Field(..., min_length=3)
    activity: list[list[float]] = Field(
        ..., description="n_modules × n_samples activity matrix (z-scored)"
    )
    module_groups: list[str] | None = None
    sample_groups: list[str] | None = None
    title: str = "Pathway-module activity"


def _demo() -> ModuleActivityInput:
    rng = np.random.default_rng(941)
    modules = [
        "OXPHOS", "glycolysis", "TCA", "fatty-acid β-ox",
        "autophagy", "ER stress", "NFkB", "IFN-γ response",
        "MAPK", "PI3K-AKT", "complement", "phagosome",
    ]
    samples = [f"s{i:02d}" for i in range(18)]
    n_m, n_s = len(modules), len(samples)
    M = rng.normal(0, 0.8, (n_m, n_s))
    # Three sample groups drive block patterns.
    grp_b = list(range(6, 12))
    grp_c = list(range(12, 18))
    for mi in range(6):          # metabolic modules suppressed in grp_b
        M[mi, grp_b] -= 1.2
    for mi in range(6, 12):      # signalling modules elevated in grp_c
        M[mi, grp_c] += 1.0
    module_groups = (
        ["metabolic"] * 4 + ["stress"] * 2 + ["signalling"] * 4 + ["immune"] * 2
    )
    sample_groups = (
        ["ctrl"] * 6 + ["LPS"] * 6 + ["LPS+rescue"] * 6
    )
    return ModuleActivityInput(
        module_names=modules,
        sample_names=samples,
        activity=M.tolist(),
        module_groups=module_groups,
        sample_groups=sample_groups,
    )


_META = RecipeMetadata(
    name="pathway_module_activity_heatmap",
    modality="omics_differential",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across samples, how does each pathway module's summarised "
        "activity score compare?"
    ),
    required_fields=("module_names", "sample_names", "activity"),
    optional_fields=("module_groups", "sample_groups", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=(
        "annotated_cluster_heatmap", "pathway_flux_bubble",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ModuleActivityInput,
    demo_contract=_demo,
)
def render(contract: ModuleActivityInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.activity, float)
    n_m, n_s = M.shape
    modules = contract.module_names
    samples = contract.sample_names
    v_hi = max(abs(M).max(), 1e-9)

    cmap = mpl.colormaps[AESTHETIC.ratio_cmap or "RdBu_r"]
    im = ax.imshow(M, cmap=cmap, vmin=-v_hi, vmax=v_hi,
                   aspect="auto", interpolation="nearest")

    ax.set_xticks(range(n_s))
    ax.set_xticklabels(samples, rotation=45, ha="right", fontsize=6.4)
    ax.set_yticks(range(n_m))
    ax.set_yticklabels(modules, fontsize=6.8)

    # Column annotation strip (sample groups) — drawn below the column
    # tick labels so it never overlaps the panel title.
    if contract.sample_groups is not None:
        groups_s = contract.sample_groups
        unique_s = list(dict.fromkeys(groups_s))
        group_colors_s = ["#6FA8DC", "#E06666", "#93C47D", "#C27BA0",
                          "#FFD966"][: len(unique_s)]
        cmap_s = {g: c for g, c in zip(unique_s, group_colors_s)}
        strip_y = n_m + 0.8
        for si, g in enumerate(groups_s):
            ax.add_patch(__import__("matplotlib").patches.Rectangle(
                (si - 0.5, strip_y), 1.0, 0.5,
                facecolor=cmap_s[g], edgecolor="white", linewidth=0.3,
                clip_on=False, zorder=3,
            ))
        unique_positions = {}
        for si, g in enumerate(groups_s):
            unique_positions.setdefault(g, []).append(si)
        for g, xs in unique_positions.items():
            ax.text(np.mean(xs), strip_y + 0.80, g,
                    ha="center", va="bottom",
                    fontsize=6.4, color="#333333", fontweight="bold",
                    clip_on=False)

    # Row annotation strip (module groups) — prefix each ytick label
    # with a small coloured square so the group is visually obvious
    # without a separate strip axes that would clash with the colorbar.
    if contract.module_groups is not None:
        groups_m = contract.module_groups
        unique_m = list(dict.fromkeys(groups_m))
        group_colors_m = ["#BDBDBD", "#8E7CC3", "#FFB266",
                          "#76A5AF", "#F6B26B"][: len(unique_m)]
        cmap_m = {g: c for g, c in zip(unique_m, group_colors_m)}
        # Thin coloured swatch just left of the heatmap, inside axes
        # so the colorbar on the right stays untouched.
        for mi, g in enumerate(groups_m):
            ax.add_patch(__import__("matplotlib").patches.Rectangle(
                (-0.48, mi - 0.48), 0.12, 0.96,
                facecolor=cmap_m[g], edgecolor="white", linewidth=0.3,
                zorder=5,
            ))
        # Module-group legend anchored below the sample-group strip so
        # it never shares horizontal space with the ctrl / LPS / rescue
        # annotation.
        from matplotlib.patches import Patch
        proxies = [Patch(facecolor=cmap_m[g], edgecolor="white", label=g)
                   for g in unique_m]
        leg = ax.legend(
            handles=proxies, fontsize=6.2,
            frameon=False, loc="upper center",
            bbox_to_anchor=(0.5, -0.26),
            ncols=len(unique_m), handlelength=1.0,
            handletextpad=0.4, columnspacing=1.4,
            title="module group", title_fontsize=6.2,
        )
        leg.get_title().set_color("#333333")

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("activity (z)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Module-rank summary (top / bottom by mean across all samples).
    row_means = M.mean(axis=1)
    top_i = int(np.argmax(row_means))
    bot_i = int(np.argmin(row_means))

    ax.set_title(
        f"{contract.title}  ·  top: {modules[top_i]} ({smart_fmt(float(row_means[top_i]))})   "
        f"bottom: {modules[bot_i]} ({smart_fmt(float(row_means[bot_i]))})",
        fontsize=8.6, pad=4,
    )
    return ax
