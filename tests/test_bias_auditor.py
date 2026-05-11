"""Tests for the figure-bias auditor (Elevation 17 — v3.12.0).

Covers each individual structural check plus the directory-level
pipeline, the Markdown renderer, and the CLI / CI integration.

Each test builds a synthetic provenance dict in-memory, writes it to a
temp ``*.provenance.json``, and runs the auditor against it.  No
matplotlib calls happen anywhere — the auditor is purely metadata-driven
by design.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.bias_auditor import (
    BiasAuditorError,
    BiasFinding,
    BiasFindingKind,
    BiasSeverity,
    audit_bias_across_directory,
    audit_bias_for_figure,
    check_3d_on_2d_data,
    check_axis_truncation,
    check_ci_omission_when_contract_requires,
    check_color_blind_unsafe,
    check_dual_axes,
    check_non_monotonic_ordinal_ordering,
    check_p_value_threshold_only,
    check_sample_size_missing_when_under_min_n,
    check_scale_distribution_mismatch,
    check_underpowered_unflagged,
    render_bias_audit_markdown,
)
from panelforge_figures.manifest.ci_runner import (
    CIAuditStep,
    CIStepResult,
    StepStatus,
    _run_audit_bias,
)

# --------------------------------------------------------------------------- #
# Fixture helpers                                                              #
# --------------------------------------------------------------------------- #


def _make_provenance(
    *,
    figure_path: str = "figure_1.png",
    recipe_full_name: str = "modality.recipe",
    family: str = "comparison",
    contract: dict[str, Any] | None = None,
    statistical_contract: dict[str, Any] | None = None,
    audit_findings: dict[str, Any] | None = None,
    caption: str | None = None,
) -> dict[str, Any]:
    """Build a minimal provenance dict compatible with the auditor.

    The auditor only inspects three structural blocks — recipe (for
    contract + statistical_contract + full_name), audit_findings, and
    optional caption metadata.  Hash / data fields are unused but
    included to mirror the real schema.
    """
    rec: dict[str, Any] = {
        "schema_version": "1.1.0",
        "figure_path": figure_path,
        "figure_sha256": "abc123",
        "rendered_at": "2026-01-01T00:00:00Z",
        "recipe": {
            "full_name": recipe_full_name,
            "module_sha": None,
            "module_path": "/tmp/recipe.py",
            "panelforge_version": "3.12.0",
            "panelforge_git_commit": "uncommitted",
            "family": family,
            "contract": contract or {},
            "statistical_contract": statistical_contract or {},
        },
        "data": {"sources": [], "column_mapping": {}},
        "audit": audit_findings or {},
        "rendering_environment": {},
    }
    if caption is not None:
        rec["caption"] = caption
    return rec


def _write_provenance(tmp_path: Path, provenance: dict[str, Any]) -> Path:
    """Write a provenance dict to ``<figure>.provenance.json``."""
    fig_path = tmp_path / provenance["figure_path"]
    fig_path.write_bytes(b"")  # touch the figure file so it exists
    out = fig_path.with_suffix(fig_path.suffix + ".provenance.json")
    out.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# 1. check_axis_truncation                                                     #
# --------------------------------------------------------------------------- #


def test_axis_truncation_flags_non_zero_start_with_positive_data() -> None:
    """y-axis starting at 1.0 when data minimum = 1.2 → warning."""
    prov = _make_provenance(
        family="comparison",
        contract={"y_axis_range": [1.0, 5.0]},
        audit_findings={"y_min": 1.2},
    )
    findings = check_axis_truncation(prov, "Figure 1")
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == BiasFindingKind.truncated_y_axis
    assert f.severity == BiasSeverity.warning
    assert "visual exaggeration risk" in f.message
    assert f.evidence["axis_min"] == 1.0
    assert f.evidence["data_min"] == 1.2


def test_axis_truncation_passes_when_axis_starts_at_zero() -> None:
    """y-axis from 0 → no finding even when data is positive."""
    prov = _make_provenance(
        family="comparison",
        contract={"y_axis_range": [0.0, 5.0]},
        audit_findings={"y_min": 1.2},
    )
    assert check_axis_truncation(prov, "Figure 1") == []


def test_axis_truncation_passes_when_data_can_be_negative() -> None:
    """If data minimum is <= 0, truncation isn't material."""
    prov = _make_provenance(
        family="comparison",
        contract={"y_axis_range": [1.0, 5.0]},
        audit_findings={"y_min": -0.5},
    )
    assert check_axis_truncation(prov, "Figure 1") == []


def test_axis_truncation_skipped_for_non_magnitude_family() -> None:
    """A timecourse panel may legitimately not start at zero."""
    prov = _make_provenance(
        family="timecourse_hierarchical_ci",
        contract={"y_axis_range": [1.0, 5.0]},
        audit_findings={"y_min": 1.2},
    )
    assert check_axis_truncation(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 2. check_dual_axes                                                           #
# --------------------------------------------------------------------------- #


def test_dual_axes_flags_incompatible_metric_pairing() -> None:
    """Dual axes with declared but different families → warning."""
    prov = _make_provenance(
        contract={
            "dual_axes": True,
            "y_axis_family": "concentration",
            "secondary_y_axis_family": "time",
        },
    )
    findings = check_dual_axes(prov, "Figure 1")
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == BiasFindingKind.dual_y_axis
    assert f.severity == BiasSeverity.warning
    assert "concentration" in f.message
    assert "time" in f.message


def test_dual_axes_passes_when_same_family() -> None:
    prov = _make_provenance(
        contract={
            "dual_axes": True,
            "y_axis_family": "concentration",
            "secondary_y_axis_family": "concentration",
        },
    )
    assert check_dual_axes(prov, "Figure 1") == []


def test_dual_axes_warns_when_families_undeclared() -> None:
    """Dual axes with no declared families → still a warning (conservative)."""
    prov = _make_provenance(
        contract={"dual_axes": True, "secondary_y_axis_label": "Right axis"},
    )
    findings = check_dual_axes(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.dual_y_axis


def test_dual_axes_skipped_when_no_secondary() -> None:
    prov = _make_provenance(contract={})
    assert check_dual_axes(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 3. check_scale_distribution_mismatch                                         #
# --------------------------------------------------------------------------- #


def test_scale_mismatch_log_data_linear_axis_warns() -> None:
    """Heavy-tailed data on a linear axis → warning."""
    prov = _make_provenance(
        contract={"y_scale": "linear"},
        audit_findings={
            "data_distribution_shape": {
                "kind": "log_distributed",
                "max_over_min": 250.0,
            }
        },
    )
    findings = check_scale_distribution_mismatch(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.linear_on_log_data
    assert findings[0].severity == BiasSeverity.warning


def test_scale_mismatch_linear_data_log_axis_warns() -> None:
    prov = _make_provenance(
        contract={"y_scale": "log"},
        audit_findings={
            "data_distribution_shape": {"kind": "linear_distributed"}
        },
    )
    findings = check_scale_distribution_mismatch(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.log_on_linear_data


def test_scale_mismatch_skipped_when_distribution_shape_missing() -> None:
    """Older sidecars without distribution_shape → graceful skip."""
    prov = _make_provenance(
        contract={"y_scale": "linear"},
        audit_findings={"some_other_field": 42},
    )
    assert check_scale_distribution_mismatch(prov, "Figure 1") == []


def test_scale_mismatch_passes_when_aligned() -> None:
    """Log data on log axis → no finding."""
    prov = _make_provenance(
        contract={"y_scale": "log"},
        audit_findings={
            "data_distribution_shape": {"kind": "log_distributed"}
        },
    )
    assert check_scale_distribution_mismatch(prov, "Figure 1") == []


def test_scale_mismatch_triggers_on_ratio_alone() -> None:
    """max_over_min > 100 alone implies log-distributed."""
    prov = _make_provenance(
        contract={"y_scale": "linear"},
        audit_findings={
            "data_distribution_shape": {"max_over_min": 500.0}
        },
    )
    findings = check_scale_distribution_mismatch(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.linear_on_log_data


# --------------------------------------------------------------------------- #
# 4. check_ci_omission_when_contract_requires                                  #
# --------------------------------------------------------------------------- #


def test_ci_omission_requires_ci_true_no_ci_is_error() -> None:
    prov = _make_provenance(
        statistical_contract={"requires_ci": True},
        audit_findings={"p_value": 0.01},
    )
    findings = check_ci_omission_when_contract_requires(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.ci_omitted
    assert findings[0].severity == BiasSeverity.error


def test_ci_omission_requires_ci_true_with_ci_passes() -> None:
    prov = _make_provenance(
        statistical_contract={"requires_ci": True},
        audit_findings={"ci_lo": 0.1, "ci_hi": 0.4},
    )
    assert check_ci_omission_when_contract_requires(prov, "Figure 1") == []


def test_ci_omission_inferred_from_family_is_warning() -> None:
    """comparison family without explicit requires_ci → warning (inferred)."""
    prov = _make_provenance(
        family="comparison",
        statistical_contract={},
        audit_findings={"p_value": 0.01},
    )
    findings = check_ci_omission_when_contract_requires(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.ci_omitted
    assert findings[0].severity == BiasSeverity.warning


def test_ci_omission_descriptive_family_skipped() -> None:
    prov = _make_provenance(
        family="descriptive",
        statistical_contract={},
        audit_findings={},
    )
    assert check_ci_omission_when_contract_requires(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 5. check_sample_size_missing_when_under_min_n                                #
# --------------------------------------------------------------------------- #


def test_sample_size_missing_n4_minN10_is_error() -> None:
    prov = _make_provenance(
        statistical_contract={"min_n_per_group": 10},
        contract={"sample_size_annotation": False},
        audit_findings={"n_per_group": 4},
    )
    findings = check_sample_size_missing_when_under_min_n(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.sample_size_missing
    assert findings[0].severity == BiasSeverity.error
    assert findings[0].evidence["n"] == 4
    assert findings[0].evidence["min_n_per_group"] == 10


def test_sample_size_with_annotation_passes() -> None:
    """If the recipe declares it overlays n labels, no finding."""
    prov = _make_provenance(
        statistical_contract={"min_n_per_group": 10},
        contract={"sample_size_annotation": True},
        audit_findings={"n_per_group": 4},
    )
    assert check_sample_size_missing_when_under_min_n(prov, "Figure 1") == []


def test_sample_size_above_min_n_passes() -> None:
    prov = _make_provenance(
        statistical_contract={"min_n_per_group": 10},
        audit_findings={"n_per_group": 50},
    )
    assert check_sample_size_missing_when_under_min_n(prov, "Figure 1") == []


def test_sample_size_skipped_when_min_n_not_set() -> None:
    prov = _make_provenance(audit_findings={"n_per_group": 4})
    assert check_sample_size_missing_when_under_min_n(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 6. check_underpowered_unflagged                                              #
# --------------------------------------------------------------------------- #


def test_underpowered_unflagged_no_caption_mention_warns() -> None:
    prov = _make_provenance(
        audit_findings={"underpowered": True},
        caption="Figure 1 shows our beautiful result.",
    )
    findings = check_underpowered_unflagged(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.underpowered_unflagged
    assert findings[0].severity == BiasSeverity.warning


def test_underpowered_with_caption_acknowledgement_passes() -> None:
    prov = _make_provenance(
        audit_findings={"underpowered": True},
        caption=(
            "Figure 1 shows preliminary results owing to limited sample size."
        ),
    )
    assert check_underpowered_unflagged(prov, "Figure 1") == []


def test_underpowered_false_skipped() -> None:
    prov = _make_provenance(audit_findings={"underpowered": False})
    assert check_underpowered_unflagged(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 7. check_3d_on_2d_data                                                       #
# --------------------------------------------------------------------------- #


def test_3d_style_on_2d_data_warns() -> None:
    prov = _make_provenance(
        contract={"style_3d_effects": True},
        audit_findings={"n_dimensions": 2},
    )
    findings = check_3d_on_2d_data(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.three_d_effects
    assert findings[0].severity == BiasSeverity.warning


def test_3d_recipe_name_pattern_triggers() -> None:
    prov = _make_provenance(
        recipe_full_name="modality.three_d_bar_chart",
        audit_findings={},
    )
    findings = check_3d_on_2d_data(prov, "Figure 1")
    assert len(findings) == 1


def test_3d_on_3d_data_passes() -> None:
    prov = _make_provenance(
        contract={"style_3d_effects": True},
        audit_findings={"n_dimensions": 3},
    )
    assert check_3d_on_2d_data(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 8. check_p_value_threshold_only                                              #
# --------------------------------------------------------------------------- #


def test_p_value_below_05_without_effect_size_warns() -> None:
    prov = _make_provenance(audit_findings={"p_value": 0.03})
    findings = check_p_value_threshold_only(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.p_value_threshold_only
    assert findings[0].severity == BiasSeverity.warning


def test_p_value_with_effect_size_passes() -> None:
    prov = _make_provenance(
        audit_findings={"p_value": 0.03, "effect_size": 0.8}
    )
    assert check_p_value_threshold_only(prov, "Figure 1") == []


def test_p_value_above_05_skipped() -> None:
    prov = _make_provenance(audit_findings={"p_value": 0.12})
    assert check_p_value_threshold_only(prov, "Figure 1") == []


def test_p_value_with_cohens_d_passes() -> None:
    prov = _make_provenance(
        audit_findings={"p_value": 0.01, "cohens_d": 0.5}
    )
    assert check_p_value_threshold_only(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 9. check_color_blind_unsafe                                                  #
# --------------------------------------------------------------------------- #


def test_jet_colormap_warns() -> None:
    prov = _make_provenance(contract={"colormap": "jet"})
    findings = check_color_blind_unsafe(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.color_blind_unsafe
    assert findings[0].severity == BiasSeverity.warning
    assert "jet" in findings[0].message.lower()


def test_rainbow_colormap_warns() -> None:
    prov = _make_provenance(contract={"colormap": "rainbow"})
    findings = check_color_blind_unsafe(prov, "Figure 1")
    assert len(findings) == 1


def test_viridis_colormap_passes() -> None:
    prov = _make_provenance(contract={"colormap": "viridis"})
    assert check_color_blind_unsafe(prov, "Figure 1") == []


def test_cividis_colormap_passes() -> None:
    prov = _make_provenance(contract={"colormap": "cividis"})
    assert check_color_blind_unsafe(prov, "Figure 1") == []


def test_no_colormap_declared_skipped() -> None:
    prov = _make_provenance(contract={})
    assert check_color_blind_unsafe(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 10. check_non_monotonic_ordinal_ordering                                     #
# --------------------------------------------------------------------------- #


def test_alphabetical_order_passes() -> None:
    prov = _make_provenance(
        contract={
            "x_categorical": True,
            "x_categorical_order": ["alpha", "beta", "gamma"],
        }
    )
    assert check_non_monotonic_ordinal_ordering(prov, "Figure 1") == []


def test_non_monotonic_order_info() -> None:
    prov = _make_provenance(
        contract={
            "x_categorical": True,
            "x_categorical_order": ["gamma", "alpha", "beta"],
        }
    )
    findings = check_non_monotonic_ordinal_ordering(prov, "Figure 1")
    assert len(findings) == 1
    assert findings[0].kind == BiasFindingKind.non_monotonic_categorical
    assert findings[0].severity == BiasSeverity.info


def test_semantic_order_passes() -> None:
    prov = _make_provenance(
        contract={
            "x_categorical": True,
            "x_categorical_order": ["wt", "het", "ko"],
            "semantic_ordering": ["wt", "het", "ko"],
        }
    )
    assert check_non_monotonic_ordinal_ordering(prov, "Figure 1") == []


# --------------------------------------------------------------------------- #
# 11. audit_bias_for_figure on a synthetic sidecar                             #
# --------------------------------------------------------------------------- #


def test_audit_bias_for_figure_multiple_issues(tmp_path: Path) -> None:
    """One sidecar tripping three checks → three findings."""
    prov = _make_provenance(
        family="comparison",
        contract={
            "y_axis_range": [1.0, 5.0],
            "colormap": "jet",
        },
        statistical_contract={"requires_ci": True},
        audit_findings={
            "y_min": 1.2,
            "p_value": 0.001,
        },
    )
    path = _write_provenance(tmp_path, prov)
    findings = audit_bias_for_figure(path)
    kinds = {f.kind for f in findings}
    assert BiasFindingKind.truncated_y_axis in kinds
    assert BiasFindingKind.color_blind_unsafe in kinds
    assert BiasFindingKind.ci_omitted in kinds
    assert BiasFindingKind.p_value_threshold_only in kinds


def test_audit_bias_for_figure_clean(tmp_path: Path) -> None:
    """A well-formed sidecar produces zero findings."""
    prov = _make_provenance(
        family="comparison",
        contract={"y_axis_range": [0.0, 5.0], "colormap": "viridis"},
        statistical_contract={"requires_ci": True},
        audit_findings={
            "y_min": 0.5,
            "ci_lo": 0.4,
            "ci_hi": 0.6,
            "p_value": 0.4,
        },
    )
    path = _write_provenance(tmp_path, prov)
    findings = audit_bias_for_figure(path)
    assert findings == ()


def test_audit_bias_for_figure_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BiasAuditorError):
        audit_bias_for_figure(tmp_path / "nonexistent.provenance.json")


def test_audit_bias_for_figure_bad_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "figure_1.png.provenance.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(BiasAuditorError):
        audit_bias_for_figure(bad)


# --------------------------------------------------------------------------- #
# 12. audit_bias_across_directory                                              #
# --------------------------------------------------------------------------- #


def test_audit_across_directory_aggregates(tmp_path: Path) -> None:
    """Two sidecars → both audited; counts and verdict are aggregate."""
    fig1 = tmp_path / "figure_1.png"
    fig2 = tmp_path / "figure_2.png"
    fig1.write_bytes(b"")
    fig2.write_bytes(b"")

    # fig1: clean
    p1 = _make_provenance(
        figure_path="figure_1.png",
        family="descriptive",
        audit_findings={},
        contract={"colormap": "viridis"},
    )
    (fig1.with_suffix(fig1.suffix + ".provenance.json")).write_text(
        json.dumps(p1), encoding="utf-8"
    )

    # fig2: tripped checks
    p2 = _make_provenance(
        figure_path="figure_2.png",
        family="comparison",
        contract={"y_axis_range": [2.0, 5.0], "colormap": "jet"},
        audit_findings={"y_min": 2.5},
    )
    (fig2.with_suffix(fig2.suffix + ".provenance.json")).write_text(
        json.dumps(p2), encoding="utf-8"
    )

    report = audit_bias_across_directory(tmp_path)
    assert report.n_figures_inspected == 2
    assert report.n_figures_skipped == 0
    assert len(report.audited_figures) == 2
    assert report.n_errors + report.n_warnings + report.n_info > 0
    # No errors (only warnings) → needs_review
    assert report.overall_verdict in ("needs_review", "concerning")


def test_audit_across_directory_empty_is_honest(tmp_path: Path) -> None:
    report = audit_bias_across_directory(tmp_path)
    assert report.n_figures_inspected == 0
    assert report.overall_verdict == "honest"


def test_audit_across_directory_missing_dir_raises() -> None:
    with pytest.raises(BiasAuditorError):
        audit_bias_across_directory(Path("/tmp/does-not-exist-bias-auditor-xyz"))


def test_audit_across_directory_concerning_when_errors(tmp_path: Path) -> None:
    """An error-level finding → verdict concerning."""
    prov = _make_provenance(
        statistical_contract={"requires_ci": True},
        audit_findings={"p_value": 0.5},
    )
    _write_provenance(tmp_path, prov)
    report = audit_bias_across_directory(tmp_path)
    assert report.n_errors >= 1
    assert report.overall_verdict == "concerning"


# --------------------------------------------------------------------------- #
# 13. BiasAuditReport.to_dict + BiasFinding.to_dict serialisation              #
# --------------------------------------------------------------------------- #


def test_bias_finding_to_dict_round_trip() -> None:
    f = BiasFinding(
        kind=BiasFindingKind.truncated_y_axis,
        severity=BiasSeverity.warning,
        figure_id="Figure 1",
        panel_id="A",
        message="msg",
        evidence={"axis_min": 1.0},
        remediation="fix it",
        location="recipe.full",
    )
    d = f.to_dict()
    # All keys serialise to JSON cleanly.
    assert json.dumps(d, default=str)
    assert d["kind"] == "truncated_y_axis"
    assert d["severity"] == "warning"


def test_bias_audit_report_to_dict_round_trip(tmp_path: Path) -> None:
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0]},
            audit_findings={"y_min": 2.5},
        ),
    )
    report = audit_bias_across_directory(tmp_path)
    d = report.to_dict()
    assert json.dumps(d, default=str)
    assert "findings" in d
    assert "overall_verdict" in d
    assert d["n_figures_inspected"] == 1


# --------------------------------------------------------------------------- #
# 14. render_bias_audit_markdown                                               #
# --------------------------------------------------------------------------- #


def test_render_markdown_contains_findings_grouped_by_severity(tmp_path: Path) -> None:
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0], "colormap": "jet"},
            statistical_contract={"requires_ci": True},
            audit_findings={"y_min": 2.5},
        ),
    )
    report = audit_bias_across_directory(tmp_path)
    md = render_bias_audit_markdown(report)
    assert "Figure-bias audit" in md
    assert "Verdict" in md
    assert "concerning" in md  # CI omitted with requires_ci=True is an error
    # Sections present for the severities we emit.
    assert "## Errors" in md
    assert "## Warnings" in md


def test_render_markdown_empty_directory() -> None:
    from panelforge_figures.manifest.bias_auditor import BiasAuditReport

    report = BiasAuditReport(
        audited_figures=(),
        findings=(),
        n_errors=0,
        n_warnings=0,
        n_info=0,
        n_figures_inspected=0,
        n_figures_skipped=0,
        overall_verdict="honest",
    )
    md = render_bias_audit_markdown(report)
    assert "Figure-bias audit" in md
    assert "honest" in md
    assert "No figures with provenance sidecars" in md


# --------------------------------------------------------------------------- #
# 15. CLI integration                                                          #
# --------------------------------------------------------------------------- #


def test_cli_audit_bias_help() -> None:
    r = CliRunner().invoke(main, ["audit-bias", "--help"])
    assert r.exit_code == 0
    assert "audit-bias" in r.output.lower() or "bias" in r.output.lower()
    assert "--output" in r.output
    assert "--json" in r.output
    assert "--fail-on-warning" in r.output


def test_cli_audit_bias_clean_dir_exit_zero(tmp_path: Path) -> None:
    """Empty figures dir → exit 0 (honest verdict)."""
    r = CliRunner().invoke(main, ["audit-bias", str(tmp_path)])
    assert r.exit_code == 0
    assert "honest" in r.output


def test_cli_audit_bias_with_errors_exit_one(tmp_path: Path) -> None:
    """Provenance with error-severity finding → exit 1."""
    _write_provenance(
        tmp_path,
        _make_provenance(
            statistical_contract={"requires_ci": True},
            audit_findings={"p_value": 0.5},
        ),
    )
    r = CliRunner().invoke(main, ["audit-bias", str(tmp_path)])
    assert r.exit_code == 1
    assert "concerning" in r.output


def test_cli_audit_bias_fail_on_warning(tmp_path: Path) -> None:
    """--fail-on-warning promotes warn (needs_review) to exit 1."""
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0]},
            audit_findings={"y_min": 2.5},
        ),
    )
    r = CliRunner().invoke(
        main, ["audit-bias", str(tmp_path), "--fail-on-warning"]
    )
    assert r.exit_code == 1
    assert "needs_review" in r.output


def test_cli_audit_bias_json_output(tmp_path: Path) -> None:
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0]},
            audit_findings={"y_min": 2.5},
        ),
    )
    r = CliRunner().invoke(main, ["audit-bias", str(tmp_path), "--json"])
    assert r.exit_code == 0  # warn-only ≠ fail unless --fail-on-warning
    data = json.loads(r.output)
    assert "findings" in data
    assert data["overall_verdict"] == "needs_review"


def test_cli_audit_bias_output_path(tmp_path: Path) -> None:
    fig_dir = tmp_path / "figs"
    fig_dir.mkdir()
    _write_provenance(
        fig_dir,
        _make_provenance(family="descriptive", audit_findings={}),
    )
    out = tmp_path / "bias_report.md"
    r = CliRunner().invoke(
        main, ["audit-bias", str(fig_dir), "--output", str(out)]
    )
    assert r.exit_code == 0
    assert out.exists()
    assert "Figure-bias audit" in out.read_text()


# --------------------------------------------------------------------------- #
# 16. CI runner integration                                                    #
# --------------------------------------------------------------------------- #


def test_ci_runner_audit_bias_real_status_on_concerning(tmp_path: Path) -> None:
    """_run_audit_bias now returns a real status (not skipped placeholder)."""
    _write_provenance(
        tmp_path,
        _make_provenance(
            statistical_contract={"requires_ci": True},
            audit_findings={"p_value": 0.5},
        ),
    )
    r = _run_audit_bias(figures_dir=tmp_path)
    assert r.step == CIAuditStep.audit_bias
    assert r.status == StepStatus.fail
    assert r.n_errors >= 1
    assert "concerning" in r.summary


def test_ci_runner_audit_bias_pass_on_honest(tmp_path: Path) -> None:
    _write_provenance(
        tmp_path,
        _make_provenance(family="descriptive", audit_findings={}),
    )
    r = _run_audit_bias(figures_dir=tmp_path)
    assert r.step == CIAuditStep.audit_bias
    assert r.status == StepStatus.pass_
    assert "honest" in r.summary


def test_ci_runner_audit_bias_warn_on_needs_review(tmp_path: Path) -> None:
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0]},
            audit_findings={"y_min": 2.5},
        ),
    )
    r = _run_audit_bias(figures_dir=tmp_path)
    assert r.step == CIAuditStep.audit_bias
    assert r.status == StepStatus.warn
    assert r.n_warnings >= 1


# --------------------------------------------------------------------------- #
# 17. Version bump                                                             #
# --------------------------------------------------------------------------- #


def test_version_bump_to_3_12_0() -> None:
    from panelforge_figures import __version__

    assert __version__ == "3.12.0"


# --------------------------------------------------------------------------- #
# 18. StatisticalContract.requires_ci field                                    #
# --------------------------------------------------------------------------- #


def test_statistical_contract_requires_ci_default_false() -> None:
    from panelforge_figures.core.statistical_contract import StatisticalContract

    sc = StatisticalContract()
    assert sc.requires_ci is False


def test_statistical_contract_requires_ci_can_be_set() -> None:
    from panelforge_figures.core.statistical_contract import StatisticalContract

    sc = StatisticalContract(requires_ci=True)
    assert sc.requires_ci is True


# --------------------------------------------------------------------------- #
# 19. CIStepResult round-trip for audit_bias                                   #
# --------------------------------------------------------------------------- #


def test_ci_step_result_audit_bias_to_dict(tmp_path: Path) -> None:
    """The audit-bias step result is JSON-serialisable."""
    _write_provenance(
        tmp_path,
        _make_provenance(
            family="comparison",
            contract={"y_axis_range": [2.0, 5.0]},
            audit_findings={"y_min": 2.5},
        ),
    )
    r = _run_audit_bias(figures_dir=tmp_path)
    assert isinstance(r, CIStepResult)
    d = r.to_dict()
    assert json.dumps(d, default=str)
    assert d["step"] == "audit-bias"
