"""Tests for E8: data-driven figure family recommender + recipe gap detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

# pandas is the heavy dep used by profile_data; tests that need it are skipped
# (rather than erroring) when pandas is absent — this matches the
# ``[recommender]`` extra in pyproject.toml.
pd = pytest.importorskip("pandas")

from panelforge_figures.cli import main  # noqa: E402
from panelforge_figures.manifest.family_recommender import (  # noqa: E402
    DataKind,
    DataProfile,
    FamilyRecommendation,
    GroupingStructure,
    RecipeGap,
    RecommenderError,
    detect_recipe_gaps,
    find_matching_recipes,
    profile_data,
    recommend_families,
)

# ─────────────────────────── synthetic data fixtures ─────────────────────


@pytest.fixture
def two_group_csv(tmp_path: Path) -> Path:
    """10-row CSV with 2 numeric columns + 1 binary group column."""
    df = pd.DataFrame({
        "group": ["A"] * 5 + ["B"] * 5,
        "response": [1.0, 1.2, 1.4, 0.9, 1.1, 2.0, 2.2, 2.4, 2.1, 1.9],
        "covariate": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    })
    out = tmp_path / "two_group.csv"
    df.to_csv(out, index=False)
    return out


@pytest.fixture
def two_by_two_csv(tmp_path: Path) -> Path:
    """40-row CSV with 2x2 factorial design."""
    rows: list[dict[str, float | str]] = []
    for f1 in ("low", "high"):
        for f2 in ("ctrl", "treat"):
            for i in range(10):
                rows.append({
                    "factor_a": f1,
                    "factor_b": f2,
                    "y": float(hash((f1, f2, i)) % 100) / 10.0,
                })
    df = pd.DataFrame(rows)
    out = tmp_path / "factorial.csv"
    df.to_csv(out, index=False)
    return out


@pytest.fixture
def correlation_csv(tmp_path: Path) -> Path:
    """50-row CSV with two numeric columns + an ordinal id."""
    rows: list[dict[str, float | int]] = []
    for i in range(50):
        rows.append({
            "x": float(i) * 0.1,
            "y": float(i) * 0.2 + (i % 3),
            "row_id": i,
        })
    df = pd.DataFrame(rows)
    out = tmp_path / "correlation.csv"
    df.to_csv(out, index=False)
    return out


@pytest.fixture
def binary_csv(tmp_path: Path) -> Path:
    """30-row CSV with a 0/1 binary column + a numeric predictor."""
    df = pd.DataFrame({
        "outcome": [0, 1] * 15,
        "score": [float(i) / 30.0 for i in range(30)],
    })
    out = tmp_path / "binary.csv"
    df.to_csv(out, index=False)
    return out


# ───────────────────────────── profile_data ──────────────────────────────


def test_profile_data_two_group_csv(two_group_csv: Path) -> None:
    profile = profile_data(two_group_csv)
    assert isinstance(profile, DataProfile)
    assert profile.n_rows == 10
    assert profile.n_cols == 3
    # numeric columns
    assert profile.column_kinds["response"] == DataKind.numeric
    assert profile.column_kinds["covariate"] == DataKind.numeric
    # group column
    assert profile.column_kinds["group"] == DataKind.categorical
    assert profile.n_groups == 2
    assert sorted(profile.n_per_group.values()) == [5, 5]
    assert profile.n_numeric == 2
    assert "group" in profile.candidate_factor_columns
    assert "response" in profile.candidate_response_columns
    # No 2x2 with a single factor column.
    assert profile.detected_2x2 is False


def test_profile_data_detects_binary_zero_one(binary_csv: Path) -> None:
    profile = profile_data(binary_csv)
    assert profile.column_kinds["outcome"] == DataKind.binary
    assert profile.n_binary == 1
    # The binary column is also a factor (2 levels).
    assert "outcome" in profile.candidate_factor_columns


def test_profile_data_detects_2x2_factorial(two_by_two_csv: Path) -> None:
    profile = profile_data(two_by_two_csv)
    assert profile.detected_2x2 is True
    assert profile.grouping_structure == GroupingStructure.factorial
    assert "factor_a" in profile.candidate_factor_columns
    assert "factor_b" in profile.candidate_factor_columns


def test_profile_data_correlation_shape(correlation_csv: Path) -> None:
    profile = profile_data(correlation_csv)
    # Two numeric response columns (x, y).
    assert "x" in profile.candidate_response_columns
    assert "y" in profile.candidate_response_columns
    # row_id is numeric; we don't enforce factor classification here.
    assert profile.n_numeric >= 2


def test_profile_data_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RecommenderError, match="not found"):
        profile_data(tmp_path / "does_not_exist.csv")


def test_profile_data_unsupported_format(tmp_path: Path) -> None:
    bogus = tmp_path / "data.bogus"
    bogus.write_text("hello world")
    with pytest.raises(RecommenderError, match="unsupported file format"):
        profile_data(bogus)


def test_profile_data_accepts_dataframe(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    profile = profile_data(df)
    assert profile.n_rows == 3
    assert profile.n_cols == 2


def test_profile_to_dict_round_trip(two_group_csv: Path) -> None:
    profile = profile_data(two_group_csv)
    d = profile.to_dict()
    assert d["n_rows"] == 10
    assert d["n_cols"] == 3
    assert d["column_kinds"]["group"] == "categorical"
    # JSON serialisable
    assert json.loads(json.dumps(d))["n_rows"] == 10


def test_profile_data_paired_id_detection(tmp_path: Path) -> None:
    """A column literally named 'subject_id' that repeats → has_paired_id=True."""
    df = pd.DataFrame({
        "subject_id": ["s1", "s2", "s3"] * 3,
        "y": list(range(9)),
    })
    out = tmp_path / "paired.csv"
    df.to_csv(out, index=False)
    profile = profile_data(out)
    assert profile.has_paired_id is True
    # Each subject has 3 measurements → repeated_measures.
    assert profile.grouping_structure == GroupingStructure.repeated_measures


# ───────────────────────── recommend_families ────────────────────────────


def test_recommend_families_two_group_returns_comparison(
    two_group_csv: Path,
) -> None:
    profile = profile_data(two_group_csv)
    recs = recommend_families(profile)
    families = [r.family for r in recs]
    assert "comparison" in families


def test_recommend_families_2x2_returns_factorial_or_coef_forest(
    two_by_two_csv: Path,
) -> None:
    profile = profile_data(two_by_two_csv)
    recs = recommend_families(profile)
    families = [r.family for r in recs]
    assert "factorial" in families
    assert "coef_forest" in families


def test_recommend_families_correlation_returns_correlation(
    correlation_csv: Path,
) -> None:
    profile = profile_data(correlation_csv)
    recs = recommend_families(profile)
    families = [r.family for r in recs]
    assert "correlation" in families


def test_recommend_families_confidence_in_unit_interval(
    two_group_csv: Path,
) -> None:
    profile = profile_data(two_group_csv)
    recs = recommend_families(profile)
    for rec in recs:
        assert 0.0 <= rec.confidence <= 1.0
        assert isinstance(rec.rationale, str) and rec.rationale


def test_recommend_families_top_k_limit(two_by_two_csv: Path) -> None:
    profile = profile_data(two_by_two_csv)
    recs = recommend_families(profile, top_k=2)
    assert len(recs) <= 2


def test_recommend_families_sorted_descending(two_by_two_csv: Path) -> None:
    profile = profile_data(two_by_two_csv)
    recs = recommend_families(profile)
    if len(recs) >= 2:
        for a, b in zip(recs, recs[1:], strict=False):
            assert a.confidence >= b.confidence


def test_recommend_families_binary_returns_diagnostic_curve(
    binary_csv: Path,
) -> None:
    profile = profile_data(binary_csv)
    recs = recommend_families(profile)
    families = [r.family for r in recs]
    assert "diagnostic_curve" in families


# ─────────────────────── find_matching_recipes ──────────────────────────


def test_find_matching_recipes_filters_by_family(two_group_csv: Path) -> None:
    profile = profile_data(two_group_csv)
    # coef_forest is a real registered family in the registry; even with no
    # matches the call must succeed and return a list.
    matches = find_matching_recipes("coef_forest", profile)
    assert isinstance(matches, list)


def test_find_matching_recipes_unknown_family_returns_empty(
    two_group_csv: Path,
) -> None:
    profile = profile_data(two_group_csv)
    matches = find_matching_recipes("definitely_not_a_real_family", profile)
    assert matches == []


def test_find_matching_recipes_respects_min_n(two_group_csv: Path) -> None:
    profile = profile_data(two_group_csv)
    # The two_group dataset has 5 per group; recipes that demand > 5 per
    # group must be filtered out.
    matches = find_matching_recipes("coef_forest", profile)
    # Sanity: each match's contract.min_n_per_group must allow our smallest
    # group, OR be None. Verify by re-checking the registry.
    from panelforge_figures.core.contract import get_recipe

    smallest = min(profile.n_per_group.values())
    for full_name in matches:
        entry = get_recipe(full_name)
        contract = getattr(entry.metadata, "statistical_contract", None)
        if contract and contract.min_n_per_group is not None:
            assert smallest >= contract.min_n_per_group


def test_find_matching_recipes_resolves_analysis_family_via_bridge(
    two_group_csv: Path,
) -> None:
    """``comparison`` is an analysis family, not a rendered RecipeFamily.

    Before the family-bridge fix, ``find_matching_recipes("comparison", …)``
    always returned ``[]`` because it string-matched the rendered
    ``RecipeFamily``. The bridge maps ``comparison`` to ``split_violin`` /
    ``ridge_by_group`` / ``timecourse_hierarchical_ci``, so it must now find
    at least one real recipe.
    """
    profile = profile_data(two_group_csv)
    matches = find_matching_recipes("comparison", profile)
    assert len(matches) >= 1, "comparison must resolve to ≥1 rendered recipe"


@pytest.mark.parametrize(
    "data_fixture",
    ["two_group_csv", "two_by_two_csv", "correlation_csv", "binary_csv"],
)
def test_recommend_families_all_outputs_resolve_or_are_gap_only(
    data_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Every recommended family must resolve to ≥1 recipe or be gap-only.

    Regression for the recommender-phantom-families bug: ``recommend_families``
    used to emit analysis-family strings (``comparison``, ``correlation``,
    ``factorial``, ``equivalence``) that ``find_matching_recipes`` could never
    match, so they were silently flagged as phantom gaps. With the family
    bridge, each emitted family either resolves to a real recipe or is an
    explicitly documented gap-only family (empty tuple in the bridge).
    """
    from panelforge_figures.manifest.family_bridge import (
        ANALYSIS_TO_RECIPE_FAMILIES,
    )

    data_path: Path = request.getfixturevalue(data_fixture)
    profile = profile_data(data_path)
    recs = recommend_families(profile)
    assert recs, "expected at least one recommendation"

    for rec in recs:
        matches = find_matching_recipes(rec.family, profile)
        explicitly_gap_only = (
            ANALYSIS_TO_RECIPE_FAMILIES.get(rec.family) == ()
        )
        assert matches or explicitly_gap_only, (
            f"family {rec.family!r} resolved to no recipes and is not an "
            f"explicitly documented gap-only family"
        )


# ─────────────────────────── detect_recipe_gaps ──────────────────────────


def test_detect_recipe_gaps_emits_when_no_matches(two_group_csv: Path) -> None:
    profile = profile_data(two_group_csv)
    # Build a synthetic high-confidence recommendation with 0 matches.
    fake_rec = FamilyRecommendation(
        family="comparison",  # not in RecipeFamily enum → guaranteed 0 matches
        confidence=0.85,
        rationale="manufactured for test",
        n_matching_recipes=0,
        matching_recipe_names=(),
    )
    gaps = detect_recipe_gaps(profile, [fake_rec])
    assert len(gaps) == 1
    g = gaps[0]
    assert isinstance(g, RecipeGap)
    assert g.family == "comparison"
    assert g.suggested_recipe_name.startswith("comparison_")
    assert g.suggested_recipe_name.endswith("_v1")
    assert g.suggested_modality == "custom_lab"
    assert "?" in g.suggested_research_question


def test_detect_recipe_gaps_suppresses_when_matches_exist(
    two_group_csv: Path,
) -> None:
    profile = profile_data(two_group_csv)
    rec_with_matches = FamilyRecommendation(
        family="coef_forest",
        confidence=0.8,
        rationale="manufactured for test",
        n_matching_recipes=3,
        matching_recipe_names=("a.b", "c.d", "e.f"),
    )
    gaps = detect_recipe_gaps(profile, [rec_with_matches])
    assert gaps == []


def test_detect_recipe_gaps_below_threshold_suppressed(
    two_group_csv: Path,
) -> None:
    profile = profile_data(two_group_csv)
    low_rec = FamilyRecommendation(
        family="comparison",
        confidence=0.10,
        rationale="too weak",
        n_matching_recipes=0,
    )
    gaps = detect_recipe_gaps(profile, [low_rec])
    assert gaps == []


def test_detect_recipe_gaps_2x2_hint_in_name(two_by_two_csv: Path) -> None:
    profile = profile_data(two_by_two_csv)
    fake_rec = FamilyRecommendation(
        family="factorial",
        confidence=0.9,
        rationale="manufactured for test",
        n_matching_recipes=0,
    )
    gaps = detect_recipe_gaps(profile, [fake_rec])
    assert len(gaps) == 1
    assert "2x2" in gaps[0].suggested_recipe_name


# ─────────────────────────────── CLI tests ───────────────────────────────


def test_cli_recommend_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommend", "--help"])
    assert result.exit_code == 0
    assert "DATA_PATH" in result.output
    assert "ranked table" in result.output


def test_cli_fill_gap_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["fill-gap", "--help"])
    assert result.exit_code == 0
    assert "--family" in result.output
    assert "--data" in result.output


def test_cli_recommend_emits_ranked_table(two_by_two_csv: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["recommend", str(two_by_two_csv)])
    assert result.exit_code == 0, result.output
    assert "recommended families" in result.output
    assert "factorial" in result.output


def test_cli_recommend_json_emits_json(two_by_two_csv: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main, ["recommend", "--json", str(two_by_two_csv)]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "profile" in payload
    assert "recommendations" in payload
    assert "gaps" in payload
    assert payload["profile"]["n_rows"] == 40


def test_cli_recommend_unknown_file_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main, ["recommend", str(tmp_path / "does_not_exist.csv")]
    )
    # Click rejects via the existence-check first.
    assert result.exit_code != 0


def test_cli_fill_gap_scaffolds_recipe_end_to_end(
    two_by_two_csv: Path, tmp_path: Path
) -> None:
    """fill-gap with --yes should scaffold a recipe + test in project_root."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "fill-gap",
            "--family", "factorial",
            "--data", str(two_by_two_csv),
            "--modality", "custom_lab",
            "--name", "factorial_2x2_smoke_v1",
            "--research-question", "Is there interaction between A and B on Y?",
            "--project-root", str(project_root),
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "wrote" in result.output
    recipe_path = (
        project_root / "src" / "panelforge_figures" / "recipes"
        / "custom_lab" / "factorial_2x2_smoke_v1.py"
    )
    test_path = (
        project_root / "tests" / "recipes"
        / "test_factorial_2x2_smoke_v1.py"
    )
    assert recipe_path.exists(), f"missing {recipe_path}"
    assert test_path.exists(), f"missing {test_path}"


def test_cli_fill_gap_unrecognised_family_errors(two_group_csv: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "fill-gap",
            "--family", "definitely_not_a_real_family",
            "--data", str(two_group_csv),
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "did not score" in result.output or "not supported" in result.output
