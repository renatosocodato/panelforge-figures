"""Test configuration: non-interactive matplotlib + eager registry import."""

from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")

from panelforge_figures.core.contract import ensure_all_imported, list_recipes


@pytest.fixture(scope="session", autouse=True)
def _load_registry():
    ensure_all_imported()


@pytest.fixture(scope="session")
def all_registered():
    ensure_all_imported()
    return list_recipes()
