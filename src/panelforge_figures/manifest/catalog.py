"""Catalog generator — the single source of truth for the skill's proposals."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from .. import __version__
from ..adapters import list_adapters
from ..core.contract import (
    ensure_all_imported,
    list_modalities,
    list_recipes,
    modality_aesthetic,
    modality_description,
)
from ..core.palette import list_palettes, palettes
from ..transforms import list_transforms

log = logging.getLogger(__name__)


def build_catalog() -> dict[str, Any]:
    """Walk the registry and emit the JSON-ready catalog dict.

    Shape:
      {
        "version": str,
        "modalities": [{name, description, aesthetic, recipes: [...]}],
        "contracts": [...],
        "adapters": [...],
        "transforms": [...],
        "themes": [...],
        "palettes": [{name, n_colors, semantic_keys, description}]
      }
    """
    ensure_all_imported()

    from ..themes import list_themes

    mods: dict[str, dict[str, Any]] = {}
    for m in list_modalities():
        aesthetic = modality_aesthetic(m)
        mods[m] = {
            "name": m,
            "description": modality_description(m),
            "aesthetic": aesthetic.model_dump() if aesthetic is not None else None,
            "recipes": [],
        }

    for entry in list_recipes():
        meta = entry.metadata
        mod = mods.setdefault(
            meta.modality,
            {
                "name": meta.modality,
                "description": modality_description(meta.modality),
                "aesthetic": None,
                "recipes": [],
            },
        )
        mod["recipes"].append(
            {
                "name": meta.name,
                "path": entry.dotted_path,
                "contract": entry.contract.__name__,
                "family": meta.family.value,
                "answers_question": meta.answers_question,
                "required_fields": list(meta.required_fields),
                "optional_fields": list(meta.optional_fields),
                "alternatives_in_modality": list(meta.alternatives_in_modality),
                "file_format_hints": list(meta.file_format_hints),
                "n_points_typical": meta.n_points_typical,
                "gallery_png": f"docs/gallery/{meta.modality}/{meta.name}.png",
                "example_manifest": meta.example_manifest,
            }
        )

    for m in mods.values():
        m["recipes"].sort(key=lambda r: r["name"])

    palette_items = [
        {
            "name": p.name,
            "n_colors": len(p.colors),
            "semantic_keys": sorted(p.semantic.keys()),
            "description": p.description,
        }
        for p in palettes()
    ]

    catalog = {
        "version": __version__,
        "modalities": sorted(mods.values(), key=lambda m: m["name"]),
        "contracts": sorted({e.contract.__name__ for e in list_recipes()}),
        "adapters": list_adapters(),
        "transforms": list_transforms(),
        "themes": list_themes(),
        "palettes": palette_items,
    }
    return catalog


def catalog_fingerprint() -> str:
    """Stable sha256 of the catalog — put into manifests so resurvey can diff."""
    j = json.dumps(build_catalog(), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(j).hexdigest()


def write_catalog_json(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build_catalog(), indent=2, sort_keys=True), encoding="utf-8")
    log.debug("wrote catalog to %s", p)
    return p


def list_palette_names() -> list[str]:
    return list_palettes()
