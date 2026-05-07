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


def _load_recipe_tags_yaml(yaml_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load `docs/recipe_tags.yaml` if it exists.  Returns empty dict
    when the file is absent (Wave 1) or PyYAML is missing (graceful
    degradation; auto-tagger fills the gap).

    Validates each entry against the closed-taxonomy enums in
    `tag_taxonomy.py`.  A typo like `anchor: DISCC1` raises
    `TagValidationError` here — catching the bug at YAML-parse time
    rather than later at JSON-Schema validation in `emit_index_json`.
    """
    if yaml_path is None:
        yaml_path = (
            Path(__file__).resolve().parents[3] / "docs" / "recipe_tags.yaml"
        )
    if not yaml_path.is_file():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover  pyyaml is in core deps
        return {}
    raw = yaml.safe_load(yaml_path.read_text()) or {}
    if not isinstance(raw, dict):  # pragma: no cover
        return {}

    # validate_tag_dict already encodes `full_name` in its TagValidationError
    # message, so we let it propagate directly — no need for try/except.
    from .tag_taxonomy import validate_tag_dict
    for full_name, tag_dict in raw.items():
        if not isinstance(tag_dict, dict):
            continue  # let downstream catch shape errors
        validate_tag_dict(tag_dict, full_name=full_name)
    return raw


def _merge_tags(
    auto: dict[str, Any],
    override: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """Merge auto-tags with YAML override.  Override wins per key.

    Returns `(merged_tags, source)` where `source ∈ {"auto", "override",
    "merged"}`.  The 8-key closed taxonomy is preserved.
    """
    if not override:
        return dict(auto), "auto"
    merged: dict[str, Any] = dict(auto)
    fully_overridden = True
    for key, val in override.items():
        # `unknown` sentinels in `auto` get freely overridden.
        if merged.get(key) != val and merged.get(key) != "unknown":
            fully_overridden = False
        merged[key] = val
    return merged, ("override" if fully_overridden else "merged")


def build_index(*, include_tags: bool = False) -> dict[str, Any]:
    """Build the agent-facing `recipes_index.json` content.

    Wave 1 (default `include_tags=False`): a superset of `build_catalog()`
    with an `index_meta` block (`schema_version`, `panelforge_version`,
    `git_commit`, `built_at`, `n_recipes`, `n_modalities`).

    Wave 2 (`include_tags=True`): adds per-recipe `tags` (auto-tagger +
    `docs/recipe_tags.yaml` override + `tags_source` provenance), top-
    level `scoring_rubric`, and `intake_questions` blocks.
    """
    catalog = build_catalog()
    counts = registry_counts()

    if include_tags:
        from .auto_tag import auto_tag_recipe
        overrides = _load_recipe_tags_yaml()
    else:
        overrides = {}

    # Per-recipe tag scaffolding.  Wave 1 emits empty dicts; Wave 2 fills
    # from auto-tagger + YAML override.
    for mod in catalog["modalities"]:
        mod["n_recipes"] = len(mod["recipes"])
        for rec in mod["recipes"]:
            if not include_tags:
                rec["tags"] = {}
                continue
            full_name = f"{mod['name']}.{rec['name']}"
            auto_tags = auto_tag_recipe(
                name=rec["name"],
                modality=mod["name"],
                family=rec["family"],
                answers_question=rec["answers_question"],
                required_fields=tuple(rec.get("required_fields", ())),
                optional_fields=tuple(rec.get("optional_fields", ())),
            )
            override_tags = overrides.get(full_name)
            merged, source = _merge_tags(auto_tags, override_tags)
            rec["tags"] = merged
            rec["tags_source"] = source

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

    # Wave-2 blocks at the top level — agents read these once at the top
    # of the index rather than per-recipe.
    if include_tags:
        from .intake import intake_questions_for_index
        from .scoring import scoring_rubric_dict
        index["scoring_rubric"] = scoring_rubric_dict()
        index["intake_questions"] = intake_questions_for_index()

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
