"""Enforce that every recipe imports from its modality's `_aesthetic` module.

This prevents recipes from silently degrading to default style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from panelforge_figures.core.contract import ensure_all_imported, list_recipes

ensure_all_imported()
_RECIPES = list_recipes()
_IDS = [e.full_name for e in _RECIPES]


@pytest.mark.parametrize("entry", _RECIPES, ids=_IDS)
def test_recipe_imports_modality_aesthetic(entry):
    """Recipe source must include `from ._aesthetic import AESTHETIC`."""
    src = _recipe_source_path(entry)
    tree = ast.parse(src.read_text(encoding="utf-8"))
    imports_aesthetic = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "_aesthetic":
            names = {n.name for n in node.names}
            if "AESTHETIC" in names:
                imports_aesthetic = True
                break
    assert imports_aesthetic, (
        f"{entry.full_name} does not `from ._aesthetic import AESTHETIC` — "
        "the modality aesthetic contract is not being honored."
    )


@pytest.mark.parametrize("entry", _RECIPES, ids=_IDS)
def test_recipe_calls_aesthetic_apply(entry):
    """Recipe source must call `AESTHETIC.apply_to_ax(...)` somewhere."""
    src = _recipe_source_path(entry)
    text = src.read_text(encoding="utf-8")
    assert "AESTHETIC.apply_to_ax" in text or "AESTHETIC.apply_to_fig" in text, (
        f"{entry.full_name} imports AESTHETIC but never applies it to an axis/figure."
    )


def _recipe_source_path(entry) -> Path:
    from importlib import import_module
    mod = import_module(entry.render.__module__)
    return Path(mod.__file__)
