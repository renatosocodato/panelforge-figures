"""Outlier-detection scatter — 2-D feature plane with Mahalanobis
boundary contour and flagged-marker annotations.
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


class OutlierScatterInput(RecipeContract):
    x_values: list[float] = Field(..., min_length=10)
    y_values: list[float] = Field(..., min_length=10)
    sample_labels: list[str] | None = None
    mahalanobis_threshold: float = Field(
        2.5, description="χ² cutoff for flagging outliers"
    )
    x_label: str = "feature 1"
    y_label: str = "feature 2"
    title: str = "Outlier detection"


def _demo() -> OutlierScatterInput:
    rng = np.random.default_rng(523)
    n_inliers = 120
    # Correlated Gaussian inliers.
    cov = np.array([[1.0, 0.5], [0.5, 1.0]])
    xy = rng.multivariate_normal([0, 0], cov, n_inliers)
    # A few outliers.
    outliers = np.array([
        [3.2, -1.8],
        [-2.5, 3.1],
        [4.0, 4.0],
        [-3.6, -3.2],
    ])
    xy = np.vstack([xy, outliers])
    names = [f"S{i + 1:03d}" for i in range(len(xy))]
    return OutlierScatterInput(
        x_values=xy[:, 0].tolist(),
        y_values=xy[:, 1].tolist(),
        sample_labels=names,
    )


_META = RecipeMetadata(
    name="outlier_detection_scatter",
    modality="meta_and_diagnostic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "In a 2-D feature plane, which points are outliers "
        "(Mahalanobis distance beyond the chosen threshold)?"
    ),
    required_fields=("x_values", "y_values"),
    optional_fields=(
        "sample_labels", "mahalanobis_threshold",
        "x_label", "y_label", "title",
    ),
    file_format_hints=("csv",),
    alternatives_in_modality=("qc_metric_radar",),
)


@register_recipe(
    metadata=_META,
    contract=OutlierScatterInput,
    demo_contract=_demo,
)
def render(contract: OutlierScatterInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)

    x = np.asarray(contract.x_values, float)
    y = np.asarray(contract.y_values, float)
    xy = np.column_stack([x, y])
    thr = float(contract.mahalanobis_threshold)

    # Mahalanobis distance.
    mu = xy.mean(axis=0)
    cov = np.cov(xy, rowvar=False)
    cov_inv = np.linalg.pinv(cov)
    diff = xy - mu
    mdist = np.sqrt(np.sum((diff @ cov_inv) * diff, axis=1))
    flagged = mdist > thr

    # Contour at threshold.
    x_grid = np.linspace(x.min() - 1, x.max() + 1, 120)
    y_grid = np.linspace(y.min() - 1, y.max() + 1, 120)
    X, Y = np.meshgrid(x_grid, y_grid)
    grid_xy = np.column_stack([X.ravel(), Y.ravel()])
    gd = grid_xy - mu
    md_grid = np.sqrt(np.sum((gd @ cov_inv) * gd, axis=1)).reshape(X.shape)
    ax.contour(X, Y, md_grid, levels=[thr],
               colors=["#C62828"], linewidths=1.0, zorder=3)
    ax.contourf(X, Y, md_grid, levels=[0, thr],
                colors=["#E8F5E9"], alpha=0.25, zorder=1)

    # Inliers.
    ax.scatter(x[~flagged], y[~flagged], s=22,
               color="#1565C0", alpha=0.65,
               edgecolor="white", linewidth=0.4, zorder=4,
               label=f"inliers (n = {int((~flagged).sum())})")
    # Outliers — flagged.
    ax.scatter(x[flagged], y[flagged], s=56,
               color="#C62828", marker="X",
               edgecolor="white", linewidth=0.8, zorder=5,
               label=f"outliers (n = {int(flagged.sum())})")

    # Annotate outliers with sample label.
    if contract.sample_labels is not None:
        labels = contract.sample_labels
        for i, (is_out, xi, yi) in enumerate(zip(flagged, x, y)):
            if is_out:
                ax.text(xi + 0.10, yi + 0.10, labels[i],
                        ha="left", va="bottom", fontsize=6.4,
                        color="#C62828", zorder=6)

    # Centroid marker + dashed line to max-distance outlier for
    # scatter_collapse line requirement.
    ax.scatter([mu[0]], [mu[1]], s=46, marker="+",
               color="#222222", zorder=5, label="centroid")
    if flagged.any():
        worst = int(np.argmax(mdist))
        ax.plot([mu[0], x[worst]], [mu[1], y[worst]],
                color="#888888", lw=0.6, ls=":", zorder=3)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.02, 0.97,
            f"Mahalanobis threshold = {smart_fmt(thr)}\n"
            f"flagged {int(flagged.sum())} / {len(x)} "
            f"({smart_fmt(float(flagged.mean()) * 100)} %)",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
