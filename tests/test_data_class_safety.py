"""Tests for the data-class safety mode (Sprint 2B — v1.11.0).

Spec: ``docs/spec_data_class_safety.md``.

Coverage map (spec §10):

* Three-mode predicates (clinical / research / public) — each
  ``is_*_allowed`` returns the value the spec table requires.
* PHI scanner positive controls (``mrn``, ``patient_dob``, ``ssn``,
  ``dob``, ``email``, ``phone``).
* PHI scanner negative controls (``cell_id``, ``area_um2``, ``feature``).
* Default class is RESEARCH.
* CLI ``figures config show`` and ``figures config set`` round-trip.
* CLI ``figures audit data-class`` happy path + HIGH-risk error path.
* Integration: ``data_bridge._llm_pass`` returns unbound under clinical.
* Integration: ``provenance.build_provenance`` redacts under clinical.

The fixtures restore the module-level data class to RESEARCH after
every test so the order of tests in the suite cannot leak state into
other test modules (e.g. ``test_data_bridge``).
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures import safety
from panelforge_figures.cli import main as cli_main
from panelforge_figures.safety import (
    DataClass,
    DataClassError,
    get_data_class,
    get_policy,
    is_llm_allowed,
    is_plugin_network_allowed,
    is_telemetry_allowed,
    is_vision_allowed,
    set_data_class,
    should_redact_provenance_hashes,
)
from panelforge_figures.safety.phi_pattern_scanner import (
    match_column,
    scan_columns_for_phi,
)

# ---------------------------------------------------------------------------
# Fixtures — auto-restore module state to RESEARCH after every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_default_class() -> Iterator[None]:
    """Reset module-level ``_CURRENT_DATA_CLASS`` to RESEARCH after each
    test so we cannot leak clinical state into adjacent test modules
    (which would silently disable LLM Pass-3 in their fixtures).
    """
    saved = get_data_class()
    try:
        yield
    finally:
        set_data_class(saved if saved == DataClass.RESEARCH else DataClass.RESEARCH)


# ---------------------------------------------------------------------------
# Module-level predicates — three-mode coverage
# ---------------------------------------------------------------------------


def test_default_data_class_is_research() -> None:
    """Spec §2: the default when no class is declared is research."""
    assert get_data_class() == DataClass.RESEARCH


def test_clinical_disables_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clinical → ``is_llm_allowed`` is False even with API key set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)
    assert is_llm_allowed() is False


def test_clinical_disables_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clinical → ``is_vision_allowed`` is False even with API key set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)
    assert is_vision_allowed() is False


def test_clinical_telemetry_off() -> None:
    """Clinical → ``is_telemetry_allowed`` is False (forced off)."""
    set_data_class(DataClass.CLINICAL)
    assert is_telemetry_allowed() is False


def test_clinical_redacts_provenance() -> None:
    """Clinical → ``should_redact_provenance_hashes`` is True."""
    set_data_class(DataClass.CLINICAL)
    assert should_redact_provenance_hashes() is True


def test_clinical_disallows_plugin_network() -> None:
    """Clinical → ``is_plugin_network_allowed`` is False."""
    set_data_class(DataClass.CLINICAL)
    assert is_plugin_network_allowed() is False


def test_research_llm_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Research + API key set → LLM allowed (key is the opt-in signal)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.RESEARCH)
    assert is_llm_allowed() is True


def test_research_llm_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Research + no API key → LLM not allowed."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    set_data_class(DataClass.RESEARCH)
    assert is_llm_allowed() is False


def test_research_vision_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """Research + API key → vision allowed; without key → not allowed."""
    set_data_class(DataClass.RESEARCH)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert is_vision_allowed() is True
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert is_vision_allowed() is False


def test_research_telemetry_opt_in_default_off() -> None:
    """Research → telemetry is opt-in but defaults OFF until project flag."""
    set_data_class(DataClass.RESEARCH)
    assert is_telemetry_allowed() is False


def test_research_provenance_full() -> None:
    """Research → full provenance hashes (no redaction)."""
    set_data_class(DataClass.RESEARCH)
    assert should_redact_provenance_hashes() is False


def test_public_llm_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Public class → ``is_llm_allowed`` is True even without API key.

    The bridge itself still checks for the key — this predicate just
    says the data class does not block the call.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    set_data_class(DataClass.PUBLIC)
    assert is_llm_allowed() is True


def test_public_vision_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Public class → ``is_vision_allowed`` is True (default-on)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    set_data_class(DataClass.PUBLIC)
    assert is_vision_allowed() is True


def test_public_telemetry_still_opt_in() -> None:
    """Public → telemetry remains opt-in (we never silently collect)."""
    set_data_class(DataClass.PUBLIC)
    assert is_telemetry_allowed() is False


def test_get_policy_matches_clinical_table() -> None:
    """The resolved DataClassPolicy for clinical matches spec §2 row."""
    set_data_class(DataClass.CLINICAL)
    p = get_policy()
    assert p.llm_pass3 == "disabled"
    assert p.telemetry == "off"
    assert p.vision == "disabled"
    assert p.provenance_hashes == "redacted"
    assert p.plugin_network_required == "disallowed"


def test_set_data_class_invalid_raises() -> None:
    """An unknown string raises ``DataClassError``."""
    with pytest.raises(DataClassError):
        set_data_class("regulated")


def test_set_data_class_accepts_string_form() -> None:
    """``set_data_class("public")`` works as a string convenience."""
    set_data_class("public")
    assert get_data_class() == DataClass.PUBLIC


# ---------------------------------------------------------------------------
# PHI scanner — positive controls (HIGH risk)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["mrn", "MRN", "Mrn", "patient_dob", "Patient-DOB", "PatientDOB",
     "ssn", "dob", "email", "phone", "phone_number",
     "date_of_birth", "BIRTHDATE", "birthday", "address", "npi"],
)
def test_phi_scanner_high_risk_positive(name: str) -> None:
    """Every name in the spec §4 high-risk set must match HIGH."""
    assert match_column(name) == "high"


# ---------------------------------------------------------------------------
# PHI scanner — medium risk
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["patient_id", "subject_id", "study_id", "encounter_id",
     "zip", "zipcode", "postal_code", "age_at_event", "age_yr",
     "sex", "gender", "race", "ethnicity"],
)
def test_phi_scanner_medium_risk(name: str) -> None:
    """Every name in the spec §4 medium-risk set must match MEDIUM."""
    assert match_column(name) == "medium"


# ---------------------------------------------------------------------------
# PHI scanner — negative controls (low risk → no match)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["cell_id", "well_id", "feature", "measurement", "area_um2",
     "intensity_mean", "velocity", "condition", "replicate", "batch",
     "channel"],
)
def test_phi_scanner_low_risk_negative(name: str) -> None:
    """Spec §4 low-risk negative controls must return None."""
    assert match_column(name) is None


def test_phi_scanner_findings_have_pattern() -> None:
    """Findings record the regex that matched for user-facing diagnostics."""
    findings = scan_columns_for_phi(["mrn", "feature", "subject_id"])
    levels = {f.column: f.risk_level for f in findings}
    assert levels == {"mrn": "high", "subject_id": "medium"}
    for f in findings:
        assert f.matched_pattern  # non-empty


def test_phi_scanner_one_finding_per_column() -> None:
    """A column is flagged at most once even if it matches multiple
    patterns at the same tier (spec §4 last paragraph + scanner
    docstring)."""
    findings = scan_columns_for_phi(["mrn"])
    assert len(findings) == 1


def test_phi_scanner_high_beats_medium() -> None:
    """A column matching both tiers wins HIGH (spec §4 last paragraph).

    ``patient_dob_age_yr`` matches the high-risk pattern ``patient_dob``
    AND the medium-risk pattern ``age_yr``; HIGH must win.
    """
    assert match_column("patient_dob_age_yr") == "high"


# ---------------------------------------------------------------------------
# Integration — LLM bridge under clinical
# ---------------------------------------------------------------------------


def test_llm_bridge_disabled_under_clinical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``data_bridge._llm_pass`` returns the unbound triple under clinical
    even when ANTHROPIC_API_KEY is set — proves the safety gate fires
    before any network code runs (spec §6 row 1)."""
    from panelforge_figures.manifest import data_bridge as db

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)

    column, conf, reason = db._llm_pass(
        field_name="estimates",
        field_type="float",
        field_description="point estimates",
        candidate_columns=["estimates_col"],
        samples={},
    )
    assert column is None
    assert conf == 0.0
    assert "data_class" in reason


# ---------------------------------------------------------------------------
# Integration — provenance redaction under clinical
# ---------------------------------------------------------------------------


def test_provenance_hashes_redacted_under_clinical(tmp_path: Path) -> None:
    """``build_provenance`` replaces sha256 with ``"[redacted]"`` under
    clinical while preserving path/format/n_rows (spec §6 row 4)."""
    from panelforge_figures.manifest import provenance as prov

    fig = tmp_path / "fig.pdf"
    fig.write_bytes(b"%PDF-1.4 fake bytes")
    src = tmp_path / "src.csv"
    src.write_text("a,b\n1,2\n3,4\n")
    recipe = tmp_path / "recipe.py"
    recipe.write_text("pass\n")

    set_data_class(DataClass.CLINICAL)
    rec = prov.build_provenance(
        figure_path=fig,
        recipe_full_name="modality.recipe",
        recipe_module_path=recipe,
        panelforge_version="1.11.0",
        panelforge_git_commit="0" * 40,
        data_files=[{"path": str(src), "format": "csv", "n_rows": 2}],
    )
    assert rec.data["sources"][0]["sha256"] == "[redacted]"
    # Path, format, n_rows must still be present for reproducibility.
    assert rec.data["sources"][0]["path"] == str(src)
    assert rec.data["sources"][0]["format"] == "csv"
    assert rec.data["sources"][0]["n_rows"] == 2


def test_provenance_hashes_full_under_research(tmp_path: Path) -> None:
    """Sanity check: the redaction path is gated, not always-on."""
    from panelforge_figures.manifest import provenance as prov

    fig = tmp_path / "fig.pdf"
    fig.write_bytes(b"%PDF-1.4 fake bytes")
    src = tmp_path / "src.csv"
    src.write_text("a\n1\n")
    recipe = tmp_path / "recipe.py"
    recipe.write_text("pass\n")

    set_data_class(DataClass.RESEARCH)
    rec = prov.build_provenance(
        figure_path=fig,
        recipe_full_name="modality.recipe",
        recipe_module_path=recipe,
        panelforge_version="1.11.0",
        panelforge_git_commit="0" * 40,
        data_files=[{"path": str(src)}],
    )
    sha = rec.data["sources"][0]["sha256"]
    assert sha is not None
    assert sha != "[redacted]"
    assert len(sha) == 64  # full sha256 hex digest


# ---------------------------------------------------------------------------
# CLI — figures config show / set
# ---------------------------------------------------------------------------


def test_cli_config_show_default() -> None:
    """``figures config show`` prints data_class + every policy row."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["config", "show"])
    assert result.exit_code == 0
    assert "data_class: research" in result.output
    assert "llm_pass3:" in result.output
    assert "telemetry:" in result.output
    assert "vision:" in result.output
    assert "provenance:" in result.output


def test_cli_config_set_data_class_clinical() -> None:
    """``figures config set data_class clinical`` flips the runtime mode."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["config", "set", "data_class", "clinical"])
    assert result.exit_code == 0
    assert "data_class = clinical" in result.output
    assert get_data_class() == DataClass.CLINICAL


def test_cli_config_set_invalid_value() -> None:
    """An invalid value exits with code 1 and a helpful message."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["config", "set", "data_class", "regulated"])
    assert result.exit_code == 1
    assert "invalid data_class" in result.output


def test_cli_config_set_unknown_key() -> None:
    """Unknown config keys exit with code 1."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["config", "set", "nonsense", "value"])
    assert result.exit_code == 1
    assert "unknown config key" in result.output


# ---------------------------------------------------------------------------
# CLI — figures audit data-class
# ---------------------------------------------------------------------------


def _write_csv_with_columns(path: Path, columns: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        writer.writerow([0] * len(columns))
    return path


def test_cli_audit_data_class_happy(tmp_path: Path) -> None:
    """No PHI patterns → exit 0 with success message."""
    data_dir = tmp_path / "data"
    _write_csv_with_columns(
        data_dir / "cells.csv",
        ["cell_id", "area_um2", "intensity_mean"],
    )
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["audit", "data-class", "--data-dir", str(data_dir)],
    )
    assert result.exit_code == 0
    assert "no PHI/PII patterns found" in result.output


def test_cli_audit_data_class_high_risk_in_research(tmp_path: Path) -> None:
    """HIGH-risk column found under data_class=research → exit 2."""
    data_dir = tmp_path / "data"
    _write_csv_with_columns(
        data_dir / "subjects.csv",
        ["subject_id", "patient_dob", "mrn"],
    )
    set_data_class(DataClass.RESEARCH)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["audit", "data-class", "--data-dir", str(data_dir)],
    )
    assert result.exit_code == 2
    assert "HIGH-risk" in result.output


def test_cli_audit_data_class_high_risk_in_clinical(tmp_path: Path) -> None:
    """HIGH-risk column under data_class=clinical → acknowledged, exit 0."""
    data_dir = tmp_path / "data"
    _write_csv_with_columns(
        data_dir / "subjects.csv",
        ["patient_dob"],
    )
    set_data_class(DataClass.CLINICAL)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["audit", "data-class", "--data-dir", str(data_dir)],
    )
    assert result.exit_code == 0
    # The acknowledgement message contains "acknowledged"
    assert "acknowledged" in result.output or "data_class=clinical" in result.output


def test_cli_audit_data_class_strict_promotes_warn(tmp_path: Path) -> None:
    """``--strict`` promotes medium-risk WARN to ERROR (exit 2)."""
    data_dir = tmp_path / "data"
    _write_csv_with_columns(
        data_dir / "samples.csv",
        ["cell_id", "subject_id"],  # medium-risk subject_id
    )
    set_data_class(DataClass.RESEARCH)
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["audit", "data-class", "--data-dir", str(data_dir), "--strict"],
    )
    assert result.exit_code == 2
    assert "medium-risk" in result.output


# ---------------------------------------------------------------------------
# Re-export sanity — every spec-named predicate is exposed on `safety`
# ---------------------------------------------------------------------------


def test_safety_module_exports_full_api() -> None:
    """Spec §6 names every predicate that gate sites must import."""
    expected = {
        "DataClass",
        "DataClassError",
        "DataClassPolicy",
        "get_data_class",
        "get_policy",
        "set_data_class",
        "is_llm_allowed",
        "is_telemetry_allowed",
        "is_vision_allowed",
        "is_plugin_network_allowed",
        "should_redact_provenance_hashes",
    }
    for name in expected:
        assert hasattr(safety, name), f"safety.{name} missing"
