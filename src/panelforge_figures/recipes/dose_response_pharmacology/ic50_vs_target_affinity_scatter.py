"""IC50 vs Ki concordance scatter across compounds."""

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


class IC50vsKiInput(RecipeContract):
    compound_names: list[str] = Field(..., min_length=3)
    ic50_nM: list[float] = Field(...)
    ki_nM: list[float] = Field(...)
    mechanism_class: list[str] | None = None
    title: str = "IC50 vs Ki concordance"


def _demo() -> IC50vsKiInput:
    rng = np.random.default_rng(211)
    n = 22
    names = [f"C{i:02d}" for i in range(n)]
    ki = 10 ** rng.uniform(0.5, 3.5, n)
    # Identity relationship plus noise; a few outliers.
    ic50 = ki * np.exp(rng.normal(0, 0.35, n))
    outliers = rng.choice(n, 3, replace=False)
    ic50[outliers] *= rng.uniform(5, 20, 3)
    mechanisms = rng.choice(
        ["signaling", "metabolic", "cytoskeletal", "other"],
        n, p=[0.35, 0.30, 0.20, 0.15],
    ).tolist()
    return IC50vsKiInput(
        compound_names=names,
        ic50_nM=ic50.tolist(),
        ki_nM=ki.tolist(),
        mechanism_class=mechanisms,
    )


_META = RecipeMetadata(
    name="ic50_vs_target_affinity_scatter",
    modality="dose_response_pharmacology",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across compounds, how well does functional IC50 correlate "
        "with binding Ki?"
    ),
    required_fields=("compound_names", "ic50_nM", "ki_nM"),
    optional_fields=("mechanism_class", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
)


@register_recipe(
    metadata=_META,
    contract=IC50vsKiInput,
    demo_contract=_demo,
)
def render(contract: IC50vsKiInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ic50 = np.asarray(contract.ic50_nM, float)
    ki = np.asarray(contract.ki_nM, float)
    mechs = (np.asarray(contract.mechanism_class)
             if contract.mechanism_class is not None
             else np.full(ic50.size, "other"))
    uniques = list(dict.fromkeys(mechs.tolist()))

    for m in uniques:
        mask = mechs == m
        color = (palette.pick(m) if m in palette.semantic
                 else palette[0])
        ax.scatter(ki[mask], ic50[mask], s=22, color=color, alpha=0.80,
                   edgecolor="white", linewidth=0.4, zorder=3,
                   label=f"{m} (n={int(mask.sum())})")

    # Identity line (Ki = IC50).
    lo = min(ki.min(), ic50.min()) * 0.5
    hi = max(ki.max(), ic50.max()) * 2
    xs = np.logspace(np.log10(lo), np.log10(hi), 100)
    ax.plot(xs, xs, color="#111111", lw=0.8, ls="--", zorder=4,
            label="Ki = IC50")

    # OLS in log-log space.
    lk = np.log10(np.clip(ki, 1e-6, None))
    li = np.log10(np.clip(ic50, 1e-6, None))
    slope, intercept = np.polyfit(lk, li, 1)
    ax.plot(xs, 10 ** (intercept + slope * np.log10(xs)),
            color="#D32F2F", lw=1.1, zorder=5,
            label=f"OLS: slope={smart_fmt(float(slope))}")

    r = float(np.corrcoef(lk, li)[0, 1]) if lk.std() > 0 else 0.0

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Ki (nM)")
    ax.set_ylabel("IC50 (nM)")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_title(
        f"{contract.title}  ·  r = {smart_fmt(r)}, n = {int(ic50.size)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
