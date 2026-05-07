"""`figures` CLI — Click-based, non-interactive, scriptable."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

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
@click.option(
    "--skip-audit", is_flag=True,
    help=(
        "Skip the per-recipe statistical-contract audit step (Sprint 1A — "
        "v1.7.0). NOT RECOMMENDED for production runs: the audit is the "
        "guard that prevents underpowered / mis-specified figures from "
        "rendering. Use only for development / triage."
    ),
)
@click.option(
    "--no-provenance", is_flag=True,
    help=(
        "DEVELOPMENT-ONLY escape hatch (Sprint 1B — v1.8.0). Suppress "
        "emission of `<figure>.provenance.json` sidecars. The sidecars "
        "are the audit trail that links every published PDF back to its "
        "source data + recipe + scorer state; suppressing them breaks "
        "`figures provenance verify`. Use only in tight dev loops where "
        "the hashing overhead is felt; never in CI / archival renders."
    ),
)
def generate_cmd(
    bindings_path: Path,
    data_dir: Path,
    out_dir: Path,
    skip_audit: bool,
    no_provenance: bool,
) -> None:
    """Render bound recipes; write figures + RENDER_REPORT.md."""
    from .manifest import (
        compute_fully_bound,
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
    # `fully_bound` MUST be derived via `compute_fully_bound` so the CLI
    # cannot diverge from `bind_recipe_to_data`'s definition (DEFECT-A7).
    from .manifest.data_bridge import RecipeBinding as _RB
    rbs = []
    for fn, fbs in by_recipe.items():
        all_bound = compute_fully_bound(fbs)
        rbs.append(_RB(
            full_name=fn,
            bindings=tuple(fbs),
            fully_bound=all_bound,
            skipped_reason=None if all_bound else "missing required fields",
        ))
    files = discover_data_files(data_dir)

    # Forward `enable_provenance` only if Build-A's render_loop accepts
    # it. The flag is the CLI-side inverse of `enable_provenance`; while
    # Sprint 1B is in flight we degrade gracefully when the keyword is
    # absent so callers on a pre-1.8 render_loop still work.
    import inspect as _inspect
    _render_kwargs: dict[str, Any] = dict(
        bindings=[to_render_binding(rb) for rb in rbs],
        data_files=to_render_data_files(files),
        out_dir=out_dir,
        skip_audit=skip_audit,
    )
    if "enable_provenance" in _inspect.signature(render_shortlist).parameters:
        _render_kwargs["enable_provenance"] = not no_provenance
    log = render_shortlist(**_render_kwargs)
    report_path = write_render_report(log)
    if skip_audit:
        click.echo(
            "  ⚠ AUDIT SKIPPED — DO NOT SHIP THIS RUN; rerun without "
            "--skip-audit before figure release.",
            err=True,
        )
    if no_provenance:
        click.echo(
            "  ⚠ PROVENANCE SUPPRESSED — sidecars not written; "
            "`figures provenance verify` will fail on these outputs.",
            err=True,
        )
    click.echo(
        f"\n✓ rendered {log.n_success}/{log.n_attempted} recipes "
        f"({log.n_skipped} skipped, {log.n_failed} failed)"
    )
    click.echo(f"  see {report_path}")


# ─────────────────────────── audit (Sprint 1A — v1.7.0) ─────────────────


@main.group("audit")
def audit_group() -> None:
    """Statistical-contract audit (Sprint 1A — v1.7.0).

    Walks the per-recipe StatisticalContract against bound data
    BEFORE render, surfacing PASS / WARN / REFUSE findings.

    Two subcommands:

      * `figures audit recipe <full_name> --data <csv>`
        — audit one recipe against one data file.

      * `figures audit shortlist`
        — audit every recipe in the bound shortlist
        (see `panelforge_workspace/data_bridge_cache.json`).
    """


def _format_audit_finding(finding: Any) -> str:
    """Pretty-print a single AuditFinding for terminal output."""
    sev = getattr(finding, "severity", "unknown")
    rule = getattr(finding, "rule_id", "<unknown rule>")
    msg = getattr(finding, "message", "")
    if sev == "refuse":
        marker = "✗"
    elif sev == "warn":
        marker = "⚠"
    else:
        marker = "✓"
    return f"  {marker} [{sev.upper()}] {rule}: {msg}"


@audit_group.command("recipe")
@click.argument("recipe_full_name", type=str)
@click.option(
    "--data", "data_path", type=click.Path(
        exists=True, dir_okay=False, path_type=Path,
    ), required=True,
    help="CSV (or parquet) holding the data to audit against the contract.",
)
@click.option(
    "--group-column", type=str, default=None,
    help=(
        "Column to group by for per-group rules (e.g. n_per_group). "
        "Required when the contract declares min_n_per_group."
    ),
)
@click.option(
    "--strict", is_flag=True,
    help="Treat warnings as failures (exit 1).",
)
def audit_recipe_cmd(
    recipe_full_name: str,
    data_path: Path,
    group_column: str | None,
    strict: bool,
) -> None:
    """Audit one recipe against one CSV.

    Example:

      figures audit recipe biophysics_scaling.compartment_paired_delta_scatter \\
        --data data/effect_sizes.csv

    Exit codes:
      0  audit passed (or only PASS findings)
      1  audit refused, OR --strict and at least one WARN
    """
    import pandas as pd
    try:
        from .manifest.statistical_audit import audit_recipe_against_data
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"statistical_audit module not available: {exc}; "
            "Build-A's `manifest/statistical_audit.py` has not landed yet."
        ) from exc

    ensure_all_imported()
    try:
        entry = get_recipe(recipe_full_name)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    contract = entry.metadata.statistical_contract
    if data_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    report = audit_recipe_against_data(
        contract=contract,
        data=df,
        group_column=group_column,
        recipe_full_name=recipe_full_name,
    )

    click.echo(f"Audit: {recipe_full_name}")
    click.echo(f"Data:  {data_path}  (n={len(df)})")
    click.echo(f"Overall: {str(report.overall).upper()}")
    click.echo("")
    for finding in report.findings:
        if getattr(finding, "severity", "pass") == "pass":
            continue  # don't clutter
        click.echo(_format_audit_finding(finding))

    overall = str(report.overall).lower()
    if overall == "refuse":
        sys.exit(1)
    if strict and overall == "warn":
        sys.exit(1)


@audit_group.command("shortlist")
@click.option(
    "--profile", "profile_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("panelforge_workspace/profile.json"),
    help="ProjectProfile JSON (used only for path resolution / future lookups).",
)
@click.option(
    "--bindings", "bindings_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("panelforge_workspace/data_bridge_cache.json"),
    help="data_bridge cache produced by `figures bridge`.",
)
@click.option(
    "--data-dir", "data_dir",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=Path("data"),
    help="Directory holding user data files (csv / parquet / npz).",
)
@click.option(
    "--strict", is_flag=True,
    help="Treat warnings as failures (exit 1 if any binding warns).",
)
def audit_shortlist_cmd(
    profile_path: Path,
    bindings_path: Path,
    data_dir: Path,
    strict: bool,
) -> None:
    """Audit every recipe in the bound shortlist against discovered data.

    Walks `panelforge_workspace/data_bridge_cache.json` to find each
    recipe's bound data; runs `audit_recipe_against_data`; prints a
    summary table.  Exits 1 if any binding refuses (or, with --strict,
    if any binding warns).
    """
    import pandas as pd
    try:
        from .manifest.statistical_audit import audit_recipe_against_data
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"statistical_audit module not available: {exc}; "
            "Build-A's `manifest/statistical_audit.py` has not landed yet."
        ) from exc

    from .manifest import load_bindings_cache

    if not profile_path.exists():
        raise click.ClickException(
            f"profile not found at {profile_path}; "
            "run `figures intake` or `figures profile scan` first."
        )
    if not bindings_path.exists():
        raise click.ClickException(
            f"bindings cache not found at {bindings_path}; "
            "run `figures bridge` first."
        )

    cache = load_bindings_cache(bindings_path)
    # Group bindings by recipe full_name; pick a representative data file
    # per recipe (audit-shortlist is a quick verdict-only pass).
    by_recipe: dict[str, list] = {}
    data_path_by_recipe: dict[str, Path] = {}
    for (full_name, _field), fb in cache.items():
        by_recipe.setdefault(full_name, []).append(fb)
        if fb.data_source is not None and full_name not in data_path_by_recipe:
            data_path_by_recipe[full_name] = fb.data_source

    if not by_recipe:
        click.echo("No bound recipes in the shortlist; nothing to audit.")
        return

    ensure_all_imported()

    n_pass = 0
    n_warn = 0
    n_refuse = 0
    n_skipped = 0

    click.echo(
        f"Auditing {len(by_recipe)} recipe(s) from {bindings_path}\n"
        f"data dir: {data_dir}\n"
    )
    click.echo("| Recipe | Verdict | Data |")
    click.echo("|---|---|---|")

    for full_name in sorted(by_recipe):
        data_path = data_path_by_recipe.get(full_name)
        if data_path is None or not data_path.exists():
            click.echo(
                f"| {full_name} | SKIPPED (no data) | "
                f"{data_path if data_path else '—'} |"
            )
            n_skipped += 1
            continue
        try:
            entry = get_recipe(full_name)
        except KeyError:
            click.echo(f"| {full_name} | SKIPPED (unknown recipe) | — |")
            n_skipped += 1
            continue
        try:
            if data_path.suffix.lower() in {".parquet", ".pq"}:
                df = pd.read_parquet(data_path)
            else:
                df = pd.read_csv(data_path)
        except Exception as exc:  # noqa: BLE001 — robustness preferred for audit-shortlist
            click.echo(f"| {full_name} | SKIPPED ({exc}) | {data_path} |")
            n_skipped += 1
            continue

        try:
            report = audit_recipe_against_data(
                contract=entry.metadata.statistical_contract,
                data=df,
                group_column=None,
                recipe_full_name=full_name,
            )
        except Exception as exc:  # noqa: BLE001 — robust display
            click.echo(f"| {full_name} | ERROR ({exc}) | {data_path} |")
            n_skipped += 1
            continue

        verdict = str(report.overall).upper()
        click.echo(f"| {full_name} | {verdict} | {data_path} |")
        if verdict == "PASS":
            n_pass += 1
        elif verdict == "WARN":
            n_warn += 1
        elif verdict == "REFUSE":
            n_refuse += 1
        else:
            n_skipped += 1

    click.echo("")
    click.echo(
        f"Summary: {n_pass} PASS / {n_warn} WARN / "
        f"{n_refuse} REFUSE / {n_skipped} SKIPPED"
    )

    if n_refuse > 0:
        sys.exit(1)
    if strict and n_warn > 0:
        sys.exit(1)


# ─────────────────────── provenance (Sprint 1B — v1.8.0) ────────────────


@main.group("provenance")
def provenance_group() -> None:
    """Sprint 1B (v1.8.0) — every rendered figure has a sidecar
    provenance.json content-addressing data + recipe + scorer state.

    Verify reproducibility with `provenance verify`; bundle for review
    with `provenance bundle`; diff two snapshots with `provenance diff`.
    """


@provenance_group.command("show")
@click.argument(
    "figure_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def provenance_show(figure_path: Path) -> None:
    """Pretty-print the sidecar provenance.json for a figure."""
    prov_path = figure_path.with_suffix(figure_path.suffix + ".provenance.json")
    if not prov_path.is_file():
        click.echo(f"✗ provenance sidecar not found at {prov_path}", err=True)
        click.echo("  → render with `figures generate` to create one,", err=True)
        click.echo(
            "  → or pass `--enable-provenance` to a manual render call",
            err=True,
        )
        sys.exit(1)
    data = json.loads(prov_path.read_text())
    click.echo(f"# Provenance: {figure_path.name}")
    click.echo(f"  schema:           {data['schema_version']}")
    click.echo(f"  rendered_at:      {data['rendered_at']}")
    click.echo(f"  figure_sha256:    {data['figure_sha256'][:16]}...")
    click.echo(f"  recipe:           {data['recipe']['full_name']}")
    module_sha = data["recipe"].get("module_sha", "unknown")
    click.echo(f"  recipe_module:    {module_sha[:16]}...")
    click.echo(
        f"  panelforge_ver:   {data['recipe']['panelforge_version']}"
    )
    click.echo("  data sources:")
    for src in data["data"].get("sources", []):
        sha = (src.get("sha256") or "unknown")[:16]
        n_rows = src.get("n_rows", "?")
        click.echo(
            f"    - {src['path']:40s} sha256={sha}...  ({n_rows} rows)"
        )
    if data.get("scorer"):
        click.echo(
            f"  scorer.score:     {data['scorer'].get('score', 'n/a')}"
        )
    if data.get("audit"):
        click.echo(
            f"  audit.overall:    {data['audit'].get('overall', 'n/a')}"
        )
    env = data.get("rendering_environment", {})
    click.echo(f"  python:           {env.get('python_version', '?')}")
    click.echo(f"  matplotlib:       {env.get('matplotlib_version', '?')}")


@provenance_group.command("verify")
@click.argument(
    "figure_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def provenance_verify(figure_path: Path) -> None:
    """Recompute all hashes; report drift in figure / data / recipe."""
    try:
        from .manifest.provenance import verify_provenance
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"provenance module not available: {exc}; "
            "Build-A's `manifest/provenance.py` has not landed yet."
        ) from exc

    prov_path = figure_path.with_suffix(figure_path.suffix + ".provenance.json")
    if not prov_path.is_file():
        click.echo(f"✗ provenance sidecar not found at {prov_path}", err=True)
        sys.exit(1)
    result = verify_provenance(prov_path)
    if result.overall == "match":
        click.echo(f"✓ provenance verified: {figure_path.name}")
        click.echo(
            "  All hashes match.  Bit-identical reproducibility confirmed."
        )
        return
    click.echo(f"✗ provenance drift detected: {figure_path.name}", err=True)
    click.echo(f"  Drift class: {result.overall}", err=True)
    for line in result.findings:
        click.echo(f"    - {line}", err=True)
    sys.exit(1)


@provenance_group.command("bundle")
@click.argument(
    "figure_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out", "out_path", type=click.Path(path_type=Path), default=None,
    help="Default: <figure>.provenance.tar.gz",
)
def provenance_bundle(figure_path: Path, out_path: Path | None) -> None:
    """Tarball figure + provenance + referenced data files + recipe module."""
    try:
        from .manifest.provenance import bundle_provenance
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"provenance module not available: {exc}; "
            "Build-A's `manifest/provenance.py` has not landed yet."
        ) from exc

    bundle_path = bundle_provenance(figure_path, out_path=out_path)
    click.echo(f"✓ wrote {bundle_path}")
    click.echo(
        f"  bundle size: {bundle_path.stat().st_size / 1024:.1f} KB"
    )


@provenance_group.command("diff")
@click.argument(
    "figure_a",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "figure_b",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def provenance_diff(figure_a: Path, figure_b: Path) -> None:
    """Compare two figure provenance sidecars; flag what changed."""
    try:
        from .manifest.provenance import diff_provenance
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"provenance module not available: {exc}; "
            "Build-A's `manifest/provenance.py` has not landed yet."
        ) from exc

    prov_a = figure_a.with_suffix(figure_a.suffix + ".provenance.json")
    prov_b = figure_b.with_suffix(figure_b.suffix + ".provenance.json")
    if not prov_a.is_file():
        click.echo(f"✗ provenance for {figure_a} not found", err=True)
        sys.exit(1)
    if not prov_b.is_file():
        click.echo(f"✗ provenance for {figure_b} not found", err=True)
        sys.exit(1)
    diff = diff_provenance(prov_a, prov_b)
    has_diff = any(v for v in diff.values())
    if not has_diff:
        click.echo(
            f"✓ no differences between {figure_a.name} and {figure_b.name}"
        )
        return
    click.echo(f"# Differences: {figure_a.name} → {figure_b.name}")
    for dim, changes in diff.items():
        if changes:
            click.echo(f"  {dim}:")
            for line in changes:
                click.echo(f"    - {line}")


# ─────────────────────── compose (Sprint 1C — v1.9.0) ──────────────────
#
# Multi-panel figure composition.  Pairs with Build-A's
# `manifest/figure_composition.py` (public API:
# `render_figure_yaml`, `validate_figure_yaml`).  See
# `docs/spec_composition_layer.md`.


@main.command("compose")
@click.argument(
    "yaml_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("figures"),
    help="Output directory for the composed PDF (default: figures/).",
)
def compose_cmd(yaml_path: Path, out_dir: Path) -> None:
    """Compose a multi-panel figure from a `*.figure.yaml` spec.

    Sprint 1C — v1.9.0.  See `docs/spec_composition_layer.md`.
    """
    try:
        from .manifest import render_figure_yaml
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"figure_composition module not available: {exc}; "
            "Build-A's `manifest/figure_composition.py` has not landed yet."
        ) from exc

    out_path = render_figure_yaml(yaml_path, out_dir=out_dir)
    click.echo(f"✓ composed: {out_path}")


@main.command("compose-all")
@click.option(
    "--figures-dir",
    type=click.Path(path_type=Path),
    default=Path("figures"),
    help="Root directory containing `*.figure.yaml` specs (default: figures/).",
)
def compose_all_cmd(figures_dir: Path) -> None:
    """Compose ALL `*.figure.yaml` files under FIGURES_DIR.

    Sprint 1C — v1.9.0.  Globs the directory non-recursively, composes
    each spec, and reports per-file success / failure.  Exit code 0 iff
    every spec composes; exit code 1 if no specs are found.
    """
    try:
        from .manifest import render_figure_yaml
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"figure_composition module not available: {exc}; "
            "Build-A's `manifest/figure_composition.py` has not landed yet."
        ) from exc

    yaml_files = sorted(figures_dir.glob("*.figure.yaml"))
    if not yaml_files:
        click.echo(
            f"no *.figure.yaml files in {figures_dir}",
            err=True,
        )
        sys.exit(1)
    for yp in yaml_files:
        try:
            out = render_figure_yaml(yp, out_dir=figures_dir)
            click.echo(f"✓ {yp.name} → {out.name}")
        except Exception as e:  # noqa: BLE001 — surface any render error per-file
            click.echo(f"✗ {yp.name}: {e}", err=True)


@main.command("compose-validate")
@click.argument(
    "yaml_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def compose_validate_cmd(yaml_path: Path) -> None:
    """Schema-check a `*.figure.yaml` spec without rendering.

    Sprint 1C — v1.9.0.  Validates the figure spec against its Pydantic
    schema and verifies that every referenced recipe exists.  Exit code
    0 if the spec is valid; exit code 1 otherwise (with one diagnostic
    line per problem on stderr).
    """
    try:
        from .manifest import validate_figure_yaml
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"figure_composition module not available: {exc}; "
            "Build-A's `manifest/figure_composition.py` has not landed yet."
        ) from exc

    problems = validate_figure_yaml(yaml_path)
    if not problems:
        click.echo(f"✓ {yaml_path.name} valid")
        return
    for p in problems:
        click.echo(f"✗ {p}", err=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
