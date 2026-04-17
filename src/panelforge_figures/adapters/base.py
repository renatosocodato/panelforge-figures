"""Adapter protocol and registry."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Protocol

log = logging.getLogger(__name__)


class AdapterProtocol(Protocol):
    def __call__(self, source: str | Path, **options: Any) -> Any: ...


_REGISTRY: dict[str, Callable[..., Any]] = {}


class AdapterRegistry:
    @staticmethod
    def register(name: str, fn: Callable[..., Any]) -> None:
        if name in _REGISTRY:
            raise ValueError(f"adapter {name!r} already registered")
        _REGISTRY[name] = fn

    @staticmethod
    def get(name: str) -> Callable[..., Any]:
        if name not in _REGISTRY:
            raise KeyError(f"unknown adapter {name!r}; known: {sorted(_REGISTRY)}")
        return _REGISTRY[name]

    @staticmethod
    def names() -> list[str]:
        return sorted(_REGISTRY)


def register_adapter(name: str, fn: Callable[..., Any]) -> None:
    AdapterRegistry.register(name, fn)


def get_adapter(name: str) -> Callable[..., Any]:
    return AdapterRegistry.get(name)


def list_adapters() -> list[str]:
    return AdapterRegistry.names()


def load_local_adapter(name: str, search_root: str | Path = ".") -> Callable[..., Any]:
    """Load `figures/adapters/local/<name>.py` from a manuscript repo.

    The module must define a callable named `load` with signature
    `(source, **options) -> dict | DataFrame`. Returns that callable.
    """
    path = Path(search_root) / "figures" / "adapters" / "local" / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"local adapter not found: {path}")
    spec = importlib.util.spec_from_file_location(f"local.{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load local adapter spec: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "load") or not callable(mod.load):
        raise ImportError(f"local adapter {path} must define a callable `load`")
    log.debug("loaded local adapter %s from %s", name, path)
    return mod.load
