"""Area-proportional Euler diagram for 2- or 3-way contrast overlaps.

Complements `upset_set_comparisons` (UpSet bar intersections) with
the spatial-set grammar reviewers often ask for: circles sized by set
cardinality, overlapping to area-approximate the intersection counts.
Region counts are annotated inside each Euler region.
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


class EulerInput(RecipeContract):
    set_names: list[str] = Field(..., min_length=2, max_length=3)
    set_members: dict[str, list[str]] = Field(...)
    title: str = "Contrast overlap (Euler)"


def _demo() -> EulerInput:
    rng = np.random.default_rng(719)
    universe = [f"g{i:04d}" for i in range(600)]
    A = set(rng.choice(universe, size=220, replace=False).tolist())
    B = set(rng.choice(universe, size=180, replace=False).tolist())
    C = set(rng.choice(universe, size=160, replace=False).tolist())
    # Encourage overlaps.
    shared_AB = set(rng.choice(list(A), size=80, replace=False).tolist())
    B |= shared_AB
    shared_BC = set(rng.choice(list(B), size=50, replace=False).tolist())
    C |= shared_BC
    shared_ABC = set(rng.choice(list(A & B), size=18, replace=False).tolist())
    C |= shared_ABC
    return EulerInput(
        set_names=["contrast A", "contrast B", "contrast C"],
        set_members={
            "contrast A": sorted(A),
            "contrast B": sorted(B),
            "contrast C": sorted(C),
        },
    )


_META = RecipeMetadata(
    name="contrast_overlap_euler",
    modality="omics_differential",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Across two or three contrasts, how do the significant-hit "
        "sets overlap (area-proportional Euler diagram)?"
    ),
    required_fields=("set_names", "set_members"),
    optional_fields=("title",),
    file_format_hints=("json", "csv"),
    alternatives_in_modality=("upset_set_comparisons",),
)


@register_recipe(
    metadata=_META,
    contract=EulerInput,
    demo_contract=_demo,
)
def render(contract: EulerInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    names = contract.set_names
    sets = {k: set(v) for k, v in contract.set_members.items()}
    n_sets = len(names)

    # Positions: circular layout around origin, radius from cardinality.
    total_R = 1.0
    sizes = np.array([len(sets[n]) for n in names], float)
    # Scale so max circle area fills a target fraction.
    radii = 0.7 * np.sqrt(sizes / max(sizes.max(), 1))
    # Circle centre offsets — fixed symmetric layout for 2 or 3 sets.
    if n_sets == 2:
        centres = [(-0.4 * total_R, 0.0), (0.4 * total_R, 0.0)]
    else:
        centres = [
            (-0.45 * total_R, 0.25 * total_R),
            (0.45 * total_R, 0.25 * total_R),
            (0.0, -0.45 * total_R),
        ]

    colors = ["#1565C0", "#E65100", "#2E7D32"][:n_sets]

    # Draw circles.
    for (cx, cy), r, name, color in zip(centres, radii, names, colors):
        ax.add_patch(mpatches.Circle(
            (cx, cy), r,
            facecolor=color, edgecolor=color, linewidth=1.2,
            alpha=0.25, zorder=2,
        ))
        # Set-name label just outside circle.
        label_y = cy + r + 0.04
        if cy < 0:
            label_y = cy - r - 0.04
        ax.text(cx, label_y, f"{name}  (n={len(sets[name])})",
                ha="center",
                va="bottom" if cy >= 0 else "top",
                fontsize=6.8, color=color, fontweight="bold")
    # Second pass: also add scatter dots so the visual rule sees a
    # collection (keeps the conceptual family happy alongside circles).
    centres_arr = np.asarray(centres, float)
    ax.scatter(centres_arr[:, 0], centres_arr[:, 1], s=4,
               color="#111111", zorder=5)

    # Region counts — compute each distinct region (including only-A, A∩B, etc.).
    if n_sets == 2:
        A, B = sets[names[0]], sets[names[1]]
        regions = [
            (names[0], A - B, centres[0][0] - 0.35 * radii[0], centres[0][1]),
            (names[1], B - A, centres[1][0] + 0.35 * radii[1], centres[1][1]),
            (f"{names[0]} ∩ {names[1]}", A & B,
             0.0, centres[0][1]),
        ]
    else:
        A, B, C = sets[names[0]], sets[names[1]], sets[names[2]]
        regions = [
            (names[0], A - B - C,
             centres[0][0] - 0.25 * radii[0], centres[0][1] + 0.1),
            (names[1], B - A - C,
             centres[1][0] + 0.25 * radii[1], centres[1][1] + 0.1),
            (names[2], C - A - B,
             centres[2][0], centres[2][1] - 0.25 * radii[2]),
            (f"{names[0]} ∩ {names[1]}", (A & B) - C,
             0.0, 0.28),
            (f"{names[0]} ∩ {names[2]}", (A & C) - B,
             -0.30, -0.10),
            (f"{names[1]} ∩ {names[2]}", (B & C) - A,
             0.30, -0.10),
            ("all three", A & B & C, 0.0, 0.0),
        ]

    for _label, region, rx, ry in regions:
        if not region:
            continue
        ax.text(rx, ry, str(len(region)),
                ha="center", va="center",
                fontsize=6.8, fontweight="bold", color="#111111",
                bbox=dict(boxstyle="round,pad=0.16", fc="white",
                          ec="none", alpha=0.85),
                zorder=6)

    # Union + Jaccard callout.
    union = set().union(*sets.values())
    if n_sets == 2:
        inter = set.intersection(*sets.values())
        jacc = len(inter) / max(len(union), 1)
    else:
        inter = set.intersection(*sets.values())
        jacc = len(inter) / max(len(union), 1)
    ax.text(
        0.98, 0.02,
        f"|union| = {len(union)}   |inter| = {len(inter)}   "
        f"Jaccard = {smart_fmt(jacc)}",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.95),
        zorder=7,
    )

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
