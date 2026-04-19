"""Cross-modality figure-integrity QA.

Renders every registered recipe's demo contract and runs the
:func:`panelforge_figures.core.qa.check_figure_integrity` rule set on
each output. Any ``error``-severity issue fails the build; ``warning``
issues surface in the captured output for triage but are allowed.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from panelforge_figures.core.contract import ensure_all_imported, list_recipes
from panelforge_figures.core.qa import check_figure_integrity

ensure_all_imported()
_RECIPES = list_recipes()
_IDS = [e.full_name for e in _RECIPES]


@pytest.mark.parametrize("entry", _RECIPES, ids=_IDS)
def test_recipe_passes_figure_integrity(entry):
    """Each recipe's rendered demo figure must pass the QA rule set."""
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    try:
        entry.render(entry.demo_contract(), ax=ax)
        report = check_figure_integrity(fig)
        assert report.ok, (
            f"{entry.full_name} failed figure integrity:\n{report.as_text()}"
        )
    finally:
        plt.close(fig)
