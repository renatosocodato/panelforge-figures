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
    """End-to-end: a recipe in a SUPPORTED family must size, exit 0, emit JSON.

    Regression for the power-family-bridge bug: the CLI passes a *rendered*
    ``RecipeFamily`` (here ``coef_forest``) into the power layer, which only
    understands *analysis* families. Without the bridge this raised
    ``PowerError`` for every family except ``coef_forest``; here we assert a
    concrete success on a real registry recipe with a hard ``exit_code == 0``
    (no ``if exit_code == 0`` escape hatch). ``coef_forest`` at ``n_groups=2``
    reduces to a t-test, which has a closed-form fallback that does not need
    statsmodels, so this runs in every environment.
    """
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    runner = CliRunner()
    result = runner.invoke(main, [
        "power", "two_way_anova_summary_plot",
        "-e", "0.4", "-a", "0.05", "-p", "0.8",
        "--n-groups", "2",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "required_n_per_group" in data
    assert data["required_n_per_group"] > 0
    # coef_forest is the rare family that is BOTH a rendered RecipeFamily and
    # an analysis family, so the bridge is the identity here.
    assert data["family"] == "coef_forest"


def test_cli_power_rendered_family_resolves_via_bridge():
    """A recipe whose rendered family ≠ analysis family must still size.

    ``split_violin`` is a rendered ``RecipeFamily`` that is NOT a power
    analysis family; the bridge must map it to ``comparison``. Before the
    fix this emitted ``"family 'split_violin' not in PARAMETRIC_FAMILIES …"``
    and exit_code 1.
    """
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    from panelforge_figures.core.contract import (
        ensure_all_imported,
        list_recipes,
    )

    ensure_all_imported()
    recipe_name = None
    for info in list_recipes():
        if info.metadata.family.value == "split_violin":
            recipe_name = info.metadata.name
            break
    assert recipe_name is not None, "expected at least one split_violin recipe"

    runner = CliRunner()
    result = runner.invoke(main, [
        "power", recipe_name,
        "-e", "0.5", "-a", "0.05", "-p", "0.8",
        "--n-groups", "2",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    # The power estimate records the *analysis* family the bridge resolved to.
    assert data["family"] == "comparison"
    assert data["required_n_per_group"] > 0


def test_cli_power_unsupported_family_is_clean_not_a_stacktrace():
    """A conceptual/decorative family must report cleanly, not crash.

    Rendered families with no defined power analysis (e.g. ``conceptual``,
    ``flow``, ``matrix``) must produce a clear message and a non-zero exit
    *without* a raw ``PowerError`` traceback bubbling up through Click.
    """
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    from panelforge_figures.core.contract import (
        ensure_all_imported,
        list_recipes,
    )

    ensure_all_imported()
    recipe_name = None
    for info in list_recipes():
        if info.metadata.family.value in {
            "conceptual", "flow", "matrix", "gantt", "radar", "contour",
        }:
            recipe_name = info.metadata.name
            break
    assert recipe_name is not None, "expected a conceptual/decorative recipe"

    runner = CliRunner()
    result = runner.invoke(main, [
        "power", recipe_name, "-e", "0.5",
    ])
    # Non-zero exit, but no unhandled exception escaping Click.
    assert result.exit_code != 0
    assert result.exception is None or isinstance(
        result.exception, SystemExit
    ), result.exception
    assert "power analysis is not defined for family" in result.output


@pytest.mark.parametrize(
    "analysis_family",
    [
        "comparison",
        "coef_forest",
        "correlation",
        "distribution",
        "equivalence",
        "concordance",
        "permutation",
        "factorial",
        "proportion",
    ],
)
def test_compute_required_n_one_per_supported_analysis_family(analysis_family):
    """Each analysis family with a registered power method must size.

    Closed-form ANOVA / chi-square families (``factorial``, ``proportion``)
    hard-require statsmodels; if it is absent the formula raises a clear
    ``RuntimeError`` and we skip rather than fail.
    """
    try:
        est = compute_required_n(
            recipe_full_name="x.y",
            family=analysis_family,
            effect_size=0.5,
            alpha=0.05,
            power_target=0.8,
            n_groups=2,
            montecarlo_iterations=150,
        )
    except RuntimeError as exc:  # statsmodels missing for ANOVA/chi-square
        pytest.skip(f"optional dependency missing for {analysis_family}: {exc}")
    assert est.required_n_per_group > 0
    assert est.family == analysis_family


def test_cli_power_requires_effect_size():
    """The -e/--effect-size option is required."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["power", "x.y"])
    # Click exits with code 2 on missing required option.
    assert result.exit_code != 0


# Cluster 7b — family bridge integrity
def test_family_bridge_slugs_are_real_recipe_families():
    """Every rendered slug in the bridge must be a real RecipeFamily member."""
    from panelforge_figures.core.contract import RecipeFamily
    from panelforge_figures.manifest.family_bridge import (
        ANALYSIS_TO_RECIPE_FAMILIES,
        RECIPE_FAMILY_TO_ANALYSIS,
    )

    valid = {f.value for f in RecipeFamily}
    for slugs in ANALYSIS_TO_RECIPE_FAMILIES.values():
        for slug in slugs:
            assert slug in valid, f"{slug!r} is not a RecipeFamily"
    for slug in RECIPE_FAMILY_TO_ANALYSIS:
        assert slug in valid, f"{slug!r} is not a RecipeFamily"


def test_family_bridge_round_trips_consistently():
    """Each RECIPE_FAMILY_TO_ANALYSIS entry round-trips back to its slug."""
    from panelforge_figures.manifest.family_bridge import (
        ANALYSIS_TO_RECIPE_FAMILIES,
        RECIPE_FAMILY_TO_ANALYSIS,
    )

    for recipe_family, analysis_family in RECIPE_FAMILY_TO_ANALYSIS.items():
        rendered = ANALYSIS_TO_RECIPE_FAMILIES.get(analysis_family, ())
        assert recipe_family in rendered, (
            f"{recipe_family!r} → {analysis_family!r} but reverse map "
            f"{rendered!r} does not include it"
        )


def test_family_bridge_analysis_families_have_power_methods():
    """Every analysis family with a non-empty render set has a power method."""
    from panelforge_figures.manifest.family_bridge import (
        ANALYSIS_TO_RECIPE_FAMILIES,
    )
    from panelforge_figures.manifest.power_families import FAMILY_TO_FORMULA

    for analysis_family in ANALYSIS_TO_RECIPE_FAMILIES:
        assert analysis_family in FAMILY_TO_FORMULA, (
            f"{analysis_family!r} has no power formula registered"
        )


# Cluster 8 — Version bump
def test_version_is_at_least_v2():
    """v2+ programme: each subsequent elevation bumps the minor version."""
    from panelforge_figures import __version__
    parts = __version__.split(".")
    assert int(parts[0]) >= 2, f"expected ≥ 2.x.y, got {__version__!r}"
