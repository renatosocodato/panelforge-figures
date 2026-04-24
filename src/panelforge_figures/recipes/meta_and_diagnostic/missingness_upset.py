"""UpSet-style missingness — set-intersection view of which variable
combinations are co-missing, with per-intersection count bar on top.

Distinct from `missing_data_pattern_matrix` (variable × row pattern
grid with marginal counts): UpSet uses an intersection-dot-matrix
with an aggregated-count bar, suitable for many variables where a
pairwise grid becomes unwieldy.

Matrix family: ≥4 patches (bars + dots satisfy this).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class MissingnessUpsetInput(RecipeContract):
    variable_names: list[str] = Field(..., min_length=3)
    intersections: list[list[int]] = Field(
        ...,
        description=(
            "list of 0/1 vectors (1 = that variable is MISSING in the "
            "intersection); outer length = n_intersections"
        ),
    )
    intersection_counts: list[int] = Field(
        ..., description="n samples with each missingness pattern"
    )
    title: str = "Missingness intersections (UpSet)"


def _demo() -> MissingnessUpsetInput:
    variables = ["sex", "age", "FRET_ratio", "process_len",
                 "cv_velocity", "biomarker"]
    # Missingness intersections (1 = missing). Sorted by count desc.
    intersections = [
        [0, 0, 0, 0, 0, 0],        # no missingness (complete cases)
        [0, 0, 0, 0, 0, 1],        # only biomarker missing
        [0, 0, 0, 0, 1, 1],        # cv_velocity + biomarker
        [0, 0, 1, 0, 1, 1],        # FRET + cv + biomarker
        [0, 1, 1, 1, 1, 1],        # age + below
        [0, 0, 0, 1, 0, 1],        # process_len + biomarker
    ]
    counts = [132, 41, 18, 9, 5, 2]
    return MissingnessUpsetInput(
        variable_names=variables,
        intersections=intersections,
        intersection_counts=counts,
    )


_META = RecipeMetadata(
    name="missingness_upset",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Which combinations of variables are co-missing most often, "
        "and how large is each intersection?"
    ),
    required_fields=(
        "variable_names", "intersections", "intersection_counts",
    ),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("missing_data_pattern_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=MissingnessUpsetInput,
    demo_contract=_demo,
)
def render(contract: MissingnessUpsetInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    vars_ = contract.variable_names
    I_mat = np.asarray(contract.intersections, int)
    counts = np.asarray(contract.intersection_counts, int)
    n_intr, n_var = I_mat.shape

    # Layout: top 60 % of axes = count bars; bottom 40 % = intersection
    # dot-matrix.
    y_bar_top = 1.0
    y_bar_bot = 0.40
    y_dot_top = 0.35
    y_dot_bot = 0.00
    x_lo = 0.18
    x_hi = 0.98
    col_w = (x_hi - x_lo) / n_intr
    col_x = [x_lo + i * col_w for i in range(n_intr)]

    # Count bars (top panel).
    max_c = float(counts.max())
    for i, c in enumerate(counts):
        bar_h = (y_bar_top - y_bar_bot) * 0.88 * (c / max_c)
        ax.add_patch(mpatches.Rectangle(
            (col_x[i] + col_w * 0.15, y_bar_bot),
            col_w * 0.70, bar_h,
            facecolor="#455A64", edgecolor="white", linewidth=0.6,
            alpha=0.90, zorder=3,
        ))
        # Count label.
        ax.text(col_x[i] + col_w * 0.5, y_bar_bot + bar_h + 0.01,
                f"{int(c)}",
                ha="center", va="bottom", fontsize=6.6,
                color="#263238", fontweight="bold", zorder=4)

    # Variable labels at left of dot matrix.
    row_h = (y_dot_top - y_dot_bot) / n_var
    for v_i, vname in enumerate(vars_):
        # Invert row order so first variable at top.
        y_row = y_dot_top - (v_i + 0.5) * row_h
        ax.text(x_lo - 0.01, y_row, vname,
                ha="right", va="center", fontsize=6.8,
                color="#333333", zorder=4)
        # Row guideline.
        ax.plot([x_lo, x_hi], [y_row, y_row],
                color="#EEEEEE", lw=0.4, zorder=1)

    # Dots per intersection.
    dot_r = min(col_w, row_h) * 0.35
    for i in range(n_intr):
        cx = col_x[i] + col_w * 0.5
        missing_rows = [v_i for v_i in range(n_var) if I_mat[i, v_i] == 1]
        # Connect selected rows with a vertical line.
        if len(missing_rows) >= 2:
            ys = [y_dot_top - (v + 0.5) * row_h for v in missing_rows]
            ax.plot([cx, cx], [min(ys), max(ys)],
                    color="#263238", lw=1.2, zorder=3)
        for v_i in range(n_var):
            y_row = y_dot_top - (v_i + 0.5) * row_h
            filled = (I_mat[i, v_i] == 1)
            ax.add_patch(mpatches.Circle(
                (cx, y_row), dot_r,
                facecolor=("#263238" if filled else "#DDDDDD"),
                edgecolor="white", linewidth=0.5,
                zorder=4,
            ))

    # Per-variable totals (bottom-left margin).
    per_var_total = []
    for v_i in range(n_var):
        t = int(np.sum(counts * I_mat[:, v_i]))
        per_var_total.append(t)
        y_row = y_dot_top - (v_i + 0.5) * row_h
        ax.text(x_hi + 0.005, y_row, f"  {t}",
                ha="left", va="center", fontsize=6.2,
                color="#777777", zorder=4)

    # Labels + cleanup.
    ax.text(x_lo - 0.01, y_bar_bot + (y_bar_top - y_bar_bot) * 0.5,
            "N samples",
            ha="right", va="center", fontsize=7.0,
            color="#333333", rotation=90, zorder=4)
    ax.text(x_hi + 0.005, y_dot_top + 0.01, "var n",
            ha="left", va="bottom", fontsize=6.0,
            color="#777777", zorder=4)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
