"""PCA loadings heatmap — variables × principal-components signed
loadings on a diverging cmap, with explained-variance bars above
each column.

Heatmap family: >=1 imshow / pcolormesh.
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
from ._shared import LoadingsBundle


class PCALoadingsHeatmapInput(RecipeContract):
    bundle: LoadingsBundle = Field(...)
    title: str = "PCA loadings heatmap"


def _demo() -> PCALoadingsHeatmapInput:
    rng = np.random.default_rng(401)
    feature_names = [
        "actin_extent", "branch_count", "soma_area", "polarity_offset",
        "Lp_actin", "Lp_mt", "fractal_dim", "coherency",
        "z_span", "tip_count", "manders_M1", "pearson_r",
    ]
    component_labels = ["PC1", "PC2", "PC3", "PC4", "PC5"]
    n_f, n_c = len(feature_names), len(component_labels)
    # Build correlated loadings: territory metrics dominate PC1, polymer
    # metrics dominate PC3, network metrics PC2.
    L = rng.normal(0, 0.18, (n_f, n_c))
    L[:4, 0] += 0.55     # territory features → PC1
    L[4:7, 2] += 0.50    # polymer features → PC3
    L[7:10, 1] += 0.48   # network features → PC2
    L[10:, 1] += 0.30
    # Normalise rows so each feature has Σ loadings² = 1.
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    explained = [0.31, 0.22, 0.16, 0.09, 0.06]
    return PCALoadingsHeatmapInput(
        bundle=LoadingsBundle(
            feature_names=feature_names,
            component_labels=component_labels,
            loadings=L.tolist(),
            explained_variance=explained,
        ),
    )


_META = RecipeMetadata(
    name="pca_loadings_heatmap",
    modality="meta_and_diagnostic",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Which input features dominate each principal component, "
        "and how much variance does each PC explain?"
    ),
    required_fields=("bundle",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("batch_effect_diagnostic_pca",),
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
    contract=PCALoadingsHeatmapInput,
    demo_contract=_demo,
)
def render(contract: PCALoadingsHeatmapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    L = np.asarray(contract.bundle.loadings, float)
    feats = contract.bundle.feature_names
    comps = contract.bundle.component_labels
    n_f, n_c = L.shape

    # Diverging heatmap centred at zero.
    v_abs = float(max(abs(L).max(), 1e-6))
    mesh = ax.pcolormesh(
        np.arange(n_c + 1) - 0.5,
        np.arange(n_f + 1) - 0.5,
        L, cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
        shading="auto", zorder=2,
    )
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("loading (signed)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Annotate large-magnitude loadings.
    threshold = float(0.55 * v_abs)
    for i in range(n_f):
        for j in range(n_c):
            if abs(L[i, j]) >= threshold:
                txt_color = "white" if abs(L[i, j]) > (0.65 * v_abs) \
                    else "#222222"
                ax.text(j, i, f"{smart_fmt(L[i, j])}",
                        ha="center", va="center",
                        fontsize=6.4, color=txt_color,
                        fontweight="bold", zorder=4)

    ax.set_xticks(range(n_c))
    ax.set_xticklabels(comps, fontsize=7.0)
    ax.set_yticks(range(n_f))
    ax.set_yticklabels(feats, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlim(-0.5, n_c - 0.5)
    ax.set_ylim(n_f - 0.5, -0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Explained-variance bar above each column (axes-fraction inset).
    if contract.bundle.explained_variance is not None:
        ev = list(contract.bundle.explained_variance)[:n_c]
        # Inset bar strip at the top of the heatmap.
        bar_ax = ax.inset_axes([0.0, 1.04, 1.0, 0.10])
        AESTHETIC.apply_to_ax(bar_ax)
        x_pos = np.arange(n_c)
        bar_ax.bar(x_pos, ev, width=0.7, color="#37474F",
                   edgecolor="white", linewidth=0.5, zorder=3)
        bar_ax.set_xticks([])
        bar_ax.set_xlim(-0.5, n_c - 0.5)
        bar_ax.set_ylim(0, max(ev) * 1.20)
        bar_ax.set_ylabel("var. expl.", fontsize=6.0)
        bar_ax.tick_params(axis="y", labelsize=5.6)
        for side in ("top", "right"):
            bar_ax.spines[side].set_visible(False)
        for j, e in enumerate(ev):
            bar_ax.text(j, e * 1.04, f"{smart_fmt(e * 100)}%",
                        ha="center", va="bottom", fontsize=5.6,
                        color="#222222", zorder=4)
        cum_ev = sum(ev)
        title_bits = f"  ·  cumulative {smart_fmt(cum_ev * 100)} %"
    else:
        title_bits = ""

    ax.set_title(
        f"{contract.title}  ·  n_features = {n_f}{title_bits}",
        fontsize=8.2, pad=20,
    )
    return ax
