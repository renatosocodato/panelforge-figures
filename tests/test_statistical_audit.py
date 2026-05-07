"""Tests for the statistical-contract audit pipeline (Sprint 1A).

Validates the 13 rule functions in
``panelforge_figures.manifest.statistical_audit`` against synthetic data,
plus integration with ``RecipeMetadata`` and the registry.

The fixtures use a fixed RNG seed so KS-test verdicts are stable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from panelforge_figures.core import (
    DEFAULT_CONTRACT,
    RecipeMetadata,
    StatisticalContract,
)
from panelforge_figures.core.contract import RecipeFamily
from panelforge_figures.manifest import (
    ALL_RULE_NAMES,
    AuditFinding,
    AuditReport,
    StatisticalContractViolation,
    audit_recipe_against_data,
)
from panelforge_figures.manifest.statistical_audit import _DEFAULT_VERDICT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _audit(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None = None,
    recipe_full_name: str = "test.recipe",
) -> AuditReport:
    return audit_recipe_against_data(
        contract=contract,
        data=data,
        group_column=group_column,
        recipe_full_name=recipe_full_name,
    )


def _findings_by_rule(report: AuditReport) -> dict[str, AuditFinding]:
    return {f.rule_id: f for f in report.findings}


# ---------------------------------------------------------------------------
# Sanity / structural tests
# ---------------------------------------------------------------------------


def test_audit_module_exposes_thirteen_rules():
    """Spec §3 enumerates exactly 13 rule names."""
    assert len(ALL_RULE_NAMES) == 13
    assert len(_DEFAULT_VERDICT) == 13
    assert set(ALL_RULE_NAMES) == set(_DEFAULT_VERDICT)


def test_default_contract_is_all_permissive():
    """Default contract has no triggering field set."""
    c = StatisticalContract()
    assert c.min_n_per_group is None
    assert c.distribution_assumption == "any"
    assert c.multiple_comparisons == "none"
    assert c.independence == "any"
    assert c.refuses_when == ()
    assert c == DEFAULT_CONTRACT


def test_recipe_metadata_carries_default_contract():
    """RecipeMetadata default keeps existing 392 untagged recipes silent."""
    m = RecipeMetadata(
        name="r",
        modality="m",
        family=RecipeFamily.coef_forest,
        answers_question="?",
        required_fields=("rows",),
    )
    assert m.statistical_contract == DEFAULT_CONTRACT


# ---------------------------------------------------------------------------
# Rule 1 — underpowered
# ---------------------------------------------------------------------------


def test_audit_default_contract_passes_all():
    """Default all-permissive contract → all 13 rules pass on any data."""
    df = pd.DataFrame({"group": ["A"] * 5 + ["B"] * 5, "value": np.arange(10.0)})
    report = _audit(StatisticalContract(), df, group_column="group")
    assert report.overall == "pass"
    assert report.findings == ()


def test_underpowered_3_cells_refused():
    """min_n_per_group=10, 3 per group → refuse with named rule."""
    df = pd.DataFrame(
        {
            "group": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
        }
    )
    contract = StatisticalContract(min_n_per_group=10)
    report = _audit(contract, df, group_column="group")
    assert report.overall == "refuse"
    by_rule = _findings_by_rule(report)
    assert "underpowered" in by_rule
    assert by_rule["underpowered"].n_observed == 3
    assert by_rule["underpowered"].threshold == 10


# ---------------------------------------------------------------------------
# Rule 2 — non_normal_with_parametric_test
# ---------------------------------------------------------------------------


def test_normal_data_with_gaussian_assumption_passes():
    """Gaussian-generated data + approximately_gaussian → pass."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "group": ["A"] * 60 + ["B"] * 60,
            "value": np.concatenate(
                [rng.normal(0, 1, 60), rng.normal(0.2, 1, 60)]
            ),
        }
    )
    contract = StatisticalContract(distribution_assumption="approximately_gaussian")
    report = _audit(contract, df, group_column="group")
    assert "non_normal_with_parametric_test" not in _findings_by_rule(report)
    assert report.overall == "pass"


def test_heavy_tail_with_gaussian_assumption_warned():
    """Cauchy-distributed data + gaussian → warn (default verdict)."""
    rng = np.random.default_rng(7)
    df = pd.DataFrame({"value": rng.standard_cauchy(200)})
    contract = StatisticalContract(distribution_assumption="approximately_gaussian")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "non_normal_with_parametric_test" in by_rule
    assert by_rule["non_normal_with_parametric_test"].severity == "warn"


# ---------------------------------------------------------------------------
# Rule 3 — uncorrected_multiple_comparisons
# ---------------------------------------------------------------------------


def test_uncorrected_mc_refused():
    """any_correction_required + no q_value column → refuse."""
    df = pd.DataFrame({"effect": [0.1, 0.2, 0.3], "p": [0.04, 0.03, 0.02]})
    contract = StatisticalContract(multiple_comparisons="any_correction_required")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "uncorrected_multiple_comparisons" in by_rule
    assert report.overall == "refuse"


def test_corrected_mc_silent_when_q_value_present():
    """Presence of q_value column quiets the rule."""
    df = pd.DataFrame(
        {"effect": [0.1, 0.2], "p": [0.04, 0.03], "q_value": [0.08, 0.06]}
    )
    contract = StatisticalContract(multiple_comparisons="any_correction_required")
    report = _audit(contract, df)
    assert "uncorrected_multiple_comparisons" not in _findings_by_rule(report)


# ---------------------------------------------------------------------------
# Rule 4 — missing_paired_structure
# ---------------------------------------------------------------------------


def test_paired_without_subject_id_refused():
    """independence=paired, no subject_id col → refuse."""
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    contract = StatisticalContract(independence="paired")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "missing_paired_structure" in by_rule
    assert report.overall == "refuse"


def test_paired_with_subject_id_passes():
    """independence=paired with valid pairing → silent."""
    df = pd.DataFrame(
        {
            "subject_id": ["s1", "s1", "s2", "s2"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    contract = StatisticalContract(independence="paired")
    report = _audit(contract, df)
    assert "missing_paired_structure" not in _findings_by_rule(report)


# ---------------------------------------------------------------------------
# Rule 5 — singular_design
# ---------------------------------------------------------------------------


def test_singular_design_refused():
    """Rank-deficient covariate matrix (col2 = 2*col1) → refuse."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=20)
    df = pd.DataFrame({"x1": x, "x2": 2.0 * x, "x3": rng.normal(size=20)})
    contract = StatisticalContract()
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "singular_design" in by_rule
    assert by_rule["singular_design"].severity == "refuse"


# ---------------------------------------------------------------------------
# Rule 6 — negative_in_non_negative
# ---------------------------------------------------------------------------


def test_negative_in_non_negative_refused():
    """non_negative + value -0.5 → refuse."""
    df = pd.DataFrame({"value": [-0.5, 1.0, 2.0]})
    contract = StatisticalContract(distribution_assumption="non_negative")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "negative_in_non_negative" in by_rule
    assert report.overall == "refuse"


# ---------------------------------------------------------------------------
# Rule 7 — unit_interval_violation
# ---------------------------------------------------------------------------


def test_unit_interval_violation_refused():
    """unit_interval + value 1.7 → refuse."""
    df = pd.DataFrame({"prop": [0.1, 0.5, 1.7]})
    contract = StatisticalContract(distribution_assumption="unit_interval")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "unit_interval_violation" in by_rule
    assert report.overall == "refuse"


# ---------------------------------------------------------------------------
# Rule 8 — non_integer_in_count
# ---------------------------------------------------------------------------


def test_non_integer_in_count_refused():
    """integer_count + 2.5 → refuse."""
    df = pd.DataFrame({"count": [1.0, 2.5, 3.0]})
    contract = StatisticalContract(distribution_assumption="integer_count")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "non_integer_in_count" in by_rule
    assert report.overall == "refuse"


# ---------------------------------------------------------------------------
# Rule 9 — excessive_missingness
# ---------------------------------------------------------------------------


def test_excessive_missingness_warned():
    """50% NaN fraction → warn (default 0.30 threshold)."""
    df = pd.DataFrame({"value": [1.0, np.nan, 2.0, np.nan, 3.0, np.nan]})
    contract = StatisticalContract()
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "excessive_missingness" in by_rule
    assert by_rule["excessive_missingness"].severity == "warn"


def test_missingness_under_threshold_silent():
    """20% NaN fraction → silent."""
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, np.nan]})
    contract = StatisticalContract()
    report = _audit(contract, df)
    assert "excessive_missingness" not in _findings_by_rule(report)


# ---------------------------------------------------------------------------
# Rule 10 — tied_zero_inflated
# ---------------------------------------------------------------------------


def test_zero_inflated_warned():
    """>40% zeros + Gaussian assumption → warn."""
    df = pd.DataFrame({"value": [0.0] * 6 + [1.0, 2.0, 3.0, 4.0]})
    contract = StatisticalContract(distribution_assumption="approximately_gaussian")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "tied_zero_inflated" in by_rule
    assert by_rule["tied_zero_inflated"].severity == "warn"


# ---------------------------------------------------------------------------
# Rule 11 — cluster_imbalance
# ---------------------------------------------------------------------------


def test_cluster_imbalance_warned():
    """Subject ratios >= 5x → warn."""
    df = pd.DataFrame(
        {
            "subject_id": ["s1"] * 20 + ["s2"] * 2 + ["s3"] * 2,
            "value": np.arange(24.0),
        }
    )
    contract = StatisticalContract(independence="clustered_by_subject")
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "cluster_imbalance" in by_rule
    assert by_rule["cluster_imbalance"].severity == "warn"


# ---------------------------------------------------------------------------
# Rule 12 — n_below_visualization_floor
# ---------------------------------------------------------------------------


def test_n_below_visualization_floor_refused():
    """n=3 < n_minimum_for_visualization=10 → refuse."""
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    contract = StatisticalContract(n_minimum_for_visualization=10)
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "n_below_visualization_floor" in by_rule
    assert report.overall == "refuse"


# ---------------------------------------------------------------------------
# Rule 13 — effect_size_units_undeclared
# ---------------------------------------------------------------------------


def test_effect_size_units_undeclared_warned():
    """Template references {d} but effect_size_in_units=None → warn."""
    df = pd.DataFrame({"value": [1.0, 2.0]})
    contract = StatisticalContract(
        rendered_claim_template="The effect was {d} (95% CI ...)",
    )
    report = _audit(contract, df)
    by_rule = _findings_by_rule(report)
    assert "effect_size_units_undeclared" in by_rule
    assert by_rule["effect_size_units_undeclared"].severity == "warn"


def test_effect_size_units_silent_when_declared():
    """effect_size_in_units set → rule does not fire."""
    df = pd.DataFrame({"value": [1.0, 2.0]})
    contract = StatisticalContract(
        rendered_claim_template="effect = {d}",
        effect_size_in_units="cohen_d",
    )
    report = _audit(contract, df)
    assert "effect_size_units_undeclared" not in _findings_by_rule(report)


# ---------------------------------------------------------------------------
# Aggregation / overall severity
# ---------------------------------------------------------------------------


def test_audit_report_overall_severity():
    """Mix of warn + refuse → overall='refuse' (max)."""
    df = pd.DataFrame({"value": [-0.5, np.nan, np.nan, np.nan, 1.0]})
    contract = StatisticalContract(distribution_assumption="non_negative")
    report = _audit(contract, df)
    severities = {f.severity for f in report.findings}
    assert "refuse" in severities
    assert "warn" in severities  # excessive_missingness
    assert report.overall == "refuse"


def test_refuses_when_escalates_warn_to_refuse():
    """refuses_when=('non_normal_with_parametric_test',) escalates default warn → refuse."""
    rng = np.random.default_rng(11)
    df = pd.DataFrame({"value": rng.standard_cauchy(200)})
    base = StatisticalContract(distribution_assumption="approximately_gaussian")
    base_report = _audit(base, df)
    by_rule = _findings_by_rule(base_report)
    assert by_rule["non_normal_with_parametric_test"].severity == "warn"

    escalated = StatisticalContract(
        distribution_assumption="approximately_gaussian",
        refuses_when=("non_normal_with_parametric_test",),
    )
    escalated_report = _audit(escalated, df)
    by_rule_e = _findings_by_rule(escalated_report)
    assert by_rule_e["non_normal_with_parametric_test"].severity == "refuse"
    assert escalated_report.overall == "refuse"


def test_refuses_when_does_not_demote_refuse():
    """refuses_when listing a default-refuse rule does not double-escalate."""
    df = pd.DataFrame({"value": [-0.5, 1.0]})
    contract = StatisticalContract(
        distribution_assumption="non_negative",
        refuses_when=("negative_in_non_negative",),
    )
    report = _audit(contract, df)
    finding = _findings_by_rule(report)["negative_in_non_negative"]
    assert finding.severity == "refuse"


def test_audit_never_raises():
    """audit_recipe_against_data returns an AuditReport even on malformed data."""
    df = pd.DataFrame()  # empty
    contract = StatisticalContract(min_n_per_group=5)
    report = _audit(contract, df)
    assert isinstance(report, AuditReport)


# ---------------------------------------------------------------------------
# Integration with the recipe registry
# ---------------------------------------------------------------------------


def test_audit_against_real_recipe():
    """A real registered recipe + permissive default contract → pass."""
    from panelforge_figures.core.contract import ensure_all_imported, list_recipes

    ensure_all_imported()
    recipes = list_recipes()
    assert recipes, "registry should be populated"
    sample = recipes[0]
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0]})
    report = audit_recipe_against_data(
        contract=sample.metadata.statistical_contract,
        data=df,
        recipe_full_name=sample.full_name,
    )
    # Default contract on existing recipes must not refuse.
    assert report.overall in {"pass", "warn"}


def test_statistical_contract_violation_is_runtime_error():
    """The exception type is exposed and is a RuntimeError subclass."""
    assert issubclass(StatisticalContractViolation, RuntimeError)


def test_audit_finding_is_frozen():
    """AuditFinding is immutable (matches the spec's frozen dataclass guidance)."""
    finding = AuditFinding(rule_id="x", severity="pass", message="ok")
    with pytest.raises((AttributeError, Exception)):
        finding.severity = "refuse"  # type: ignore[misc]
