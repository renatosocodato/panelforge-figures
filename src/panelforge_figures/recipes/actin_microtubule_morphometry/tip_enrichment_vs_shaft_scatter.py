"""Tip vs shaft intensity per cell — apical-enrichment scatter with y=x reference."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class TipShaftInput(RecipeContract):
    tip_intensity: list[float] = Field(...)
    shaft_intensity: list[float] = Field(...)
    condition: list[str] | None = None
    title: str = "Tip vs shaft intensity"


def _demo() -> TipShaftInput:
    rng = np.random.default_rng(779)
    # Controls: tip ≈ shaft (unenriched). Mutants: tip > shaft (enriched).
    shaft_c = rng.lognormal(0.0, 0.35, 60)
    tip_c = shaft_c + rng.normal(0.05, 0.12, 60)
    shaft_m = rng.lognormal(0.0, 0.35, 60)
    tip_m = 1.6 * shaft_m + rng.normal(0.2, 0.20, 60)
    tip = np.concatenate([tip_c, tip_m])
    shaft = np.concatenate([shaft_c, shaft_m])
    cond = (["control"] * 60) + (["mutant"] * 60)
    return TipShaftInput(
        tip_intensity=tip.tolist(),
        shaft_intensity=shaft.tolist(),
        condition=cond,
    )


_META = RecipeMetadata(
    name="tip_enrichment_vs_shaft_scatter",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "For each cell, is a target marker enriched at tips vs. along the shaft?"
    ),
    required_fields=("tip_intensity", "shaft_intensity"),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("protrusion_length_velocity_joint",),
)


@register_recipe(
    metadata=_META,
    contract=TipShaftInput,
    demo_contract=_demo,
)
def render(contract: TipShaftInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    tip = np.asarray(contract.tip_intensity, float)
    shaft = np.asarray(contract.shaft_intensity, float)
    mask = np.isfinite(tip) & np.isfinite(shaft)
    tip, shaft = tip[mask], shaft[mask]

    lo = float(min(tip.min(), shaft.min()))
    hi = float(max(tip.max(), shaft.max()))
    span = hi - lo
    ax.set_xlim(lo - 0.04 * span, hi + 0.04 * span)
    ax.set_ylim(lo - 0.04 * span, hi + 0.04 * span)

    # y = x reference.
    ax.plot([lo, hi], [lo, hi], color="#888888", lw=0.8, ls="--",
            zorder=1, label="$y = x$ (no enrichment)")

    cond = (np.asarray(contract.condition)[mask]
            if contract.condition is not None else None)
    if cond is not None:
        uniques = list(dict.fromkeys(cond.tolist()))
        for i, name in enumerate(uniques):
            m = cond == name
            color = palette[i % len(palette.colors)]
            ax.scatter(shaft[m], tip[m], s=16, color=color, alpha=0.7,
                       edgecolor="white", linewidth=0.3, zorder=3,
                       label=f"{name} (n={int(m.sum())})")
    else:
        ax.scatter(shaft, tip, s=16, color=palette[0], alpha=0.7,
                   edgecolor="white", linewidth=0.3, zorder=3)

    # OLS fit across all points.
    slope, intercept = np.polyfit(shaft, tip, 1)
    xs = np.linspace(lo, hi, 120)
    ys = slope * xs + intercept
    ax.plot(xs, ys, color="#111111", lw=1.1, zorder=4,
            label=f"fit (slope = {smart_fmt(float(slope))})")

    # Pearson r, paired-sample t on (tip - shaft).
    try:
        r_val, _ = stats.pearsonr(shaft, tip)
        _, p_paired = stats.wilcoxon(tip, shaft)
    except Exception:
        r_val, p_paired = float("nan"), float("nan")
    enriched_frac = float(np.mean(tip > shaft))
    ax.text(
        0.04, 0.96,
        f"r = {smart_fmt(float(r_val))}\n"
        f"tip > shaft: {enriched_frac * 100:.0f}% of cells\n"
        f"Wilcoxon p = {smart_fmt(float(p_paired))}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    ax.set_xlabel("shaft intensity (a.u.)")
    ax.set_ylabel("tip intensity (a.u.)")
    ax.set_aspect("equal")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
