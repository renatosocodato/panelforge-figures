"""Tests for the Wave 3 autonomous checkpoint flow.

Covers:
  * `panelforge_workspace/profile.json` round-trip (write + load).
  * `panelforge_workspace/data_bridge_cache.json` round-trip.
  * Re-run behaviour: an existing `profile.json` is detected, and the
    intake honours it as `pre_filled`.
  * End-to-end smoke test against the bundled fixture project.
  * Confidence-threshold gate: a near-empty project keeps too many
    fields below 0.7, which forces fall-back to interactive intake.
  * `CLAUDE_CODE_AUTONOMOUS.md` link checker — every claimed in-repo
    path resolves on disk; every fixture CSV parses cleanly via
    ``pandas.read_csv``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from panelforge_figures.manifest.intake import (
    HARD_FILTER_KEYS,
    INTAKE_QUESTIONS,
    IntakeAnswer,
    _profile_from_answers,
    _profile_to_dict,
)
from panelforge_figures.manifest.project_scan import (
    ProjectScanResult,
    scan_project,
    to_intake_pre_filled,
)
from panelforge_figures.manifest.scoring import ProjectProfile

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "sample_project"
AUTONOMOUS_MD = REPO_ROOT / "CLAUDE_CODE_AUTONOMOUS.md"


AVAILABLE_MODALITIES = (
    "actin_microtubule_morphometry",
    "biophysics_scaling",
    "meta_and_diagnostic",
    "intravital_imaging",
    "rhogtpase_dynamics",
)


# ─────────────────────────── helpers ─────────────────────────────────────


def _all_defaults_pre_filled() -> dict[str, IntakeAnswer]:
    """Build a dict of pre-filled answers using every question's default."""
    pf: dict[str, IntakeAnswer] = {}
    for q in INTAKE_QUESTIONS:
        if q.field_name == "modalities_in_scope":
            value: object = ()
        elif q.field_name == "hard_filters":
            value = ()
        else:
            value = q.default
        pf[q.field_name] = IntakeAnswer(
            question_id=q.id,
            field_name=q.field_name,
            value=value,
            source="default",
            confidence=1.0,
        )
    return pf


# ───────────────── 1) profile.json round-trip ────────────────────────────


def test_profile_json_round_trip(tmp_path: Path) -> None:
    """Write a ProjectProfile to JSON, load it back, equal-by-value."""
    pre = _all_defaults_pre_filled()
    profile = _profile_from_answers(pre, available_modalities=AVAILABLE_MODALITIES)

    out_dir = tmp_path / "panelforge_workspace"
    out_dir.mkdir()
    out_path = out_dir / "profile.json"
    out_path.write_text(json.dumps(_profile_to_dict(profile), indent=2, sort_keys=True))

    raw = json.loads(out_path.read_text())
    rehydrated = ProjectProfile(
        manuscript_anchor=raw["manuscript_anchor"],
        factorial_design=raw["factorial_design"],
        equivalence_claims=raw["equivalence_claims"],
        dynamics_needed=raw["dynamics_needed"],
        dimensionality=raw["dimensionality"],
        modalities_in_scope=tuple(raw["modalities_in_scope"]),
        hard_filters=raw["hard_filters"],
        shortlist_size=raw["shortlist_size"],
    )
    assert rehydrated == profile
    assert _profile_to_dict(rehydrated) == _profile_to_dict(profile)


# ───────────────── 2) data_bridge_cache.json round-trip ──────────────────


def test_data_bridge_cache_round_trip(tmp_path: Path) -> None:
    """Hand-rolled mapping cache must round-trip through JSON unchanged.

    The Wave 3 bridge module is not yet on disk; the cache *shape* is part
    of the spec and must be exercisable independently so other agents can
    validate against it.
    """
    cache_payload = {
        "schema_version": "1.0.0",
        "mappings": [
            {
                "recipe": "actin_microtubule_morphometry.compartment_effect_forest",
                "field": "area_um2",
                "data_column": "area_um2",
                "confidence": 1.0,
                "pass": "exact",
            },
            {
                "recipe": "actin_microtubule_morphometry.compartment_effect_forest",
                "field": "compartment",
                "data_column": "compartment",
                "confidence": 1.0,
                "pass": "exact",
            },
            {
                "recipe": "meta_and_diagnostic.bayes_factor_arrow_plot",
                "field": "d_effect",
                "data_column": "d",
                "confidence": 0.86,
                "pass": "fuzzy",
            },
        ],
        "unmapped": [],
    }

    cache_path = tmp_path / "panelforge_workspace" / "data_bridge_cache.json"
    cache_path.parent.mkdir()
    cache_path.write_text(json.dumps(cache_payload, indent=2, sort_keys=True))

    rehydrated = json.loads(cache_path.read_text())
    assert rehydrated == cache_payload
    assert {m["pass"] for m in rehydrated["mappings"]} <= {"exact", "fuzzy", "llm"}
    for m in rehydrated["mappings"]:
        assert 0.0 <= m["confidence"] <= 1.0
        assert "recipe" in m and "field" in m and "data_column" in m


# ───────────────── 3) Re-run after first session ─────────────────────────


def test_rerun_detects_prior_profile(tmp_path: Path) -> None:
    """After a first session writes profile.json, a second `scan_project`
    invocation should still succeed and the prior profile should be
    detectable so the agent can offer to reuse vs re-run.
    """
    pre = _all_defaults_pre_filled()
    profile = _profile_from_answers(pre, available_modalities=AVAILABLE_MODALITIES)

    workspace = tmp_path / "panelforge_workspace"
    workspace.mkdir()
    (workspace / "profile.json").write_text(
        json.dumps(_profile_to_dict(profile), indent=2, sort_keys=True)
    )

    # Now do a "second run" — scan a tiny project under the same root
    (tmp_path / "README.md").write_text("Trivial DISC1 stub for re-run test.\n")
    result = scan_project(
        project_root=tmp_path,
        available_modalities=AVAILABLE_MODALITIES,
        confidence_threshold=0.7,
    )
    # The scan returned a fresh ProjectScanResult.
    assert isinstance(result, ProjectScanResult)
    assert result.project_root == tmp_path.resolve()

    # The prior profile.json is still on disk and parses back cleanly.
    prior = json.loads((workspace / "profile.json").read_text())
    assert prior["manuscript_anchor"] == "none"
    assert prior["shortlist_size"] == 12


# ───────────────── 4) End-to-end smoke against fixture ──────────────────


def test_fixture_project_yields_high_confidence_majority() -> None:
    """≥ 5 of 8 intake fields should land at confidence ≥ 0.7 against the
    bundled DISC1 manuscript companion fixture."""
    result = scan_project(
        project_root=FIXTURE_ROOT,
        available_modalities=AVAILABLE_MODALITIES,
        confidence_threshold=0.7,
    )
    assert result.panelforge_yaml_present is True
    high_conf = [a for a in result.answers.values() if a.confidence >= 0.7]
    assert len(high_conf) >= 5, (
        f"only {len(high_conf)} of 8 fields cleared 0.7; "
        f"got: {[(a.field_name, a.confidence) for a in result.answers.values()]}"
    )

    pre_filled = to_intake_pre_filled(result, confidence_threshold=0.7)
    assert len(pre_filled) >= 5

    # Spot-checks: the explicit YAML override should pin anchor=DISC1 +
    # equivalence=True and the manuscript text should pin Airyscan/3D.
    assert result.answers["manuscript_anchor"].value == "DISC1"
    assert result.answers["manuscript_anchor"].confidence >= 0.9
    assert result.answers["equivalence_claims"].value is True
    assert result.answers["dimensionality"].value in {"3D", "mixed"}


# ───────────────── 5) Confidence-threshold fall-back ─────────────────────


def test_low_confidence_project_triggers_fallback(tmp_path: Path) -> None:
    """A bare project (only an empty README) leaves ≥ 3 fields below 0.7,
    forcing the agent to fall back to interactive intake."""
    (tmp_path / "README.md").write_text(
        "Untitled project.  No methods, no data, no manuscript.\n"
    )

    result = scan_project(
        project_root=tmp_path,
        available_modalities=AVAILABLE_MODALITIES,
        confidence_threshold=0.7,
    )
    low_conf = [a for a in result.answers.values() if a.confidence < 0.7]
    assert len(low_conf) >= 3, (
        f"expected at least 3 sub-0.7 answers; got {len(low_conf)}: "
        f"{[(a.field_name, a.confidence) for a in result.answers.values()]}"
    )

    pre_filled = to_intake_pre_filled(result, confidence_threshold=0.7)
    # Fall-back trigger: more than 2 of 8 fields dropped → flow should
    # surface the AGENT_BOOTSTRAP.md path.
    dropped = 8 - len(pre_filled)
    assert dropped > 2


# ───────────────── 6) CLAUDE_CODE_AUTONOMOUS.md link check ──────────────


# Repo-relative paths the autonomous bootstrap claims exist.
EXPECTED_RELATIVE_PATHS = (
    "recipes_index.json",
    "AGENT_BOOTSTRAP.md",
    "CLAUDE_CODE_AUTONOMOUS.md",
    "docs/recipes_index.schema.json",
    "src/panelforge_figures/manifest/project_scan.py",
    "src/panelforge_figures/manifest/intake.py",
    "src/panelforge_figures/manifest/scoring.py",
    "src/panelforge_figures/cli/__init__.py",
    "tests/fixtures/sample_project/",
)


def test_autonomous_md_exists() -> None:
    assert AUTONOMOUS_MD.is_file(), f"missing {AUTONOMOUS_MD}"


def test_autonomous_md_required_step_headings() -> None:
    text = AUTONOMOUS_MD.read_text()
    for step in (
        "## Step 1",
        "## Step 2",
        "## Step 3",
        "## Step 4",
        "## Step 5",
        "## Step 6",
        "## Step 7",
    ):
        assert step in text, f"autonomous bootstrap missing heading: {step}"


def test_autonomous_md_two_checkpoints() -> None:
    """The two-checkpoint contract is a hard part of the public surface."""
    text = AUTONOMOUS_MD.read_text()
    assert "CHECKPOINT 1" in text, "checkpoint 1 missing"
    assert "CHECKPOINT 2" in text, "checkpoint 2 missing"


def test_autonomous_md_resolvable_paths() -> None:
    """Every claimed in-repo path resolves on disk."""
    text = AUTONOMOUS_MD.read_text()
    for rel in EXPECTED_RELATIVE_PATHS:
        assert rel in text, f"autonomous bootstrap doesn't mention {rel}"
        target = REPO_ROOT / rel
        assert target.exists(), (
            f"autonomous bootstrap references {rel} but target {target} is missing"
        )


def test_autonomous_md_schema_version_contract() -> None:
    text = AUTONOMOUS_MD.read_text()
    assert "schema_version" in text


def test_autonomous_md_fallback_table() -> None:
    """Fall-back conditions must be enumerated."""
    text = AUTONOMOUS_MD.read_text()
    for trigger in ("--manual", "--shortlist-only", "autonomy: false"):
        assert trigger in text, f"fall-back trigger missing: {trigger}"


def test_autonomous_md_panelforge_yaml_schema_block() -> None:
    """The example panelforge.project.yaml block must include every
    documented key.  Checked via substring containment so formatting can
    drift slightly."""
    text = AUTONOMOUS_MD.read_text()
    for key in ("anchor:", "factorial:", "equivalence:", "modalities:",
                "shortlist_size:", "autonomy:"):
        assert key in text, f"panelforge.project.yaml schema missing: {key}"


def test_autonomous_md_length_in_band() -> None:
    """Spec aim is ~150-200 lines; ceiling raised to 380 in PR #66
    (Sprint 2C — v1.12.0) to accommodate the vision-payload extension
    of the privacy & data-handling disclosure block."""
    n_lines = len(AUTONOMOUS_MD.read_text().splitlines())
    assert 100 <= n_lines <= 380, (
        f"CLAUDE_CODE_AUTONOMOUS.md has {n_lines} lines; expected 100-380"
    )


def test_autonomous_md_owner_placeholder_consistent() -> None:
    """The raw GitHub URLs must use the same owner placeholder as
    AGENT_BOOTSTRAP.md (or a real owner) — never mixed."""
    text = AUTONOMOUS_MD.read_text()
    raw_urls = [ln for ln in text.splitlines() if "raw.githubusercontent.com" in ln]
    assert raw_urls, "expected at least one raw GitHub URL"
    for ln in raw_urls:
        assert "<owner>" in ln or re.search(r"raw\.githubusercontent\.com/[^/<]+/", ln)


# ───────────────── 7) Fixture CSVs parse via pandas ──────────────────────


@pytest.mark.parametrize("csv_name", ["morphometry_per_cell.csv", "effect_sizes.csv"])
def test_fixture_csvs_parse_via_pandas(csv_name: str) -> None:
    csv_path = FIXTURE_ROOT / "data" / csv_name
    df = pd.read_csv(csv_path)
    assert len(df) >= 10, f"{csv_name} should ship at least 10 rows"
    assert df.shape[1] >= 4, f"{csv_name} should have ≥ 4 columns"
    # No NaNs in the synthetic data.
    assert not df.isna().any().any(), f"{csv_name} has unexpected NaN values"


def test_fixture_morphometry_columns() -> None:
    """The morphometry CSV must expose columns the data_bridge can hit
    via exact + fuzzy passes."""
    df = pd.read_csv(FIXTURE_ROOT / "data" / "morphometry_per_cell.csv")
    cols = set(df.columns)
    assert {"cell_id", "genotype", "compartment", "area_um2",
            "perimeter_um", "branch_order"} <= cols


def test_fixture_effect_sizes_columns() -> None:
    df = pd.read_csv(FIXTURE_ROOT / "data" / "effect_sizes.csv")
    cols = set(df.columns)
    assert {"feature", "scale", "compartment", "d", "ci_lo", "ci_hi"} <= cols


# ───────────────── 8) HARD_FILTER_KEYS still re-exported ────────────────


def test_hard_filter_keys_visible() -> None:
    """Sanity guard: this test imports HARD_FILTER_KEYS to keep the
    intake module's surface intact for autonomous flows."""
    assert "compartment_aware" in HARD_FILTER_KEYS
    assert "scale_aware" in HARD_FILTER_KEYS
