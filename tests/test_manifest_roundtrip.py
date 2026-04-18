"""Manifest schema validates, YAML round-trip preserves structure, resolver validates."""

from __future__ import annotations

from pathlib import Path

import yaml

from panelforge_figures.manifest import (
    Manifest,
    load_manifest,
    validate_manifest,
)


def test_minimal_manifest_validates(tmp_path: Path):
    manifest_path = Path(__file__).parent / "fixtures" / "minimal.manifest.yaml"
    m = load_manifest(manifest_path)
    assert isinstance(m, Manifest)
    assert m.version == 1
    assert len(m.figures) == 1
    problems = validate_manifest(manifest_path, check_data=True)
    assert problems == [], f"unexpected problems: {problems}"


def test_roundtrip_yaml_preserves_recipe_names(tmp_path: Path):
    src = Path(__file__).parent / "fixtures" / "minimal.manifest.yaml"
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    out = tmp_path / "round.yaml"
    out.write_text(yaml.safe_dump(data), encoding="utf-8")
    m = load_manifest(out)
    assert m.figures[0].panels[0].recipe.endswith("sobol_first_total_pair")


def test_validate_rejects_unknown_recipe(tmp_path: Path):
    bad_manifest = tmp_path / "bad.yaml"
    bad_manifest.write_text(
        "version: 1\n"
        "theme: default\n"
        "palette: okabe_ito\n"
        "figures:\n"
        "  - id: fig\n"
        "    size: single\n"
        "    panels:\n"
        "      - id: A\n"
        "        recipe: sensitivity_analysis.does_not_exist\n"
        "        data:\n"
        "          source: __passthrough__\n"
        "          adapter: passthrough\n",
        encoding="utf-8",
    )
    problems = validate_manifest(bad_manifest, check_data=False)
    assert any("unknown recipe" in p for p in problems)
