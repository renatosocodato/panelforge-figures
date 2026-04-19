"""Exemplar extremes — min / median / max cells per condition for a named metric."""

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


class ExemplarExtreme(RecipeContract):
    condition: str
    quantile_label: str = Field(..., description="'min' | 'median' | 'max'")
    thumbnail: list[list[float]] = Field(...)
    metric_value: float


class ExemplarExtremesInput(RecipeContract):
    exemplars: list[ExemplarExtreme] = Field(..., min_length=3)
    target_metric_label: str = Field(..., description="e.g. 'total process length (µm)'")
    pixel_size_um: float = 0.3
    scale_bar_um: float = 5.0
    title: str = "Exemplar extremes"


def _demo() -> ExemplarExtremesInput:
    rng = np.random.default_rng(745)
    H, W = 40, 40
    yy, xx = np.mgrid[:H, :W]
    exemplars: list[ExemplarExtreme] = []
    for cond in ("control", "mutant", "rescue"):
        for q_label, metric_mu in (("min", 40.0), ("median", 85.0), ("max", 160.0)):
            cx, cy = W // 2 + rng.integers(-2, 3), H // 2 + rng.integers(-2, 3)
            img = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / 55.0)
            n_proc = {"min": 2, "median": 3, "max": 5}[q_label]
            for _ in range(n_proc):
                theta = rng.uniform(0, 2 * np.pi)
                length = {"min": 8, "median": 14, "max": 18}[q_label]
                for t in np.linspace(0, length, 40):
                    px = cx + t * np.cos(theta)
                    py = cy + t * np.sin(theta)
                    if 0 <= px < W and 0 <= py < H:
                        img += 0.9 * np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / 2.6)
            img = (img / max(img.max(), 1e-9)
                   + rng.normal(0, 0.015, (H, W)))
            metric_value = metric_mu + rng.uniform(-3, 3)
            exemplars.append(ExemplarExtreme(
                condition=cond,
                quantile_label=q_label,
                thumbnail=img.tolist(),
                metric_value=metric_value,
            ))
    return ExemplarExtremesInput(
        exemplars=exemplars,
        target_metric_label="total process length (µm)",
    )


_META = RecipeMetadata(
    name="exemplar_extremes_panel",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "For each condition, what do the min / median / max cells look like "
        "with respect to a target metric?"
    ),
    required_fields=("exemplars", "target_metric_label"),
    optional_fields=("pixel_size_um", "scale_bar_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("per_cell_thumbnail_grid_with_metrics",),
)


@register_recipe(
    metadata=_META,
    contract=ExemplarExtremesInput,
    demo_contract=_demo,
)
def render(contract: ExemplarExtremesInput, ax=None, **_):
    import matplotlib.pyplot as plt

    # Collect ordered (condition × quantile) grid.
    conditions = list(dict.fromkeys([e.condition for e in contract.exemplars]))
    quantiles = ["min", "median", "max"]
    nrows = len(conditions)
    ncols = len(quantiles)

    if ax is None:
        fig = plt.figure(figsize=(5.0, 4.8))
        gs = fig.add_gridspec(nrows, ncols, wspace=0.10, hspace=0.28)
        axes = [[fig.add_subplot(gs[r, c]) for c in range(ncols)]
                for r in range(nrows)]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(nrows, ncols, wspace=0.10, hspace=0.28)
        axes = [[fig.add_subplot(sub[r, c]) for c in range(ncols)]
                for r in range(nrows)]
    AESTHETIC.apply_to_fig(fig)
    for row in axes:
        for ai in row:
            AESTHETIC.apply_to_ax(ai)

    # Build lookup by (cond, quantile) → exemplar.
    by_key: dict[tuple[str, str], ExemplarExtreme] = {}
    for e in contract.exemplars:
        by_key[(e.condition, e.quantile_label)] = e

    for r, cond in enumerate(conditions):
        for c, q in enumerate(quantiles):
            ai = axes[r][c]
            ai.set_xticks([])
            ai.set_yticks([])
            for side in ("top", "right", "left", "bottom"):
                ai.spines[side].set_visible(False)
            ex = by_key.get((cond, q))
            if ex is None:
                ai.axis("off")
                continue
            img = np.asarray(ex.thumbnail, float)
            ai.imshow(img, cmap="gray_r", aspect="equal",
                      interpolation="bilinear")
            # Column header (top row only).
            if r == 0:
                ai.set_title(q, fontsize=7.4, pad=3, color="#111111")
            # Row label (left column only).
            if c == 0:
                ai.text(-0.08, 0.5, cond, transform=ai.transAxes,
                        ha="right", va="center", fontsize=7.4,
                        color="#111111", rotation=0)
            # Metric callout under the thumbnail.
            ai.text(0.5, -0.08,
                    f"{smart_fmt(ex.metric_value)}",
                    transform=ai.transAxes, ha="center", va="top",
                    fontsize=6.2, color="#222222")

            # Scale bar on the leftmost panel of each row.
            if c == 0:
                H, W = img.shape
                bar_len_px = contract.scale_bar_um / max(contract.pixel_size_um, 1e-6)
                ai.plot([W * 0.08, W * 0.08 + bar_len_px],
                        [H * 0.92, H * 0.92],
                        color="white", lw=2.2, solid_capstyle="butt", zorder=5)

    fig.suptitle(
        f"{contract.title}  ·  {contract.target_metric_label}",
        fontsize=9.0, y=0.995,
    )
    return axes[0][0]
