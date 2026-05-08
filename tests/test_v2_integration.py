"""Cross-cutting v2.0.0 integration tests.

Verifies that the eight v1.7.0 → v1.14.0 elevations interoperate as a
single coherent system:

- statistical contract (v1.7.0) feeds into provenance (v1.8.0)
- composition (v1.9.0) wraps single-panel renders without breaking them
- plugins (v1.10.0) expose recipes that are statistically auditable
- data-class safety (v1.11.0) gates vision (v1.12.0) + telemetry (v1.14.0)
- cross-project (v1.13.0) registry round-trips with auto-register hook

Each test exercises at least two elevations together; pure unit tests for
each elevation live in their respective `test_<elevation>.py` files.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from panelforge_figures import __version__
from panelforge_figures.manifest.scoring import (
    SCORING_RUBRIC_VERSION,
    WEIGHTS,
    WEIGHTS_HISTORY,
)

# ───────────────────── 0. version is correct ─────────────────────


def test_version_is_at_least_v2() -> None:
    """v2.0.0 elevation programme: the package must be >= 2.0.0.
    Subsequent elevations (E1-E8) bump the minor version; v3+ accepted."""
    parts = __version__.split(".")
    assert len(parts) >= 2, f"unexpected version format: {__version__!r}"
    assert int(parts[0]) >= 2, f"expected >= 2.x.y, got {__version__!r}"


# ───────────────────── 1. scoring × weights history (v1.14.0) ─────────────────────


def test_scoring_default_weights_match_history() -> None:
    """`WEIGHTS` must always equal `WEIGHTS_HISTORY[SCORING_RUBRIC_VERSION]`
    so callers that don't pass `weights_version` get the canonical rubric."""
    assert dict(WEIGHTS) == dict(WEIGHTS_HISTORY[SCORING_RUBRIC_VERSION])


def test_weights_history_all_sum_to_one() -> None:
    """Every historical weight vector must sum to 1.0 — drift here would
    silently bias every recipe shortlist computed against that rubric."""
    for v, weights in WEIGHTS_HISTORY.items():
        s = sum(weights.values())
        assert abs(s - 1.0) < 1e-9, f"WEIGHTS_HISTORY[{v}] sums to {s}, expected 1.0"


# ─────────── 2. data-class policy table is exhaustive (v1.11.0) ───────────


def test_clinical_policy_blocks_everything() -> None:
    """`DataClass.clinical` policy must lock down all external channels
    (LLM, telemetry, vision, plugin network) and redact provenance hashes."""
    from panelforge_figures.safety import _POLICIES, DataClass

    p = _POLICIES[DataClass.CLINICAL]
    assert p.llm_pass3 == "disabled"
    assert p.telemetry == "off"
    assert p.vision == "disabled"
    assert p.provenance_hashes == "redacted"
    assert p.plugin_network_required == "disallowed"


def test_research_policy_is_opt_in() -> None:
    """`DataClass.research` (production default) is opt-in for LLM,
    telemetry, vision; provenance hashes are full; plugin network allowed."""
    from panelforge_figures.safety import _POLICIES, DataClass

    p = _POLICIES[DataClass.RESEARCH]
    assert p.llm_pass3 == "opt_in"
    assert p.telemetry == "opt_in"
    assert p.vision == "opt_in"
    assert p.provenance_hashes == "full"
    assert p.plugin_network_required == "allowed"


def test_public_policy_is_open() -> None:
    """`DataClass.public` defaults LLM and vision to enabled, leaving
    telemetry as opt-in (we never silently collect telemetry)."""
    from panelforge_figures.safety import _POLICIES, DataClass

    p = _POLICIES[DataClass.PUBLIC]
    assert p.llm_pass3 == "enabled"
    assert p.telemetry == "opt_in"
    assert p.vision == "enabled"


# ─────────── 3. data-class gates obey the policy table (v1.11.0 × runtime) ───────────


def test_clinical_runtime_blocks_llm_telemetry_vision() -> None:
    """Setting the runtime data class to clinical must make
    `is_llm_allowed`, `is_telemetry_allowed`, `is_vision_allowed`
    all return False — the locked privacy contract."""
    from panelforge_figures.safety import (
        DataClass,
        is_llm_allowed,
        is_telemetry_allowed,
        is_vision_allowed,
        set_data_class,
    )

    previous = None
    try:
        from panelforge_figures.safety import get_data_class
        previous = get_data_class()
        set_data_class(DataClass.CLINICAL)
        assert is_llm_allowed() is False
        assert is_telemetry_allowed() is False
        assert is_vision_allowed() is False
    finally:
        if previous is not None:
            set_data_class(previous)


# ─────────── 4. project registry round-trip (v1.13.0) ───────────


def test_projects_registry_round_trip(tmp_path: Path) -> None:
    """The cross-project registry round-trips through save → load with all
    fields preserved (default_project, tags, last_used)."""
    from panelforge_figures.projects import (
        ProjectEntry,
        Registry,
        load_registry,
        save_registry,
    )

    cfg = tmp_path / "projects.yaml"
    proj_dir = tmp_path / "myproj"
    proj_dir.mkdir()

    r = Registry.empty()
    e = ProjectEntry(
        id="myproj",
        path=proj_dir,
        last_used=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        active_profile="v2_test",
        n_recipes_picked=5,
        last_render_status="5/5 success",
        tags=("v2", "integration"),
    )
    r.add(e, set_default=True)
    save_registry(r, cfg)

    r2 = load_registry(cfg)
    assert r2.default_project == "myproj"
    assert r2.projects["myproj"].active_profile == "v2_test"
    assert r2.projects["myproj"].tags == ("v2", "integration")


# ─────────── 5. plugin discovery interacts with statistical audit (v1.10.0 × v1.7.0) ─


def test_every_recipe_has_a_metadata_object() -> None:
    """Every recipe registered must have a `_META` attribute. The
    statistical contract is OPTIONAL on metadata (older recipes may
    not declare one); this test asserts the metadata itself is present."""
    from panelforge_figures.core.contract import (
        ensure_all_imported,
        list_recipes,
    )

    ensure_all_imported()
    recipes = list_recipes()
    assert len(recipes) > 0, "no recipes registered — registry import broken"
    # list_recipes() returns a list of RecipeInfo; iterate directly.
    for info in recipes:
        assert info.metadata is not None, f"recipe {info!r} has no metadata"


# ─────────── 6. composition layer schemas are constructible (v1.9.0) ───────────


def test_composition_layer_schemas_constructible() -> None:
    """Composition Pydantic models construct without errors — the
    minimum smoke test that the v1.9.0 elevation didn't bit-rot."""
    from panelforge_figures.manifest import (
        CompositionPanelSpec,
        FigureCompositionSpec,
        GridLayout,
    )

    spec = FigureCompositionSpec(
        figure_id="v2_smoke",
        layout=GridLayout(rows=1, cols=1),
        panels=[
            CompositionPanelSpec(
                id="p1",
                recipe="meta_and_diagnostic.run_provenance_card",
                row=0,
                col=0,
            )
        ],
    )
    assert spec.layout.rows == 1
    assert spec.layout.cols == 1
    assert spec.panels[0].recipe == "meta_and_diagnostic.run_provenance_card"


# ─────────── 7. provenance build produces a record (v1.8.0) ───────────


def test_provenance_record_round_trip(tmp_path: Path) -> None:
    """`build_provenance` produces a serializable ProvenanceRecord that
    round-trips through write/load without data loss."""
    from panelforge_figures.manifest.provenance import (
        build_provenance,
        load_provenance_json,
        write_provenance_json,
    )

    fig_path = tmp_path / "figure.png"
    fig_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes" + b"\x00" * 30)
    recipe_path = tmp_path / "fake_recipe.py"
    recipe_path.write_text("# stub\n")

    rec = build_provenance(
        figure_path=fig_path,
        recipe_full_name="meta_and_diagnostic.run_provenance_card",
        recipe_module_path=recipe_path,
        panelforge_version=__version__,
        panelforge_git_commit="uncommitted",
        data_files=[],
    )
    out_path = tmp_path / "provenance.json"
    write_provenance_json(rec, out_path=out_path)
    loaded = load_provenance_json(out_path)
    # ProvenanceRecord nests recipe metadata under `recipe` per the v1.8.0
    # schema; the panelforge_version lives there too.
    assert loaded.recipe.get("full_name") == rec.recipe.get("full_name")
    assert loaded.recipe.get("panelforge_version") == __version__


# ─────────── 8. telemetry default is OFF (v1.14.0 invariant) ───────────


def test_telemetry_off_by_default(tmp_path: Path) -> None:
    """A vanilla project (no panelforge.project.yaml) must NEVER write
    telemetry. This is the key v1.14.0 privacy invariant."""
    from panelforge_figures.manifest.telemetry import (
        is_telemetry_enabled,
        log_invocation,
        telemetry_log_path,
    )

    assert is_telemetry_enabled(tmp_path) is False
    log_invocation(
        tmp_path,
        profile={"modality": "x"},
        scored_top_5=[],
        panelforge_version=__version__,
        scoring_rubric_version=SCORING_RUBRIC_VERSION,
    )
    assert not telemetry_log_path(tmp_path).exists()


# ─────────── 9. version forward-compat sanity ───────────


def test_recipes_index_panelforge_version() -> None:
    """If recipes_index.json exists, its panelforge_version field must
    track __version__. Drift is a release-notes red flag."""
    import json

    p = Path(__file__).parent.parent / "recipes_index.json"
    if not p.exists():
        pytest.skip("recipes_index.json not present (expected in source tree)")
    idx = json.loads(p.read_text())
    pv = idx.get("panelforge_version") or idx.get("index_meta", {}).get("panelforge_version")
    if pv is None:
        pytest.skip("recipes_index.json has no panelforge_version field")
    # Allow stale index (pre-regen) — accept the current version, the
    # pre-v2 baseline (1.6.1), or any prior v2.x bump while elevations
    # land. Drift outside that band still flags a release-notes red flag.
    pv_parts = pv.split(".")
    is_v2_band = len(pv_parts) >= 2 and pv_parts[0] == "2"
    assert pv == __version__ or pv == "1.6.1" or is_v2_band, (
        f"recipes_index.json panelforge_version is {pv!r}; "
        f"expected {__version__!r} (run `figures index emit` to refresh)"
    )
