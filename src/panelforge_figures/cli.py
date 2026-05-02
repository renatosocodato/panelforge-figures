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
    "--no-tags", is_flag=True,
    help=(
        "Emit Wave-1-shape index without `tags`, `scoring_rubric`, or "
        "`intake_questions` blocks.  Default is Wave-2 mode (with tags)."
    ),
)
def index_emit(out: Path, no_tags: bool) -> None:
    """Regenerate `recipes_index.json`."""
    include_tags = not no_tags
    p = emit_index_json(out, include_tags=include_tags)
    n = sum(len(m["recipes"]) for m in build_index(include_tags=include_tags)["modalities"])
    mode = "Wave-2" if include_tags else "Wave-1"
    click.echo(f"wrote {p}  ({n} recipes; {mode} mode)")


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


# ─────────────────────────── intake (Wave 2) ──────────────────────────

@main.command("intake")
@click.option(
    "--out", "out_path", type=click.Path(path_type=Path),
    default=Path("panelforge_workspace/profile.json"),
    help="Where to write the assembled ProjectProfile JSON.",
)
def intake_cmd(out_path: Path) -> None:
    """Run the 8-question interactive intake.

    Writes the resulting ProjectProfile to disk.  Use this profile
    with `figures generate` (Wave 3) to produce a ranked shortlist.
    """
    from .core.contract import list_modalities
    from .manifest import run_intake_interactive
    ensure_all_imported()
    available = tuple(list_modalities())
    profile = run_intake_interactive(
        available_modalities=available,
        pre_filled=None,
        out_path=out_path,
    )
    click.echo(f"\n✓ profile written to {out_path}")
    click.echo(
        f"  anchor={profile.manuscript_anchor}  "
        f"factorial={profile.factorial_design}  "
        f"equivalence={profile.equivalence_claims}  "
        f"shortlist_size={profile.shortlist_size}"
    )


# ─────────────────────────── autonomous flow (Wave 3) ──────────────────

@main.group("profile")
def profile_group() -> None:
    """Project-scan + intake helpers for the Claude Code autonomous flow."""


@profile_group.command("scan")
@click.option(
    "--project-root", "project_root",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=Path("."),
    help="Project directory to scan (default: cwd).",
)
@click.option(
    "--out", "out_path", type=click.Path(path_type=Path),
    default=Path("panelforge_workspace/profile.json"),
    help="Where to write the scan-derived ProjectProfile JSON.",
)
def profile_scan_cmd(project_root: Path, out_path: Path) -> None:
    """Scan README/manuscript/data/; pre-fill the 8 intake answers.

    Writes the inferred ProjectProfile + per-answer confidence scores
    to disk so downstream `figures intake` / `figures bridge` /
    `figures generate` can consume it.
    """
    from .core.contract import list_modalities
    from .manifest import (
        run_intake_interactive,
        scan_project,
        to_intake_pre_filled,
    )
    ensure_all_imported()
    available = tuple(list_modalities())
    result = scan_project(project_root, available_modalities=available)

    click.echo(f"scanned {project_root}: {len(result.files_read)} files read")
    for fname, ans in result.answers.items():
        click.echo(f"  {ans.label:24s}  {fname}: {ans.value!r:20s} (conf={ans.confidence:.2f})")

    pre_filled = to_intake_pre_filled(result)
    click.echo(f"\n{len(pre_filled)} of 8 fields meet ≥0.7 confidence; "
               "passing to intake")
    profile = run_intake_interactive(
        available_modalities=available,
        pre_filled=pre_filled,
        out_path=out_path,
    )
    click.echo(f"\n✓ profile written to {out_path}")
    click.echo(f"  anchor={profile.manuscript_anchor}  "
               f"factorial={profile.factorial_design}  "
               f"shortlist_size={profile.shortlist_size}")


@main.command("bridge")
@click.option(
    "--profile", "profile_path", type=click.Path(path_type=Path, exists=True),
    default=Path("panelforge_workspace/profile.json"),
)
@click.option(
    "--data-dir", type=click.Path(path_type=Path), default=Path("data"),
    help="Directory holding user data files (csv / parquet / npz).",
)
@click.option(
    "--out", "cache_path", type=click.Path(path_type=Path),
    default=Path("panelforge_workspace/data_bridge_cache.json"),
)
@click.option(
    "--no-llm", is_flag=True,
    help="Skip Pass-3 LLM fallback (use exact + fuzzy only).",
)
def bridge_cmd(
    profile_path: Path, data_dir: Path, cache_path: Path, no_llm: bool,
) -> None:
    """Bind user data columns to recipe contract fields (3-pass).

    Reads `panelforge_workspace/profile.json` for the shortlist
    derived from `figures profile scan` + `figures intake`, walks
    `data/`, runs Pass-1 exact → Pass-2 fuzzy → Pass-3 LLM (gated on
    ANTHROPIC_API_KEY env var; opt out with --no-llm).
    """
    from .manifest import (
        ProjectProfile,
        bind_shortlist_to_data,
        build_index,
        discover_data_files,
        score_recipes,
        write_bindings_cache,
    )

    raw = json.loads(profile_path.read_text())
    profile = ProjectProfile(
        manuscript_anchor=raw["manuscript_anchor"],
        factorial_design=raw["factorial_design"],
        equivalence_claims=raw["equivalence_claims"],
        dynamics_needed=raw["dynamics_needed"],
        dimensionality=raw["dimensionality"],
        modalities_in_scope=tuple(raw["modalities_in_scope"]),
        hard_filters=dict(raw["hard_filters"]),
        shortlist_size=int(raw["shortlist_size"]),
    )

    ensure_all_imported()
    idx = build_index(include_tags=True)
    flat = [
        {
            "modality": m["name"], "name": r["name"], "family": r["family"],
            "answers_question": r["answers_question"], "tags": r["tags"],
        }
        for m in idx["modalities"] for r in m["recipes"]
    ]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        scored = score_recipes(profile, flat)
    shortlist = [r.full_name for r in scored]
    click.echo(f"shortlist of {len(shortlist)} recipes from profile")

    files = discover_data_files(data_dir)
    click.echo(f"discovered {len(files)} data files in {data_dir}")

    bindings = bind_shortlist_to_data(
        shortlist=shortlist, data_files=files, use_llm=not no_llm,
    )
    n_bound = sum(1 for b in bindings if b.fully_bound)
    click.echo(f"bound {n_bound}/{len(bindings)} recipes")

    write_bindings_cache(bindings, cache_path)
    click.echo(f"✓ bindings written to {cache_path}")


@main.command("generate")
@click.option(
    "--bindings", "bindings_path", type=click.Path(path_type=Path, exists=True),
    default=Path("panelforge_workspace/data_bridge_cache.json"),
)
@click.option(
    "--data-dir", type=click.Path(path_type=Path), default=Path("data"),
)
@click.option(
    "--out-dir", type=click.Path(path_type=Path), default=Path("figures"),
)
def generate_cmd(bindings_path: Path, data_dir: Path, out_dir: Path) -> None:
    """Render bound recipes; write figures + RENDER_REPORT.md."""
    from .manifest import (
        discover_data_files,
        load_bindings_cache,
        render_shortlist,
        to_render_binding,
        to_render_data_files,
        write_render_report,
    )

    cache = load_bindings_cache(bindings_path)
    # Group by recipe full_name; this stub assumes one binding per recipe.
    by_recipe: dict[str, list] = {}
    for (full_name, _field), fb in cache.items():
        by_recipe.setdefault(full_name, []).append(fb)
    # Reconstruct RecipeBindings (canonical data_bridge shape).
    from .manifest.data_bridge import RecipeBinding as _RB
    rbs = []
    for fn, fbs in by_recipe.items():
        all_bound = all(fb.column_name is not None for fb in fbs)
        rbs.append(_RB(
            full_name=fn,
            bindings=tuple(fbs),
            fully_bound=all_bound,
            skipped_reason=None if all_bound else "unbound fields",
        ))
    files = discover_data_files(data_dir)
    log = render_shortlist(
        bindings=[to_render_binding(rb) for rb in rbs],
        data_files=to_render_data_files(files),
        out_dir=out_dir,
    )
    report_path = write_render_report(log)
    click.echo(
        f"\n✓ rendered {log.n_success}/{log.n_attempted} recipes "
        f"({log.n_skipped} skipped, {log.n_failed} failed)"
    )
    click.echo(f"  see {report_path}")


if __name__ == "__main__":
    main()
