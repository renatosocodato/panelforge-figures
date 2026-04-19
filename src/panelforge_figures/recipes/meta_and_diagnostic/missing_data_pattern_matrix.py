"""Missing-data pattern matrix — van Buuren-style pattern summary.

Rows are unique missing-data patterns; columns are variables. Cells are filled
(observed) or empty (missing). A right margin shows the count of rows in each
pattern; a bottom margin shows the missingness fraction per variable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
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


class MissingPatternInput(RecipeContract):
    variable_names: list[str] = Field(..., min_length=1)
    patterns: list[list[int]] = Field(..., description="rows of 0/1 (1=observed, 0=missing)")
    pattern_counts: list[int] = Field(..., description="N rows per pattern")
    variable_missing_frac: list[float] | None = None
    title: str = "Missing-data pattern matrix"


def _demo() -> MissingPatternInput:
    variables = ["sex", "age", "FRET_ratio", "process_len", "cv_velocity", "biomarker"]
    patterns = [
        [1, 1, 1, 1, 1, 1],  # complete
        [1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 0, 0],
        [1, 1, 0, 1, 0, 0],
        [1, 0, 0, 0, 0, 0],
    ]
    counts = [132, 41, 18, 7, 2]
    df = pd.DataFrame(
        np.repeat(patterns, counts, axis=0),
        columns=variables,
    )
    miss = (1 - df.mean()).tolist()
    return MissingPatternInput(
        variable_names=variables,
        patterns=patterns,
        pattern_counts=counts,
        variable_missing_frac=miss,
    )


_META = RecipeMetadata(
    name="missing_data_pattern_matrix",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question="Which variables are co-missing, how often, and which rows are complete?",
    required_fields=("variable_names", "patterns", "pattern_counts"),
    optional_fields=("variable_missing_frac", "title"),
    file_format_hints=("tabular", "pandas"),
    alternatives_in_modality=("qc_metric_radar",),
)


@register_recipe(metadata=_META, contract=MissingPatternInput, demo_contract=_demo)
def render(contract: MissingPatternInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    P = np.array(contract.patterns)                          # (n_patterns, n_vars)
    counts = np.array(contract.pattern_counts, dtype=int)
    n_vars = P.shape[1]
    n_pat = P.shape[0]

    obs_color = palette[0]
    miss_color = "#EEEEEE"
    for i in range(n_pat):
        for j in range(n_vars):
            color = obs_color if P[i, j] == 1 else miss_color
            ax.add_patch(
                __import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
                    (j, -i), 0.9, 0.9, facecolor=color, edgecolor="white", linewidth=0.8,
                )
            )
            if P[i, j] == 0:
                ax.text(j + 0.45, -i + 0.45, "·", ha="center", va="center",
                        color="#AAAAAA", fontsize=9.0)

    # Right margin: row counts per pattern.
    for i, c in enumerate(counts):
        ax.text(n_vars + 0.3, -i + 0.45, f"{int(c)}", va="center", ha="left",
                fontsize=7.2, color="#333333")
    ax.text(n_vars + 0.3, 1.5, "N rows", va="center", ha="left",
            fontsize=6.8, color="#555555")

    # Bottom margin: missingness fraction per variable.
    miss_frac = contract.variable_missing_frac
    if miss_frac is not None:
        for j, f in enumerate(miss_frac):
            ax.text(j + 0.45, -n_pat + 0.2, smart_fmt(f),
                    ha="center", va="top", fontsize=6.8,
                    color="#B71C1C" if f > 0.25 else "#333333")
        ax.text(-0.3, -n_pat + 0.2, "missing\nfrac", ha="right", va="top",
                fontsize=6.8, color="#555555")

    # Axis decoration.
    ax.set_xticks(np.arange(n_vars) + 0.45)
    ax.set_xticklabels(contract.variable_names, rotation=35, ha="right", fontsize=7.2)
    ax.set_yticks([])
    ax.set_xlim(-0.4, n_vars + 1.6)
    ax.set_ylim(-n_pat - 0.6, 2.3)
    ax.set_title(contract.title, fontsize=9.0)
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    return ax
