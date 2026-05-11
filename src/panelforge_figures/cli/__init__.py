"""`figures` CLI — Click-based, non-interactive, scriptable."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from .. import __version__
from ..adapters import list_adapters
from ..core.contract import (
    ensure_all_imported,
    get_recipe,
    list_recipes,
    modality_description,
    registry_counts,
)
from ..core.palette import list_palettes
from ..manifest import (
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
    from ..themes import list_themes
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
    from ..gallery.generator import regenerate_gallery
    paths = regenerate_gallery(out)
    click.echo(f"regenerated {len(paths)} gallery PNGs under {out}")


@gallery.command("diff")
@click.option("--root", type=click.Path(path_type=Path), default=Path("docs/gallery"))
@click.option("--threshold", type=float, default=0.02, help="L1 diff threshold (0-1).")
def gallery_diff(root: Path, threshold: float) -> None:
    from ..gallery.generator import diff_gallery
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
    from ..core.contract import list_modalities
    from ..manifest import run_intake_interactive
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
@click.option(
    "--reference-figure",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Optional: reference figure PNG/JPG to seed inference via the "
        "vision API (Sprint 2C — v1.12.0).  Sends the image bytes to "
        "Anthropic; gated on data_class and ANTHROPIC_API_KEY."
    ),
)
def profile_scan_cmd(
    project_root: Path,
    out_path: Path,
    reference_figure: Path | None,
) -> None:
    """Scan README/manuscript/data/; pre-fill the 8 intake answers.

    Writes the inferred ProjectProfile + per-answer confidence scores
    to disk so downstream `figures intake` / `figures bridge` /
    `figures generate` can consume it.

    With ``--reference-figure``, additionally calls the vision API to
    extract visual signals from the reference image.  See
    ``docs/spec_vision_input.md`` for the full design.
    """
    from ..core.contract import list_modalities
    from ..manifest import (
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

    # Vision augmentation — Sprint 2C.
    if reference_figure is not None:
        from ..manifest.vision_input import (
            VisionUnavailableError,
            vision_scan_reference_figure,
        )
        from ..manifest.vision_input import (
            to_intake_pre_filled as to_intake_pre_filled_from_vision,
        )
        click.echo(
            f"\n[vision] scanning {reference_figure.name} "
            f"({reference_figure.stat().st_size} bytes)..."
        )
        try:
            vision_result = vision_scan_reference_figure(reference_figure)
        except VisionUnavailableError as exc:
            click.echo(f"[vision] skipped: {exc}", err=True)
        else:
            click.echo(
                f"[vision] inferred {len(vision_result.inferences)} signals "
                f"(model={vision_result.model}, "
                f"~${vision_result.cost_usd_estimate:.4f}/call)"
            )
            for inf in vision_result.inferences:
                click.echo(
                    f"  {inf.field_name:30s} = {inf.value!r:20s} "
                    f"conf={inf.confidence:.2f}"
                )
            vision_pre_fill = to_intake_pre_filled_from_vision(vision_result)
            if vision_pre_fill:
                click.echo(
                    f"[vision] {len(vision_pre_fill)} field(s) above "
                    f"threshold; merging into intake pre-fill"
                )
                # Merge: vision wins where text-scan didn't reach the
                # threshold; existing text-scan answers are preserved
                # (they have stronger confidence semantics from §3 of
                # the spec).
                from ..manifest import IntakeAnswer
                field_to_qid = {
                    "factorial_design": 1,
                    "equivalence_claims": 2,
                    "manuscript_anchor": 3,
                    "dynamics_needed": 4,
                    "dimensionality": 5,
                }
                for fname, value in vision_pre_fill.items():
                    if fname in pre_filled:
                        continue  # text-scan already won
                    qid = field_to_qid.get(fname)
                    if qid is None:
                        continue
                    pre_filled[fname] = IntakeAnswer(
                        question_id=qid,
                        field_name=fname,
                        value=value,
                        source="inferred",
                        confidence=0.8,  # vision threshold per spec §3
                    )
                    click.echo(f"  [vision] {fname} = {value!r}")

    click.echo(f"\n{len(pre_filled)} of 8 fields meet >=0.7 confidence; "
               "passing to intake")
    profile = run_intake_interactive(
        available_modalities=available,
        pre_filled=pre_filled,
        out_path=out_path,
    )
    click.echo(f"\n[ok] profile written to {out_path}")
    click.echo(f"  anchor={profile.manuscript_anchor}  "
               f"factorial={profile.factorial_design}  "
               f"shortlist_size={profile.shortlist_size}")


# ──────────────── vision input + refinement (Sprint 2C — v1.12.0) ───────
#
# Vision-driven recipe selection + iterative figure refinement.  See
# `docs/spec_vision_input.md` for the full design.  All three commands
# below are gated on ``safety.is_vision_allowed()`` (clinical refuses,
# research uses ANTHROPIC_API_KEY as the opt-in signal, public is
# default-on).


@main.command("refine")
@click.argument(
    "figure_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument("instruction", type=str)
@click.option(
    "--recipe", "recipe_module_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Optional: path to the recipe Python module that produced "
        "the figure.  Sent to Anthropic alongside the rendered PNG "
        "so the model can reason about what's mutable in the contract."
    ),
)
def refine_cmd(
    figure_path: Path,
    instruction: str,
    recipe_module_path: Path | None,
) -> None:
    """Refine a rendered figure with a natural-language instruction.

    Sends the rendered PNG/PDF + the recipe Python source + the
    instruction to Claude vision; receives a JSON-patch on the
    contract.  The patch is printed for review — re-render only after
    inspecting it.

    Example::

        figures refine figures/forest_v3.pdf "make y-axis log-scale"
    """
    from ..manifest.vision_input import VisionUnavailableError, refine_figure

    try:
        outcome = refine_figure(
            figure_path,
            instruction,
            recipe_module_path=recipe_module_path,
        )
    except VisionUnavailableError as exc:
        click.echo(f"[refine] vision unavailable: {exc}", err=True)
        sys.exit(1)

    click.echo(f"# Refinement of {figure_path.name}")
    click.echo(f"  instruction: {instruction!r}")
    if outcome.contract_patch:
        click.echo("  suggested contract patch:")
        click.echo(json.dumps(outcome.contract_patch, indent=4))
    else:
        click.echo("  suggested contract patch: (empty — model returned no actionable patch)")
    if outcome.suggested_alternatives:
        click.echo("  alternative recipes:")
        for alt in outcome.suggested_alternatives:
            click.echo(f"    - {alt}")
    click.echo(f"\n  cost estimate: ~${outcome.cost_usd_estimate:.4f}")


@main.command("vision-explain")
@click.argument(
    "image_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def vision_explain_cmd(image_path: Path) -> None:
    """Have Claude explain what's in a figure (read-only).

    Calls the same scanner as ``profile scan --reference-figure`` but
    prints all inferences regardless of confidence threshold and does
    not change any contract.  Useful for sanity-checking what vision
    sees in a figure before driving downstream refinement.
    """
    from ..manifest.vision_input import (
        VisionUnavailableError,
        vision_scan_reference_figure,
    )

    try:
        result = vision_scan_reference_figure(image_path)
    except VisionUnavailableError as exc:
        click.echo(f"[vision-explain] unavailable: {exc}", err=True)
        sys.exit(1)

    click.echo(f"# Vision analysis: {image_path.name}")
    click.echo(f"Model: {result.model}")
    click.echo(f"Image SHA-256: {result.image_sha256}")
    click.echo(f"Inferences ({len(result.inferences)}):")
    for inf in result.inferences:
        click.echo(
            f"  {inf.field_name:30s} = {inf.value!r:20s} "
            f"conf={inf.confidence:.2f}"
        )
    click.echo(f"\n  cost estimate: ~${result.cost_usd_estimate:.4f}")


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
    from ..manifest import (
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
    from ..manifest import (
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
    from ..manifest.data_bridge import RecipeBinding as _RB
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
        from ..manifest.statistical_audit import audit_recipe_against_data
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
        from ..manifest.statistical_audit import audit_recipe_against_data
    except ImportError as exc:  # pragma: no cover — Build-A scaffold guard
        raise click.ClickException(
            f"statistical_audit module not available: {exc}; "
            "Build-A's `manifest/statistical_audit.py` has not landed yet."
        ) from exc

    from ..manifest import load_bindings_cache

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


# ──────────── audit data-class (Sprint 2B — v1.11.0) ───────────────────


@audit_group.command("data-class")
@click.option(
    "--data-dir", "data_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("data"),
    help="Directory to scan recursively for tabular data files (default: data/).",
)
@click.option(
    "--strict", is_flag=True,
    help="Promote medium-risk WARN to ERROR (CI-friendly).",
)
def audit_data_class_cmd(data_dir: Path, strict: bool) -> None:
    """Scan column names under data/ for PHI/PII patterns.

    Reports a PHI risk audit against the current ``data_class`` (set
    via ``figures config set data_class <value>``).  See
    ``docs/spec_data_class_safety.md`` §5 for the behaviour matrix.

    Exit codes:

      * 0 — clean OR only INFO/WARN findings without ``--strict``.
      * 2 — at least one HIGH-risk column found while
        ``data_class != clinical`` (or any WARN under ``--strict``).
    """
    from ..safety import DataClass, get_data_class
    from ..safety.phi_pattern_scanner import scan_columns_for_phi

    cls = get_data_class()
    click.echo(f"Current data_class: {cls.value}")
    click.echo(f"Scanning columns under {data_dir} ...")

    # Collect (file_name, column) pairs across CSVs only — parquet/h5ad
    # support is reserved for Sprint 3+ (spec §5: walks data/ for csv,
    # parquet, feather, h5ad).  CSV header reads are cheap and
    # zero-dependency; richer formats can land alongside their gates.
    all_columns: list[tuple[str, str]] = []
    for csv in sorted(data_dir.rglob("*.csv")):
        try:
            import pandas as pd
            df = pd.read_csv(csv, nrows=0)
            for c in df.columns:
                all_columns.append((csv.name, str(c)))
        except Exception as exc:  # noqa: BLE001 — best-effort scan
            click.echo(f"  warn: skipping {csv.name}: {exc}", err=True)

    findings = scan_columns_for_phi([c for _f, c in all_columns])
    if not findings:
        click.echo(
            f"✓ no PHI/PII patterns found across {len(all_columns)} columns"
        )
        return

    high = [f for f in findings if f.risk_level == "high"]
    medium = [f for f in findings if f.risk_level == "medium"]

    if high and cls != DataClass.CLINICAL:
        click.echo(
            f"✗ {len(high)} HIGH-risk column(s) found but "
            f"data_class={cls.value}",
            err=True,
        )
        for f in high:
            click.echo(
                f"    - {f.column} (matched: {f.matched_pattern})",
                err=True,
            )
        click.echo(
            "  → set data_class=clinical OR remove/anonymise these columns",
            err=True,
        )
        sys.exit(2)
    if high and cls == DataClass.CLINICAL:
        click.echo(
            f"  {len(high)} HIGH-risk column(s) found "
            "(acknowledged under data_class=clinical):"
        )
        for f in high:
            click.echo(f"    - {f.column} (matched: {f.matched_pattern})")

    if medium:
        verb = "✗" if strict else "⚠"
        click.echo(f"{verb} {len(medium)} medium-risk column(s):")
        for f in medium:
            click.echo(f"    - {f.column} (matched: {f.matched_pattern})")
        if strict:
            sys.exit(2)


# ──────────── config (Sprint 2B — v1.11.0) ─────────────────────────────


@main.group("config")
def config_group() -> None:
    """View / set ``panelforge.project.yaml`` configuration.

    Sprint 2B (v1.11.0) — currently exposes only ``data_class``;
    spec §8 sketches the v2.0.0 surface (overrides + interactive
    confirmation flow for clinical) which will land in subsequent
    sprints.
    """


@config_group.command("show")
def config_show_cmd() -> None:
    """Print current ``data_class`` and resolved policy."""
    from ..safety import get_data_class, get_policy

    cls = get_data_class()
    policy = get_policy()
    click.echo(f"data_class: {cls.value}")
    click.echo(f"  llm_pass3:        {policy.llm_pass3}")
    click.echo(f"  telemetry:        {policy.telemetry}")
    click.echo(f"  vision:           {policy.vision}")
    click.echo(f"  provenance:       {policy.provenance_hashes}")
    click.echo(f"  plugin_network:   {policy.plugin_network_required}")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key: str, value: str) -> None:
    """Set a config value.

    Currently only ``data_class`` is supported.  Future overrides
    (per spec §3) will be wired in subsequent sprints.
    """
    from ..safety import DataClass, DataClassError, set_data_class

    if key == "data_class":
        try:
            set_data_class(DataClass(value))
        except (ValueError, DataClassError):
            click.echo(
                f"✗ invalid data_class: {value!r}; "
                "valid values: clinical / research / public",
                err=True,
            )
            sys.exit(1)
        click.echo(f"✓ data_class = {value}")
        return
    click.echo(f"✗ unknown config key: {key}", err=True)
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
        from ..manifest.provenance import verify_provenance
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
        from ..manifest.provenance import bundle_provenance
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
        from ..manifest.provenance import diff_provenance
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


# ─────────────────────── caption (Elevation E5 — v2.5.0) ───────────────
#
# Audit-driven caption drafts. Pairs with Build-A's
# `manifest/caption.py` (public API: `draft_caption_from_provenance`,
# `render_caption_markdown`). The output is a stub the user edits,
# NOT final text — an auditable seed for the writing process.


def _caption_style_choices() -> list[str]:
    """Materialise the CaptionStyle enum values for click.Choice.

    Imported lazily so the CLI module does not pull caption.py at
    interpreter start (it has no other consumers in v2.5.0).
    """
    from ..manifest.caption import CaptionStyle

    return [s.value for s in CaptionStyle]


@main.command("caption")
@click.argument(
    "provenance_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--style",
    type=click.Choice(_caption_style_choices()),
    default="plain",
    help="House style for the title line (plain, nature, cell, nejm, lab_default).",
)
@click.option(
    "--use-llm",
    is_flag=True,
    help="Opt-in flag for LLM polish; gated by the data-class policy "
    "and deferred to v2.6.0 — emits template-only with a marker note.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Write markdown to this path; otherwise print to stdout.",
)
def caption_cmd(
    provenance_path: Path,
    style: str,
    use_llm: bool,
    output: Path | None,
) -> None:
    """Draft a figure caption from a provenance.json sidecar."""
    from ..manifest.caption import (
        CaptionError,
        CaptionStyle,
        draft_caption_from_provenance,
        render_caption_markdown,
    )

    try:
        draft = draft_caption_from_provenance(
            provenance_path,
            style=CaptionStyle(style),
            use_llm=use_llm,
        )
    except CaptionError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        sys.exit(1)

    md = render_caption_markdown(draft)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"))
    else:
        click.echo(md)


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
        from ..manifest import render_figure_yaml
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
        from ..manifest import render_figure_yaml
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
        from ..manifest import validate_figure_yaml
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


# ─────────────────── plugins (Sprint 2A — v1.10.0) ─────────────────────
#
# Project-extensible recipes discovered via `entry_points` (preferred)
# or a `panelforge_plugins/` directory at the project root.  See
# `docs/spec_project_plugins.md`.


@main.group("plugins")
def plugins_group() -> None:
    """Project plugin discovery + management (Sprint 2A — v1.10.0).

    Plugins extend the catalog with project-local recipes via
    ``entry_points`` (preferred for installable groups) or a
    ``panelforge_plugins/`` directory at the project root (preferred
    for solo researchers).  See ``docs/spec_project_plugins.md``.
    """


@plugins_group.command("list")
def plugins_list_cmd() -> None:
    """List all discovered plugins (entry-points + directory)."""
    from ..plugins import discover_all_plugins

    plugins = discover_all_plugins()
    if not plugins:
        click.echo("no plugins discovered")
        return
    click.echo(f"discovered {len(plugins)} plugin(s):")
    for p in plugins:
        n_recipes = len(p.discovered_recipes)
        click.echo(
            f"  {p.name:30s} {p.version:12s} {p.source:14s} "
            f"recipes={n_recipes:<3d} {p.module_path}"
        )


@plugins_group.command("describe")
@click.argument("plugin_name")
def plugins_describe_cmd(plugin_name: str) -> None:
    """Show details about a specific plugin."""
    from ..plugins import discover_all_plugins

    plugins = {p.name: p for p in discover_all_plugins()}
    if plugin_name not in plugins:
        click.echo(f"✗ plugin {plugin_name!r} not found", err=True)
        sys.exit(1)
    p = plugins[plugin_name]
    click.echo(f"plugin: {p.name}")
    click.echo(f"  version:        {p.version}")
    click.echo(f"  source:         {p.source}")
    click.echo(f"  module_path:    {p.module_path}")
    if p.discovered_recipes:
        click.echo(f"  recipes ({len(p.discovered_recipes)}):")
        for r in p.discovered_recipes:
            click.echo(f"    - {r}")
    else:
        click.echo("  recipes: (none registered)")


# ─────────────────────────── projects (Sprint 3A) ───────────────────────────

@main.group("projects")
def projects_group() -> None:
    """Multi-project registry: list / register / switch / diff / portfolio.

    Sprint 3A — see ``docs/spec_cross_project.md``. The registry lives at
    ``~/.config/panelforge/projects.yaml`` (XDG-aware) and stores **paths,
    not data** — switching projects only re-reads the local
    ``panelforge_workspace/``.
    """


def _format_last_used(dt: Any) -> str:
    """Render a UTC datetime as ``YYYY-MM-DD HH:MM`` for the list table."""
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return "n/a"


@projects_group.command("list")
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path (default: ~/.config/panelforge/projects.yaml).")
def projects_list_cmd(config_path: Path | None) -> None:
    """Print a table of registered projects with last-used + status."""
    from ..projects import load_registry

    registry = load_registry(config_path)
    if not registry.projects:
        click.echo("no projects registered")
        click.echo("(register one with `figures projects register <path>`)")
        return
    header = (
        f"  {'ID':<24} {'LAST USED':<18} {'PROFILE':<18} "
        f"{'RECIPES':<8} {'STATUS':<16} TAGS"
    )
    click.echo(header)
    for pid, entry in registry.projects.items():
        marker = "*" if pid == registry.default_project else " "
        tags = ", ".join(entry.tags) if entry.tags else ""
        click.echo(
            f"{marker} {pid:<24} {_format_last_used(entry.last_used):<18} "
            f"{entry.active_profile:<18} {entry.n_recipes_picked:<8} "
            f"{entry.last_render_status:<16} {tags}"
        )
    click.echo("")
    click.echo("(* = default project; switch with `figures projects switch <id>`)")


def _read_project_id_from_yaml(path: Path) -> str | None:
    """Best-effort read of ``project_id`` from ``panelforge.project.yaml``."""
    for name in ("panelforge.project.yaml", "panelforge.project.yml"):
        candidate = path / name
        if candidate.is_file():
            try:
                import yaml as _yaml

                with candidate.open("r", encoding="utf-8") as fh:
                    data = _yaml.safe_load(fh) or {}
                if isinstance(data, dict):
                    pid = data.get("project_id")
                    if isinstance(pid, str) and pid:
                        return pid
            except Exception:  # noqa: BLE001 — fall through to fallback
                return None
    return None


@projects_group.command("register")
@click.argument("path", type=click.Path(path_type=Path), default=Path("."))
@click.option("--id", "project_id", type=str, default=None,
              help="Override the project_id (default: read panelforge.project.yaml).")
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_register_cmd(path: Path, project_id: str | None,
                          config_path: Path | None) -> None:
    """Add PATH to the registry (PATH defaults to the current directory)."""
    from datetime import datetime

    from ..projects import (
        ProjectIdCollision,
        ProjectPathMissing,
        load_registry,
        register_if_absent,
    )

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        click.echo(f"✗ path is not a directory: {resolved}", err=True)
        sys.exit(1)
    if project_id is None:
        project_id = _read_project_id_from_yaml(resolved)
    if project_id is None:
        project_id = f"{resolved.name}_{datetime.now().year}"

    existing = load_registry(config_path)
    is_first = not existing.projects
    try:
        register_if_absent(
            path=resolved,
            project_id=project_id,
            profile="default",
            n_recipes=0,
            status="not yet rendered",
            config_path=config_path,
            set_default=is_first,
        )
    except ProjectIdCollision as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(1)
    except ProjectPathMissing as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(1)
    if is_first:
        click.echo(f"✓ Registered as `{project_id}`. {click.style('(default project)', bold=True)}")
    else:
        click.echo(f"✓ Registered as `{project_id}`.")


@projects_group.command("switch")
@click.argument("project_id", type=str)
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_switch_cmd(project_id: str, config_path: Path | None) -> None:
    """Set the default project to PROJECT_ID and warm-load its workspace."""
    from ..projects import ProjectPathMissing, switch_default

    try:
        entry = switch_default(project_id, config_path=config_path)
    except KeyError:
        click.echo(f"✗ project not registered: {project_id!r}", err=True)
        sys.exit(1)
    except ProjectPathMissing as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(1)
    click.echo(
        f"✓ Switched. Active profile: {entry.active_profile}. "
        f"{entry.n_recipes_picked} recipes in manifest."
    )
    click.echo("  (warm-loaded panelforge_workspace/state.json — no scan re-run)")


@projects_group.command("current")
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_current_cmd(config_path: Path | None) -> None:
    """Print the active project + key metadata."""
    from ..projects import load_registry

    registry = load_registry(config_path)
    if not registry.default_project or registry.default_project not in registry.projects:
        click.echo("No active project (run `figures projects switch <id>`).")
        sys.exit(1)
    entry = registry.projects[registry.default_project]
    click.echo(f"Active project: {click.style(entry.id, bold=True)}")
    click.echo(f"  Path:           {entry.path}")
    click.echo(f"  Profile:        {entry.active_profile}")
    click.echo(f"  Recipes picked: {entry.n_recipes_picked}")
    click.echo(f"  Last render:    {entry.last_render_status}")
    click.echo(f"  Last used:      {_format_last_used(entry.last_used)} UTC")


@projects_group.command("diff")
@click.argument("a_id", type=str)
@click.argument("b_id", type=str)
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_diff_cmd(a_id: str, b_id: str, config_path: Path | None) -> None:
    """Recipe-overlap analysis between two registered projects."""
    from ..projects import load_registry
    from ..projects.portfolio import diff_projects

    registry = load_registry(config_path)
    if a_id not in registry.projects:
        click.echo(f"✗ project not registered: {a_id!r}", err=True)
        sys.exit(1)
    if b_id not in registry.projects:
        click.echo(f"✗ project not registered: {b_id!r}", err=True)
        sys.exit(1)
    report = diff_projects(registry, a_id, b_id)
    a_count = len(report.shared) + len(report.a_only)
    b_count = len(report.shared) + len(report.b_only)
    click.echo("")
    click.echo(f"Project A ({a_id}): {a_count} recipes")
    click.echo(f"Project B ({b_id}): {b_count} recipes")
    click.echo("")
    click.echo(f"Shared ({len(report.shared)}):")
    for recipe in report.shared:
        click.echo(f"  - {recipe}")
    click.echo("")
    click.echo(f"A only ({len(report.a_only)}):")
    for recipe in report.a_only:
        click.echo(f"  - {recipe}")
    click.echo("")
    click.echo(f"B only ({len(report.b_only)}):")
    for recipe in report.b_only:
        click.echo(f"  - {recipe}")
    if report.suggestion:
        click.echo("")
        click.echo(report.suggestion)
        click.echo(
            f"Run:  figures compose-from-shared {a_id} {b_id} "
            "--out shared_methods.figure.yaml"
        )


@projects_group.command("portfolio")
@click.option("--png", "png_path", type=click.Path(path_type=Path), default=None,
              help="Also emit a matplotlib PNG of the heatmap.")
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_portfolio_cmd(png_path: Path | None, config_path: Path | None) -> None:
    """Portfolio summary across every registered project."""
    from ..projects import load_registry
    from ..projects.portfolio import (
        aggregate_portfolio,
        render_heatmap_png,
        render_heatmap_terminal,
        top_n_recipes,
    )

    registry = load_registry(config_path)
    if not registry.projects:
        click.echo("no projects registered — nothing to summarise")
        return
    summary = aggregate_portfolio(registry)
    click.echo(
        f"Portfolio summary — {summary.n_projects} projects, "
        f"{summary.n_distinct_recipes} distinct recipes used"
    )
    click.echo("")
    click.echo("Top 10 recipes (by project-count):")
    for row in top_n_recipes(summary, n=10):
        click.echo(
            f"  {row.project_count}/{summary.n_projects}  {row.recipe_full_name}"
        )
    click.echo("")
    click.echo("Recipe usage heatmap")
    click.echo(render_heatmap_terminal(summary))
    if png_path is not None:
        out = render_heatmap_png(summary, Path(png_path))
        click.echo(f"✓ Wrote heatmap PNG to {out}")


@projects_group.command("unregister")
@click.argument("project_id", type=str)
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_unregister_cmd(project_id: str, config_path: Path | None) -> None:
    """Remove PROJECT_ID from the registry; never deletes project files."""
    from ..projects import unregister

    try:
        unregister(project_id, config_path=config_path)
    except KeyError:
        click.echo(f"✗ project not registered: {project_id!r}", err=True)
        sys.exit(1)
    click.echo(f"✓ Unregistered `{project_id}`. (project files untouched)")


@projects_group.command("validate")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.option("--config-path", type=click.Path(path_type=Path), default=None,
              help="Override the registry path.")
def projects_validate_cmd(yes: bool, config_path: Path | None) -> None:
    """Walk the registry, drop entries whose path no longer exists."""
    from ..projects import load_registry, validate_registry

    registry = load_registry(config_path)
    stale = [
        pid for pid, entry in registry.projects.items() if not entry.path.is_dir()
    ]
    if not stale:
        click.echo("✓ Registry clean (no stale entries).")
        return
    click.echo("Stale entries (path missing):")
    for pid in stale:
        click.echo(f"  - {pid}  ({registry.projects[pid].path})")
    if not yes and not click.confirm("Drop these entries from the registry?"):
        click.echo("(no changes made)")
        return
    dropped = validate_registry(prompt=False, config_path=config_path)
    click.echo(f"✓ Dropped {len(dropped)} stale entr{'y' if len(dropped) == 1 else 'ies'}.")


# ─────────────────── telemetry + active learning (Sprint 3B — v1.14.0) ──
#
# Opt-in usage telemetry, manual pick-recording, and offline weight
# calibration.  See ``docs/spec_active_learning.md`` for the full spec.
# Telemetry is OFF by default and is NEVER auto-uploaded — the user
# explicitly runs ``figures telemetry export`` and ships the file by
# hand if they wish.


@main.group("telemetry")
def telemetry_group() -> None:
    """Opt-in usage telemetry — local only, never auto-uploaded.

    Activated by setting ``telemetry: opt-in`` in
    ``panelforge.project.yaml``.  When active, every ``figures generate``
    call appends a row to ``panelforge_workspace/usage.jsonl``.  The user
    later records their pick with ``figures pick <recipe_name>`` and
    optionally ships an aggregated artifact via ``figures telemetry
    export``.  See ``docs/spec_active_learning.md`` §3 + §9.
    """


@telemetry_group.command("status")
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge.project.yaml (default: cwd).",
)
def telemetry_status_cmd(project_root: Path) -> None:
    """Print on/off + log location + row count."""
    from ..manifest.telemetry import (
        is_telemetry_enabled,
        telemetry_log_path,
    )

    enabled = is_telemetry_enabled(project_root)
    log_path = telemetry_log_path(project_root)
    if not enabled:
        click.echo("telemetry: off (default — no rows written)")
        return
    n_rows = 0
    if log_path.exists():
        n_rows = sum(
            1 for line in log_path.read_text().splitlines() if line.strip()
        )
    click.echo(
        f"telemetry: opt-in (writing to {log_path}, {n_rows} rows)"
    )


@telemetry_group.command("export")
@click.argument(
    "output_path",
    type=click.Path(path_type=Path),
)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge.project.yaml (default: cwd).",
)
@click.option(
    "--anonymize/--no-anonymize",
    default=True,
    help="Replace session_id with sha256(session_id)[:16] (default: on).",
)
@click.option(
    "--include-unpicked/--drop-unpicked",
    default=False,
    help=(
        "By default rows without user_picked are dropped (they carry no "
        "calibration signal).  Pass --include-unpicked to keep them."
    ),
)
def telemetry_export_cmd(
    output_path: Path,
    project_root: Path,
    anonymize: bool,
    include_unpicked: bool,
) -> None:
    """Write a sanitized aggregated JSONL artifact.

    The file is the user's to ship — panelforge does NOT upload it.
    """
    from ..manifest.telemetry import (
        TelemetryError,
        export_telemetry,
        is_telemetry_enabled,
    )

    if not is_telemetry_enabled(project_root):
        click.echo(
            click.style(
                "✗ telemetry is off; nothing to export",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)
    try:
        n = export_telemetry(
            project_root,
            output_path,
            anonymize=anonymize,
            drop_unpicked=not include_unpicked,
        )
    except TelemetryError as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(1)
    click.echo(f"✓ exported {n} row(s) to {output_path}")


@main.command("pick")
@click.argument("full_name", type=str)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge.project.yaml (default: cwd).",
)
@click.option(
    "--session-id",
    type=str,
    default=None,
    help=(
        "Disambiguate when multiple un-picked rows are present.  "
        "Defaults to the most recent un-picked row when unique."
    ),
)
def pick_cmd(
    full_name: str, project_root: Path, session_id: str | None
) -> None:
    """Set ``user_picked`` on the most recent telemetry row.

    Friendly UsageError if no candidate row exists or if multiple rows
    are ambiguous and ``--session-id`` is not supplied.  See
    ``docs/spec_active_learning.md`` §2.
    """
    from ..manifest.telemetry import TelemetryError, set_user_pick

    try:
        set_user_pick(project_root, full_name, session_id=session_id)
    except TelemetryError as exc:
        raise click.UsageError(str(exc)) from exc
    click.echo(
        click.style(
            f"✓ recorded pick: {full_name}",
            fg="green",
        )
    )


@main.command("suggest-weights")
@click.option(
    "--aggregate-from",
    "aggregate_from",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Aggregated telemetry JSONL (concatenation of exported rows).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    required=True,
    help="Where to write the weight-proposal JSON.",
)
@click.option(
    "--seed",
    type=int,
    default=42,
    help="RNG seed for the train/test split (default: 42, deterministic).",
)
def suggest_weights_cmd(
    aggregate_from: Path, output_path: Path, seed: int
) -> None:
    """Cross-validate, propose new weights.

    Runs an offline grid search over ±0.05 perturbations of the locked
    weights and writes a JSON artifact reporting the current and
    suggested top-3 hit rates plus uplift.  The CLI never edits source
    files — a maintainer reviews the JSON and decides whether to ship a
    new ``WEIGHTS_HISTORY`` entry.  See ``docs/spec_active_learning.md``
    §5.
    """
    from ..manifest.weight_calibration import (
        CalibrationInput,
        load_telemetry_rows,
        suggest_weights,
    )

    rows = load_telemetry_rows(aggregate_from)
    if not rows:
        click.echo(
            click.style(
                f"✗ no calibration-bearing rows in {aggregate_from} "
                "(rows must have user_picked set and at least one "
                "rejected_higher_scored entry)",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)
    out = suggest_weights(CalibrationInput(rows=rows, seed=seed))
    payload = {
        "n_rows": out.n_rows,
        "n_train": out.n_train,
        "n_test": out.n_test,
        "current_weights_version": out.current_weights_version,
        "current_weights": dict(out.current_weights),
        "current_top3_hit_rate": out.current_top3_hit_rate,
        "suggested_weights": dict(out.suggested_weights),
        "suggested_top3_hit_rate": out.suggested_top3_hit_rate,
        "uplift": out.suggested_top3_hit_rate - out.current_top3_hit_rate,
        "seed": out.seed,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    click.echo(
        f"✓ proposal written to {output_path}  "
        f"(uplift {payload['uplift']:+.3f})"
    )


# ─────────────────── reproducibility envelope (E3 — v2.2.0) ──────────────

@main.command("lock")
@click.option("--project-root", type=click.Path(path_type=Path), default=Path("."))
@click.option("--output", type=click.Path(path_type=Path), default=Path("panelforge.lock.json"))
@click.option("--data-file", type=click.Path(path_type=Path), multiple=True,
              help="Path to a data file to include in the lock (repeatable).")
@click.option("--figure-path", type=click.Path(path_type=Path), default=None,
              help="Path to a rendered figure to hash into the lock.")
@click.option("--numpy-seed", type=int, default=None)
@click.option("--python-random-seed", type=int, default=None)
def lock_cmd(
    project_root: Path,
    output: Path,
    data_file: tuple[Path, ...],
    figure_path: Path | None,
    numpy_seed: int | None,
    python_random_seed: int | None,
) -> None:
    """Write a panelforge.lock.json with full env snapshot.

    Captures: Python version, OS, BLAS, RNG seeds, git state, uv.lock SHA
    (or pip freeze fallback), data file SHAs, optional figure SHA.
    """
    from panelforge_figures import __version__
    from panelforge_figures.manifest.reproducibility import (
        RNGSeeds,
        build_lock,
        save_lock,
    )

    seeds = RNGSeeds(
        numpy_seed=numpy_seed,
        python_random_seed=python_random_seed,
        torch_seed=None,
        hypothesis_seed=None,
    )
    lock = build_lock(
        project_root=project_root,
        panelforge_version=__version__,
        data_files=list(data_file) if data_file else None,
        figure_path=figure_path,
        rng_seeds=seeds,
    )
    saved_at = save_lock(lock, output)
    click.echo(click.style(f"✓ wrote {saved_at}", fg="green"))
    click.echo(f"  schema:           {lock.schema_version}")
    click.echo(f"  panelforge:       {lock.panelforge_version}")
    click.echo(f"  python:           {lock.environment.python_version}")
    click.echo(
        f"  git:              {lock.panelforge_git_commit[:8]}"
        f"{'-dirty' if lock.panelforge_git_dirty else ''}"
    )
    if lock.uv_lock_path:
        click.echo(f"  uv.lock:          {lock.uv_lock_sha256[:16]}...")
    else:
        click.echo(f"  pip freeze rows:  {len(lock.pip_freeze)}")
    click.echo(f"  data files:       {len(lock.data_files)}")
    if lock.figure_sha256:
        click.echo(f"  figure:           {lock.figure_sha256[:16]}...")


@main.command("replay")
@click.argument("lock_path", type=click.Path(exists=True, path_type=Path))
@click.option("--workdir", type=click.Path(path_type=Path), default=Path("."))
@click.option("--recipe", type=str, required=False,
              help="Recipe full_name to re-render (defaults to the lock's recipe if known).")
def replay_cmd(lock_path: Path, workdir: Path, recipe: str | None) -> None:
    """Replay a panelforge.lock.json — verify env match + (in v2.2.0)
    report drift diagnostics. Full uv-sync re-render is post-v2.2.
    """
    from panelforge_figures.manifest.reproducibility import (
        ReproducibilityError,
        load_lock,
        replay_lock,
    )

    try:
        lock = load_lock(lock_path)
    except ReproducibilityError as exc:
        click.echo(click.style(f"✗ failed to load lock: {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)

    click.echo(f"replaying {lock_path}")
    click.echo(f"  panelforge:  {lock.panelforge_version}")
    click.echo(f"  git commit:  {lock.panelforge_git_commit[:8]}")
    click.echo(f"  python:      {lock.environment.python_version}")
    click.echo(f"  created:     {lock.created_at}")
    click.echo()

    result = replay_lock(
        lock,
        workdir=workdir,
        recipe_full_name=recipe or "<unknown>",
        contract_dict={},
    )

    if result.success:
        click.echo(click.style("✓ env matches lock", fg="green"))
        for msg in result.log_messages:
            click.echo(f"  {msg}")
    else:
        click.echo(click.style("✗ env drift detected", fg="red"))
        for field, diff in result.drift_diagnostics.items():
            click.echo(f"  {field}: expected {diff['expected']!r}, actual {diff['actual']!r}")
        click.get_current_context().exit(1)


# ─────────────────── adaptive power analysis (E4 — v2.3.0) ──────────────

@main.command("power")
@click.argument("recipe", type=str)
@click.option("--effect-size", "-e", type=float, required=True,
              help="Effect size in the family's native units (e.g. Cohen's d=0.3).")
@click.option("--alpha", "-a", type=float, default=0.05)
@click.option("--power", "-p", "power_target", type=float, default=0.80,
              help="Desired statistical power (default 0.80).")
@click.option("--n-groups", type=int, default=2,
              help="Number of groups (e.g. 2 for t-test, 4 for 2x2 factorial).")
@click.option("--df-num", type=int, default=None,
              help="Numerator degrees of freedom (for ANOVA / chi-square).")
@click.option("--df-den", type=int, default=None,
              help="Denominator degrees of freedom (for ANOVA).")
@click.option("--montecarlo-iterations", type=int, default=1000,
              help="MC iterations for nonparametric families (default 1000).")
@click.option("--effect-size-units", type=str, default=None)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON output.")
def power_cmd(
    recipe: str, effect_size: float, alpha: float,
    power_target: float, n_groups: int,
    df_num: int | None, df_den: int | None,
    montecarlo_iterations: int, effect_size_units: str | None,
    as_json: bool,
) -> None:
    """Compute required N for a recipe at given effect size + alpha + power.

    Example:
      figures power two_way_anova_summary_plot -e 0.3 -a 0.05 -p 0.8
    """
    import json as _json

    from panelforge_figures.core.contract import (
        ensure_all_imported,
        list_recipes,
    )
    from panelforge_figures.manifest.power import (
        PowerError,
        compute_required_n,
    )

    ensure_all_imported()
    recipes = list_recipes()

    # Find the recipe by full_name OR bare name (modality.name OR name)
    matched = None
    for info in recipes:
        full = f"{info.metadata.modality}.{info.metadata.name}"
        if recipe == full or recipe == info.metadata.name:
            matched = info
            break

    if matched is None:
        click.echo(click.style(
            f"✗ no recipe matching {recipe!r}; "
            f"use `figures list-recipes` to see options",
            fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    family = matched.metadata.family.value
    full_name = f"{matched.metadata.modality}.{matched.metadata.name}"

    try:
        result = compute_required_n(
            recipe_full_name=full_name,
            family=family,
            effect_size=effect_size,
            alpha=alpha,
            power_target=power_target,
            df_num=df_num, df_den=df_den,
            n_groups=n_groups,
            montecarlo_iterations=montecarlo_iterations,
            effect_size_units=effect_size_units,
        )
    except PowerError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    if as_json:
        click.echo(_json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return

    # Human-friendly output
    click.echo(click.style(
        f"power analysis: {full_name}", fg="cyan"))
    click.echo(f"  family:           {result.family}")
    click.echo(f"  method:           {result.method.value}")
    click.echo(f"  effect_size:      {result.effect_size}  ({result.effect_size_units})")
    click.echo(f"  alpha:            {result.alpha}")
    click.echo(f"  power_target:     {result.power_target}")
    click.echo(click.style(
        f"  required_n_per_group: {result.required_n_per_group}",
        fg="green", bold=True))
    click.echo(f"  required_n_total:    {result.required_n_total}")
    if result.montecarlo_iterations:
        click.echo(f"  mc_iterations:    {result.montecarlo_iterations}")
    for note in result.notes:
        click.echo(f"  note:             {note}")


# ─────────────────────────── mcp (E1 — v2.1.0) ────────────────────────────


@main.group("mcp")
def mcp_group() -> None:
    """Model Context Protocol server — expose recipes as Claude tools."""


@mcp_group.command("serve")
@click.option(
    "--transport",
    type=click.Choice(["stdio"]),
    default="stdio",
    help="Transport (only stdio supported in v2.1).",
)
@click.option("--no-recipes", is_flag=True, help="Disable recipe tools.")
@click.option("--no-scorer", is_flag=True, help="Disable scorer tools.")
@click.option("--no-index", is_flag=True, help="Disable index tools.")
@click.option("--no-provenance", is_flag=True, help="Disable provenance tools.")
@click.option("--no-projects", is_flag=True, help="Disable projects tools.")
@click.option(
    "--with-telemetry",
    is_flag=True,
    help="Expose telemetry tools (gated; runtime may still refuse).",
)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Project root containing panelforge.project.yaml.",
)
def mcp_serve_cmd(
    transport: str,
    no_recipes: bool,
    no_scorer: bool,
    no_index: bool,
    no_provenance: bool,
    no_projects: bool,
    with_telemetry: bool,
    project_root: Path | None,
) -> None:
    """Run the panelforge MCP server (stdio transport).

    NOTE: stdout is reserved for MCP protocol messages only.  All status
    messages go to stderr via ``click.echo(..., err=True)``.
    """
    # Imports are lazy so the rest of the CLI works without the [mcp] extra.
    from ..mcp import MCPServerConfig, MCPUnavailableError, serve_stdio

    config = MCPServerConfig(
        expose_recipes=not no_recipes,
        expose_scorer=not no_scorer,
        expose_index=not no_index,
        expose_provenance=not no_provenance,
        expose_projects=not no_projects,
        expose_telemetry=with_telemetry,
        project_root=project_root,
    )

    try:
        import asyncio

        asyncio.run(serve_stdio(config))
    except MCPUnavailableError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
    except KeyboardInterrupt:
        click.echo("✓ MCP server shut down.", err=True)


# ─────────────────────────── verify-claims (E2 — v2.5.0) ──────────────────


@main.command("verify-claims")
@click.argument(
    "manuscript",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--figures",
    "figures_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("panelforge_workspace/figures"),
    help="Directory of rendered figures + provenance sidecars.",
)
@click.option("--alpha", type=float, default=0.05, help="Significance threshold.")
@click.option(
    "--correlation-threshold",
    type=float,
    default=0.1,
    help="Minimum |r| for a correlation to be considered present.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of Markdown.")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the report (default: stdout).",
)
def verify_claims_cmd(
    manuscript: Path,
    figures_dir: Path,
    alpha: float,
    correlation_threshold: float,
    as_json: bool,
    output: Path | None,
) -> None:
    """Cross-check Figure N claims in MANUSCRIPT against rendered figures."""
    from panelforge_figures.manifest.claim_check import (
        render_markdown_report,
        report_to_dict,
        verify_manuscript,
    )

    report = verify_manuscript(
        manuscript,
        figures_dir,
        alpha=alpha,
        correlation_threshold=correlation_threshold,
    )

    if as_json:
        text = json.dumps(report_to_dict(report), indent=2)
    else:
        text = render_markdown_report(report)

    if output:
        output.write_text(text, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"))
    else:
        click.echo(text)

    if report.n_unsupported > 0:
        click.echo(
            click.style(
                f"\n✗ {report.n_unsupported} unsupported claim(s) — exiting 1",
                fg="red",
            ),
            err=True,
        )
        click.get_current_context().exit(1)


# ────────────────────────── author-recipe (E6 — v3.0.0rc1) ────────────────


@main.command("author-recipe")
@click.option("--modality", required=True, type=str,
              help="Modality (lowercase_snake_case).")
@click.option("--name", "recipe_name", required=True, type=str,
              help="Recipe name (lowercase_snake_case).")
@click.option("--family", required=True,
              type=click.Choice([
                  "coef_forest", "comparison", "correlation",
                  "factorial", "equivalence",
              ]))
@click.option("--research-question", required=True, type=str,
              help="Plain-English research question this recipe is meant to answer.")
@click.option("--project-root", type=click.Path(path_type=Path), default=Path("."),
              help="Project root for the new recipe.")
@click.option("--overwrite", is_flag=True,
              help="Overwrite existing recipe / test files.")
@click.option("--render-demo/--no-render-demo", default=True,
              help="Render the demo PNG into docs/gallery/.")
def author_recipe_cmd(
    modality: str,
    recipe_name: str,
    family: str,
    research_question: str,
    project_root: Path,
    overwrite: bool,
    render_demo: bool,
) -> None:
    """Scaffold a new recipe (.py + test + gallery PNG) following the panelforge pattern.

    The author refines the rendering body; everything else is wired up.
    """
    from ..manifest.recipe_authoring import (
        RecipeAuthoringError,
        render_demo_to_gallery,
        scaffold_recipe,
        write_scaffold,
    )

    try:
        scaffold = scaffold_recipe(
            modality=modality,
            recipe_name=recipe_name,
            family=family,
            research_question=research_question,
            project_root=project_root,
        )
        paths = write_scaffold(scaffold, overwrite=overwrite)
        click.echo(click.style(f"✓ wrote {paths['recipe']}", fg="green"))
        click.echo(click.style(f"✓ wrote {paths['test']}", fg="green"))
        if render_demo:
            try:
                gallery_path = render_demo_to_gallery(scaffold)
                click.echo(click.style(f"✓ wrote {gallery_path}", fg="green"))
            except Exception as exc:  # pragma: no cover
                click.echo(click.style(
                    f"⚠ demo rendering failed: {exc}", fg="yellow"))
    except RecipeAuthoringError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)


# ─────────────────────── manuscript alignment (E7 — v3.0.0rc2) ───────────────


@main.command("align-manuscript")
@click.argument(
    "manuscript",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--backend",
    type=click.Choice(["tfidf", "sentence_transformers"]),
    default="tfidf",
    help="Similarity backend (tfidf is offline, no extra deps).",
)
@click.option("--top-n", type=int, default=20, help="Number of top recipes to show.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def align_manuscript_cmd(
    manuscript: Path, backend: str, top_n: int, as_json: bool,
) -> None:
    """Score recipes by their semantic alignment with the manuscript text.

    Output: ranked list of recipes whose ``answers_question`` matches
    sections in the manuscript.  Default backend (``tfidf``) requires no
    extra deps; ``sentence_transformers`` requires
    ``pip install panelforge-figures[embeddings]``.
    """
    import json as _json

    from ..core.contract import ensure_all_imported, list_recipes
    from ..manifest.manuscript_alignment import (
        AlignmentBackend,
        compute_alignment_scores,
        score_to_dict,
    )

    ensure_all_imported()
    recipes = list_recipes()
    scores = compute_alignment_scores(
        manuscript, recipes, backend=AlignmentBackend(backend),
    )
    scores.sort(key=lambda s: s.score, reverse=True)
    top = scores[:top_n]

    if as_json:
        click.echo(_json.dumps([score_to_dict(s) for s in top], indent=2))
        return

    click.echo(click.style(
        f"manuscript: {manuscript.name}  ·  backend: {backend}  ·  top {top_n}",
        fg="cyan",
    ))
    click.echo(f"{'rank':>4}  {'score':>5}  recipe")
    for i, s in enumerate(top, 1):
        click.echo(f"{i:>4}  {s.score:5.3f}  {s.recipe_full_name}")


# ─────────────── data-driven family recommender (E8 — v3.1.0) ─────────────


@main.command("recommend")
@click.argument(
    "data_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--top-k", type=int, default=5,
              help="Maximum number of family recommendations to display.")
@click.option("--show-gaps/--no-show-gaps", default=True,
              help="Surface families with no matching recipe as recipe gaps.")
@click.option("--json", "as_json", is_flag=True,
              help="Emit machine-readable JSON instead of a pretty table.")
def recommend_cmd(
    data_path: Path, top_k: int, show_gaps: bool, as_json: bool
) -> None:
    """Profile DATA_PATH and recommend high-value figure families.

    Default (no --json): prints a ranked table with rationale + matching
    recipes per family + recipe-gaps callout. The principled stance is
    preserved — the user picks the family from the recommendations.
    """
    import json as _json

    from ..manifest.family_recommender import (
        RecommenderError,
        detect_recipe_gaps,
        profile_data,
        recommend_families,
    )

    try:
        profile = profile_data(data_path)
    except RecommenderError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    recs = recommend_families(profile, top_k=top_k)
    gaps = detect_recipe_gaps(profile, recs) if show_gaps else []

    if as_json:
        click.echo(_json.dumps({
            "profile": profile.to_dict(),
            "recommendations": [
                {
                    "family": r.family,
                    "confidence": r.confidence,
                    "rationale": r.rationale,
                    "n_matching_recipes": r.n_matching_recipes,
                    "matching_recipes": list(r.matching_recipe_names),
                }
                for r in recs
            ],
            "gaps": [
                {
                    "family": g.family,
                    "data_profile_summary": g.data_profile_summary,
                    "suggested_recipe_name": g.suggested_recipe_name,
                    "suggested_modality": g.suggested_modality,
                    "suggested_research_question": g.suggested_research_question,
                    "rationale": g.rationale,
                }
                for g in gaps
            ],
        }, indent=2))
        return

    click.echo(click.style(
        f"data: {data_path.name}  ·  "
        f"{profile.n_rows} rows × {profile.n_cols} cols",
        fg="cyan",
    ))
    click.echo(f"  grouping:    {profile.grouping_structure.value}")
    click.echo(f"  factors:     {profile.candidate_factor_columns}")
    click.echo(f"  responses:   {profile.candidate_response_columns}")
    click.echo(
        f"  missing:     {profile.fraction_missing:.0%} "
        f"({profile.n_missing_total} cells)"
    )
    if profile.notes:
        for note in profile.notes:
            click.echo(click.style(f"  note: {note}", fg="yellow"))
    click.echo()

    if not recs:
        click.echo(click.style(
            "no families scored above the confidence floor — the data shape "
            "is unusual; consider providing a richer data file.",
            fg="yellow",
        ))
    else:
        click.echo(click.style("recommended families:", fg="green", bold=True))
        for i, r in enumerate(recs, 1):
            click.echo(
                f"  {i}. {r.family}  (confidence {r.confidence:.2f})"
            )
            click.echo(f"     rationale: {r.rationale}")
            click.echo(
                f"     matching recipes: {r.n_matching_recipes}"
            )
            for name in r.matching_recipe_names[:3]:
                click.echo(f"       · {name}")

    if gaps:
        click.echo()
        click.echo(click.style("recipe gaps detected:", fg="yellow", bold=True))
        for g in gaps:
            click.echo(f"  ⚠ family {g.family}: no good-fit recipe")
            click.echo(f"    suggested name: {g.suggested_recipe_name}")
            click.echo(
                f"    research question: {g.suggested_research_question}"
            )
            click.echo(f"    rationale: {g.rationale}")
        click.echo()
        click.echo(click.style(
            "→ scaffold a tailored recipe via:", fg="cyan",
        ))
        first_gap_family = gaps[0].family
        click.echo(
            "    figures fill-gap "
            f"--family {first_gap_family} --data {data_path} "
            f"--name {gaps[0].suggested_recipe_name}"
        )


@main.command("fill-gap")
@click.option("--family", required=True, type=str,
              help="Figure family to scaffold a recipe for.")
@click.option("--data", "data_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Data file used to derive the recipe scaffold.")
@click.option("--modality", type=str, default="custom_lab",
              help="Modality the new recipe lives in.")
@click.option("--name", "recipe_name", type=str, default=None,
              help="Recipe name (defaults to the auto-suggested gap name).")
@click.option("--research-question", type=str, default=None,
              help="Research question (defaults to the auto-suggested one).")
@click.option("--project-root", type=click.Path(path_type=Path),
              default=Path("."),
              help="Project root for the new recipe.")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def fill_gap_cmd(
    family: str,
    data_path: Path,
    modality: str,
    recipe_name: str | None,
    research_question: str | None,
    project_root: Path,
    yes: bool,
) -> None:
    """Interactively scaffold a tailored recipe for a (family, data) gap.

    Reads the data, computes a profile, generates a sensible default
    recipe_name + research_question if not given, prompts for confirmation,
    then invokes E6's ``scaffold_recipe`` + ``write_scaffold`` +
    ``render_demo_to_gallery``.
    """
    from ..manifest.family_recommender import (
        RecommenderError,
        detect_recipe_gaps,
        profile_data,
        recommend_families,
    )
    from ..manifest.recipe_authoring import (
        RecipeAuthoringError,
        render_demo_to_gallery,
        scaffold_recipe,
        write_scaffold,
    )

    try:
        profile = profile_data(data_path)
    except RecommenderError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    recs = recommend_families(profile)
    target = next((r for r in recs if r.family == family), None)
    if target is None:
        click.echo(click.style(
            f"✗ family {family!r} did not score above the confidence floor "
            "for this data; reconsider the data shape or use "
            "`figures author-recipe` to scaffold an unconstrained recipe.",
            fg="red",
        ), err=True)
        click.get_current_context().exit(1)
        return

    gaps = detect_recipe_gaps(profile, [target], confidence_threshold=0.0)
    gap = gaps[0] if gaps else None

    final_name = recipe_name or (
        gap.suggested_recipe_name if gap else f"{family}_custom_v1"
    )
    final_q = research_question or (
        gap.suggested_research_question
        if gap
        else "TODO: research question"
    )

    click.echo(click.style("about to scaffold:", fg="cyan"))
    click.echo(f"  modality:           {modality}")
    click.echo(f"  recipe_name:        {final_name}")
    click.echo(f"  family:             {family}")
    click.echo(f"  research_question:  {final_q}")
    click.echo(f"  project_root:       {project_root}")
    if target.n_matching_recipes > 0:
        click.echo(click.style(
            f"  note: {target.n_matching_recipes} matching recipe(s) already "
            "exist in the registry — you may not need a new one.",
            fg="yellow",
        ))

    if not yes:
        if not click.confirm("\nproceed?"):
            click.echo("aborted.")
            return

    try:
        scaffold = scaffold_recipe(
            modality=modality,
            recipe_name=final_name,
            family=family,
            research_question=final_q,
            project_root=project_root,
        )
        paths = write_scaffold(scaffold, overwrite=False)
        click.echo(click.style(f"✓ wrote {paths['recipe']}", fg="green"))
        click.echo(click.style(f"✓ wrote {paths['test']}", fg="green"))
        try:
            gallery_path = render_demo_to_gallery(scaffold)
            click.echo(click.style(f"✓ wrote {gallery_path}", fg="green"))
        except Exception as exc:  # pragma: no cover
            click.echo(click.style(
                f"⚠ demo render failed: {exc}", fg="yellow"))
    except RecipeAuthoringError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)


# ─────────────────── novelty scout (E9 — v3.2.0) ──────────────────────────


@main.command("novelty-scout")
@click.option(
    "--from-yaml", "yaml_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a panel-candidates YAML (one entry per panel: "
         "panel_id, recipe_full_name, research_question, [role], [modality]).",
)
@click.option(
    "--candidate-recipe", "candidate_recipes", multiple=True,
    help="Quick form: one recipe full_name per flag, "
         "research_question read from _META.answers_question.",
)
@click.option(
    "--target", type=click.Choice(["maximal", "balanced", "permissive"]),
    default="maximal",
)
@click.option(
    "--api-key", type=str, default=None,
    help="Consensus API key (default: $CONSENSUS_API_KEY).",
)
@click.option(
    "--mock", is_flag=True,
    help="Use MockConsensusClient (no live API calls; for offline testing).",
)
@click.option(
    "--output", type=click.Path(path_type=Path), default=None,
    help="Path for the markdown / JSON report (default: stdout markdown).",
)
@click.option(
    "--json", "as_json", is_flag=True,
    help="Emit machine-readable JSON instead of markdown.",
)
@click.option("--limit-per-query", type=int, default=20)
def novelty_scout_cmd(
    yaml_path: Path | None,
    candidate_recipes: tuple[str, ...],
    target: str,
    api_key: str | None,
    mock: bool,
    output: Path | None,
    as_json: bool,
    limit_per_query: int,
) -> None:
    """Score figure-plan panels by literature novelty (Consensus.app backed).

    Classifies each panel as REPETITION / INCREMENTAL / HIDDEN_NOVELTY /
    ULTRA_NOVELTY. Supporting panels (controls / baselines / methodology /
    provenance) are PROTECTED from demotion regardless of class.

    With --target=maximal (default), recommends:

      promote ULTRA_NOVELTY     -> main figure prominence
      keep + flag HIDDEN_NOVELTY (opportunity)
      demote INCREMENTAL        -> supplementary
      drop REPETITION
    """
    import json as _json

    import yaml

    from panelforge_figures.manifest.novelty_scout import (
        ConsensusProClient,
        ConsensusUnavailableError,
        MockConsensusClient,
        PanelCandidate,
        PanelRole,
        TargetNovelty,
        render_markdown_report,
        score_figure_plan,
    )

    # Build panel candidates from input source
    panels: list[PanelCandidate] = []
    if yaml_path:
        data = yaml.safe_load(yaml_path.read_text()) or {}
        for entry in data.get("panels", []):
            panels.append(
                PanelCandidate(
                    panel_id=entry["panel_id"],
                    recipe_full_name=entry["recipe_full_name"],
                    research_question=entry.get("research_question") or "",
                    role=PanelRole(entry.get("role", "auto")),
                    figure_id=entry.get("figure_id"),
                    modality=entry.get("modality"),
                    extra_query_terms=tuple(entry.get("extra_query_terms", []) or []),
                )
            )
    if candidate_recipes:
        ensure_all_imported()
        recipes = {
            f"{r.metadata.modality}.{r.metadata.name}": r
            for r in list_recipes()
        }
        for full_name in candidate_recipes:
            r = recipes.get(full_name)
            if r is None:
                click.echo(
                    click.style(
                        f"⚠ recipe {full_name!r} not found in registry — skipping",
                        fg="yellow",
                    ),
                    err=True,
                )
                continue
            panels.append(
                PanelCandidate(
                    panel_id=full_name,
                    recipe_full_name=full_name,
                    research_question=r.metadata.answers_question,
                    modality=r.metadata.modality,
                )
            )
    if not panels:
        click.echo(
            click.style(
                "✗ no panels to assess — pass --from-yaml or --candidate-recipe",
                fg="red",
            ),
            err=True,
        )
        click.get_current_context().exit(1)
        return

    # Pick the client
    client: Any
    if mock:
        client = MockConsensusClient()
        click.echo(
            click.style(
                "[mock] using MockConsensusClient — no live API calls",
                fg="yellow",
            )
        )
    else:
        try:
            client = ConsensusProClient(api_key=api_key)
        except ConsensusUnavailableError as exc:
            click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
            click.get_current_context().exit(1)
            return

    # Run scoring
    target_enum = TargetNovelty(target)
    report = score_figure_plan(panels, client, target=target_enum)

    # Emit
    if as_json:
        text = _json.dumps(report.to_dict(), indent=2)
    else:
        text = render_markdown_report(report)

    if output:
        output.write_text(text)
        click.echo(click.style(f"✓ wrote {output}", fg="green"))
    else:
        click.echo(text)

    # Brief stderr summary regardless
    click.echo(
        click.style(
            f"\n→ verdict: {report.overall_verdict}  "
            f"(density {report.novelty_density:.2f}; "
            f"{report.n_ultra_novelty} ultra, {report.n_hidden_novelty} hidden, "
            f"{report.n_incremental} incremental, {report.n_repetition} repetition, "
            f"{report.n_protected} supporting-protected)",
            fg="cyan",
        ),
        err=True,
    )


# ─────────────────── figures-scout orchestrator (E9 — phase 2, v3.3.0) ─────


@main.command("scout")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--max-figures", type=int, default=4)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default="cell",
)
@click.option(
    "--target-novelty",
    type=click.Choice(["maximal", "balanced", "permissive", "none"]),
    default="maximal",
)
@click.option(
    "--mock-novelty/--live-novelty", default=False,
    help="Use MockConsensusClient (no live API calls).",
)
@click.option(
    "--plan-out", type=click.Path(path_type=Path),
    default=Path("figures_plan.yaml"),
)
@click.option(
    "--report-out", type=click.Path(path_type=Path), default=None,
    help="Markdown report path (default: stdout).",
)
@click.option(
    "--manuscript-policy",
    type=click.Choice(["detect", "update", "propose", "preserve"]),
    default="detect",
    help="What to do when an existing manuscript is found (E10).",
)
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--interactive",
    is_flag=True,
    help="Open interactive TUI (requires panelforge-figures[tui]).",
)
def scout_cmd(
    project_root: Path,
    max_figures: int,
    venue: str,
    target_novelty: str,
    mock_novelty: bool,
    plan_out: Path,
    report_out: Path | None,
    manuscript_policy: str,
    as_json: bool,
    interactive: bool,
) -> None:
    """Walk PROJECT_ROOT, propose a multi-figure narrative plan, surface gaps + novelty."""
    if interactive:
        from .tui_scout import InteractiveScoutError, run_interactive_scout
        try:
            out = run_interactive_scout(
                project_root,
                max_figures=max_figures,
                venue=venue,
                target_novelty=target_novelty,
                use_mock_novelty=mock_novelty,
                plan_out=plan_out,
            )
        except InteractiveScoutError as exc:
            click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
            click.get_current_context().exit(1)
            return
        click.echo(click.style(f"\n✓ interactive session saved → {out}", fg="green"))
        return
    import json as _json

    from panelforge_figures.manifest.scout import (
        render_scout_report_markdown,
        save_figure_plan_yaml,
        scout_project,
    )

    report = scout_project(
        project_root,
        max_figures=max_figures,
        venue=venue,
        target_novelty=target_novelty,
        use_mock_novelty=mock_novelty,
        manuscript_policy=manuscript_policy,
    )

    save_figure_plan_yaml(report.figure_plan, plan_out)
    click.echo(click.style(f"✓ wrote {plan_out}", fg="green"), err=True)

    if as_json:
        text = _json.dumps(report.to_dict(), indent=2, default=str)
    else:
        text = render_scout_report_markdown(report)

    if report_out:
        report_out.write_text(text)
        click.echo(click.style(f"✓ wrote {report_out}", fg="green"), err=True)
    else:
        click.echo(text)

    click.echo(
        click.style(
            f"\n→ next: figures execute-plan {plan_out}",
            fg="cyan",
        ),
        err=True,
    )


@main.command("execute-plan")
@click.argument(
    "plan_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--yes", is_flag=True, help="Skip per-gap confirmation prompts.")
@click.option(
    "--no-scaffold-recipes", "scaffold_recipes",
    flag_value=False, default=True,
)
@click.option(
    "--no-render-figures", "render_figures",
    flag_value=False, default=True,
)
@click.option(
    "--no-draft-captions", "draft_captions",
    flag_value=False, default=True,
)
@click.option(
    "--no-scaffold-manuscript", "scaffold_manuscript",
    flag_value=False, default=True,
)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default="cell",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]), default="latex",
)
@click.option(
    "--manuscript-policy",
    type=click.Choice(["detect", "update", "propose", "preserve"]),
    default="preserve",
    help="What to do when an existing manuscript is found (E10).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-render even when the cache says inputs are unchanged (E11).",
)
def execute_plan_cmd(
    plan_path: Path,
    yes: bool,
    scaffold_recipes: bool,
    render_figures: bool,
    draft_captions: bool,
    scaffold_manuscript: bool,
    venue: str,
    fmt: str,
    manuscript_policy: str,
    force: bool,
) -> None:
    """Execute a figures_plan.yaml: scaffold gaps, render figures, draft captions, scaffold manuscript."""
    from panelforge_figures.manifest.execute_plan import (
        ExecutionError,
        execute_plan,
    )

    try:
        result = execute_plan(
            plan_path, yes=yes, scaffold_recipes=scaffold_recipes,
            render_figures=render_figures, draft_captions=draft_captions,
            scaffold_manuscript=scaffold_manuscript,
            manuscript_venue=venue, manuscript_format=fmt,
            manuscript_policy=manuscript_policy,
            force=force,
        )
    except ExecutionError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    click.echo(
        click.style(
            f"\n✓ done. {result.n_panels_rendered}/{result.n_panels_attempted} "
            f"panels rendered, "
            f"{result.n_panels_cached} cached, "
            f"{result.n_recipes_scaffolded} recipes scaffolded, "
            f"{result.n_captions_drafted} captions drafted",
            fg="green",
        )
    )
    if result.manuscript_path:
        click.echo(
            click.style(
                f"  manuscript: {result.manuscript_path}",
                fg="green",
            )
        )
    for panel_id, status, msg in result.panels_status:
        sym = {
            "rendered": "✓",
            "scaffolded_then_rendered": "+",
            "cached": "=",
            "skipped_gap": "!",
            "failed": "x",
        }.get(status, ".")
        click.echo(f"  {sym} {panel_id}  {status}  {msg}")


@main.command("manuscript-scaffold")
@click.argument(
    "plan_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default="cell",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]), default="latex",
)
@click.option("--output", type=click.Path(path_type=Path), default=None)
@click.option("--overwrite", is_flag=True)
def manuscript_scaffold_cmd(
    plan_path: Path,
    venue: str,
    fmt: str,
    output: Path | None,
    overwrite: bool,
) -> None:
    """Scaffold manuscript/main.tex from a figures_plan.yaml."""
    from panelforge_figures.manifest.manuscript_scaffold import (
        ManuscriptFormat,
        ScaffoldError,
        Venue,
        scaffold_manuscript,
    )
    from panelforge_figures.manifest.scout import load_figure_plan_yaml

    plan = load_figure_plan_yaml(plan_path)
    try:
        result = scaffold_manuscript(
            plan,
            project_root=plan.project_root,
            venue=Venue(venue),
            format=ManuscriptFormat(fmt),
            output_path=output,
            overwrite=overwrite,
        )
    except ScaffoldError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    click.echo(
        click.style(f"✓ wrote {result.manuscript_path}", fg="green")
    )
    click.echo(
        click.style(f"✓ wrote {result.references_path}", fg="green")
    )
    click.echo(f"  venue:               {result.venue.value}")
    click.echo(f"  format:              {result.format.value}")
    click.echo(f"  figures:             {result.n_figures}")
    click.echo(f"  captions drafted:    {result.n_captions_drafted}")
    click.echo(f"  methods paragraphs:  {result.n_methods_paragraphs}")


# ─────────────── E10 — manuscript group (scaffold + blueprint-import) ────────


@main.group("manuscript")
def manuscript_group() -> None:
    """Manuscript scaffolding, blueprint-import, and collision handling."""


@manuscript_group.command("scaffold")
@click.argument(
    "plan_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default="cell",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]), default="latex",
)
@click.option("--output", type=click.Path(path_type=Path), default=None)
@click.option("--overwrite", is_flag=True)
def manuscript_scaffold_group_cmd(
    plan_path: Path,
    venue: str,
    fmt: str,
    output: Path | None,
    overwrite: bool,
) -> None:
    """Scaffold manuscript/main.tex from a figures_plan.yaml.

    This is an alias for the top-level ``figures manuscript-scaffold``
    command — placed inside the new ``manuscript`` group for ergonomic
    grouping with ``manuscript blueprint-import``.
    """
    from panelforge_figures.manifest.manuscript_scaffold import (
        ManuscriptFormat,
        ScaffoldError,
        Venue,
        scaffold_manuscript,
    )
    from panelforge_figures.manifest.scout import load_figure_plan_yaml

    plan = load_figure_plan_yaml(plan_path)
    try:
        result = scaffold_manuscript(
            plan,
            project_root=plan.project_root,
            venue=Venue(venue),
            format=ManuscriptFormat(fmt),
            output_path=output,
            overwrite=overwrite,
        )
    except ScaffoldError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    click.echo(click.style(f"✓ wrote {result.manuscript_path}", fg="green"))
    click.echo(click.style(f"✓ wrote {result.references_path}", fg="green"))
    click.echo(f"  venue:               {result.venue.value}")
    click.echo(f"  format:              {result.format.value}")
    click.echo(f"  figures:             {result.n_figures}")
    click.echo(f"  captions drafted:    {result.n_captions_drafted}")
    click.echo(f"  methods paragraphs:  {result.n_methods_paragraphs}")


@manuscript_group.command("blueprint-import")
@click.argument(
    "manuscript_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out", "output_plan_path",
    type=click.Path(path_type=Path),
    default=Path("figures_plan.yaml"),
    help="Where to write the emitted figures_plan.yaml.",
)
@click.option("--min-similarity", type=float, default=0.4)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default=None,
    help="Override venue (default: derive from manuscript hint, else cell).",
)
@click.option("--json", "as_json", is_flag=True)
def blueprint_import_cmd(
    manuscript_path: Path,
    output_plan_path: Path,
    min_similarity: float,
    venue: str | None,
    as_json: bool,
) -> None:
    """Inverse direction: manuscript → figures_plan.yaml.

    Parses an existing manuscript, identifies figure captions, matches each
    to a panelforge recipe via caption similarity, emits figures_plan.yaml.
    Captions with no good-fit recipe are flagged as gaps for ``figures fill-gap``.
    """
    from panelforge_figures.manifest.manuscript_blueprint import (
        BlueprintImportError,
        import_blueprint_from_manuscript,
    )

    try:
        result = import_blueprint_from_manuscript(
            manuscript_path,
            output_plan_path=output_plan_path,
            min_similarity=min_similarity,
            venue=venue,
        )
    except BlueprintImportError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    if as_json:
        import json as _json
        payload = {
            "manuscript_path": str(result.manuscript_path),
            "n_figures_parsed": result.n_figures_parsed,
            "n_figures_matched": result.n_figures_matched,
            "n_figures_unmatched": result.n_figures_unmatched,
            "figure_plan_path": (
                str(result.figure_plan_path)
                if result.figure_plan_path else None
            ),
            "matches": [
                {
                    "figure_id": m.figure_id,
                    "caption_excerpt": m.caption_excerpt,
                    "suggested_recipe_full_name": m.suggested_recipe_full_name,
                    "similarity_score": m.similarity_score,
                    "candidate_alternatives": list(m.candidate_alternatives),
                }
                for m in result.matches
            ],
            "notes": list(result.notes),
        }
        click.echo(_json.dumps(payload, indent=2, default=str))
        return

    if result.figure_plan_path:
        click.echo(
            click.style(f"✓ wrote {result.figure_plan_path}", fg="green")
        )
    click.echo(f"  manuscript:        {result.manuscript_path}")
    click.echo(f"  figures parsed:    {result.n_figures_parsed}")
    click.echo(f"  matched:           {result.n_figures_matched}")
    click.echo(f"  unmatched (gaps):  {result.n_figures_unmatched}")
    for m in result.matches:
        marker = "·" if m.similarity_score >= min_similarity else "GAP"
        recipe = m.suggested_recipe_full_name or "(no match)"
        click.echo(
            f"  {marker:4s} {m.figure_id:12s} "
            f"sim={m.similarity_score:.2f}  →  {recipe}"
        )
    for note in result.notes:
        click.echo(click.style(f"  note: {note}", fg="yellow"))


# ─────────────── E11 — render cache (status / clear / invalidate) ─────────────


@main.group("cache")
def cache_group() -> None:
    """Inspect and manage the incremental render cache (E11).

    The cache lives at ``panelforge_workspace/render_cache.json`` and
    tracks per-panel SHAs so ``figures execute-plan`` can skip panels
    whose inputs haven't changed since the last render.
    """


@cache_group.command("status")
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge_workspace/ (default: cwd).",
)
def cache_status_cmd(project_root: Path) -> None:
    """Show cache state: file path, entry count, oldest, newest."""
    from panelforge_figures.manifest.render_cache import (
        cache_path_for_project,
        load_cache,
    )

    cache = load_cache(project_root)
    path = cache_path_for_project(project_root)
    click.echo(f"cache: {path}")
    click.echo(f"exists: {path.exists()}")
    click.echo(f"entries: {len(cache.entries)}")
    if cache.entries:
        sorted_by_time = sorted(
            cache.entries.values(), key=lambda e: e.rendered_at
        )
        click.echo(f"oldest: {sorted_by_time[0].rendered_at}")
        click.echo(f"newest: {sorted_by_time[-1].rendered_at}")
        click.echo()
        click.echo(
            f"{'panel_id':<24}  {'figure_id':<12}  "
            f"{'rendered_at':<20}  recipe"
        )
        for e in sorted_by_time:
            click.echo(
                f"{e.panel_id:<24}  {e.figure_id:<12}  "
                f"{e.rendered_at:<20}  {e.recipe_full_name}"
            )


@cache_group.command("clear")
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge_workspace/ (default: cwd).",
)
@click.option(
    "--yes", is_flag=True,
    help="Skip the confirmation prompt.",
)
def cache_clear_cmd(project_root: Path, yes: bool) -> None:
    """Delete the render cache file (force a full re-render next time)."""
    from panelforge_figures.manifest.render_cache import cache_path_for_project

    path = cache_path_for_project(project_root)
    if not path.exists():
        click.echo("cache is already empty")
        return
    if not yes and not click.confirm(f"delete {path}?"):
        click.echo("aborted")
        return
    path.unlink()
    click.echo(click.style(f"✓ deleted {path}", fg="green"))


@cache_group.command("invalidate")
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Project root containing panelforge_workspace/ (default: cwd).",
)
@click.option(
    "--panel-id",
    multiple=True,
    required=True,
    help="Panel ID(s) to remove from the cache; may be passed multiple times.",
)
def cache_invalidate_cmd(project_root: Path, panel_id: tuple[str, ...]) -> None:
    """Remove specific panel(s) from the cache, forcing re-render next time."""
    from panelforge_figures.manifest.render_cache import load_cache, save_cache

    cache = load_cache(project_root)
    removed = 0
    for pid in panel_id:
        if cache.get(pid):
            cache.remove(pid)
            removed += 1
            click.echo(click.style(f"✓ removed {pid}", fg="green"))
        else:
            click.echo(click.style(f"! {pid} not in cache", fg="yellow"))
    save_cache(cache, project_root)
    click.echo(f"\n{removed} panel(s) invalidated")


# ────────── E12 — STAR Methods + reporting checklists (v3.6.0) ────────────


@main.command("star-methods")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--plan-path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to figures_plan.yaml; if absent, no per-recipe methods text.",
)
@click.option(
    "--venue",
    type=click.Choice(["plain", "nature", "cell", "nejm", "biorxiv", "science"]),
    default="cell",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]),
    default="latex",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="If set, write the rendered output to this file.",
)
def star_methods_cmd(
    project_root: Path,
    plan_path: Path | None,
    venue: str,
    fmt: str,
    out: Path | None,
) -> None:
    """Generate STAR Methods table + sections from project state."""
    from panelforge_figures.manifest.scout import load_figure_plan_yaml
    from panelforge_figures.manifest.star_methods import (
        StarMethodsError,
        generate_star_methods,
        render_star_methods_table_latex,
        render_star_methods_table_markdown,
    )

    plan = None
    if plan_path is not None:
        try:
            plan = load_figure_plan_yaml(plan_path)
        except Exception as exc:
            click.echo(
                click.style(f"✗ failed to load plan: {exc}", fg="red"), err=True
            )
            click.get_current_context().exit(1)
            return

    try:
        table = generate_star_methods(
            project_root, plan, venue=venue, format=fmt
        )
    except StarMethodsError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    if fmt == "latex":
        body = render_star_methods_table_latex(table)
    else:
        body = render_star_methods_table_markdown(table)

    sections: list[str] = []
    sections.append(body)

    if table.method_details_paragraphs:
        if fmt == "latex":
            sections.append(r"\subsection*{Method Details}")
        else:
            sections.append("## Method Details")
        for family in sorted(table.method_details_paragraphs):
            sections.append(table.method_details_paragraphs[family])

    if table.quantification_paragraphs:
        if fmt == "latex":
            sections.append(r"\subsection*{Quantification and Statistical Analysis}")
        else:
            sections.append("## Quantification and Statistical Analysis")
        for family in sorted(table.quantification_paragraphs):
            sections.append(table.quantification_paragraphs[family])

    if fmt == "latex":
        sections.append(r"\subsection*{Data and Code Availability}")
    else:
        sections.append("## Data and Code Availability")
    sections.append(table.data_and_code_section)

    output_text = "\n\n".join(sections) + "\n"

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output_text, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {out}", fg="green"))
    else:
        click.echo(output_text)

    click.echo(
        click.style(
            f"  Key Resources Table:        {len(table.key_resources)} rows",
            fg="cyan",
        ),
        err=True,
    )
    click.echo(
        click.style(
            f"  Method-details paragraphs:  {len(table.method_details_paragraphs)}",
            fg="cyan",
        ),
        err=True,
    )
    click.echo(
        click.style(
            f"  Quantification paragraphs:  {len(table.quantification_paragraphs)}",
            fg="cyan",
        ),
        err=True,
    )
    click.echo(
        click.style(f"  Venue: {table.venue}; format: {fmt}", fg="cyan"),
        err=True,
    )


@main.group("checklist")
def checklist_group() -> None:
    """Reporting checklists: ARRIVE / CONSORT / STARD / MIQE."""


def _render_and_write_checklist(checklist, fmt: str, out: Path | None) -> None:
    from panelforge_figures.manifest.reporting_checklists import (
        render_checklist_latex,
        render_checklist_markdown,
    )

    if fmt == "latex":
        body = render_checklist_latex(checklist)
    else:
        body = render_checklist_markdown(checklist)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {out}", fg="green"))
    else:
        click.echo(body)

    total = (
        checklist.n_present
        + checklist.n_absent
        + checklist.n_not_applicable
        + checklist.n_unknown
    )
    click.echo(
        click.style(f"  {checklist.kind.value} — total {total} items", fg="cyan"),
        err=True,
    )
    click.echo(
        click.style(
            f"  present={checklist.n_present}  absent={checklist.n_absent}  "
            f"n/a={checklist.n_not_applicable}  unknown={checklist.n_unknown}",
            fg="cyan",
        ),
        err=True,
    )


def _load_plan_if_any(plan_path: Path | None):
    if plan_path is None:
        return None
    try:
        from panelforge_figures.manifest.scout import load_figure_plan_yaml

        return load_figure_plan_yaml(plan_path)
    except Exception:
        return None


@checklist_group.command("arrive")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--manuscript",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to manuscript file (.md or .tex) for keyword scanning.",
)
@click.option(
    "--plan-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to figures_plan.yaml for contract-evidence classification.",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]),
    default="markdown",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
)
def checklist_arrive_cmd(
    project_root: Path,
    manuscript: Path | None,
    plan_path: Path | None,
    fmt: str,
    out: Path | None,
) -> None:
    """Generate ARRIVE 2.0 checklist for animal-research papers."""
    from panelforge_figures.manifest.reporting_checklists import (
        ChecklistError,
        generate_arrive_checklist,
    )

    plan = _load_plan_if_any(plan_path)
    try:
        checklist = generate_arrive_checklist(
            project_root, manuscript_path=manuscript, figure_plan=plan
        )
    except ChecklistError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    _render_and_write_checklist(checklist, fmt, out)


@checklist_group.command("consort")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--manuscript",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--plan-path",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]),
    default="markdown",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
)
def checklist_consort_cmd(
    project_root: Path,
    manuscript: Path | None,
    plan_path: Path | None,
    fmt: str,
    out: Path | None,
) -> None:
    """Generate CONSORT 2010 checklist for randomised controlled trials."""
    from panelforge_figures.manifest.reporting_checklists import (
        ChecklistError,
        generate_consort_checklist,
    )

    plan = _load_plan_if_any(plan_path)
    try:
        checklist = generate_consort_checklist(
            project_root, manuscript_path=manuscript, figure_plan=plan
        )
    except ChecklistError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    _render_and_write_checklist(checklist, fmt, out)


@checklist_group.command("stard")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--manuscript",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--plan-path",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]),
    default="markdown",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
)
def checklist_stard_cmd(
    project_root: Path,
    manuscript: Path | None,
    plan_path: Path | None,
    fmt: str,
    out: Path | None,
) -> None:
    """Generate STARD 2015 checklist for diagnostic-accuracy studies."""
    from panelforge_figures.manifest.reporting_checklists import (
        ChecklistError,
        generate_stard_checklist,
    )

    plan = _load_plan_if_any(plan_path)
    try:
        checklist = generate_stard_checklist(
            project_root, manuscript_path=manuscript, figure_plan=plan
        )
    except ChecklistError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    _render_and_write_checklist(checklist, fmt, out)


@checklist_group.command("miqe")
@click.argument(
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--manuscript",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--plan-path",
    type=click.Path(path_type=Path),
    default=None,
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["latex", "markdown"]),
    default="markdown",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
)
def checklist_miqe_cmd(
    project_root: Path,
    manuscript: Path | None,
    plan_path: Path | None,
    fmt: str,
    out: Path | None,
) -> None:
    """Generate MIQE checklist for qPCR experiments."""
    from panelforge_figures.manifest.reporting_checklists import (
        ChecklistError,
        generate_miqe_checklist,
    )

    plan = _load_plan_if_any(plan_path)
    try:
        checklist = generate_miqe_checklist(
            project_root, manuscript_path=manuscript, figure_plan=plan
        )
    except ChecklistError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    _render_and_write_checklist(checklist, fmt, out)


# ─────────────────────── xref linter (E13 — v3.7.0) ──────────────────────────


@main.group("lint")
def lint_group() -> None:
    """Manuscript / figure linting commands."""


@lint_group.command("xrefs")
@click.argument(
    "manuscript_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--figures",
    "figures_dir",
    type=click.Path(path_type=Path),
    default=Path("panelforge_workspace/figures"),
    help="Directory containing rendered figure files (pdf/png/svg).",
)
@click.option(
    "--min-caption-chars",
    type=int,
    default=30,
    help="Minimum caption length before emitting caption_too_short.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Write report to this file instead of stdout.",
)
@click.option(
    "--json", "as_json", is_flag=True,
    help="Emit machine-readable JSON instead of markdown.",
)
@click.option(
    "--fail-on-warning", is_flag=True,
    help="Exit 1 on any warning, not just errors.",
)
def lint_xrefs_cmd(
    manuscript_path: Path,
    figures_dir: Path,
    min_caption_chars: int,
    output: Path | None,
    as_json: bool,
    fail_on_warning: bool,
) -> None:
    """Cross-reference linter: orphan refs/figures, missing captions, dead paths."""
    import json as _json

    from ..manifest.xref_linter import (
        LintError,
        lint_xrefs,
        render_lint_report_markdown,
    )

    try:
        report = lint_xrefs(
            manuscript_path,
            figures_dir=figures_dir if figures_dir and figures_dir.exists() else None,
            min_caption_chars=min_caption_chars,
        )
    except LintError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(2)
        return

    if as_json:
        text = _json.dumps(report.to_dict(), indent=2, default=str)
    else:
        text = render_lint_report_markdown(report)

    if output is not None:
        output.write_text(text, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"))
    else:
        click.echo(text)

    if report.n_errors > 0:
        click.get_current_context().exit(1)
    elif fail_on_warning and report.n_warnings > 0:
        click.get_current_context().exit(1)


# ─────────────────────── E14: smart citation insertion ───────────────────────


@main.group("cite")
def cite_group() -> None:
    """Citation suggestion + insertion commands.

    The ``cite`` group reads cached Consensus.app paper records (produced
    by E9-phase-1 / ``novelty-scout``) and proposes ``\\cite{...}``
    insertions for claim sentences in the target manuscript. Default
    mode is a non-destructive dry-run preview; pass ``--apply`` to
    write the insertions and augment ``references.bib`` in place.
    """


@cite_group.command("suggest")
@click.argument(
    "manuscript_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--cache-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Consensus cache dir (default: panelforge_workspace/.consensus_cache "
         "under the manuscript's parent).",
)
@click.option("--min-similarity", type=float, default=0.6,
              help="Minimum cosine similarity between cached query and claim "
                   "sentence (default: 0.6).")
@click.option(
    "--bib-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Existing references.bib path for cite-key dedup "
         "(default: manuscript_path.parent/references.bib).",
)
@click.option("--apply", "apply_changes", is_flag=True,
              help="Apply suggestions in-place (default: dry-run preview).")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Where to write the suggestions report (default: stdout).",
)
@click.option("--json", "as_json", is_flag=True,
              help="Emit JSON instead of Markdown.")
@click.option(
    "--top-n",
    type=int,
    default=3,
    help="Number of papers from the best-matching cached query to cite "
         "(default: 3).",
)
def cite_suggest_cmd(
    manuscript_path: Path,
    cache_dir: Path | None,
    min_similarity: float,
    bib_path: Path | None,
    apply_changes: bool,
    output: Path | None,
    as_json: bool,
    top_n: int,
) -> None:
    """Suggest \\cite{} insertions for claim sentences from the Consensus cache.

    Default mode is DRY-RUN — prints suggestions for review.
    Pass ``--apply`` to insert citations + augment references.bib.
    """
    from panelforge_figures.manifest.citation_inserter import (
        InserterError,
        apply_citation_insertions,
        render_suggestions_markdown,
        suggest_citations_for_manuscript,
    )

    effective_bib = bib_path or (manuscript_path.parent / "references.bib")

    try:
        result = suggest_citations_for_manuscript(
            manuscript_path,
            cache_dir=cache_dir,
            min_similarity=min_similarity,
            existing_bib_path=effective_bib,
            top_n_papers=top_n,
        )
    except InserterError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(1)
        return

    backup_manuscript: Path | None = None
    backup_bib: Path | None = None

    if apply_changes and result.suggestions:
        # Recompute backup paths *before* the apply pass so we can
        # report them in the result. The helper picks the same paths
        # because it checks file existence at call time.
        try:
            apply_citation_insertions(
                manuscript_path,
                list(result.suggestions),
                list(result.new_bib_entries),
                existing_bib_path=effective_bib,
                backup=True,
            )
        except InserterError as exc:
            click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
            click.get_current_context().exit(1)
            return
        # Find the actual backups (the helper picked the first
        # non-conflicting names; we look up the latest .bak* files).
        backup_manuscript = _latest_backup(manuscript_path)
        backup_bib = _latest_backup(effective_bib) if effective_bib.exists() else None

        from panelforge_figures.manifest.citation_inserter import (
            CitationInsertionResult,
        )
        result = CitationInsertionResult(
            manuscript_path=result.manuscript_path,
            n_sentences_scanned=result.n_sentences_scanned,
            n_suggestions=result.n_suggestions,
            n_applied=len(result.suggestions),
            new_bib_entries=result.new_bib_entries,
            suggestions=result.suggestions,
            backup_manuscript_path=backup_manuscript,
            backup_bib_path=backup_bib,
        )

    if as_json:
        payload: dict[str, Any] = {
            "manuscript_path": str(result.manuscript_path),
            "n_sentences_scanned": result.n_sentences_scanned,
            "n_suggestions": result.n_suggestions,
            "n_applied": result.n_applied,
            "min_similarity": min_similarity,
            "suggestions": [
                {
                    "sentence": s.sentence,
                    "line_number": s.line_number,
                    "char_offset": s.char_offset,
                    "cite_keys": list(s.cite_keys),
                    "confidence": s.confidence,
                    "rationale": s.rationale,
                }
                for s in result.suggestions
            ],
            "new_bib_entries": [
                {
                    "entry_type": e.entry_type,
                    "cite_key": e.cite_key,
                    "fields": dict(e.fields),
                }
                for e in result.new_bib_entries
            ],
            "backup_manuscript_path": (
                str(result.backup_manuscript_path)
                if result.backup_manuscript_path else None
            ),
            "backup_bib_path": (
                str(result.backup_bib_path)
                if result.backup_bib_path else None
            ),
        }
        text = json.dumps(payload, indent=2, default=str)
    else:
        text = render_suggestions_markdown(result)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"))
    else:
        click.echo(text)


def _latest_backup(path: Path) -> Path | None:
    """Return the most recently-created ``.bak*`` sibling of ``path``.

    Helper for the CLI to report which file the writer backed up to,
    since the writer itself returns only the (modified) target paths.
    """
    parent = path.parent
    stem_suffix = path.name + ".bak"
    candidates = sorted(
        (p for p in parent.glob(f"{stem_suffix}*") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None



# ───────────────────────── E18: bundled CI audit ─────────────────────────


@main.command("ci-audit")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    help="Path to the panelforge project root (default: current dir).",
)
@click.option(
    "--manuscript",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the manuscript .tex/.md (optional).",
)
@click.option(
    "--figures-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the rendered figures directory.",
)
@click.option(
    "--plan-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to figures_plan.yaml (optional; used by checklists).",
)
@click.option(
    "--venue",
    type=str,
    default=None,
    help="Target venue for venue-specific audits (E16).",
)
@click.option(
    "--steps",
    type=str,
    default="",
    help="Comma-separated step list (default: scout,verify-claims,"
         "lint-xrefs,checklist-arrive when manuscript provided; scout otherwise).",
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    help="Treat warnings as failures (exit 1 on warn).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the Markdown report (default: stdout).",
)
@click.option(
    "--output-json",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the JSON report.",
)
@click.option(
    "--output-junit",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the JUnit XML report.",
)
@click.option(
    "--github-comment",
    is_flag=True,
    help="Render PR-comment-sized Markdown (truncated) to --output / stdout.",
)
def ci_audit_cmd(
    project_root: Path,
    manuscript: Path | None,
    figures_dir: Path | None,
    plan_path: Path | None,
    venue: str | None,
    steps: str,
    fail_on_warning: bool,
    output: Path | None,
    output_json: Path | None,
    output_junit: Path | None,
    github_comment: bool,
) -> None:
    """Run the bundled CI audit chain (scout + verify-claims + lint-xrefs + checklist).

    Designed for invocation from CI (GitHub Actions, GitLab CI, Jenkins, etc.).
    Outputs Markdown by default; --output-json + --output-junit emit
    machine-readable artefacts for downstream tooling.

    Exit codes:
      0 — pass (or warn without --fail-on-warning)
      1 — fail / error / warn-with-fail-on-warning
      2 — internal runner error (bad step name, bad path)
    """
    import json as _json

    from panelforge_figures.manifest.ci_runner import (
        CIAuditStep,
        StepStatus,
        render_ci_report_github_comment,
        render_ci_report_junit_xml,
        render_ci_report_markdown,
        run_ci_audit,
    )

    steps_list: tuple[CIAuditStep, ...] | None = None
    if steps:
        try:
            steps_list = tuple(
                CIAuditStep(s.strip()) for s in steps.split(",") if s.strip()
            )
        except ValueError as exc:
            click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
            click.get_current_context().exit(2)
            return

    try:
        report = run_ci_audit(
            project_root,
            manuscript_path=manuscript,
            figures_dir=figures_dir,
            plan_path=plan_path,
            steps=steps_list,
            venue=venue,
            fail_on_warning=fail_on_warning,
        )
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard
        click.echo(click.style(f"✗ CI runner failed: {exc}", fg="red"), err=True)
        click.get_current_context().exit(2)
        return

    md = (
        render_ci_report_github_comment(report)
        if github_comment
        else render_ci_report_markdown(report)
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"), err=True)
    else:
        click.echo(md)

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            _json.dumps(report.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        click.echo(click.style(f"✓ wrote {output_json}", fg="green"), err=True)

    if output_junit is not None:
        output_junit.parent.mkdir(parents=True, exist_ok=True)
        output_junit.write_text(
            render_ci_report_junit_xml(report), encoding="utf-8"
        )
        click.echo(click.style(f"✓ wrote {output_junit}", fg="green"), err=True)

    # ── Exit code ────────────────────────────────────────────────────────
    if report.overall_status in (StepStatus.fail, StepStatus.error):
        click.get_current_context().exit(1)
    elif fail_on_warning and report.overall_status == StepStatus.warn:
        click.get_current_context().exit(1)


# --------------------------------------------------------------------------- #
# audit-venue (E16)                                                            #
# --------------------------------------------------------------------------- #


@main.command("audit-venue")
@click.argument(
    "manuscript_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--venue",
    type=str,
    required=True,
    help="Target venue (nature, cell, nejm, science, biorxiv, elife, "
         "plos_one, jama, plain).",
)
@click.option(
    "--figures-dir",
    type=click.Path(path_type=Path),
    default=Path("panelforge_workspace/figures"),
    help="Directory containing rendered figures.",
)
@click.option(
    "--bib-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional path to a BibTeX file (reserved).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the Markdown report (default: stdout).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit JSON (machine-readable) instead of Markdown.",
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    help="Treat warnings as failures (exit 1 on warn).",
)
def audit_venue_cmd(
    manuscript_path: Path,
    venue: str,
    figures_dir: Path,
    bib_path: Path | None,
    output: Path | None,
    as_json: bool,
    fail_on_warning: bool,
) -> None:
    """Audit MANUSCRIPT_PATH + figures package against target VENUE's locked rules.

    Compares the manuscript and figures directory against the journal's
    "Instructions to Authors" (figure caps, abstract format, required
    statements, citation style, color mode, etc.) and emits a pass/warn/fail
    report.

    Exit codes:
      0 — pass (or warn without --fail-on-warning)
      1 — blocked (any error) / warn-with-fail-on-warning
      2 — internal error (unknown venue, parse failure)
    """
    from panelforge_figures.manifest.venue_auditor import (
        Venue,
        VenueAuditorError,
        audit_venue,
        render_venue_audit_markdown,
    )

    try:
        venue_enum = Venue(venue)
    except ValueError:
        click.echo(
            click.style(
                f"✗ unknown venue: {venue!r}; expected one of "
                f"{[v.value for v in Venue]}",
                fg="red",
            ),
            err=True,
        )
        click.get_current_context().exit(2)
        return

    fdir = figures_dir if figures_dir.exists() else None

    try:
        report = audit_venue(
            manuscript_path,
            venue=venue_enum,
            figures_dir=fdir,
            bib_path=bib_path,
        )
    except VenueAuditorError as exc:
        click.echo(click.style(f"✗ venue auditor failed: {exc}", fg="red"), err=True)
        click.get_current_context().exit(2)
        return

    if as_json:
        payload = json.dumps(report.to_dict(), indent=2, default=str)
    else:
        payload = render_venue_audit_markdown(report)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"), err=True)
    else:
        click.echo(payload)

    # ── Exit code ────────────────────────────────────────────────────────
    if report.overall_verdict == "blocked":
        click.get_current_context().exit(1)
    elif fail_on_warning and report.overall_verdict == "needs_revision":
        click.get_current_context().exit(1)

# ─────────────────────────── audit-bias (E17 — v3.12.0) ─────────────────


@main.command("audit-bias")
@click.argument(
    "figures_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("panelforge_workspace/figures"),
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Path for the Markdown report (default: stdout).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit machine-readable JSON instead of Markdown.",
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    help="Treat warnings as failures (exit 1 when verdict is needs_review).",
)
def audit_bias_cmd(
    figures_dir: Path,
    output: Path | None,
    as_json: bool,
    fail_on_warning: bool,
) -> None:
    """Audit rendered figures for visualization-bias patterns.

    Walks ``FIGURES_DIR`` for ``*.provenance.json`` sidecars and runs the
    Elevation 17 structural-bias checks against each one (truncated
    axes, dual-axes, log/linear scale mismatches, missing CIs, missing
    sample-size annotations on underpowered figures, 3D embellishments
    on 2D data, p-values without effect sizes, colour-blind-unsafe
    colormaps).

    Exit codes:
      0 — verdict is ``honest`` (or ``needs_review`` without --fail-on-warning)
      1 — verdict is ``concerning`` (or ``needs_review`` with --fail-on-warning)
      2 — internal auditor error (bad path, malformed sidecar set)
    """
    import json as _json

    from panelforge_figures.manifest.bias_auditor import (
        BiasAuditorError,
        audit_bias_across_directory,
        render_bias_audit_markdown,
    )

    try:
        report = audit_bias_across_directory(figures_dir)
    except BiasAuditorError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        click.get_current_context().exit(2)
        return
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard
        click.echo(click.style(f"✗ bias auditor failed: {exc}", fg="red"), err=True)
        click.get_current_context().exit(2)
        return

    if as_json:
        rendered = _json.dumps(report.to_dict(), indent=2, default=str)
    else:
        rendered = render_bias_audit_markdown(report)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        click.echo(click.style(f"✓ wrote {output}", fg="green"), err=True)
    else:
        click.echo(rendered)

    if report.overall_verdict == "concerning":
        click.get_current_context().exit(1)
    elif fail_on_warning and report.overall_verdict == "needs_review":
        click.get_current_context().exit(1)



if __name__ == "__main__":
    main()
