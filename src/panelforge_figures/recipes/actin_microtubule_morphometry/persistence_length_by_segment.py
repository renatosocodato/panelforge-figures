"""Persistence length per segment — forest with bootstrap CI by condition."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SegmentPersistenceInput(RecipeContract):
    segment_lp_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → per-segment persistence-length values (µm)"
    )
    n_bootstrap: int = 500
    title: str = "Per-segment persistence length"


def _demo() -> SegmentPersistenceInput:
    rng = np.random.default_rng(811)
    return SegmentPersistenceInput(
        segment_lp_by_condition={
            "control":  rng.gamma(6.0, 0.6, 140).tolist(),   # mean ≈ 3.6
            "mutant":   rng.gamma(3.5, 0.5, 130).tolist(),   # mean ≈ 1.75
            "rescue":   rng.gamma(5.2, 0.55, 125).tolist(),  # mean ≈ 2.9
        },
    )


_META = RecipeMetadata(
    name="persistence_length_by_segment",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "What is the distribution of per-segment persistence length across "
        "conditions, with bootstrap 95% CI on the mean?"
    ),
    required_fields=("segment_lp_by_condition",),
    optional_fields=("n_bootstrap", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("persistence_length_fit",),
)


@register_recipe(
    metadata=_META,
    contract=SegmentPersistenceInput,
    demo_contract=_demo,
)
def render(contract: SegmentPersistenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.segment_lp_by_condition.keys())
    y = np.arange(len(conditions))[::-1]
    rng = np.random.default_rng(813)

    # Backdrop: jittered per-segment points at each row.
    for yi, cond in zip(y, conditions):
        vals = np.asarray(contract.segment_lp_by_condition[cond], float)
        vals = vals[np.isfinite(vals) & (vals > 0)]
        color = palette[list(conditions).index(cond) % len(palette.colors)]
        jitter = rng.uniform(-0.24, 0.24, vals.size)
        ax.scatter(vals, yi + jitter, s=6, color=color, alpha=0.35,
                   edgecolor="none", zorder=2)

        # Bootstrap mean + 95% CI.
        if vals.size >= 4:
            n_boot = int(contract.n_bootstrap)
            boot_means = np.empty(n_boot, dtype=float)
            for b in range(n_boot):
                idx = rng.integers(0, vals.size, vals.size)
                boot_means[b] = float(vals[idx].mean())
            mean_hat = float(vals.mean())
            ci_lo, ci_hi = np.quantile(boot_means, [0.025, 0.975])
            ax.plot([ci_lo, ci_hi], [yi, yi], color="#111111",
                    lw=1.2, zorder=3)
            for xe in (ci_lo, ci_hi):
                ax.plot([xe, xe], [yi - 0.14, yi + 0.14],
                        color="#111111", lw=1.2, zorder=3)
            ax.scatter([mean_hat], [yi], s=40, color=color,
                       edgecolor="white", linewidth=0.9, zorder=4)
            # Right-of-CI numeric label.
            ax.text(ci_hi * 1.04, yi,
                    f"{smart_fmt(mean_hat)}  ({smart_fmt(ci_lo)}-{smart_fmt(ci_hi)}) µm",
                    ha="left", va="center", fontsize=6.4, color="#222222")

    # Reference line at the grand mean.
    all_vals = np.concatenate([
        np.asarray(contract.segment_lp_by_condition[c], float)
        for c in conditions
    ])
    grand = float(all_vals.mean())
    ax.axvline(grand, color="#888888", lw=0.7, ls="--", zorder=1,
               label=f"grand mean = {smart_fmt(grand)} µm")

    xmax = float(all_vals.max())
    ax.set_xlim(0, xmax * 1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(conditions, fontsize=7.0)
    ax.set_xlabel(r"persistence length $L_p$ ($\mu$m)")
    ax.set_title(
        f"{contract.title}  ·  bootstrap 95% CI,  N_boot = {contract.n_bootstrap}",
        fontsize=8.4, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
