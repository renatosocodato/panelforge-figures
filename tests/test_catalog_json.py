"""Catalog JSON shape + contents."""

import json
from pathlib import Path

from panelforge_figures.manifest import (
    build_catalog,
    catalog_fingerprint,
    write_catalog_json,
)


def test_catalog_structure_minimal():
    cat = build_catalog()
    assert "version" in cat
    assert "modalities" in cat
    assert "adapters" in cat
    assert "transforms" in cat
    assert "themes" in cat
    assert "palettes" in cat
    total = sum(len(m["recipes"]) for m in cat["modalities"])
    assert total >= 18


def test_catalog_recipe_has_required_metadata():
    cat = build_catalog()
    for mod in cat["modalities"]:
        for r in mod["recipes"]:
            for k in (
                "name",
                "path",
                "family",
                "answers_question",
                "required_fields",
                "alternatives_in_modality",
                "gallery_png",
            ):
                assert k in r, f"recipe {mod['name']}.{r.get('name')} missing key {k}"
            assert r["gallery_png"].startswith("docs/gallery/")


def test_catalog_fingerprint_is_stable_sha256():
    fp1 = catalog_fingerprint()
    fp2 = catalog_fingerprint()
    assert fp1 == fp2
    assert fp1.startswith("sha256:") and len(fp1) == len("sha256:") + 64


def test_write_catalog_json_roundtrip(tmp_path: Path):
    out = tmp_path / "catalog.json"
    write_catalog_json(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"]
    n_recipes = sum(len(m["recipes"]) for m in data["modalities"])
    assert n_recipes >= 18
