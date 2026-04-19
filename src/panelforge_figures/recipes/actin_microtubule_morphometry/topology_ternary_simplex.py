"""Topology ternary simplex — (linear, branched, looped) fractions per cell."""

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


class TopologyTernaryInput(RecipeContract):
    linear_fraction: list[float] = Field(...)
    branched_fraction: list[float] = Field(...)
    looped_fraction: list[float] = Field(...)
    condition: list[str] = Field(..., description="per-cell condition label")
    title: str = "Topology ternary simplex"


def _demo() -> TopologyTernaryInput:
    rng = np.random.default_rng(727)
    conds = []
    lin, bra, loo = [], [], []
    for name, (a, b, c) in [
        ("control", (4.0, 2.0, 1.0)),   # linear-dominant
        ("mutant",  (1.5, 3.5, 2.0)),   # branched-looped
        ("rescue",  (3.0, 2.5, 1.2)),   # near-control
    ]:
        draws = rng.dirichlet([a, b, c], 40)
        lin.extend(draws[:, 0].tolist())
        bra.extend(draws[:, 1].tolist())
        loo.extend(draws[:, 2].tolist())
        conds.extend([name] * 40)
    return TopologyTernaryInput(
        linear_fraction=lin,
        branched_fraction=bra,
        looped_fraction=loo,
        condition=conds,
    )


_META = RecipeMetadata(
    name="topology_ternary_simplex",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "What fraction of the skeleton is linear vs. branched vs. looped, "
        "and how do conditions partition within that simplex?"
    ),
    required_fields=(
        "linear_fraction", "branched_fraction", "looped_fraction", "condition",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


def _bary_to_cart(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert barycentric (a + b + c = 1) into 2-D cartesian for an
    equilateral triangle with vertices at
    A = (0, 0), B = (1, 0), C = (0.5, √3/2).
    """
    x = 0.0 * a + 1.0 * b + 0.5 * c
    y = (np.sqrt(3.0) / 2.0) * c
    return x, y


@register_recipe(
    metadata=_META,
    contract=TopologyTernaryInput,
    demo_contract=_demo,
)
def render(contract: TopologyTernaryInput, ax=None, **_):
    from scipy.spatial import ConvexHull

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    a = np.asarray(contract.linear_fraction, float)
    b = np.asarray(contract.branched_fraction, float)
    c = np.asarray(contract.looped_fraction, float)
    cond = np.asarray(contract.condition)

    # Renormalise to guard against near-unit but non-exact sums.
    s = a + b + c
    s = np.where(s <= 0, 1.0, s)
    a, b, c = a / s, b / s, c / s

    # Triangle outline + grid lines.
    V_A = (0.0, 0.0)
    V_B = (1.0, 0.0)
    V_C = (0.5, np.sqrt(3) / 2)
    ax.plot([V_A[0], V_B[0], V_C[0], V_A[0]],
            [V_A[1], V_B[1], V_C[1], V_A[1]],
            color="#333333", lw=1.1, zorder=2)
    for f in (0.25, 0.50, 0.75):
        x1, y1 = _bary_to_cart(np.array([f]), np.array([1 - f]), np.array([0.0]))
        x2, y2 = _bary_to_cart(np.array([f]), np.array([0.0]), np.array([1 - f]))
        x3, y3 = _bary_to_cart(np.array([1 - f]), np.array([f]), np.array([0.0]))
        x4, y4 = _bary_to_cart(np.array([0.0]), np.array([f]), np.array([1 - f]))
        x5, y5 = _bary_to_cart(np.array([1 - f]), np.array([0.0]), np.array([f]))
        x6, y6 = _bary_to_cart(np.array([0.0]), np.array([1 - f]), np.array([f]))
        ax.plot([x1[0], x2[0]], [y1[0], y2[0]], color="#DDDDDD", lw=0.4, zorder=1)
        ax.plot([x3[0], x4[0]], [y3[0], y4[0]], color="#DDDDDD", lw=0.4, zorder=1)
        ax.plot([x5[0], x6[0]], [y5[0], y6[0]], color="#DDDDDD", lw=0.4, zorder=1)

    # Vertex labels.
    ax.text(V_A[0] - 0.02, V_A[1] - 0.03, "linear",
            ha="right", va="top", fontsize=7.0, color="#111111")
    ax.text(V_B[0] + 0.02, V_B[1] - 0.03, "branched",
            ha="left", va="top", fontsize=7.0, color="#111111")
    ax.text(V_C[0], V_C[1] + 0.02, "looped",
            ha="center", va="bottom", fontsize=7.0, color="#111111")

    # Scatter per condition + convex hull.
    uniques = list(dict.fromkeys(cond.tolist()))
    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        x, y = _bary_to_cart(a[m], b[m], c[m])
        ax.scatter(x, y, s=20, color=color, alpha=0.75,
                   edgecolor="white", linewidth=0.35, zorder=4,
                   label=f"{name} (n={int(m.sum())})")
        if m.sum() >= 3:
            try:
                pts = np.column_stack([x, y])
                hull = ConvexHull(pts)
                verts = pts[hull.vertices]
                verts = np.vstack([verts, verts[0]])
                ax.plot(verts[:, 0], verts[:, 1], color=color,
                        lw=1.1, alpha=0.8, zorder=5)
            except Exception:
                pass

    # Summary: centroid linear/branched/looped per condition.
    summary = "  ·  ".join(
        f"{name}: ({smart_fmt(float(a[cond == name].mean()))}, "
        f"{smart_fmt(float(b[cond == name].mean()))}, "
        f"{smart_fmt(float(c[cond == name].mean()))})"
        for name in uniques
    )
    ax.text(0.5, -0.08, summary, transform=ax.transAxes,
            ha="center", va="top", fontsize=6.0, color="#444444")

    ax.set_aspect("equal")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.12, V_C[1] + 0.10)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.2)
    return ax
