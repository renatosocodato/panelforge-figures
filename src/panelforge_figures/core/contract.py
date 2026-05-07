"""Recipe contracts and registry.

Every recipe:
  - has a pydantic `RecipeContract` that validates the data it accepts,
  - declares the scientific question it answers and the modality it belongs to,
  - provides a `.demo_contract()` callable returning a realistic synthetic
    `RecipeContract` instance,
  - is registered in the global recipe registry via `@register_recipe(...)`,
  - is importable from `panelforge_figures.recipes.<modality>.<recipe>`.

The registry is the ground truth for the catalog — CLI and skill both read it.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from .statistical_contract import StatisticalContract

log = logging.getLogger(__name__)


class RecipeFamily(StrEnum):
    """Family tags drive the quality-gate rules in tests/quality_rules/."""

    split_violin = "split_violin"
    coef_forest = "coef_forest"
    phase_portrait = "phase_portrait"
    sobol_bar = "sobol_bar"
    bifurcation = "bifurcation"
    volcano = "volcano"
    timecourse_hierarchical_ci = "timecourse_hierarchical_ci"
    ridge_by_group = "ridge_by_group"
    hysteresis_loop = "hysteresis_loop"
    # Decorative / conceptual families — no strict geometry gate.
    conceptual = "conceptual"
    heatmap = "heatmap"
    radar = "radar"
    gantt = "gantt"
    flow = "flow"
    matrix = "matrix"
    contour = "contour"
    scatter_collapse = "scatter_collapse"
    ladder = "ladder"
    diagnostic_curve = "diagnostic_curve"


class RecipeContract(BaseModel):
    """Marker base class for recipe input contracts. Subclass per recipe."""

    model_config = {"arbitrary_types_allowed": True}


@dataclass(frozen=True)
class RecipeMetadata:
    """Every registered recipe exposes this metadata for the catalog."""

    name: str                          # module-local name, e.g. "phase_portrait_tristable"
    modality: str                      # modality module name, e.g. "rhogtpase_dynamics"
    family: RecipeFamily
    answers_question: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    file_format_hints: tuple[str, ...] = ()
    n_points_typical: str = ""
    alternatives_in_modality: tuple[str, ...] = ()
    example_manifest: str | None = None  # relative to repo root
    # Statistical-rigor contract (Sprint 1A). Default is all-permissive so
    # the 392 untagged recipes render unchanged. Per-recipe contracts are
    # the Tier-1 (cdc42 + disc1) migration target — see Build-C.
    statistical_contract: StatisticalContract = field(
        default_factory=lambda: StatisticalContract(),
        kw_only=True,
    )


@dataclass
class _RegistryEntry:
    metadata: RecipeMetadata
    dotted_path: str
    render: Callable[..., Any]
    contract: type[RecipeContract]
    demo_contract: Callable[[], RecipeContract]

    @property
    def full_name(self) -> str:
        return f"{self.metadata.modality}.{self.metadata.name}"


_REGISTRY: dict[str, _RegistryEntry] = {}
_MODALITY_DESCRIPTIONS: dict[str, str] = {}
_MODALITY_AESTHETICS: dict[str, Any] = {}


def register_recipe(
    *,
    metadata: RecipeMetadata,
    contract: type[RecipeContract],
    demo_contract: Callable[[], RecipeContract],
):
    """Decorator: mark a function as a renderer and register it.

    Example:
        @register_recipe(metadata=..., contract=MyInput, demo_contract=_demo)
        def render(contract: MyInput, ax=None, **kwargs): ...
    """
    def _decorator(fn):
        dotted = f"{fn.__module__}.{fn.__name__}"
        entry = _RegistryEntry(
            metadata=metadata,
            dotted_path=dotted,
            render=fn,
            contract=contract,
            demo_contract=demo_contract,
        )
        if entry.full_name in _REGISTRY:
            raise ValueError(f"duplicate recipe registration: {entry.full_name}")
        _REGISTRY[entry.full_name] = entry
        # Expose .demo_contract on the function itself for convenience.
        fn.demo_contract = demo_contract
        fn.metadata = metadata
        fn.contract_cls = contract
        log.debug("registered recipe %s", entry.full_name)
        return fn

    return _decorator


def register_modality(name: str, description: str, aesthetic: Any | None = None) -> None:
    """Modality registry — populated at import time by each modality's __init__."""
    _MODALITY_DESCRIPTIONS[name] = description
    if aesthetic is not None:
        _MODALITY_AESTHETICS[name] = aesthetic


def list_recipes() -> list[_RegistryEntry]:
    return list(_REGISTRY.values())


def list_modalities() -> list[str]:
    return sorted(_MODALITY_DESCRIPTIONS)


def get_recipe(full_name: str) -> _RegistryEntry:
    if full_name not in _REGISTRY:
        raise KeyError(f"unknown recipe: {full_name}")
    return _REGISTRY[full_name]


def modality_description(name: str) -> str:
    return _MODALITY_DESCRIPTIONS.get(name, "")


def modality_aesthetic(name: str) -> Any | None:
    return _MODALITY_AESTHETICS.get(name)


def ensure_all_imported() -> None:
    """Import every modality subpackage so decorators run. Idempotent."""
    from .. import recipes as _recipes_pkg  # noqa: F401
    pkg = importlib.import_module("panelforge_figures.recipes")
    if not hasattr(pkg, "__path__"):
        return
    import pkgutil
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.ispkg:
            importlib.import_module(f"panelforge_figures.recipes.{mod.name}")


def registry_counts() -> dict[str, int]:
    """Quick summary: {modality: recipe_count}."""
    counts: dict[str, int] = {}
    for e in _REGISTRY.values():
        counts[e.metadata.modality] = counts.get(e.metadata.modality, 0) + 1
    return counts
