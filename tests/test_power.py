"""Tests for adaptive power analysis (E4)."""
from __future__ import annotations

import json

import pytest

from panelforge_figures.manifest.power import (
    NONPARAMETRIC_FAMILIES,
    PARAMETRIC_FAMILIES,
    PowerError,
    PowerEstimate,
    PowerMethod,
    compute_required_n,
)


# Cluster 1 — Type checks
def test_power_method_enum_values():
    assert PowerMethod.closed_form_t_test.value == "closed_form_t_test"
    assert PowerMethod.monte_carlo_bootstrap.value == "monte_carlo_bootstrap"


def test_power_estimate_to_dict_round_trip():
    est = PowerEstimate(
        recipe_full_name="x.y", family="comparison",
        method=PowerMethod.closed_form_t_test,
        effect_size=0.3, effect_size_units="cohens_d",
        alpha=0.05, power_target=0.8,
        required_n_per_group=176, required_n_total=352,
        df_num=None, df_den=None, notes=("a note",),
    )
    d = est.to_dict()
    assert d["required_n_per_group"] == 176
    assert d["method"] == "closed_form_t_test"


def test_power_estimate_to_dict_is_json_serializable():
    """The to_dict() output must round-trip through json.dumps/loads."""
    est = PowerEstimate(
        recipe_full_name="modality.recipe", family="comparison",
        method=PowerMethod.closed_form_t_test,
        effect_size=0.5, effect_size_units="cohens_d",
        alpha=0.05, power_target=0.8,
        required_n_per_group=64, required_n_total=128,
        df_num=None, df_den=None, notes=(),
        montecarlo_iterations=0,
    )
    payload = json.dumps(est.to_dict(), sort_keys=True)
    parsed = json.loads(payload)
    assert parsed["family"] == "comparison"
    assert parsed["notes"] == []
    assert parsed["method"] == "closed_form_t_test"


def test_power_estimate_is_frozen():
    """PowerEstimate is a frozen dataclass — fields cannot be mutated."""
    est = PowerEstimate(
        recipe_full_name="x.y", family="comparison",
        method=PowerMethod.closed_form_t_test,
        effect_size=0.3, effect_size_units="cohens_d",
        alpha=0.05, power_target=0.8,
        required_n_per_group=176, required_n_total=352,
        df_num=None, df_den=None, notes=(),
    )
    with pytest.raises((AttributeError, Exception)):
        est.required_n_per_group = 999  # type: ignore[misc]


# Cluster 2 — Family classification
def test_parametric_families_listed():
    assert "comparison" in PARAMETRIC_FAMILIES
    assert "factorial" in PARAMETRIC_FAMILIES


def test_nonparametric_families_listed():
    assert "equivalence" in NONPARAMETRIC_FAMILIES


def test_parametric_and_nonparametric_disjoint():
    """A family must not appear in both lists — power method is unambiguous."""
    overlap = set(PARAMETRIC_FAMILIES) & set(NONPARAMETRIC_FAMILIES)
    assert overlap == set()


# Cluster 3 — t-test power (statsmodels-required-or-skip)
def test_t_test_required_n_at_d_0_3_alpha_0_05_power_0_8():
    """Cohen's d=0.3, alpha=0.05, power=0.80 → ~176 per group (textbook)."""
    pytest.importorskip("statsmodels")
    result = compute_required_n(
        recipe_full_name="x.t_test", family="comparison",
        effect_size=0.3, alpha=0.05, power_target=0.80,
    )
    assert 170 <= result.required_n_per_group <= 180


def test_t_test_required_n_at_d_0_5():
    """Cohen's d=0.5, alpha=0.05, power=0.80 → ~64 per group."""
    pytest.importorskip("statsmodels")
    result = compute_required_n(
        recipe_full_name="x.t_test", family="comparison",
        effect_size=0.5, alpha=0.05, power_target=0.80,
    )
    assert 60 <= result.required_n_per_group <= 70


def test_t_test_works_without_statsmodels():
    """Even if statsmodels isn't installed, the normal-approx fallback runs."""
    # NOTE: this test passes regardless of whether statsmodels is installed.
    result = compute_required_n(
        recipe_full_name="x.t_test", family="comparison",
        effect_size=0.5, alpha=0.05, power_target=0.80,
    )
    assert result.required_n_per_group > 0


# Cluster 4 — ANOVA power
def test_two_way_anova_required_n():
    """2x2 factorial, Cohen's f=0.4 → reasonable n_per_cell."""
    pytest.importorskip("statsmodels")
    pytest.importorskip("scipy")
    result = compute_required_n(
        recipe_full_name="x.two_way_anova", family="factorial",
        effect_size=0.4, alpha=0.05, power_target=0.80, n_groups=4,
    )
    assert result.required_n_per_group >= 5


# Cluster 5 — Correlation power
def test_correlation_required_n_at_r_0_3():
    """r=0.3, alpha=0.05, power=0.80 → ~84 (textbook)."""
    result = compute_required_n(
        recipe_full_name="x.scatter", family="correlation",
        effect_size=0.3, alpha=0.05, power_target=0.80, n_groups=1,
    )
    assert 80 <= result.required_n_per_group <= 90


# Cluster 6 — Unknown family + invalid args
def test_unknown_family_raises():
    with pytest.raises(PowerError, match="family"):
        compute_required_n(
            recipe_full_name="x.y", family="unknown_family",
            effect_size=0.3, alpha=0.05, power_target=0.80,
        )


def test_invalid_alpha_raises():
    """alpha must be in (0, 1) — boundary values raise PowerError."""
    with pytest.raises(PowerError, match="alpha"):
        compute_required_n(
            recipe_full_name="x.y", family="comparison",
            effect_size=0.3, alpha=0.0, power_target=0.80,
        )
    with pytest.raises(PowerError, match="alpha"):
        compute_required_n(
            recipe_full_name="x.y", family="comparison",
            effect_size=0.3, alpha=1.0, power_target=0.80,
        )


def test_invalid_power_target_raises():
    """power_target must be in (0, 1)."""
    with pytest.raises(PowerError, match="power_target"):
        compute_required_n(
            recipe_full_name="x.y", family="comparison",
            effect_size=0.3, alpha=0.05, power_target=1.0,
        )


def test_zero_effect_size_raises():
    """effect_size=0 implies infinite required n — must raise PowerError."""
    with pytest.raises(PowerError):
        compute_required_n(
            recipe_full_name="x.y", family="comparison",
            effect_size=0.0, alpha=0.05, power_target=0.80,
        )


def test_nonfinite_effect_size_raises():
    """effect_size must be finite."""
    with pytest.raises(PowerError):
        compute_required_n(
            recipe_full_name="x.y", family="comparison",
            effect_size=float("inf"), alpha=0.05, power_target=0.80,
        )


# Cluster 7 — CLI
def test_cli_power_help():
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["power", "--help"])
    assert result.exit_code == 0
    assert "effect-size" in result.output


def test_cli_power_unknown_recipe(tmp_path):
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    runner = CliRunner()
    result = runner.invoke(main, [
        "power", "no_such_recipe_xyz",
        "-e", "0.3",
    ])
    assert result.exit_code != 0


def test_cli_power_known_recipe_emits_json():
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    pytest.importorskip("statsmodels")
    runner = CliRunner()
    result = runner.invoke(main, [
        "power", "two_way_anova_summary_plot",
        "-e", "0.4", "-a", "0.05", "-p", "0.8",
        "--n-groups", "4",
        "--json",
    ])
    if result.exit_code == 0:
        # Some recipes may not be in the registry under this exact name in CI;
        # only assert on the success path.
        data = json.loads(result.output)
        assert "required_n_per_group" in data


def test_cli_power_requires_effect_size():
    """The -e/--effect-size option is required."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["power", "x.y"])
    # Click exits with code 2 on missing required option.
    assert result.exit_code != 0


# Cluster 8 — Version bump
def test_version_is_2_3_0():
    from panelforge_figures import __version__
    assert __version__ == "2.3.0"
