"""Transforms: declarative data reshaping applied between adapter and recipe."""

from .aggregate import aggregate_group
from .derive import derive_columns
from .join import left_join, merge_on
from .reshape import melt_long, pivot_wide

_REGISTRY = {
    "melt_long": melt_long,
    "pivot_wide": pivot_wide,
    "aggregate_group": aggregate_group,
    "left_join": left_join,
    "merge_on": merge_on,
    "derive_columns": derive_columns,
}


def get_transform(name: str):
    if name not in _REGISTRY:
        raise KeyError(f"unknown transform {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_transforms() -> list[str]:
    return sorted(_REGISTRY)


__all__ = [
    "aggregate_group",
    "derive_columns",
    "get_transform",
    "left_join",
    "list_transforms",
    "melt_long",
    "merge_on",
    "pivot_wide",
]
