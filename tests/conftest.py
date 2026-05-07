"""Test configuration: non-interactive matplotlib + eager registry import."""

from __future__ import annotations

import os
import tempfile

import matplotlib
import pytest

matplotlib.use("Agg")

# Isolate the per-user projects-registry (spec_cross_project §2) from the
# real home directory during tests so ``scan_project``'s auto-register hook
# (Sprint 3A) and any direct registry I/O cannot mutate the developer's
# ``~/.config/panelforge/projects.yaml``.
_TEST_XDG = tempfile.mkdtemp(prefix="panelforge-tests-xdg-")
os.environ.setdefault("XDG_CONFIG_HOME", _TEST_XDG)

from panelforge_figures.core.contract import ensure_all_imported, list_recipes  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _load_registry():
    ensure_all_imported()


@pytest.fixture(scope="session")
def all_registered():
    ensure_all_imported()
    return list_recipes()
