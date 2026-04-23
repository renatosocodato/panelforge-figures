"""Batch-effect PCA — PC1 × PC2 scatter coloured by batch with
convex-hull / ellipse per batch.

Distinct from `qc_metric_radar` (per-sample multi-metric polar):
here the grammar is an embedding scatter focused on batch-clustering.
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


class BatchPCAInput(RecipeContract):
    pc1: list[float] = Field(..., min_length=5)
    pc2: list[float] = Field(..., min_length=5)
    batch_labels: list[str] = Field(..., min_length=5)
    explained_variance: tuple[float, float] | None = Field(
        None,
        description="(pc1_var, pc2_var) each in [0,1]",
    )
    title: str = "Batch-effect PCA"


def _demo() -> BatchPCAInput:
    rng = np.random.default_rng(839)
    # Three batches with clear batch-effect structure.
    pts = []
    batches = []
    for b, (cx, cy) in enumerate([(-1.5, 0.2), (0.5, 0.8), (0.8, -1.2)]):
        cov = np.array([[0.35, 0.08], [0.08, 0.30]])
        xy = rng.multivariate_normal([cx, cy], cov, 12)
        pts.append(xy)
        batches.extend([f"batch {b + 1}"] * 12)
    xy = np.vstack(pts)
    return BatchPCAInput(
        pc1=xy[:, 0].tolist(),
        pc2=xy[:, 1].tolist(),
        batch_labels=batches,
        explained_variance=(0.42, 0.26),
    )


_META = RecipeMetadata(
    name="batch_effect_diagnostic_pca",
    modality="meta_and_diagnostic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Do samples cluster by batch rather than by condition "
        "(batch-effect diagnostic)?"
    ),
    required_fields=("pc1", "pc2", "batch_labels"),
    optional_fields=("explained_variance", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("qc_metric_radar",),
)


@register_recipe(
    metadata=_META,
    contract=BatchPCAInput,
    demo_contract=_demo,
)
def render(contract: BatchPCAInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)

    pc1 = np.asarray(contract.pc1, float)
    pc2 = np.asarray(contract.pc2, float)
    batches = contract.batch_labels
    unique = list(dict.fromkeys(batches))
    palette_colors = ["#1565C0", "#E65100", "#2E7D32", "#6A1B9A", "#C2185B"]
    bmap = {b: palette_colors[i % len(palette_colors)]
            for i, b in enumerate(unique)}

    # Per-batch scatter + ellipse + centroid line.
    for b in unique:
        mask = np.array([bl == b for bl in batches])
        if mask.sum() == 0:
            continue
        c = bmap[b]
        ax.scatter(pc1[mask], pc2[mask], s=34, color=c,
                   edgecolor="white", linewidth=0.5,
                   alpha=0.85, zorder=4,
                   label=f"{b} (n = {int(mask.sum())})")
        # Covariance ellipse (2-sigma).
        xy = np.column_stack([pc1[mask], pc2[mask]])
        mu = xy.mean(axis=0)
        cov = np.cov(xy, rowvar=False)
        vals, vecs = np.linalg.eigh(cov)
        order = np.argsort(vals)[::-1]
        vals = vals[order]
        vecs = vecs[:, order]
        angle = float(np.degrees(np.arctan2(vecs[1, 0], vecs[0, 0])))
        width, height = 2 * 2 * np.sqrt(np.maximum(vals, 1e-9))
        ax.add_patch(mpatches.Ellipse(
            mu, width, height, angle=angle,
            facecolor=c, edgecolor=c, alpha=0.12,
            linewidth=0.9, zorder=2,
        ))
        # Centroid line from origin.
        ax.plot([0, mu[0]], [0, mu[1]],
                color=c, lw=0.6, ls=":", alpha=0.6, zorder=3)
        # Centroid marker.
        ax.scatter([mu[0]], [mu[1]], s=46, marker="+",
                   color=c, linewidth=1.2, zorder=5)

    # Compute "batch clustering score" = 1 - (within SSE) / (total SSE).
    xy = np.column_stack([pc1, pc2])
    mu_global = xy.mean(axis=0)
    total_sse = float(np.sum((xy - mu_global) ** 2))
    within_sse = 0.0
    for b in unique:
        mask = np.array([bl == b for bl in batches])
        if mask.sum() == 0:
            continue
        xy_b = xy[mask]
        mu_b = xy_b.mean(axis=0)
        within_sse += float(np.sum((xy_b - mu_b) ** 2))
    batch_score = 1.0 - within_sse / max(total_sse, 1e-9)

    if contract.explained_variance is not None:
        pc1_var = float(contract.explained_variance[0]) * 100
        pc2_var = float(contract.explained_variance[1]) * 100
        ax.set_xlabel(f"PC1 ({smart_fmt(pc1_var)} %)")
        ax.set_ylabel(f"PC2 ({smart_fmt(pc2_var)} %)")
    else:
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.0)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    verdict = ("strong batch-effect (likely confounding)"
               if batch_score > 0.5
               else "weak batch-effect")
    ax.text(0.02, 0.02,
            f"batch-clustering score = {smart_fmt(batch_score)}\n"
            f"-> {verdict}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4,
            color=("#C62828" if batch_score > 0.5 else "#2E7D32"),
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
