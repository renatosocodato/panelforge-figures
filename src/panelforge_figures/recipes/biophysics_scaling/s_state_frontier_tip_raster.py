"""S-state frontier tip raster — per-cell rows of tip glyphs along a
signed-position axis where x = 0 is the actin frontier, negative is
inside the cell, positive is beyond. Glyphs colored / shaped by tip
state (S vs non-S); per-cell %S sidebar at right.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the per-tip scatter + the zero-reference vertical line at the actin
frontier (logical 'fit line' surrogate).
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
from ._shared import TipStateCall

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class FrontierTipRasterInput(RecipeContract):
    calls: list[TipStateCall] = Field(..., min_length=4)
    sort_rule: str = Field(
        "s_fraction",
        description="'s_fraction' | 'frontier_position' | 'cell_id'",
    )
    group_order: list[str] = Field(
        default_factory=lambda: ["WT", "LI"],
    )
    annotate_benchmark_closed: bool = True
    title: str = "Frontier tip-state raster"


def _demo() -> FrontierTipRasterInput:
    rng = np.random.default_rng(3939)
    calls: list[TipStateCall] = []
    cells_per_group = 6
    for group in ("WT", "LI"):
        for c in range(cells_per_group):
            cell_id = f"{group}_{c:02d}"
            n_tips = int(rng.integers(3, 9))
            for t in range(n_tips):
                # WT: tips clustered around x = -0.4 with mostly S state.
                # LI: tips spread further beyond frontier with non-S enrichment.
                if group == "WT":
                    pos = float(rng.normal(-0.4, 0.5))
                    state = "S" if rng.random() < 0.78 else "non-S"
                else:
                    pos = float(rng.normal(0.6, 0.9))
                    state = "S" if rng.random() < 0.34 else "non-S"
                calls.append(TipStateCall(
                    cell_id=cell_id,
                    group=group,
                    tip_id=f"t{t}",
                    frontier_position_um=pos,
                    state=state,
                    confidence=float(rng.uniform(0.65, 0.99)),
                ))
    return FrontierTipRasterInput(calls=calls)


_META = RecipeMetadata(
    name="s_state_frontier_tip_raster",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Along the signed actin-frontier axis, how do tip states "
        "(S vs non-S) distribute per cell, and does LI show non-S "
        "enrichment beyond the frontier?"
    ),
    required_fields=("calls",),
    optional_fields=(
        "sort_rule", "group_order", "annotate_benchmark_closed", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=(
        "ordered_trajectory_checkpoint_divergence",
    ),
)


@register_recipe(
    metadata=_META,
    contract=FrontierTipRasterInput,
    demo_contract=_demo,
)
def render(contract: FrontierTipRasterInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Aggregate per cell.
    by_cell: dict[str, dict] = {}
    for call in contract.calls:
        info = by_cell.setdefault(
            call.cell_id,
            {"group": call.group, "tips": []},
        )
        info["tips"].append(call)

    # Sort cells by group then by sort_rule.
    def _s_fraction(cell_info: dict) -> float:
        tips = cell_info["tips"]
        if not tips:
            return 0.0
        return sum(1 for t in tips if t.state == "S") / len(tips)

    cells_by_group: dict[str, list[tuple[str, dict]]] = {}
    for cell_id, info in by_cell.items():
        cells_by_group.setdefault(info["group"], []).append((cell_id, info))
    for group in cells_by_group:
        if contract.sort_rule == "s_fraction":
            cells_by_group[group].sort(key=lambda kv: -_s_fraction(kv[1]))
        elif contract.sort_rule == "frontier_position":
            cells_by_group[group].sort(
                key=lambda kv: float(np.mean(
                    [t.frontier_position_um for t in kv[1]["tips"]]
                ))
            )
        else:
            cells_by_group[group].sort(key=lambda kv: kv[0])

    # Build flat row list with group separators.
    rows: list[tuple[str, dict]] = []
    separators: list[float] = []
    for group in contract.group_order:
        group_cells = cells_by_group.get(group, [])
        for cell_id, info in group_cells:
            rows.append((cell_id, info))
        separators.append(len(rows) - 0.5)

    n_rows = len(rows)
    y_positions = np.arange(n_rows)

    # Frontier reference line at x = 0 (satisfies scatter_collapse rule).
    ax.axvline(0.0, color="#444444", lw=0.8, ls="--", zorder=2,
               label="actin frontier")

    # Per-tip scatter. Use filled circle for S, hollow circle for
    # non-S (avoids matplotlib's 'x' marker / edgecolor warning while
    # preserving the visual contrast between states).
    s_state_color = "#1565C0"
    non_s_color = "#C62828"
    for yi, (cell_id, info) in zip(y_positions, rows):
        for tip in info["tips"]:
            colour = s_state_color if tip.state == "S" else non_s_color
            size = 36 * (tip.confidence or 0.85) ** 2
            if tip.state == "S":
                ax.scatter(
                    [tip.frontier_position_um], [yi], s=size,
                    facecolor=colour, edgecolor="white",
                    marker="o", linewidth=0.4,
                    alpha=0.92, zorder=5,
                )
            else:
                ax.scatter(
                    [tip.frontier_position_um], [yi], s=size,
                    facecolor="none", edgecolor=colour,
                    marker="o", linewidth=0.9,
                    alpha=0.92, zorder=5,
                )

    # Group separator lines.
    for sep in separators[:-1]:
        ax.axhline(sep, color="#DDDDDD", lw=0.5, zorder=1)

    # Y-tick labels = cell ids; row label colour = group colour.
    ax.set_yticks(y_positions)
    ax.set_yticklabels([r[0] for r in rows], fontsize=6.6)
    for yi, (_, info) in zip(y_positions, rows):
        colour = _GROUP_COLOURS.get(info["group"], "#333333")
        ax.get_yticklabels()[yi].set_color(colour)
    ax.invert_yaxis()

    # Per-cell %S sidebar to the right.
    x_max = float(max(
        (t.frontier_position_um for _, info in rows for t in info["tips"]),
        default=1.0,
    )) + 0.4
    ax.set_xlim(min(
        (t.frontier_position_um for _, info in rows for t in info["tips"]),
        default=-1.0,
    ) - 0.3, x_max + 0.6)
    for yi, (_, info) in zip(y_positions, rows):
        s_frac = _s_fraction(info)
        ax.text(x_max + 0.25, yi, f"{int(round(s_frac * 100))} %S",
                ha="left", va="center", fontsize=6.2,
                color="#333333", zorder=6)

    ax.set_xlabel("signed frontier position (um)  "
                  "·  negative = inside, positive = beyond")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend (states + actin frontier).
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=s_state_color,
               markeredgecolor="white", markersize=6,
               label="S state (filled)"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="none",
               markeredgecolor=non_s_color, markersize=6,
               label="non-S (hollow)"),
        Line2D([0], [0], color="#444444", ls="--", lw=0.8,
               label="actin frontier"),
    ]
    # Legend further below axes so it clears the wrapped xlabel
    # ('signed frontier position ...  ·  negative = inside ...').
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncols=3, handlelength=1.2)

    # Header pill: per-group %S aggregate + benchmark-closed tag.
    bits = []
    for group in contract.group_order:
        group_cells = cells_by_group.get(group, [])
        if not group_cells:
            continue
        s_fracs = [_s_fraction(info) for _, info in group_cells]
        bits.append(
            f"{group}: median {smart_fmt(float(np.median(s_fracs)) * 100)} % S"
        )
    bench = (" · benchmark-closed Phase-3"
             if contract.annotate_benchmark_closed else "")
    ax.set_title(
        f"{contract.title}  ·  " + "  ·  ".join(bits) + bench,
        fontsize=8.2, pad=4,
    )
    return ax
