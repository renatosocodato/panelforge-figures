"""Tests for `docs/recipes_index.schema.json` (JSON-Schema for the index).

Verifies:
  * The schema file itself is valid JSON-Schema (loads + parses).
  * `build_index()` output validates against the schema (Wave-1 mode).
  * `build_index(include_tags=True)` also validates (Wave-2-mode preview).
  * The committed `recipes_index.json` validates against the schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from panelforge_figures.manifest import build_index


def _load_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    p = repo_root / "docs" / "recipes_index.schema.json"
    return json.loads(p.read_text())


def test_schema_file_exists() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    p = repo_root / "docs" / "recipes_index.schema.json"
    assert p.is_file(), f"schema not found at {p}"


def test_schema_is_valid_jsonschema_dialect_2020_12() -> None:
    pytest.importorskip("jsonschema")
    import jsonschema

    schema = _load_schema()
    assert schema.get("$schema", "").endswith("draft/2020-12/schema")
    # Validate the schema itself against its meta-schema.
    jsonschema.Draft202012Validator.check_schema(schema)


def test_build_index_wave1_validates_against_schema() -> None:
    pytest.importorskip("jsonschema")
    import jsonschema

    schema = _load_schema()
    idx = build_index(include_tags=False)
    jsonschema.validate(instance=idx, schema=schema)


def test_build_index_wave2_validates_against_schema() -> None:
    """Wave 2 turns on tags + scoring_rubric + intake_questions; the
    schema must still validate."""
    pytest.importorskip("jsonschema")
    import jsonschema

    schema = _load_schema()
    idx = build_index(include_tags=True)
    jsonschema.validate(instance=idx, schema=schema)


def test_committed_index_validates_against_schema() -> None:
    pytest.importorskip("jsonschema")
    import jsonschema

    repo_root = Path(__file__).resolve().parents[1]
    p = repo_root / "recipes_index.json"
    if not p.is_file():
        pytest.skip("recipes_index.json not committed yet (Wave 1 in progress)")
    schema = _load_schema()
    idx = json.loads(p.read_text())
    jsonschema.validate(instance=idx, schema=schema)
