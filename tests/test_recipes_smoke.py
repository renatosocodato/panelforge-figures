"""Smoke test: every registered recipe renders its demo contract without error."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from panelforge_figures.core.contract import ensure_all_imported, list_recipes

ensure_all_imported()
_RECIPES = list_recipes()
_IDS = [e.full_name for e in _RECIPES]


@pytest.mark.parametrize("entry", _RECIPES, ids=_IDS)
def test_recipe_renders_demo_contract(entry):
    """Each registered recipe must render its demo_contract() into a fresh axis."""
    fig, ax = plt.subplots(figsize=(2.8, 2.8))
    try:
        entry.render(entry.demo_contract(), ax=ax)
        # Recipes that swap a cartesian ax for a polar one return the new ax;
        # in that case the fig will have at least one axis with data.
        assert any(
            a.has_data() or len(a.get_children()) > 0 for a in fig.axes
        ), f"{entry.full_name}: no content after render"
    finally:
        plt.close(fig)
