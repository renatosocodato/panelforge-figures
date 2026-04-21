"""Branching trajectory with marked branch-points and per-branch colouring.

Different from `trajectory_pseudotime_arrow` (one summary arrow on the
UMAP): this recipe renders a branching graph of the pseudotime
trajectory — branch points are marked, each branch is colour-coded,
and each terminal endpoint is labelled with its cluster identity.
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


class TrajectoryBranch(RecipeContract):
    name: str
    cells_umap1: list[float]
    cells_umap2: list[float]
    endpoint_label: str


class BranchingTrajectoryInput(RecipeContract):
    branches: list[TrajectoryBranch] = Field(..., min_length=2)
    branch_points_umap1: list[float] = Field(default_factory=list)
    branch_points_umap2: list[float] = Field(default_factory=list)
    title: str = "Branching trajectory"


def _demo() -> BranchingTrajectoryInput:
    rng = np.random.default_rng(733)
    # Start trunk: 0 → 4 along x from (-4,0).
    n_trunk = 120
    t_trunk = np.linspace(0, 1, n_trunk)
    trunk_x = -4 + 4 * t_trunk + rng.normal(0, 0.12, n_trunk)
    trunk_y = 0.3 * np.sin(t_trunk * 3) + rng.normal(0, 0.12, n_trunk)
    # Branch A: trunk → up-right.
    n_a = 80
    t_a = np.linspace(0, 1, n_a)
    a_x = 0 + 2.5 * t_a + rng.normal(0, 0.10, n_a)
    a_y = 0 + 3.0 * t_a + rng.normal(0, 0.10, n_a)
    # Branch B: trunk → down-right.
    n_b = 90
    t_b = np.linspace(0, 1, n_b)
    b_x = 0 + 3.0 * t_b + rng.normal(0, 0.10, n_b)
    b_y = 0 - 2.2 * t_b + rng.normal(0, 0.10, n_b)
    return BranchingTrajectoryInput(
        branches=[
            TrajectoryBranch(
                name="trunk",
                cells_umap1=trunk_x.tolist(), cells_umap2=trunk_y.tolist(),
                endpoint_label="progenitor"),
            TrajectoryBranch(
                name="branch-A",
                cells_umap1=a_x.tolist(), cells_umap2=a_y.tolist(),
                endpoint_label="activated"),
            TrajectoryBranch(
                name="branch-B",
                cells_umap1=b_x.tolist(), cells_umap2=b_y.tolist(),
                endpoint_label="DAM"),
        ],
        branch_points_umap1=[0.0],
        branch_points_umap2=[0.0],
    )


_META = RecipeMetadata(
    name="trajectory_branching_force_directed",
    modality="single_cell_embeddings",
    family=RecipeFamily.conceptual,
    answers_question=(
        "When the trajectory has multiple branches, where are the "
        "branch points and which cells commit to each fate?"
    ),
    required_fields=("branches",),
    optional_fields=(
        "branch_points_umap1", "branch_points_umap2", "title",
    ),
    file_format_hints=("json", "parquet"),
    alternatives_in_modality=(
        "trajectory_pseudotime_arrow", "diffusion_map_2d",
    ),
)


@register_recipe(
    metadata=_META,
    contract=BranchingTrajectoryInput,
    demo_contract=_demo,
)
def render(contract: BranchingTrajectoryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    branch_colors = ["#455A64", "#E65100", "#2E7D32", "#6A1B9A", "#1565C0"]

    all_x: list[float] = []
    all_y: list[float] = []
    for i, br in enumerate(contract.branches):
        color = branch_colors[i % len(branch_colors)]
        x = np.asarray(br.cells_umap1, float)
        y = np.asarray(br.cells_umap2, float)
        all_x.extend(x.tolist())
        all_y.extend(y.tolist())
        ax.scatter(x, y, s=8, color=color, alpha=0.60,
                   edgecolor="white", linewidth=0.2, zorder=3,
                   label=f"{br.name} -> {br.endpoint_label}")
        # Draw a smooth path through the branch: ordered along x.
        order = np.argsort(x)
        ax.plot(x[order], y[order], color=color, lw=1.2, alpha=0.85,
                zorder=4)
        # Endpoint label at the far end.
        end_idx = int(order[-1])
        ax.text(x[end_idx] + 0.15, y[end_idx], br.endpoint_label,
                ha="left", va="center", fontsize=6.8, color=color,
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec=color, lw=0.5, alpha=0.95),
                zorder=6)

    # Branch points — big circle patches so the conceptual quality
    # rule sees ≥2 decorative patches on the axis.
    import matplotlib.patches as mpatches
    for i, (bx, by) in enumerate(zip(
            contract.branch_points_umap1, contract.branch_points_umap2)):
        ax.add_patch(mpatches.Circle(
            (bx, by), 0.22,
            facecolor="white", edgecolor="#111111", linewidth=1.4,
            zorder=7,
        ))
        ax.add_patch(mpatches.Circle(
            (bx, by), 0.08,
            facecolor="#111111", edgecolor="none", zorder=8,
        ))
        ax.text(bx, by + 0.45, f"BP{i+1}",
                ha="center", va="bottom", fontsize=6.4,
                color="#111111", fontweight="bold", zorder=9)

    # Extend axes a touch for clarity.
    pad = 0.8
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    n_total = sum(len(br.cells_umap1) for br in contract.branches)
    ax.set_title(
        f"{contract.title}  ·  {len(contract.branches)} branches, "
        f"N cells = {n_total}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="lower left",
              handlelength=1.2)

    # Branch-size callout.
    sizes = [f"{br.name}: {len(br.cells_umap1)}" for br in contract.branches]
    ax.text(
        0.99, 0.02,
        "   ".join(sizes) + f"   ·  {smart_fmt(len(contract.branch_points_umap1))} branch pt",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.2, color="#333333",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )
    return ax
