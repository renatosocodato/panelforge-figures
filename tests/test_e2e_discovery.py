"""End-to-end discovery flow — Wave 4.

Exercises the full agent transcript top-to-bottom against the bundled
DISC1 fixture project, in the order an autonomous Claude Code session
would walk it:

    1. fetch  recipes_index.json  →  validate against the JSON-Schema
    2. project scan               →  ProjectScanResult
    3. intake assembly            →  ProjectProfile (no Click prompts)
    4. score                      →  ranked shortlist
    5. bridge                     →  per-recipe FieldBindings (no LLM)
    6. render                     →  RENDER_REPORT.md (mocked render fn)

Tests marked ``@pytest.mark.slow`` run only on main / scheduled CI.
The slow filter lives in ``pyproject.toml`` as
``addopts = ["-m", "not slow", ...]``.

The deterministic env vars ``PANELFORGE_BUILT_AT`` and
``PANELFORGE_GIT_COMMIT`` are pinned at session scope so any
``recipes_index.json`` rebuilt during the run is byte-stable.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from panelforge_figures.core.contract import (
    ensure_all_imported,
    list_modalities,
)
from panelforge_figures.manifest import (
    ProjectProfile,
    bind_shortlist_to_data,
    build_index,
    discover_data_files,
    score_recipes,
    write_render_report,
)
from panelforge_figures.manifest.intake import (
    HARD_FILTER_KEYS,
    INTAKE_QUESTIONS,
    IntakeAnswer,
    _profile_from_answers,
)
from panelforge_figures.manifest.project_scan import (
    ProjectScanResult,
    scan_project,
    to_intake_pre_filled,
)
from panelforge_figures.manifest.render_loop import (
    RenderBinding,
    RenderDataFile,
    RenderLog,
    RenderOutcome,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "sample_project"
INDEX_PATH = REPO_ROOT / "recipes_index.json"
SCHEMA_PATH = REPO_ROOT / "docs" / "recipes_index.schema.json"

DISC1_WAVE = "v1.4.0-beta-cytoskeletal_morphometry_companion"


# ────────────────────────── deterministic env ──────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _deterministic_env() -> None:
    """Pin built-at / git-commit so any index rebuilt during this run is stable.

    The scoping is session — autonomous CI may rebuild the index inside the
    fixture's ``tmp_path``; pinning these keeps the run reproducible.
    """
    os.environ.setdefault("PANELFORGE_BUILT_AT", "1970-01-01T00:00:00Z")
    os.environ.setdefault("PANELFORGE_GIT_COMMIT", "e2e-test")


# ────────────────────────── helpers ────────────────────────────────────


def _registry_modalities() -> tuple[str, ...]:
    """Return the live registry's modality list as a sorted tuple."""
    ensure_all_imported()
    return tuple(list_modalities())


def _flatten_index_recipes(index: dict) -> list[dict]:
    """Flatten the index's modalities → recipes into the score_recipes shape."""
    return [
        {
            "modality": m["name"],
            "name": r["name"],
            "family": r["family"],
            "answers_question": r["answers_question"],
            "tags": r.get("tags", {}),
        }
        for m in index.get("modalities", [])
        for r in m.get("recipes", [])
    ]


def _profile_from_scan(
    scan: ProjectScanResult,
    *,
    available_modalities: tuple[str, ...],
) -> ProjectProfile:
    """Assemble a ProjectProfile from a ProjectScanResult — no Click prompts.

    Honours the same pre-fill discipline as ``run_intake_interactive`` but
    without I/O: high-confidence inferred answers replace question defaults;
    everything else falls back to the question default.
    """
    pre_filled = to_intake_pre_filled(scan, confidence_threshold=0.7)

    answers: dict[str, IntakeAnswer] = {}
    for q in INTAKE_QUESTIONS:
        pf = pre_filled.get(q.field_name)
        if pf is not None:
            answers[q.field_name] = pf
            continue
        # Fallback: spec default for the question.
        if q.field_name == "modalities_in_scope":
            value: object = ()                       # → all
        elif q.field_name == "hard_filters":
            value = ()                               # → none
        else:
            value = q.default
        answers[q.field_name] = IntakeAnswer(
            question_id=q.id,
            field_name=q.field_name,
            value=value,
            source="default",
            confidence=1.0,
        )

    return _profile_from_answers(
        answers, available_modalities=available_modalities
    )


# ────────────────────────── Step 1 — fetch index ───────────────────────


def test_e2e_fetch_and_validate_index(tmp_path: Path) -> None:
    """Step 1 — load the committed recipes_index.json and validate the schema."""
    pytest.importorskip("jsonschema")
    import jsonschema

    assert INDEX_PATH.is_file(), f"committed index missing: {INDEX_PATH}"
    assert SCHEMA_PATH.is_file(), f"committed schema missing: {SCHEMA_PATH}"

    # Round-trip through tmp_path to mimic an agent's "fetch → cache" step.
    cached = tmp_path / "recipes_index.cached.json"
    cached.write_text(INDEX_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    index = json.loads(cached.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Schema validity
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(instance=index, schema=schema)

    # Wave-2 invariants the rest of the e2e flow depends on.
    assert index["index_meta"]["tags_enabled"] is True
    assert "scoring_rubric" in index
    assert "intake_questions" in index
    assert index["index_meta"]["n_recipes"] >= 100
    assert len(index["modalities"]) >= 18


# ────────────────────────── Step 2 — project scan ──────────────────────


def test_e2e_project_scan_disc1_fixture() -> None:
    """Step 2 — scan the bundled DISC1 fixture; assert ≥6 of 8 fields ≥0.7."""
    available = _registry_modalities()
    result = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=available,
        confidence_threshold=0.7,
    )

    assert isinstance(result, ProjectScanResult)
    assert result.panelforge_yaml_present is True

    high_conf = [a for a in result.answers.values() if a.confidence >= 0.7]
    assert len(high_conf) >= 6, (
        f"expected ≥6 of 8 fields at conf ≥0.7; got {len(high_conf)}: "
        + ", ".join(
            f"{a.field_name}={a.confidence:.2f}"
            for a in result.answers.values()
        )
    )

    # Spot-check the YAML overrides + manuscript hits.
    assert result.answers["manuscript_anchor"].value == "DISC1"
    assert result.answers["equivalence_claims"].value is True


# ────────────────────────── Step 3 — intake assembly ───────────────────


def test_e2e_intake_pre_fill_to_profile() -> None:
    """Step 3 — build a ProjectProfile from pre-filled answers (no Click I/O)."""
    available = _registry_modalities()
    scan = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=available,
        confidence_threshold=0.7,
    )
    profile = _profile_from_scan(scan, available_modalities=available)

    assert isinstance(profile, ProjectProfile)
    # Anchor + equivalence are explicitly pinned by the fixture YAML.
    assert profile.manuscript_anchor == "DISC1"
    assert profile.equivalence_claims is True
    # All HARD_FILTER_KEYS are present (default False unless flipped on).
    assert set(profile.hard_filters.keys()) == set(HARD_FILTER_KEYS)
    assert profile.shortlist_size >= 1


# ────────────────────────── Step 4 — score ─────────────────────────────


@pytest.mark.slow
def test_e2e_score_disc1_top1_is_disc1_pack() -> None:
    """Step 4 — top-scoring recipe for the DISC1 profile lives in the disc1 pack.

    Uses the live tagged index (build_index include_tags=True) so the result
    reflects the same tag pool an agent would see in production.
    """
    available = _registry_modalities()
    scan = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=available,
        confidence_threshold=0.7,
    )
    profile = _profile_from_scan(scan, available_modalities=available)

    index = build_index(include_tags=True)
    flat = _flatten_index_recipes(index)

    # The shortlist may legitimately be smaller than the requested size when
    # the modality scope is narrow — silence the "underfilled" UserWarning.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        scored = score_recipes(profile, flat)

    assert scored, "scorer produced an empty shortlist for the DISC1 fixture"
    top = scored[0]
    # Post-DEFECT-A2 fix (Wave-3 polish), DISC1 + equivalence + static +
    # mixed-dim profiles cluster near 0.49-0.57 depending on YAML overrides.
    # The disc1-pack recipes float to the top by anchor + compartment_aware.
    assert top.score >= 0.45, (
        f"top-1 score too low: {top.score:.3f} for {top.full_name}"
    )
    assert top.tags.get("wave") == DISC1_WAVE, (
        f"top-1 recipe {top.full_name!r} has wave={top.tags.get('wave')!r}; "
        f"expected {DISC1_WAVE!r}"
    )


# ────────────────────────── Step 5 — bridge ────────────────────────────


def test_e2e_bridge_against_fixture_data() -> None:
    """Step 5 — bridge the top-3 recipes against the fixture's data/ files.

    Pass-1 (exact) + Pass-2 (fuzzy) only; Pass-3 is gated on
    ``ANTHROPIC_API_KEY`` and explicitly disabled here so the test is
    deterministic and offline-safe.
    """
    available = _registry_modalities()
    scan = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=available,
        confidence_threshold=0.7,
    )
    profile = _profile_from_scan(scan, available_modalities=available)

    index = build_index(include_tags=True)
    flat = _flatten_index_recipes(index)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        scored = score_recipes(profile, flat)
    assert scored, "no recipes survived scoring; cannot test bridging"

    shortlist = [r.full_name for r in scored[:3]]
    data_files = discover_data_files(FIXTURE_ROOT / "data")
    assert data_files, "fixture data/ should contain CSVs the bridge can probe"

    bindings = bind_shortlist_to_data(
        shortlist=shortlist, data_files=data_files, use_llm=False,
    )

    assert len(bindings) == len(shortlist)
    # Each RecipeBinding has a list of FieldBindings + a fully_bound flag.
    for rb in bindings:
        assert rb.full_name in shortlist
        assert isinstance(rb.fully_bound, bool)
        assert isinstance(rb.bindings, tuple)
        assert len(rb.bindings) > 0, (
            f"recipe {rb.full_name} produced no FieldBindings — every "
            "Pydantic contract has at least one required field"
        )

    # Sanity: each FieldBinding row carries a known pass label.  No-LLM
    # mode means Pass-3 is never invoked, so "llm" should never appear.
    valid_passes = {"exact", "fuzzy", "unbound"}
    for rb in bindings:
        for fb in rb.bindings:
            assert fb.pass_used in valid_passes, (
                f"unexpected pass label {fb.pass_used!r} for "
                f"{rb.full_name}.{fb.contract_field}"
            )


# ────────────────────────── Step 6 — render (mocked) ───────────────────


def _stub_render_outcome(full_name: str, out_dir: Path) -> RenderOutcome:
    """Synthesise a successful RenderOutcome without touching matplotlib."""
    pdf = out_dir / f"{full_name}.pdf"
    png = out_dir / f"{full_name}.png"
    # Touch zero-byte files so write_render_report's path-resolution sees
    # them and locates the report alongside the (fake) artefacts.
    pdf.write_bytes(b"")
    png.write_bytes(b"")
    return RenderOutcome(
        full_name=full_name,
        status="success",
        pdf_path=pdf,
        png_path=png,
        error_class=None,
        error_message=None,
        traceback_excerpt=None,
        elapsed_seconds=0.0,
    )


@pytest.mark.slow
def test_e2e_full_transcript_smoke(tmp_path: Path) -> None:
    """Steps 1–6 in sequence on the fixture; assert no exceptions + report shape.

    Render is mocked: ``render_shortlist`` is replaced with a no-op stub
    that emits success outcomes so the report-writing path can be exercised
    without invoking matplotlib (slow + fragile in CI).
    """
    pytest.importorskip("jsonschema")
    import jsonschema

    # 1. fetch + validate the committed index
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=index, schema=schema)

    # 2. scan
    available = _registry_modalities()
    scan = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=available,
        confidence_threshold=0.7,
    )
    assert scan.panelforge_yaml_present is True

    # 3. intake assembly
    profile = _profile_from_scan(scan, available_modalities=available)
    assert profile.manuscript_anchor == "DISC1"

    # 4. score (use the live index so we score against the same tag pool
    #    the agent sees; the committed JSON file may be slightly older).
    flat = _flatten_index_recipes(build_index(include_tags=True))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        scored = score_recipes(profile, flat)
    assert scored, "scorer produced empty shortlist for DISC1 fixture"

    # 5. bridge (no LLM)
    shortlist = [r.full_name for r in scored[:3]]
    data_files = discover_data_files(FIXTURE_ROOT / "data")
    bindings = bind_shortlist_to_data(
        shortlist=shortlist, data_files=data_files, use_llm=False,
    )

    # 6. render — mocked.  Replace ``render_shortlist`` with a stub that
    #    skips matplotlib altogether.  We then write the real Markdown
    #    report against the synthesised log.
    out_dir = tmp_path / "figures"
    out_dir.mkdir()
    fake_outcomes = tuple(
        _stub_render_outcome(rb.full_name, out_dir) for rb in bindings
    )
    fake_log = RenderLog(
        project_root=tmp_path,
        n_attempted=len(fake_outcomes),
        n_success=len(fake_outcomes),
        n_skipped=0,
        n_failed=0,
        outcomes=fake_outcomes,
        started_at="1970-01-01T00:00:00Z",
        finished_at="1970-01-01T00:00:01Z",
    )

    def _no_op_render_shortlist(
        *, bindings, data_files, out_dir,
        dpi: int = 300, figsize: tuple[float, float] = (4.2, 3.2),
    ) -> RenderLog:
        # All parameters intentionally unused — this stub bypasses
        # matplotlib entirely and returns the pre-built log.
        del bindings, data_files, out_dir, dpi, figsize
        return fake_log

    with patch(
        "panelforge_figures.manifest.render_loop.render_shortlist",
        new=_no_op_render_shortlist,
    ):
        # Demonstrate that the patch is in place before invoking.
        from panelforge_figures.manifest import render_loop as _rl
        log = _rl.render_shortlist(
            bindings=[
                RenderBinding(full_name=rb.full_name, fully_bound=rb.fully_bound)
                for rb in bindings
            ],
            data_files=[
                RenderDataFile(file_id=str(df.path), path=df.path)
                for df in data_files
            ],
            out_dir=out_dir,
        )

    assert log is fake_log
    assert log.n_attempted == len(bindings)

    # Write the actual report — exercises the report-writing path.
    report_path = write_render_report(log, out_dir / "RENDER_REPORT.md")
    assert report_path.is_file()
    text = report_path.read_text(encoding="utf-8")
    assert "# Render Report" in text
    assert "**panelforge version:**" in text
    assert f"**Total recipes attempted:** {log.n_attempted}" in text
    assert f"**Rendered:** {log.n_success}" in text
    assert "## Successful" in text
    assert "## Skipped" in text
    assert "## Failed" in text
    assert "## Next steps" in text
    # Each shortlisted recipe shows up in the success table.
    for rb in bindings:
        assert rb.full_name in text
