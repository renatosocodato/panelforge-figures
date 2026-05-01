"""`figures` CLI — Click-based, non-interactive, scriptable."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from . import __version__
from .adapters import list_adapters
from .core.contract import (
    ensure_all_imported,
    get_recipe,
    list_recipes,
    modality_description,
    registry_counts,
)
from .core.palette import list_palettes
from .manifest import (
    build_catalog,
    build_index,
    catalog_fingerprint,
    emit_index_json,
    render_manifest,
    validate_manifest,
    write_catalog_json,
)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


@click.group(help="panelforge-figures — publication-grade figures from a declarative manifest.")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.version_option(__version__, prog_name="figures")
def main(verbose: bool) -> None:
    _setup_logging(verbose)


# ─────────────────────────── render / validate ───────────────────────────

@main.command()
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path),
                default=Path("figures.manifest.yaml"), required=False)
@click.option("--search-root", type=click.Path(path_type=Path), default=Path("."),
              help="Root for resolving local adapters and data paths.")
def render(manifest: Path, search_root: Path) -> None:
    """Render all figures per MANIFEST (default: figures.manifest.yaml)."""
    paths = render_manifest(manifest, search_root=search_root)
    click.echo(f"rendered {len(paths)} output files")
    for p in paths:
        click.echo(f"  {p}")


@main.command()
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path),
                default=Path("figures.manifest.yaml"), required=False)
@click.option("--search-root", type=click.Path(path_type=Path), default=Path("."))
@click.option("--skip-data", is_flag=True, help="Skip data-load check.")
def validate(manifest: Path, search_root: Path, skip_data: bool) -> None:
    """Validate MANIFEST: schema + recipes + (optional) data availability."""
    problems = validate_manifest(manifest, search_root=search_root, check_data=not skip_data)
    if problems:
        for p in problems:
            click.echo(f"✗ {p}", err=True)
        sys.exit(1)
    click.echo("✓ manifest is valid")


# ──────────────────────────── catalog ────────────────────────────────────

@main.command("catalog")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--by", type=click.Choice(["modality", "family"]), default="modality",
              help="Group recipes in the human-readable view.")
def catalog_cmd(as_json: bool, by: str) -> None:
    """Emit the recipe catalog."""
    ensure_all_imported()
    cat = build_catalog()
    if as_json:
        click.echo(json.dumps(cat, indent=2, sort_keys=True))
        return
    click.echo(f"panelforge-figures {cat['version']}")
    click.echo(f"fingerprint: {catalog_fingerprint()}")
    click.echo(f"themes: {', '.join(cat['themes'])}")
    click.echo(f"palettes: {', '.join(p['name'] for p in cat['palettes'])}")
    click.echo(f"adapters: {', '.join(cat['adapters'])}")
    click.echo(f"transforms: {', '.join(cat['transforms'])}")
    click.echo("")
    if by == "modality":
        for m in cat["modalities"]:
            click.echo(f"  {m['name']}  ({len(m['recipes'])} recipes)")
            if m["description"]:
                click.echo(f"      {m['description']}")
            for r in m["recipes"]:
                click.echo(f"      - {r['name']}  [{r['family']}]")
    else:
        by_family: dict[str, list] = {}
        for m in cat["modalities"]:
            for r in m["recipes"]:
                by_family.setdefault(r["family"], []).append((m["name"], r["name"]))
        for fam in sorted(by_family):
            click.echo(f"  {fam}  ({len(by_family[fam])} recipes)")
            for mod, name in sorted(by_family[fam]):
                click.echo(f"      - {mod}.{name}")


# ─────────────────────────── listing helpers ────────────────────────────

@main.command("list-recipes")
@click.option("--by-modality", is_flag=True, help="Group by modality.")
@click.option("--family", type=str, default=None, help="Filter by family name.")
def list_recipes_cmd(by_modality: bool, family: str | None) -> None:
    ensure_all_imported()
    entries = list_recipes()
    if family:
        entries = [e for e in entries if e.metadata.family.value == family]
    if by_modality:
        by: dict[str, list] = {}
        for e in entries:
            by.setdefault(e.metadata.modality, []).append(e)
        for mod in sorted(by):
            click.echo(f"{mod}")
            for e in sorted(by[mod], key=lambda x: x.metadata.name):
                click.echo(f"  {e.metadata.name}")
    else:
        for e in sorted(entries, key=lambda x: (x.metadata.modality, x.metadata.name)):
            click.echo(f"{e.metadata.modality}.{e.metadata.name}")


@main.command("list-adapters")
def list_adapters_cmd() -> None:
    for name in list_adapters():
        click.echo(name)


@main.command("list-themes")
def list_themes_cmd() -> None:
    from .themes import list_themes
    for name in list_themes():
        click.echo(name)


@main.command("list-palettes")
def list_palettes_cmd() -> None:
    for name in list_palettes():
        click.echo(name)


# ─────────────────────────── introspection ──────────────────────────────

@main.command("show-recipe")
@click.argument("name")
def show_recipe_cmd(name: str) -> None:
    ensure_all_imported()
    entry = get_recipe(name)
    click.echo(f"{entry.full_name}")
    click.echo(f"  path     : {entry.dotted_path}")
    click.echo(f"  family   : {entry.metadata.family.value}")
    click.echo(f"  question : {entry.metadata.answers_question}")
    click.echo(f"  required : {', '.join(entry.metadata.required_fields)}")
    if entry.metadata.optional_fields:
        click.echo(f"  optional : {', '.join(entry.metadata.optional_fields)}")
    if entry.metadata.alternatives_in_modality:
        click.echo(f"  alts     : {', '.join(entry.metadata.alternatives_in_modality)}")
    doc = (entry.render.__doc__ or "").strip()
    if doc:
        click.echo("")
        click.echo(doc)


@main.command("show-modality")
@click.argument("name")
def show_modality_cmd(name: str) -> None:
    ensure_all_imported()
    click.echo(f"{name}")
    click.echo(f"  {modality_description(name)}")
    recipes = [e for e in list_recipes() if e.metadata.modality == name]
    for e in sorted(recipes, key=lambda x: x.metadata.name):
        click.echo(f"  - {e.metadata.name}: {e.metadata.answers_question}")


# ─────────────────────────── gallery ────────────────────────────────────

@main.group()
def gallery() -> None:
    """Manage the committed gallery under docs/gallery/."""


@gallery.command("regenerate")
@click.option("--out", type=click.Path(path_type=Path), default=Path("docs/gallery"))
def gallery_regenerate(out: Path) -> None:
    from .gallery.generator import regenerate_gallery
    paths = regenerate_gallery(out)
    click.echo(f"regenerated {len(paths)} gallery PNGs under {out}")


@gallery.command("diff")
@click.option("--root", type=click.Path(path_type=Path), default=Path("docs/gallery"))
@click.option("--threshold", type=float, default=0.02, help="L1 diff threshold (0-1).")
def gallery_diff(root: Path, threshold: float) -> None:
    from .gallery.generator import diff_gallery
    diffs = diff_gallery(root, threshold=threshold)
    if not diffs:
        click.echo("✓ no gallery drift above threshold")
        return
    for name, d in diffs:
        click.echo(f"  {name}: L1={d:.4f}")


# ─────────────────────────── misc ───────────────────────────────────────

@main.command("write-catalog")
@click.option("--out", type=click.Path(path_type=Path), default=Path("catalog.json"))
def write_catalog_cmd(out: Path) -> None:
    write_catalog_json(out)
    click.echo(f"wrote {out}")


@main.command()
def stats() -> None:
    ensure_all_imported()
    counts = registry_counts()
    total = sum(counts.values())
    click.echo(f"recipes: {total}  modalities: {len(counts)}")
    for mod in sorted(counts):
        click.echo(f"  {mod}: {counts[mod]}")


# ─────────────────────────── recipes_index.json ─────────────────────────

@main.group("index")
def index_group() -> None:
    """Manage the agent-facing `recipes_index.json` (Wave 1+).

    The index is a single JSON file at the repo root that any CLI agent
    can fetch via raw GitHub URL without cloning the repo.  See
    `AGENT_BOOTSTRAP.md` for the agent contract.
    """


@index_group.command("emit")
@click.option(
    "--out", type=click.Path(path_type=Path), default=Path("recipes_index.json"),
    help="Path to write the index (default: repo root).",
)
@click.option(
    "--include-tags", is_flag=True,
    help=(
        "Wave-2 mode: emit per-recipe tags + scoring_rubric + "
        "intake_questions blocks.  Wave 1 callers should leave this off."
    ),
)
def index_emit(out: Path, include_tags: bool) -> None:
    """Regenerate `recipes_index.json`."""
    p = emit_index_json(out, include_tags=include_tags)
    n = sum(len(m["recipes"]) for m in build_index(include_tags=include_tags)["modalities"])
    click.echo(f"wrote {p}  ({n} recipes)")


@index_group.command("validate")
@click.option(
    "--path", "index_path", type=click.Path(path_type=Path),
    default=Path("recipes_index.json"),
)
@click.option(
    "--schema", "schema_path", type=click.Path(path_type=Path),
    default=Path("docs/recipes_index.schema.json"),
)
def index_validate(index_path: Path, schema_path: Path) -> None:
    """Validate `recipes_index.json` against the JSON-Schema and the registry.

    Checks:
      1. Index file exists and is valid JSON.
      2. Schema file exists and is valid JSON-Schema.
      3. Every recipe in the registry appears in the index.
      4. Every recipe in the index appears in the registry (no orphans).
      5. The `index_meta.panelforge_version` matches the installed package.
    """
    if not index_path.is_file():
        click.echo(f"✗ {index_path} not found", err=True)
        sys.exit(1)
    try:
        index = json.loads(index_path.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"✗ {index_path} is not valid JSON: {e}", err=True)
        sys.exit(1)

    # Optional jsonschema dep for full validation; degrade gracefully.
    if schema_path.is_file():
        try:
            import jsonschema  # type: ignore[import-not-found]
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(instance=index, schema=schema)
        except ImportError:
            click.echo(
                "ⓘ jsonschema not installed; skipping schema validation "
                "(install via `pip install jsonschema` for strict checks)",
                err=True,
            )
        except jsonschema.ValidationError as e:  # type: ignore[name-defined]
            click.echo(f"✗ schema violation: {e.message}", err=True)
            sys.exit(1)

    # Registry parity.
    ensure_all_imported()
    registry_full_names = {f"{e.metadata.modality}.{e.metadata.name}"
                           for e in list_recipes()}
    index_full_names = set()
    for mod in index.get("modalities", []):
        for rec in mod.get("recipes", []):
            index_full_names.add(f"{mod['name']}.{rec['name']}")

    missing_in_index = registry_full_names - index_full_names
    orphan_in_index = index_full_names - registry_full_names
    if missing_in_index:
        click.echo(
            f"✗ {len(missing_in_index)} recipes registered but missing from index:",
            err=True,
        )
        for n in sorted(missing_in_index):
            click.echo(f"    - {n}", err=True)
        sys.exit(1)
    if orphan_in_index:
        click.echo(
            f"✗ {len(orphan_in_index)} recipes in index but not registered:",
            err=True,
        )
        for n in sorted(orphan_in_index):
            click.echo(f"    - {n}", err=True)
        sys.exit(1)

    pkg_version = index.get("index_meta", {}).get("panelforge_version", "")
    if pkg_version != __version__:
        click.echo(
            f"⚠ index built with panelforge {pkg_version} but installed "
            f"package is {__version__}",
            err=True,
        )

    n = len(index_full_names)
    click.echo(f"✓ {index_path} valid  ({n} recipes; schema_version "
               f"{index.get('index_meta', {}).get('schema_version', '?')})")


if __name__ == "__main__":
    main()
