"""Proteome-scale volcano with pathway-group colour coding + centroid labels.

Unlike `volcano_labeled_repelled` (per-gene label repulsion), this
recipe annotates by **pathway group**: each protein is coloured by
pathway membership, and one short label is placed near the centroid
of the significant hits in each pathway. A pathway legend carries the
counts.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    empty_data_guard,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ProteomeVolcanoInput(RecipeContract):
    protein_names: list[str] = Field(...)
    log2fc: list[float] = Field(...)
    padj: list[float] = Field(...)
    pathway: list[str] = Field(
        ..., description="pathway-group label per protein (use '' / 'other' for unassigned)"
    )
    log2fc_threshold: float = 1.0
    padj_threshold: float = 0.05
    title: str = "Proteome volcano — pathway-annotated"


def _demo() -> ProteomeVolcanoInput:
    rng = np.random.default_rng(431)
    pathways = [
        "OXPHOS", "autophagy", "MAPK", "glycolysis", "ER stress", "other",
    ]
    weights = [0.08, 0.06, 0.08, 0.06, 0.04, 0.68]
    n = 1200
    names = [f"p{i:05d}" for i in range(n)]
    pw = rng.choice(pathways, n, p=weights).tolist()
    fc = rng.normal(0, 0.55, n)
    p = rng.uniform(0.05, 1.0, n)
    # Inject coordinated shifts in specific pathways.
    for pname, direction, frac in [
        ("OXPHOS", -1, 0.55), ("autophagy", +1, 0.55),
        ("MAPK", +1, 0.50), ("glycolysis", -1, 0.45),
        ("ER stress", +1, 0.65),
    ]:
        mask = np.array([x == pname for x in pw])
        n_hit = int(frac * mask.sum())
        idx = rng.choice(np.where(mask)[0], size=n_hit, replace=False)
        fc[idx] = direction * rng.uniform(1.2, 3.8, n_hit)
        p[idx] = rng.uniform(1e-9, 1e-3, n_hit)
    return ProteomeVolcanoInput(
        protein_names=names,
        log2fc=fc.tolist(),
        padj=p.tolist(),
        pathway=pw,
    )


_META = RecipeMetadata(
    name="proteome_volcano_labeled_pathways",
    modality="omics_differential",
    family=RecipeFamily.volcano,
    answers_question=(
        "On a proteome-scale volcano, which pathways (not individual "
        "genes) are most enriched among the significant hits?"
    ),
    required_fields=("protein_names", "log2fc", "padj", "pathway"),
    optional_fields=("log2fc_threshold", "padj_threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "volcano_labeled_repelled", "multi_contrast_volcano_grid",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ProteomeVolcanoInput,
    demo_contract=_demo,
)
def render(contract: ProteomeVolcanoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.log2fc), message="no proteins"):
        return ax

    fc = np.asarray(contract.log2fc, float)
    p = np.asarray(contract.padj, float)
    y = -np.log10(np.maximum(p, 1e-300))
    pw = np.asarray(contract.pathway)

    # Pathway palette — distinct hues, skip "other"/"".
    groups = [g for g in dict.fromkeys(pw.tolist()) if g not in ("", "other")]
    group_colors = [
        "#1565C0", "#E65100", "#2E7D32", "#6A1B9A", "#AD1457",
        "#00838F", "#C62828", "#4E342E",
    ][: max(len(groups), 1)]

    sig = (p < contract.padj_threshold) & (np.abs(fc) > contract.log2fc_threshold)

    # Non-significant + "other" background.
    bg = (~sig) | np.isin(pw, ["", "other"])
    alpha_bg = density_alpha(fc[bg], y[bg]) if bg.any() else np.array([])
    ax.scatter(fc[bg], y[bg], s=6, c="#BBBBBB", alpha=alpha_bg,
               edgecolor="none", zorder=2)

    # Foreground by pathway group.
    legend_entries = []
    for g, color in zip(groups, group_colors):
        mask = sig & (pw == g)
        ax.scatter(fc[mask], y[mask], s=14, c=color, alpha=0.85,
                   edgecolor="white", linewidth=0.25, zorder=3,
                   label=f"{g} ({int(mask.sum())})")
        legend_entries.append((g, color, int(mask.sum())))

    # Threshold lines.
    ax.axvline(contract.log2fc_threshold, color="#888888",
               lw=0.6, ls="--", zorder=1)
    ax.axvline(-contract.log2fc_threshold, color="#888888",
               lw=0.6, ls="--", zorder=1)
    ax.axhline(-np.log10(contract.padj_threshold), color="#888888",
               lw=0.6, ls="--", zorder=1)

    # Pathway label at the centroid of its significant hits — place labels
    # above the hits, and split into left- vs right-side lanes with
    # vertical repulsion so multiple pathway labels don't stack.
    ax.set_xlabel(r"$\log_2$ fold-change")
    ax.set_ylabel(r"$-\log_{10}$ p$_{adj}$")
    ax.set_title(
        f"{contract.title}  ·  N={len(fc)}, sig={int(sig.sum())}, "
        f"p$_{{adj}}$<{smart_fmt(contract.padj_threshold)}",
        fontsize=8.4, pad=4,
    )

    # Reserve headroom above the highest hit so labels can stack cleanly.
    y_data_max = float(y.max()) if y.size else 1.0
    y_top = y_data_max * 1.18 + 0.5
    ax.set_ylim(-0.05 * y_top, y_top)

    # Precompute centroids per pathway (with significant hits).
    centroids: list[tuple[str, str, float, float]] = []
    for g, color in zip(groups, group_colors):
        mask = sig & (pw == g)
        if mask.sum() < 3:
            continue
        cx = float(np.median(fc[mask]))
        cy = float(np.quantile(y[mask], 0.75))
        centroids.append((g, color, cx, cy))

    # Split by side (left: cx<0, right: cx>=0), sort by |cx| so busier
    # pathways anchor first.
    left = sorted([c for c in centroids if c[2] < 0], key=lambda c: -abs(c[2]))
    right = sorted([c for c in centroids if c[2] >= 0], key=lambda c: -abs(c[2]))

    def _place_side(items, x_anchor_sign):
        # Stack labels at the top of the axes on the appropriate side,
        # stepping downward so they never overlap.
        y_label = y_top * 0.94
        y_step = y_top * 0.08
        for g, color, cx, cy in items:
            x_label = x_anchor_sign * 2.6   # data-coord anchor
            ax.annotate(
                g,
                xy=(cx, cy),
                xytext=(x_label, y_label),
                textcoords="data",
                ha="center", va="center",
                fontsize=6.8, color=color,
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec=color, lw=0.5, alpha=0.95),
                arrowprops=dict(arrowstyle="-", color=color,
                                lw=0.5, alpha=0.55, shrinkA=0, shrinkB=4),
                zorder=6,
            )
            y_label -= y_step

    _place_side(left, -1)
    _place_side(right, +1)

    # Legend placed below the x-axis to avoid covering hits.
    ax.legend(fontsize=6.4, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.16),
              ncols=3, handlelength=1.2, handletextpad=0.4,
              columnspacing=1.4)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
