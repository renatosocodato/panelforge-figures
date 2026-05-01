"""Catalog generator — the single source of truth for the skill's proposals.

Two flavours of catalog are emitted:

- `build_catalog()` / `write_catalog_json()` — the original, full programmatic
  catalog used by the `figures catalog --json` command.
- `build_index()` / `emit_index_json()` — the agent-facing index landing at
  repo-root `recipes_index.json`.  In Wave 1 it is a near-superset of the
  catalog with additional `built_at`, `git_commit`, `n_recipes`, and
  `schema_version` fields.  Wave 2 adds `tags`, `scoring_rubric`, and
  `intake_questions` blocks (controlled by `include_tags=True`).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from datetime import UTC, datetime
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
    registry_counts,
)
from ..core.palette import list_palettes, palettes
from ..transforms import list_transforms

log = logging.getLogger(__name__)


# Schema version of the agent-facing index (`recipes_index.json`).  Bumped on
# breaking changes: field rename, type change, removal.  Additive changes
# (new optional fields) do not bump the version.
INDEX_SCHEMA_VERSION = "1.0.0"


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


# ─────────────────────────── recipes_index.json ────────────────────────────


def _git_commit() -> str:
    """Return the current commit SHA, or 'unknown' when not in a git tree.

    Allows override via `PANELFORGE_GIT_COMMIT` env var (used by CI builds
    that may run outside `git`).  Reads only `git rev-parse HEAD`; never
    mutates the working tree.
    """
    env = os.environ.get("PANELFORGE_GIT_COMMIT")
    if env:
        return env.strip()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=2,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


def _now_iso_utc() -> str:
    """ISO-8601 UTC timestamp truncated to seconds (deterministic per second).

    Allows override via `PANELFORGE_BUILT_AT` env var so CI / tests can
    force a stable value.
    """
    env = os.environ.get("PANELFORGE_BUILT_AT")
    if env:
        return env.strip()
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_index(*, include_tags: bool = False) -> dict[str, Any]:
    """Build the agent-facing `recipes_index.json` content.

    Wave 1 (default `include_tags=False`): a superset of `build_catalog()`
    with an `index_meta` block (`schema_version`, `panelforge_version`,
    `git_commit`, `built_at`, `n_recipes`, `n_modalities`).

    Wave 2 (`include_tags=True`): adds per-recipe `tags`, top-level
    `scoring_rubric`, and `intake_questions` blocks.  Wave 1 callers
    receive an empty `tags: {}` placeholder per recipe so downstream
    schema can stay forward-compatible.
    """
    catalog = build_catalog()
    counts = registry_counts()

    # Per-recipe tag scaffolding.  Wave 1 emits empty dicts; Wave 2 will
    # populate from `auto_tag.py` + `docs/recipe_tags.yaml` override.
    for mod in catalog["modalities"]:
        mod["n_recipes"] = len(mod["recipes"])
        for rec in mod["recipes"]:
            rec["tags"] = {} if not include_tags else rec.get("tags", {})

    index = {
        "index_meta": {
            "schema_version": INDEX_SCHEMA_VERSION,
            "panelforge_version": __version__,
            "git_commit": _git_commit(),
            "built_at": _now_iso_utc(),
            "n_recipes": sum(counts.values()),
            "n_modalities": len(counts),
            "tags_enabled": include_tags,
        },
        "version": catalog["version"],
        "modalities": catalog["modalities"],
        "contracts": catalog["contracts"],
        "adapters": catalog["adapters"],
        "transforms": catalog["transforms"],
        "themes": catalog["themes"],
        "palettes": catalog["palettes"],
    }

    # Wave-2 placeholders surfaced at the top level so JSON-Schema can
    # reserve the keys today.  Empty dicts in Wave 1; populated in Wave 2.
    if include_tags:
        # Wave 2 will fill these from `manifest/scoring.py` + `intake.py`.
        index["scoring_rubric"] = {}
        index["intake_questions"] = []

    return index


def emit_index_json(
    path: str | Path = "recipes_index.json",
    *,
    include_tags: bool = False,
) -> Path:
    """Write `recipes_index.json` to disk (default: repo root).

    The output is sorted, indent=2, with deterministic keys so a CI
    `git diff --exit-code` after regeneration catches drift.

    **Stable-headers convention.**  When the output path resolves to
    `recipes_index.json` (the canonical committed location), this
    function auto-sets `PANELFORGE_BUILT_AT="1970-01-01T00:00:00Z"`
    and `PANELFORGE_GIT_COMMIT="committed"` for the duration of the
    call so contributors don't need env-var discipline when
    regenerating the committed file.  Custom paths get live values.
    """
    p = Path(path)
    if p.parent != Path("") and p.parent != Path("."):
        p.parent.mkdir(parents=True, exist_ok=True)

    is_committed_index = p.name == "recipes_index.json"
    saved_built_at = os.environ.get("PANELFORGE_BUILT_AT")
    saved_git_commit = os.environ.get("PANELFORGE_GIT_COMMIT")
    try:
        if is_committed_index:
            # Caller may have set these explicitly; honour the override.
            os.environ.setdefault("PANELFORGE_BUILT_AT", "1970-01-01T00:00:00Z")
            os.environ.setdefault("PANELFORGE_GIT_COMMIT", "committed")
        p.write_text(
            json.dumps(
                build_index(include_tags=include_tags),
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
    finally:
        # Restore any pre-existing env values exactly.
        if is_committed_index:
            if saved_built_at is None:
                os.environ.pop("PANELFORGE_BUILT_AT", None)
            else:
                os.environ["PANELFORGE_BUILT_AT"] = saved_built_at
            if saved_git_commit is None:
                os.environ.pop("PANELFORGE_GIT_COMMIT", None)
            else:
                os.environ["PANELFORGE_GIT_COMMIT"] = saved_git_commit
    log.debug("wrote recipes_index to %s", p)
    return p
