"""Sample single-file plugin used by `tests/test_plugin_discovery.py`.

Registers ONE recipe under modality ``disc1_extras`` to verify that the
discovery + loading machinery wires up plugin recipes identically to
catalog recipes.  Render is intentionally minimal — the goal is to
prove the contract / metadata flow end-to-end, not to exercise
matplotlib heavily.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import Field

from panelforge_figures.core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)

__version__ = "0.1.0"


class CohortViolinInput(RecipeContract):
    """Inputs for the sample plugin's cohort_violin recipe."""

    cohort_names: list[str] = Field(..., min_length=2)
    cohort_values: list[list[float]] = Field(
        ..., description="cohort_values[cohort] = list of measurements",
    )
    title: str = "DISC1 cohort violin (plugin)"


def _demo() -> CohortViolinInput:
    rng = np.random.default_rng(11)
    return CohortViolinInput(
        cohort_names=["Ctrl", "DISC1"],
        cohort_values=[
            rng.normal(0.0, 1.0, 50).tolist(),
            rng.normal(0.6, 1.2, 50).tolist(),
        ],
    )


_META = RecipeMetadata(
    name="cohort_violin",
    modality="disc1_extras",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does the DISC1 cohort distribution differ from control under "
        "the lab's local cohort definition?"
    ),
    required_fields=("cohort_names", "cohort_values"),
    optional_fields=("title",),
    file_format_hints=("csv",),
)


@register_recipe(metadata=_META, contract=CohortViolinInput, demo_contract=_demo)
def render(contract: CohortViolinInput, ax: Any = None, **_: Any) -> Any:
    """Render the cohort violin (plugin recipe)."""
    if ax is None:
        import matplotlib.pyplot as plt

        _, ax = plt.subplots(figsize=(4.0, 2.6))
    parts = ax.violinplot(contract.cohort_values, showmeans=True)
    ax.set_xticks(range(1, len(contract.cohort_names) + 1))
    ax.set_xticklabels(contract.cohort_names)
    ax.set_title(contract.title, fontsize=9.0)
    return ax, parts
