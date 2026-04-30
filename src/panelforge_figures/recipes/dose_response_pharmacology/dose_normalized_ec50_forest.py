"""Dose-normalised EC50 forest — compounds as x-fold of the most-potent lead."""

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


class NormalizedEC50Input(RecipeContract):
    compound_names: list[str] = Field(..., min_length=3)
    ec50_nM: list[float] = Field(...)
    ec50_ci_nM: list[tuple[float, float]] | None = None
    mechanism_class: list[str] | None = None
    title: str = "Dose-normalised EC50"


def _demo() -> NormalizedEC50Input:
    rng = np.random.default_rng(311)
    names = [f"C{i+1:02d}" for i in range(14)]
    ec50 = 10 ** rng.uniform(0.4, 3.2, len(names))
    ci = [(v * 0.78, v * 1.28) for v in ec50]
    mechs = rng.choice(
        ["signaling", "metabolic", "cytoskeletal", "other"],
        len(names), p=[0.45, 0.30, 0.15, 0.10],
    ).tolist()
    return NormalizedEC50Input(
        compound_names=names,
        ec50_nM=ec50.tolist(),
        ec50_ci_nM=ci,
        mechanism_class=mechs,
    )


_META = RecipeMetadata(
    name="dose_normalized_ec50_forest",
    modality="dose_response_pharmacology",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across a compound series, how do EC50s compare when "
        "normalised to the most potent lead (x-fold)?"
    ),
    required_fields=("compound_names", "ec50_nM"),
    optional_fields=("ec50_ci_nM", "mechanism_class", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
)


@register_recipe(
    metadata=_META,
    contract=NormalizedEC50Input,
    demo_contract=_demo,
)
def render(contract: NormalizedEC50Input, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    names = list(contract.compound_names)
    ec50 = np.asarray(contract.ec50_nM, float)
    lead = float(ec50.min())
    fold = ec50 / lead
    ci = contract.ec50_ci_nM
    mechs = (np.asarray(contract.mechanism_class)
             if contract.mechanism_class is not None
             else np.full(len(names), "other"))

    order = np.argsort(fold)
    names = [names[i] for i in order]
    fold = fold[order]
    mechs = mechs[order]
    ci_sorted = [ci[i] for i in order] if ci is not None else None

    y = np.arange(len(names))[::-1]
    for yi, f, m, nm in zip(y, fold, mechs, names):
        color = (palette.pick(m) if m in palette.semantic
                 else palette[0])
        ax.scatter([f], [yi], s=38, color=color, edgecolor="white",
                   linewidth=0.6, zorder=4)
        if ci_sorted is not None:
            lo, hi = ci_sorted[names.index(nm)]
            ax.plot([lo / lead, hi / lead], [yi, yi],
                    color=color, lw=1.1, zorder=3)

    # Reference at 1× (lead).
    ax.axvline(1.0, color="#111111", lw=0.8, ls="--", zorder=2,
               label="lead (1×)")
    ax.axvline(10.0, color="#888888", lw=0.6, ls=":", zorder=1,
               label="10× lead")

    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.0)
    ax.set_xlabel(r"EC50 / EC50$_{lead}$  (×-fold)")
    ax.set_title(
        f"{contract.title}  ·  lead EC50 = {smart_fmt(lead)} nM "
        f"({names[-1]})",
        fontsize=8.6, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.grid(axis="x", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Right-of-marker numeric label.
    xmax = float(fold.max()) * 2.5
    for yi, f in zip(y, fold):
        ax.annotate(f"×{smart_fmt(float(f))}",
                    xy=(f, yi), xytext=(6, 0),
                    textcoords="offset points",
                    ha="left", va="center", fontsize=6.4, color="#222222")
    ax.set_xlim(max(fold.min() * 0.6, 0.5), xmax)
    return ax
