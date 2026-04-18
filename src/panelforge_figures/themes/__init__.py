"""Theme registry — per-venue rcParams overlays.

Each theme module must call `register_theme(name, fn)` at import time where
`fn` returns a dict of matplotlib rcParams overrides to layer on top of the
base style.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from typing import Any

_REGISTRY: dict[str, Callable[[], dict[str, Any]]] = {}


def register_theme(name: str, overrides: Callable[[], dict[str, Any]]) -> None:
    _REGISTRY[name] = overrides


def get_theme(name: str) -> dict[str, Any]:
    if name not in _REGISTRY:
        raise KeyError(f"unknown theme {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def list_themes() -> list[str]:
    return sorted(_REGISTRY)


def apply_theme(name: str) -> None:
    from ..core.style import apply_base_style
    overrides = get_theme(name)
    apply_base_style(theme=name, overrides=overrides)


def _autoload_themes() -> None:
    pkg = __name__
    for m in pkgutil.iter_modules(__path__):  # noqa: F821 (Python magic var)
        if m.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg}.{m.name}")


_autoload_themes()

__all__ = ["apply_theme", "get_theme", "list_themes", "register_theme"]
