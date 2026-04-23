"""Per-sample QC-metric heatmap — sample × metric matrix with per-cell
z-score colouring and threshold-flag overlay.

Distinct from `qc_metric_radar` (polar per-sample aggregate) and
`missing_data_pattern_matrix` (co-missingness): this shows continuous
per-cell QC values with automatic flagging.
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


class DataQualityHeatmapInput(RecipeContract):
    sample_names: list[str] = Field(..., min_length=3)
    metric_names: list[str] = Field(..., min_length=3)
    values: list[list[float]] = Field(
        ..., description="n_samples × n_metrics QC values"
    )
    pass_threshold: list[float] = Field(
        ..., description="per-metric threshold for passing (len = n_metrics)"
    )
    higher_is_better: list[bool] = Field(
        ..., description="per-metric direction flag",
    )
    title: str = "Per-sample QC heatmap"


def _demo() -> DataQualityHeatmapInput:
    rng = np.random.default_rng(421)
    samples = [f"S{i + 1:02d}" for i in range(12)]
    metrics = ["coverage", "mapping %", "duplication %",
               "GC content", "PCR bias", "3'-bias"]
    hib = [True, True, False, True, False, False]
    thresh = [30.0, 0.90, 0.25, 0.48, 0.3, 0.35]
    # Generate values around each threshold, with a few failures.
    V = np.zeros((len(samples), len(metrics)))
    for j, (t, up) in enumerate(zip(thresh, hib)):
        if up:
            V[:, j] = rng.normal(t * 1.15, t * 0.20, len(samples))
        else:
            V[:, j] = rng.normal(t * 0.75, t * 0.20, len(samples))
    # Inject a few failures.
    V[2, 1] = 0.70    # mapping % low
    V[5, 0] = 18.0    # coverage low
    V[8, 2] = 0.45    # duplication high
    return DataQualityHeatmapInput(
        sample_names=samples,
        metric_names=metrics,
        values=V.tolist(),
        pass_threshold=thresh,
        higher_is_better=hib,
    )


_META = RecipeMetadata(
    name="data_quality_heatmap",
    modality="meta_and_diagnostic",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Per sample × QC metric, which cells fail a pre-specified "
        "threshold?"
    ),
    required_fields=(
        "sample_names", "metric_names", "values",
        "pass_threshold", "higher_is_better",
    ),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("qc_metric_radar",),
)


@register_recipe(
    metadata=_META,
    contract=DataQualityHeatmapInput,
    demo_contract=_demo,
)
def render(contract: DataQualityHeatmapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    samples = contract.sample_names
    metrics = contract.metric_names
    V = np.asarray(contract.values, float)
    thr = np.asarray(contract.pass_threshold, float)
    hib = list(contract.higher_is_better)
    n_s, n_m = V.shape

    # z-score each metric column to a standard scale.
    mu = V.mean(axis=0)
    sd = V.std(axis=0, ddof=1)
    Z = (V - mu) / np.where(sd > 1e-9, sd, 1.0)
    # Flip metrics where lower is better so large Z = "good".
    for j, up in enumerate(hib):
        if not up:
            Z[:, j] = -Z[:, j]

    v_abs = float(max(abs(Z).max(), 1e-6))
    im = ax.imshow(Z, cmap="RdYlGn",
                   vmin=-v_abs, vmax=v_abs,
                   aspect="auto", interpolation="nearest", zorder=2)

    ax.set_xticks(range(n_m))
    ax.set_xticklabels(metrics, rotation=35, ha="right", fontsize=6.8)
    ax.set_yticks(range(n_s))
    ax.set_yticklabels(samples, fontsize=6.8)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label("metric z-score (higher = better)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Threshold-flag overlay: annotate FAIL cells with ✕.
    fails = np.zeros_like(V, dtype=bool)
    for j, (t, up) in enumerate(zip(thr, hib)):
        col = V[:, j]
        fails[:, j] = (col < t) if up else (col > t)

    for i in range(n_s):
        for j in range(n_m):
            if fails[i, j]:
                ax.text(j, i, "x",
                        ha="center", va="center", fontsize=8.6,
                        color="#222222", fontweight="bold", zorder=4)

    # Global pass-rate callout.
    pass_rate = float(1.0 - fails.mean())
    ax.set_title(
        f"{contract.title}  ·  global pass-rate "
        f"{smart_fmt(pass_rate * 100)} %",
        fontsize=8.6, pad=4,
    )
    return ax
