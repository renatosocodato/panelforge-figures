"""Alternative hypothesis exclusion table — alternative interpretations
on rows × evaluation criteria on columns; cell glyphs Y / N / ~
(Helvetica-safe ASCII) for whether each criterion supports / rules-out
/ is equivocal-on each alternative; per-row overall verdict in a
right-most flag column.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC
from ._shared import ExclusionRow

_GLYPH_COLOR = {
    "Y": "#2E7D32",     # criterion supports the hypothesis
    "N": "#C62828",     # criterion rules out
    "~": "#FB8C00",     # equivocal
}

_VERDICT_COLOR = {
    "ruled_out": "#C62828",
    "equivocal": "#FB8C00",
    "consistent": "#2E7D32",
}


class HypothesisExclusionTableInput(RecipeContract):
    rows: list[ExclusionRow] = Field(..., min_length=2)
    criterion_order: list[str] | None = None
    title: str = "Alternative hypothesis exclusion table"


def _demo() -> HypothesisExclusionTableInput:
    rows = [
        ExclusionRow(
            hypothesis="Global polymer degradation",
            criteria={
                "polymer Lp invariant": "N",
                "fractal dim invariant": "N",
                "PSD regime invariant": "N",
            },
            overall_verdict="ruled_out",
        ),
        ExclusionRow(
            hypothesis="Global motor hyperactivation",
            criteria={
                "polymer Lp invariant": "Y",
                "fractal dim invariant": "Y",
                "PSD regime invariant": "N",
            },
            overall_verdict="ruled_out",
        ),
        ExclusionRow(
            hypothesis="Global cytoskeletal coupling collapse",
            criteria={
                "polymer Lp invariant": "Y",
                "fractal dim invariant": "Y",
                "PSD regime invariant": "Y",
            },
            overall_verdict="equivocal",
        ),
        ExclusionRow(
            hypothesis="Confinement-driven buckling",
            criteria={
                "polymer Lp invariant": "Y",
                "fractal dim invariant": "Y",
                "PSD regime invariant": "Y",
            },
            overall_verdict="consistent",
        ),
    ]
    return HypothesisExclusionTableInput(
        rows=rows,
        criterion_order=[
            "polymer Lp invariant", "fractal dim invariant",
            "PSD regime invariant",
        ],
    )


_META = RecipeMetadata(
    name="alternative_hypothesis_exclusion_table",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across alternative interpretations, which criteria rule "
        "out which hypotheses, and what is the overall verdict for "
        "each alternative?"
    ),
    required_fields=("rows",),
    optional_fields=("criterion_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("replication_retrospective_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=HypothesisExclusionTableInput,
    demo_contract=_demo,
)
def render(contract: HypothesisExclusionTableInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    if contract.criterion_order is None:
        criterion_order: list[str] = []
        for r in contract.rows:
            for k in r.criteria:
                if k not in criterion_order:
                    criterion_order.append(k)
    else:
        criterion_order = list(contract.criterion_order)
    n_rows = len(contract.rows)
    n_cols = len(criterion_order) + 1   # + verdict column

    # Cell-patch background using add_patch (≥4 cell patches for matrix
    # family rule).
    import matplotlib.patches as mpatches
    for i, r in enumerate(contract.rows):
        for j, c in enumerate(criterion_order):
            ax.add_patch(mpatches.Rectangle(
                (j - 0.5, i - 0.5), 1.0, 1.0,
                facecolor="#F8F9FA", edgecolor="#DDDDDD",
                linewidth=0.6, zorder=2,
            ))
        # Verdict column background.
        ax.add_patch(mpatches.Rectangle(
            (n_cols - 1 - 0.5, i - 0.5), 1.0, 1.0,
            facecolor="#F2F4F6", edgecolor="#CCCCCC",
            linewidth=0.6, zorder=2,
        ))

    # Glyphs.
    for i, r in enumerate(contract.rows):
        for j, c in enumerate(criterion_order):
            glyph = r.criteria.get(c, "~")
            colour = _GLYPH_COLOR.get(glyph, "#777777")
            ax.text(j, i, glyph, ha="center", va="center",
                    fontsize=9.6, color=colour, fontweight="bold",
                    zorder=4)
        # Verdict cell.
        verdict = r.overall_verdict
        ax.text(n_cols - 1, i, verdict.replace("_", " "),
                ha="center", va="center", fontsize=6.6,
                color=_VERDICT_COLOR.get(verdict, "#222222"),
                fontweight="bold", zorder=4)

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([r.hypothesis for r in contract.rows],
                       fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(criterion_order) + ["verdict"],
                       fontsize=6.6, rotation=20, ha="right")
    ax.set_xlim(-0.6, n_cols - 0.4)
    ax.set_ylim(n_rows - 0.4, -0.6)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(left=False, bottom=False)

    # Legend strip below.
    legend_text = "Y = supports  ·  N = rules out  ·  ~ = equivocal"
    ax.text(0.5, -0.18, legend_text,
            transform=ax.transAxes,
            ha="center", va="top", fontsize=6.4,
            color="#666666", style="italic", zorder=4)

    n_ruled_out = sum(1 for r in contract.rows
                      if r.overall_verdict == "ruled_out")
    n_consistent = sum(1 for r in contract.rows
                       if r.overall_verdict == "consistent")
    ax.set_title(
        f"{contract.title}  ·  {n_rows} alternatives  ·  "
        f"{n_ruled_out} ruled out, {n_consistent} consistent",
        fontsize=8.2, pad=6,
    )
    return ax
