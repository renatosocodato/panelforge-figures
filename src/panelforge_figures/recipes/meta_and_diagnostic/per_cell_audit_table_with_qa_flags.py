"""Per-cell audit table with QA flags — per-row metric values plus a
status flag column (pass / borderline / flag / fail) coloured by
verdict.

Matrix family: >=1 imshow OR >=4 cell patches.
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
from ._shared import CellAuditRow

_FLAG_COLOR = {
    "pass": "#2E7D32",
    "borderline": "#FB8C00",
    "flag": "#EF6C00",
    "fail": "#C62828",
}


class PerCellAuditTableInput(RecipeContract):
    rows: list[CellAuditRow] = Field(..., min_length=4)
    column_order: list[str] | None = None
    title: str = "Per-cell audit table"


def _demo() -> PerCellAuditTableInput:
    rng = np.random.default_rng(411)
    rows: list[CellAuditRow] = []
    column_order = ["Lp_actin_um", "Lp_mt_um", "fit_R2",
                    "n_segments", "censored"]
    for k in range(20):
        # Most cells pass; a few fail / borderline.
        flag = "pass"
        if k in (3, 11):
            flag = "fail"
        elif k in (5, 14, 17):
            flag = "borderline"
        elif k == 7:
            flag = "flag"
        cols = {
            "Lp_actin_um": float(rng.normal(8.0, 1.4)),
            "Lp_mt_um": float(rng.normal(40.0, 6.0)),
            "fit_R2": float(rng.uniform(0.78, 0.98))
            if flag == "pass" else float(rng.uniform(0.40, 0.82)),
            "n_segments": float(int(rng.integers(40, 120))),
            "censored": 1.0 if flag in ("flag", "fail") else 0.0,
        }
        rows.append(CellAuditRow(
            cell_id=f"C{k:02d}", columns=cols, flag=flag,
        ))
    return PerCellAuditTableInput(
        rows=rows, column_order=column_order,
    )


_META = RecipeMetadata(
    name="per_cell_audit_table_with_qa_flags",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per cell, which measurements pass / fail QA, and what is "
        "the row-level verdict flag?"
    ),
    required_fields=("rows",),
    optional_fields=("column_order", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("data_quality_heatmap",),
)


@register_recipe(
    metadata=_META,
    contract=PerCellAuditTableInput,
    demo_contract=_demo,
)
def render(contract: PerCellAuditTableInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Resolve column order.
    if contract.column_order is None:
        # Take union of column keys, preserving first-seen order.
        col_set: list[str] = []
        for r in contract.rows:
            for k in r.columns:
                if k not in col_set:
                    col_set.append(k)
        column_order = col_set
    else:
        column_order = list(contract.column_order)
    n_cols = len(column_order) + 1   # + flag column
    n_rows = len(contract.rows)

    fig = ax.figure
    # Per-column data array for column-wise z-score colouring.
    data = np.zeros((n_rows, len(column_order)))
    for i, r in enumerate(contract.rows):
        for j, k in enumerate(column_order):
            data[i, j] = float(r.columns.get(k, np.nan))

    # Background pcolormesh (z-scored per column) to convey magnitude.
    Z = np.zeros_like(data)
    for j in range(data.shape[1]):
        col = data[:, j]
        finite = np.isfinite(col)
        if finite.sum() > 1:
            mu = float(col[finite].mean())
            sd = float(col[finite].std(ddof=1))
            if sd > 1e-9:
                Z[:, j] = (col - mu) / sd
    v_abs = float(max(abs(Z).max(), 1e-6))

    X = np.arange(n_cols + 1) - 0.5
    Y = np.arange(n_rows + 1) - 0.5
    Z_show = np.zeros((n_rows, n_cols))
    Z_show[:, : len(column_order)] = Z
    mask = np.zeros_like(Z_show, dtype=bool)
    mask[:, len(column_order)] = True   # flag column hidden from heat
    Z_masked = np.ma.masked_array(Z_show, mask=mask)

    mesh = ax.pcolormesh(X, Y, Z_masked, cmap="RdBu_r",
                         vmin=-v_abs, vmax=v_abs,
                         shading="auto", zorder=2)

    # Annotate metric values.
    for i, r in enumerate(contract.rows):
        for j, k in enumerate(column_order):
            v = data[i, j]
            if not np.isfinite(v):
                continue
            text_color = "white" if abs(Z[i, j]) > (0.55 * v_abs) \
                else "#222222"
            ax.text(j, i, f"{smart_fmt(v)}",
                    ha="center", va="center", fontsize=6.4,
                    color=text_color, zorder=4)
        # Flag column.
        flag_col_idx = len(column_order)
        flag = r.flag
        ax.text(flag_col_idx, i, flag,
                ha="center", va="center", fontsize=6.4,
                color=_FLAG_COLOR.get(flag, "#222222"),
                fontweight="bold", zorder=4)

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([r.cell_id for r in contract.rows], fontsize=6.4)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(column_order) + ["flag"],
                       fontsize=6.6, rotation=20, ha="right")
    ax.tick_params(axis="x", which="major", pad=4)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    cbar = fig.colorbar(mesh, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("z-scored per-column", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Verdict tally in title.
    counts = {k: 0 for k in _FLAG_COLOR}
    for r in contract.rows:
        counts[r.flag] = counts.get(r.flag, 0) + 1
    bits = "  ".join(f"{k}: {v}" for k, v in counts.items() if v > 0)
    ax.set_title(
        f"{contract.title}  ·  n = {n_rows}  ·  {bits}",
        fontsize=8.2, pad=4,
    )
    return ax
