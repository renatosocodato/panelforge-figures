"""Gallery regeneration ships a PNG for every recipe."""

from pathlib import Path

from panelforge_figures.core.contract import ensure_all_imported, list_recipes
from panelforge_figures.gallery import regenerate_gallery


def test_gallery_regenerates_one_png_per_recipe(tmp_path: Path):
    ensure_all_imported()
    paths = regenerate_gallery(tmp_path)
    expected = {
        tmp_path / e.metadata.modality / f"{e.metadata.name}.png"
        for e in list_recipes()
    }
    assert set(paths) == expected
    for p in paths:
        assert p.stat().st_size > 0
