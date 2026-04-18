"""Per-family quality assertions on each recipe's demo render."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from panelforge_figures.core.contract import ensure_all_imported, list_recipes

from .quality_rules import RULES

ensure_all_imported()
_RECIPES = list_recipes()
_IDS = [e.full_name for e in _RECIPES]


@pytest.mark.parametrize("entry", _RECIPES, ids=_IDS)
def test_recipe_quality_markers(entry):
    family = entry.metadata.family.value
    rule = RULES.get(family)
    if rule is None:
        pytest.skip(f"no quality rule registered for family={family}")
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    try:
        entry.render(entry.demo_contract(), ax=ax)
        rule(fig, entry)
    finally:
        plt.close(fig)
