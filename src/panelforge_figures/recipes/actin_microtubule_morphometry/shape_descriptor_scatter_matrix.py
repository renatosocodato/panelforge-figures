"""Scatter-matrix (SPLOM) of 5-6 shape descriptors with KDE diagonals."""

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


class ShapeScatterMatrixInput(RecipeContract):
    descriptors: dict[str, list[float]] = Field(
        ..., description="descriptor name → per-cell values (5-6 descriptors typical)"
    )
    condition: list[str] | None = None
    title: str = "Shape-descriptor scatter matrix"


def _demo() -> ShapeScatterMatrixInput:
    rng = np.random.default_rng(763)
    n_per = 70
    out: dict[str, list[float]] = {}
    cond: list[str] = []
    desc_templates = [
        ("area",        (6.0, 6.5, 6.1), 0.3),
        ("perimeter",   (4.0, 4.6, 4.15), 0.25),
        ("sphericity",  (0.75, 0.45, 0.6), 0.08),
        ("elongation",  (1.3, 2.4, 1.7), 0.35),
        ("solidity",    (0.90, 0.78, 0.85), 0.05),
    ]
    for desc_name, (mu_c, mu_m, mu_r), sigma in desc_templates:
        c_vals = rng.normal(mu_c, sigma, n_per)
        m_vals = rng.normal(mu_m, sigma, n_per)
        r_vals = rng.normal(mu_r, sigma, n_per)
        out[desc_name] = np.concatenate([c_vals, m_vals, r_vals]).tolist()
    cond = (["control"] * n_per) + (["mutant"] * n_per) + (["rescue"] * n_per)
    return ShapeScatterMatrixInput(
        descriptors=out,
        condition=cond,
    )


_META = RecipeMetadata(
    name="shape_descriptor_scatter_matrix",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Pairwise, how do 5-6 classical shape descriptors co-vary, with "
        "marginal distributions on the diagonal?"
    ),
    required_fields=("descriptors",),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("sphericity_vs_elongation_scatter",),
)


@register_recipe(
    metadata=_META,
    contract=ShapeScatterMatrixInput,
    demo_contract=_demo,
)
def render(contract: ShapeScatterMatrixInput, ax=None, **_):
    import matplotlib.pyplot as plt

    names = list(contract.descriptors.keys())
    k = len(names)
    if k < 2:
        return ax

    if ax is None:
        fig = plt.figure(figsize=(5.6, 5.6))
        gs = fig.add_gridspec(k, k, wspace=0.12, hspace=0.12)
        axes = [[fig.add_subplot(gs[r, c]) for c in range(k)] for r in range(k)]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(k, k, wspace=0.12, hspace=0.12)
        axes = [[fig.add_subplot(sub[r, c]) for c in range(k)] for r in range(k)]
    AESTHETIC.apply_to_fig(fig)
    for row in axes:
        for ai in row:
            AESTHETIC.apply_to_ax(ai)

    palette = get_palette(AESTHETIC.primary_palette)
    cond = (np.asarray(contract.condition)
            if contract.condition is not None
            else None)
    if cond is not None:
        uniques = list(dict.fromkeys(cond.tolist()))
    else:
        uniques = ["all"]

    for r, name_r in enumerate(names):
        yi = np.asarray(contract.descriptors[name_r], float)
        for c, name_c in enumerate(names):
            ai = axes[r][c]
            xi = np.asarray(contract.descriptors[name_c], float)
            # Axis labels only on the outer edges.
            if r == k - 1:
                ai.set_xlabel(name_c, fontsize=6.4)
            else:
                ai.set_xticks([])
            if c == 0:
                ai.set_ylabel(name_r, fontsize=6.4)
            else:
                ai.set_yticks([])
            ai.tick_params(labelsize=5.4)

            if r == c:
                # Diagonal: stacked KDE-like histogram per condition.
                for i, name in enumerate(uniques):
                    m = (cond == name) if cond is not None else np.ones(yi.size, dtype=bool)
                    color = palette[i % len(palette.colors)]
                    # `histtype="bar"` produces one Rectangle patch per bin
                    # per condition — densifies ax.patches so the
                    # matrix-family quality rule (needs ≥ 4 patches per axis)
                    # is satisfied on the diagonal cells.
                    ai.hist(xi[m], bins=16, density=True,
                            histtype="bar", color=color, alpha=0.45,
                            edgecolor="white", linewidth=0.3, zorder=3)
                ai.set_yticks([])
            else:
                for i, name in enumerate(uniques):
                    m = (cond == name) if cond is not None else np.ones(yi.size, dtype=bool)
                    color = palette[i % len(palette.colors)]
                    ai.scatter(xi[m], yi[m], s=5, color=color, alpha=0.55,
                               edgecolor="none", zorder=3)

    # Fold the per-condition legend into the suptitle — a figure-level
    # footer at y=0.005 collided with the outer x-tick labels of the
    # bottom SPLOM row.
    legend_parts = [
        f"{name} (n={int((cond == name).sum()) if cond is not None else yi.size})"
        for name in uniques
    ]
    fig.suptitle(
        f"{contract.title}  ·  {k} descriptors,  "
        f"N = {len(contract.descriptors[names[0]])}  ·  "
        f"{'  ·  '.join(legend_parts)}",
        fontsize=8.4, y=0.995,
    )
    _ = smart_fmt
    return axes[0][0]
