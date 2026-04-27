"""Branch-order topology per cell — split violin of branch-order
distribution per condition.

Split-violin family: >=2 violin bodies + >=1 median marker.
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

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
}


class CellSkeleton(RecipeContract):
    cell_id: str
    branch_orders: list[int]
    n_bifurcations: int
    total_length_um: float
    condition: str


class BranchOrderTopologyInput(RecipeContract):
    skeletons: list[CellSkeleton] = Field(..., min_length=4)
    title: str = "Branch-order topology per cell"


def _demo() -> BranchOrderTopologyInput:
    rng = np.random.default_rng(3121)
    skeletons: list[CellSkeleton] = []
    for cond, mu_branch in (("control", 2.1), ("DISC1", 2.7)):
        for k in range(40):
            branches = rng.poisson(mu_branch, size=20).tolist()
            skeletons.append(CellSkeleton(
                cell_id=f"{cond}_C{k:02d}",
                branch_orders=branches,
                n_bifurcations=int(rng.poisson(mu_branch * 4)),
                total_length_um=float(rng.gamma(shape=4.0, scale=20.0)),
                condition=cond,
            ))
    return BranchOrderTopologyInput(skeletons=skeletons)


_META = RecipeMetadata(
    name="branch_order_topology_per_cell",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per condition, what is the per-cell branch-order distribution, "
        "and how does it relate to total skeleton length?"
    ),
    required_fields=("skeletons",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("cell_shape_descriptors_by_state",),
)


@register_recipe(
    metadata=_META,
    contract=BranchOrderTopologyInput,
    demo_contract=_demo,
)
def render(contract: BranchOrderTopologyInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    conditions = list(dict.fromkeys(s.condition for s in contract.skeletons))
    positions = np.arange(len(conditions))

    medians: dict[str, float] = {}
    for pos, cond in zip(positions, conditions):
        # Pool all branch orders for this condition.
        all_branches = []
        for s in contract.skeletons:
            if s.condition == cond:
                all_branches.extend(s.branch_orders)
        vals = np.asarray(all_branches, float)
        if vals.size == 0:
            continue
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        parts = ax.violinplot([vals], positions=[pos], widths=0.78,
                              showmeans=False, showmedians=False,
                              showextrema=False)
        for pc in parts["bodies"]:
            pc.set_facecolor(colour)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.55)
        med = float(np.median(vals))
        q1, q3 = np.quantile(vals, [0.25, 0.75])
        ax.plot([pos, pos], [q1, q3],
                color="black", lw=2.2, zorder=5,
                solid_capstyle="butt")
        ax.scatter([pos], [med], s=28, facecolor="white",
                   edgecolor="black", linewidth=0.8, zorder=6)
        medians[cond] = med

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_xlabel("condition")
    ax.set_ylabel("branch order")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    bits = [f"{c}: med {smart_fmt(m)}" for c, m in medians.items()]
    n_total = len(contract.skeletons)
    ax.set_title(
        f"{contract.title}  ·  n = {n_total} cells  ·  "
        + "   ".join(bits),
        fontsize=8.4, pad=4,
    )
    return ax
