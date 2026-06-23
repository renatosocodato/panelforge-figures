"""Closed-taxonomy enum classes for recipe tags.

Used by `manifest/catalog.py:_load_recipe_tags_yaml` to validate
`docs/recipe_tags.yaml` entries at parse time.  Catching typos here
(e.g. `anchor: DISCC1` instead of `DISC1`) gives a clearer error than
JSON-Schema validation at index-emit time.

The `unknown` sentinel is also accepted — the auto-tagger emits it
for low-confidence inferences, and the merge function in `catalog.py`
flows auto-tagger output through the same validation path.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

__all__ = [
    "UNKNOWN_SENTINEL",
    "TAG_ENUMS",
    "BOOL_TAGS",
    "TagAnchor",
    "TagDimensionality",
    "TagDynamics",
    "TagWave",
    "TagValidationError",
    "validate_tag",
    "validate_tag_dict",
]

# Sentinel for tags the auto-tagger could not infer.
UNKNOWN_SENTINEL: str = "unknown"


class TagAnchor(StrEnum):
    DISC1 = "DISC1"
    CDC42 = "CDC42"
    DISC1_CDC42 = "DISC1+CDC42"
    RhoA = "RhoA"
    RAC1 = "RAC1"
    GENERIC = "generic"


class TagDimensionality(StrEnum):
    TWO_D = "2D"
    THREE_D = "3D"
    ONE_D = "1D"
    SCALAR = "scalar"


class TagDynamics(StrEnum):
    STATIC = "static"
    KYMOGRAPH = "kymograph"
    LIVE = "live"
    ORDERED_PSEUDOTIME = "ordered_pseudotime"


class TagWave(StrEnum):
    V1_0 = "v1.0"
    V1_1_0_BIOPHYSICS = "v1.1.0-beta-biophysics_scaling"
    V1_2_0_ACTIN_MT = "v1.2.0-beta-actin_microtubule_morphometry"
    V1_3_0_INTRAVITAL = "v1.3.0-beta-intravital_imaging"
    V1_4_0_CYTOSKELETAL = "v1.4.0-beta-cytoskeletal_morphometry_companion"
    V1_5_0_FACTORIAL = "v1.5.0-beta-factorial_design_companion"


# Map tag-name → enum class (for validation lookup).
TAG_ENUMS: dict[str, type[StrEnum]] = {
    "anchor": TagAnchor,
    "dimensionality": TagDimensionality,
    "dynamics": TagDynamics,
    "wave": TagWave,
}

BOOL_TAGS: frozenset[str] = frozenset({
    "factorial", "equivalence", "compartment_aware", "scale_aware",
})


class TagValidationError(ValueError):
    """Raised when a YAML override has an out-of-taxonomy tag value."""


def validate_tag(
    tag_name: str,
    value: Any,
    *,
    full_name: str | None = None,
) -> None:
    """Validate one tag value against the closed taxonomy.

    Accepts:
      - the canonical enum string for {anchor, dimensionality, dynamics, wave}
      - `"unknown"` sentinel for any string-valued tag
      - True / False for boolean tags
    Raises:
      TagValidationError with a message citing the offending key + value
      + allowed values.
    """
    if tag_name in BOOL_TAGS:
        # Accept the auto-tagger sentinel for boolean tags too — keeps the
        # validator symmetric across enum-tags and bool-tags so future
        # callers (e.g. validating auto-tagger output) don't trip.
        if value == UNKNOWN_SENTINEL:
            return
        if not isinstance(value, bool):
            ctx = f"{full_name}." if full_name else ""
            raise TagValidationError(
                f"{ctx}{tag_name}: expected bool, got {value!r} "
                f"({type(value).__name__})"
            )
        return
    if tag_name in TAG_ENUMS:
        if value == UNKNOWN_SENTINEL:
            return
        enum_cls = TAG_ENUMS[tag_name]
        try:
            enum_cls(value)
        except ValueError:
            allowed = ", ".join(repr(m.value) for m in enum_cls)
            ctx = f"{full_name}." if full_name else ""
            raise TagValidationError(
                f"{ctx}{tag_name}: invalid value {value!r}.  "
                f"Allowed: {allowed} (or {UNKNOWN_SENTINEL!r}).",
            ) from None
        return
    # Unknown tag name → silently skip (forward-compat for new tags).


def validate_tag_dict(
    tags: dict[str, Any],
    *,
    full_name: str | None = None,
) -> None:
    """Validate every key/value in a tag dict.  Raises on first failure."""
    for key, val in tags.items():
        validate_tag(key, val, full_name=full_name)
