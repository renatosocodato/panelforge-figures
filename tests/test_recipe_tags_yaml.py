"""Tests for `docs/recipe_tags.yaml` — the manual tag override file.

Verifies bidirectional consistency vs the live registry:
  * Every YAML key is a real `{modality}.{name}` (no orphans).
  * YAML values use only closed-taxonomy tag values.
  * YAML is sorted by key (CI hygiene).
  * Closed-taxonomy enum validation (PR #57): typos like
    `anchor: DISCC1` raise `TagValidationError` with a clear message.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from panelforge_figures.core.contract import ensure_all_imported, list_recipes
from panelforge_figures.manifest.tag_taxonomy import (
    TagValidationError,
    validate_tag_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TAGS_YAML = REPO_ROOT / "docs" / "recipe_tags.yaml"

# Closed taxonomy values from the spec (RECIPE_DISCOVERY_SYSTEM.md §2.4).
VALID_ANCHOR = {"DISC1", "CDC42", "DISC1+CDC42", "RhoA", "RAC1", "generic"}
VALID_DIMENSIONALITY = {"2D", "3D", "1D", "scalar"}
VALID_DYNAMICS = {"static", "kymograph", "live", "ordered_pseudotime"}
VALID_WAVE = {
    "v1.0",
    "v1.1.0-beta-biophysics_scaling",
    "v1.2.0-beta-actin_microtubule_morphometry",
    "v1.3.0-beta-intravital_imaging",
    "v1.4.0-beta-cytoskeletal_morphometry_companion",
    "v1.5.0-beta-factorial_design_companion",
}


def _load_yaml() -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(TAGS_YAML.read_text()) or {}


def test_yaml_file_exists() -> None:
    assert TAGS_YAML.is_file(), f"recipe_tags.yaml not found at {TAGS_YAML}"


def test_yaml_has_at_least_50_entries() -> None:
    data = _load_yaml()
    assert len(data) >= 50, (
        f"recipe_tags.yaml only has {len(data)} entries; "
        "Wave 2 expects ≥50 (cdc42 + disc1 packs at minimum)"
    )


def test_no_orphan_keys() -> None:
    """Every YAML key must correspond to a registered recipe."""
    ensure_all_imported()
    registry = {f"{e.metadata.modality}.{e.metadata.name}" for e in list_recipes()}
    data = _load_yaml()
    orphans = set(data.keys()) - registry
    assert not orphans, f"YAML keys not in registry: {sorted(orphans)}"


def test_all_tag_values_in_closed_taxonomy() -> None:
    data = _load_yaml()
    for full_name, tags in data.items():
        if not isinstance(tags, dict):
            pytest.fail(f"{full_name}: tags must be a dict, got {type(tags)}")
        if "anchor" in tags:
            assert tags["anchor"] in VALID_ANCHOR, (
                f"{full_name}: invalid anchor '{tags['anchor']}'"
            )
        if "dimensionality" in tags:
            assert tags["dimensionality"] in VALID_DIMENSIONALITY, (
                f"{full_name}: invalid dimensionality '{tags['dimensionality']}'"
            )
        if "dynamics" in tags:
            assert tags["dynamics"] in VALID_DYNAMICS, (
                f"{full_name}: invalid dynamics '{tags['dynamics']}'"
            )
        if "wave" in tags:
            assert tags["wave"] in VALID_WAVE, (
                f"{full_name}: invalid wave '{tags['wave']}'"
            )
        for bool_key in (
            "factorial",
            "equivalence",
            "compartment_aware",
            "scale_aware",
        ):
            if bool_key in tags:
                assert isinstance(tags[bool_key], bool), (
                    f"{full_name}: {bool_key} must be bool, got {tags[bool_key]!r}"
                )


def test_yaml_sorted_by_key() -> None:
    """CI hygiene: YAML must be sorted alphabetically by key for clean
    diffs and predictable merge conflicts."""
    data = _load_yaml()
    keys = list(data.keys())
    sorted_keys = sorted(keys)
    if keys != sorted_keys:
        # Find the first out-of-order pair to make debugging easier.
        for i, (got, want) in enumerate(zip(keys, sorted_keys, strict=False)):
            if got != want:
                pytest.fail(
                    f"recipe_tags.yaml not sorted at line ~{i+1}: "
                    f"got '{got}' but expected '{want}'"
                )


def test_cdc42_pack_recipes_marked_factorial() -> None:
    """All 25 cdc42_factorial_companion recipes must have factorial=true."""
    data = _load_yaml()
    cdc42_keys = [
        k for k, v in data.items()
        if isinstance(v, dict) and v.get("wave") == "v1.5.0-beta-factorial_design_companion"
    ]
    assert len(cdc42_keys) >= 20, (
        f"expected ≥20 cdc42-pack entries; got {len(cdc42_keys)}"
    )
    for k in cdc42_keys:
        assert data[k].get("factorial") is True, (
            f"{k}: cdc42-pack recipe must have factorial=true"
        )


def test_disc1_pack_recipes_have_disc1_anchor() -> None:
    """All disc1_manuscript_companion recipes must have anchor=DISC1."""
    data = _load_yaml()
    disc1_keys = [
        k for k, v in data.items()
        if isinstance(v, dict) and v.get("wave") == "v1.4.0-beta-cytoskeletal_morphometry_companion"
    ]
    assert len(disc1_keys) >= 20, (
        f"expected ≥20 disc1-pack entries; got {len(disc1_keys)}"
    )
    for k in disc1_keys:
        assert data[k].get("anchor") == "DISC1", (
            f"{k}: disc1-pack recipe must have anchor=DISC1"
        )


# ───────────────────────── PR #57 enum validation ─────────────────────────


def test_validate_tag_dict_accepts_canonical_values() -> None:
    """Every valid combination of canonical taxonomy values passes."""
    for anchor in VALID_ANCHOR:
        for dim in VALID_DIMENSIONALITY:
            for dyn in VALID_DYNAMICS:
                for wave in VALID_WAVE:
                    validate_tag_dict({
                        "anchor": anchor,
                        "dimensionality": dim,
                        "dynamics": dyn,
                        "wave": wave,
                        "factorial": True,
                        "equivalence": False,
                        "compartment_aware": True,
                        "scale_aware": False,
                    })


def test_validate_tag_dict_accepts_unknown_sentinel() -> None:
    """The `"unknown"` sentinel is accepted for any string-valued tag."""
    for tag_name in ("anchor", "dimensionality", "dynamics", "wave"):
        validate_tag_dict({tag_name: "unknown"})
    # And mixed: some unknowns + some canonical values.
    validate_tag_dict({
        "anchor": "unknown",
        "dimensionality": "2D",
        "dynamics": "unknown",
        "wave": "v1.0",
    })


def test_validate_tag_dict_rejects_typo_anchor() -> None:
    """`anchor: 'DISCC1'` raises with allowed values listed."""
    with pytest.raises(TagValidationError) as excinfo:
        validate_tag_dict({"anchor": "DISCC1"})
    msg = str(excinfo.value)
    assert "DISCC1" in msg
    # Allowed values must be in the error.
    assert "'DISC1'" in msg
    assert "'CDC42'" in msg
    assert "'generic'" in msg
    assert "unknown" in msg


def test_validate_tag_dict_rejects_typo_dynamics() -> None:
    """`dynamics: 'stahtic'` raises with clear msg."""
    with pytest.raises(TagValidationError) as excinfo:
        validate_tag_dict({"dynamics": "stahtic"})
    msg = str(excinfo.value)
    assert "stahtic" in msg
    assert "'static'" in msg
    assert "'kymograph'" in msg
    assert "'live'" in msg


def test_validate_tag_dict_rejects_typo_wave() -> None:
    """`wave: 'v1.999'` raises."""
    with pytest.raises(TagValidationError) as excinfo:
        validate_tag_dict({"wave": "v1.999"})
    msg = str(excinfo.value)
    assert "v1.999" in msg
    assert "'v1.0'" in msg


def test_validate_tag_dict_rejects_non_bool_for_boolean_tag() -> None:
    """`factorial: 'yes'` raises (string is not a bool)."""
    with pytest.raises(TagValidationError) as excinfo:
        validate_tag_dict({"factorial": "yes"})
    msg = str(excinfo.value)
    assert "factorial" in msg
    assert "bool" in msg


def test_validate_tag_dict_includes_full_name_in_error() -> None:
    """Error message must include the offending YAML key."""
    full_name = "biophysics_scaling.compartment_paired_delta_scatter"
    with pytest.raises(TagValidationError) as excinfo:
        validate_tag_dict({"anchor": "DISCC1"}, full_name=full_name)
    assert full_name in str(excinfo.value)


def test_existing_yaml_validates_cleanly() -> None:
    """All entries in the live `docs/recipe_tags.yaml` must pass validation."""
    data = _load_yaml()
    for full_name, tags in data.items():
        if not isinstance(tags, dict):
            pytest.fail(f"{full_name}: tags must be a dict, got {type(tags)}")
        # If validation raises, the test fails with the YAML-key context
        # baked into the exception message.
        validate_tag_dict(tags, full_name=full_name)
