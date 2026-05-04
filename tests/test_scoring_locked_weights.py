"""Tests for the locked-weight scorer (RECIPE_DISCOVERY_SYSTEM.md §3).

The weights are *frozen constants*.  These tests are the canary: any change to
the weight table or match-function semantics MUST require an explicit edit
here.  Treat failures as a spec amendment, not a flaky test.
"""

from __future__ import annotations

import warnings

import pytest

from panelforge_figures.manifest.scoring import (
    DEFAULT_SHORTLIST_SIZE,
    MINIMUM_SCORE_FOR_SHORTLIST,
    SCORING_RUBRIC_VERSION,
    WEIGHTS,
    WEIGHTS_SUM_CHECK,
    ProjectProfile,
    ScoredRecipe,
    match_anchor,
    match_bool,
    match_dim,
    match_dynamics,
    score_recipes,
    scoring_rubric_dict,
)

# ---------------------------------------------------------------------------
# 1. Locked-weight constants.
# ---------------------------------------------------------------------------


def test_weights_sum_exactly_one() -> None:
    """The locked-weight rubric must always sum to 1.0 — spec invariant."""
    assert sum(WEIGHTS.values()) == pytest.approx(WEIGHTS_SUM_CHECK, abs=1e-12)
    assert WEIGHTS_SUM_CHECK == 1.00


def test_weights_individual_values_locked() -> None:
    """The individual weights are frozen by the spec; this test guards them."""
    assert WEIGHTS["factorial"] == 0.30
    assert WEIGHTS["equivalence"] == 0.25
    assert WEIGHTS["anchor"] == 0.20
    assert WEIGHTS["dynamics"] == 0.15
    assert WEIGHTS["dimensionality"] == 0.10


def test_weights_mapping_is_immutable() -> None:
    """``WEIGHTS`` is a MappingProxyType — must reject mutation."""
    with pytest.raises(TypeError):
        WEIGHTS["factorial"] = 0.99       # type: ignore[index]


def test_rubric_dict_carries_version_and_weights() -> None:
    rubric = scoring_rubric_dict()
    assert rubric["version"] == SCORING_RUBRIC_VERSION
    assert rubric["weights"] == dict(WEIGHTS)
    assert rubric["weights_sum"] == 1.00
    assert rubric["minimum_score_for_shortlist"] == MINIMUM_SCORE_FOR_SHORTLIST
    assert rubric["default_shortlist_size"] == DEFAULT_SHORTLIST_SIZE
    assert "anchor_match_strength" in rubric["tie_breakers"]


# ---------------------------------------------------------------------------
# 2. Match functions — 4 cases each.
# ---------------------------------------------------------------------------


class TestMatchBool:
    def test_both_true(self) -> None:
        assert match_bool(True, True) == 1.0

    def test_both_false(self) -> None:
        # DEFECT-A2 fix: presence-checked semantics — only profile=True
        # AND recipe=True earns the weight.  Both False = no contribution
        # (matches RECIPE_SELECTION.md worked-example arithmetic).
        assert match_bool(False, False) == 0.0

    def test_recipe_false_profile_true(self) -> None:
        # Spec note: "no penalty, just no contribution".
        assert match_bool(False, True) == 0.0

    def test_recipe_true_profile_false(self) -> None:
        # Asymmetric: a factorial-tagged recipe in a non-factorial
        # project does NOT earn the weight.
        assert match_bool(True, False) == 0.0

    def test_recipe_none_treated_as_false(self) -> None:
        # Both "None" and False sides yield 0.0 — only explicit True/True
        # matches.
        assert match_bool(None, False) == 0.0
        assert match_bool(None, True) == 0.0


class TestMatchAnchor:
    def test_exact_match(self) -> None:
        assert match_anchor("DISC1", "DISC1") == 1.0

    def test_generic_recipe_partial(self) -> None:
        # generic recipes always score 0.5 regardless of profile anchor.
        assert match_anchor("generic", "DISC1") == 0.5
        assert match_anchor("generic", "CDC42") == 0.5

    def test_profile_both_overlaps_specific_recipe(self) -> None:
        assert match_anchor("DISC1", "both") == 0.7
        assert match_anchor("CDC42", "both") == 0.7

    def test_mismatch(self) -> None:
        assert match_anchor("DISC1", "CDC42") == 0.0
        assert match_anchor(None, "DISC1") == 0.0
        # exact-but-empty does NOT short-circuit to 1.0.
        assert match_anchor("", "") == 0.0


class TestMatchDynamics:
    def test_exact(self) -> None:
        # DEFECT-2 fix: static/static lands on the 0.3 baseline branch
        # (matches RECIPE_SELECTION.md prose intent: "I want static" =
        # "I have no dynamics signal to discriminate on").
        assert match_dynamics("static", "static") == 0.3
        # Non-static exact matches still score 1.0.
        assert match_dynamics("kymograph", "kymograph") == 1.0

    def test_profile_mixed_any_match(self) -> None:
        assert match_dynamics("kymograph", "mixed") == 0.8
        assert match_dynamics("live", "mixed") == 0.8

    def test_static_baseline(self) -> None:
        # static always counts a little — baselines are universally useful.
        assert match_dynamics("static", "kymograph") == 0.3

    def test_mismatch(self) -> None:
        assert match_dynamics("kymograph", "live") == 0.0
        assert match_dynamics(None, "static") == 0.0


class TestMatchDim:
    def test_exact(self) -> None:
        assert match_dim("2D", "2D") == 1.0
        assert match_dim("3D", "3D") == 1.0

    def test_profile_mixed(self) -> None:
        # 0.7 always when profile is "mixed", regardless of recipe value.
        assert match_dim("2D", "mixed") == 0.7
        assert match_dim("3D", "mixed") == 0.7

    def test_recipe_mixed_in_2d_project(self) -> None:
        # Asymmetry: only profile==mixed produces 0.7.  A recipe tagged "mixed"
        # in a 2D project is just a mismatch.
        assert match_dim("mixed", "2D") == 0.0

    def test_mismatch(self) -> None:
        assert match_dim("2D", "3D") == 0.0
        assert match_dim(None, "2D") == 0.0


# ---------------------------------------------------------------------------
# 3. Hard-filter case — modality scope + boolean tag gates narrow the pool.
# ---------------------------------------------------------------------------


def _profile_compartment_aware() -> ProjectProfile:
    return ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=False,
        equivalence_claims=True,
        dynamics_needed="static",
        dimensionality="mixed",
        modalities_in_scope=("biophysics_scaling", "actin_microtubule_morphometry"),
        hard_filters={"compartment_aware": True},
    )


def test_hard_filters_narrow_pool_to_two() -> None:
    """5 fixtures, of which only 2 satisfy modality scope + compartment_aware."""
    profile = _profile_compartment_aware()
    fixtures = [
        # In scope + tag set → keeps.
        {
            "modality": "biophysics_scaling",
            "name": "scaling_compartment_split",
            "family": "biophysics",
            "answers_question": "Q1",
            "tags": {
                "compartment_aware": True,
                "factorial": False,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
            },
        },
        # In scope + tag set → keeps.
        {
            "modality": "actin_microtubule_morphometry",
            "name": "morph_compartment_overlay",
            "family": "morphometry",
            "answers_question": "Q2",
            "tags": {
                "compartment_aware": True,
                "factorial": False,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "3D",
            },
        },
        # In scope but compartment_aware == False → drops.
        {
            "modality": "biophysics_scaling",
            "name": "scaling_no_compartment",
            "family": "biophysics",
            "answers_question": "Q3",
            "tags": {
                "compartment_aware": False,
                "factorial": False,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
            },
        },
        # Modality out of scope → drops even though all tags align.
        {
            "modality": "scrnaseq",
            "name": "umap_overview",
            "family": "single_cell",
            "answers_question": "Q4",
            "tags": {
                "compartment_aware": True,
                "factorial": False,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
            },
        },
        # Missing the gate tag entirely → drops.
        {
            "modality": "actin_microtubule_morphometry",
            "name": "morph_no_gate",
            "family": "morphometry",
            "answers_question": "Q5",
            "tags": {
                "factorial": False,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
            },
        },
    ]

    with warnings.catch_warnings():
        # Default shortlist_size=12 will trigger an underfill warning; the
        # spec mandates that, but the test only cares about the surviving set.
        warnings.simplefilter("ignore", UserWarning)
        out = score_recipes(profile, fixtures)
    assert len(out) == 2
    names = {r.name for r in out}
    assert names == {"scaling_compartment_split", "morph_compartment_overlay"}


# ---------------------------------------------------------------------------
# 4. Soft-scoring case — expected score order with no hard filters.
# ---------------------------------------------------------------------------


def test_soft_scoring_orders_descending() -> None:
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=False,
        equivalence_claims=True,
        dynamics_needed="static",
        dimensionality="mixed",
        modalities_in_scope=("m1",),
        hard_filters={},
    )
    fixtures = [
        # Best — every match.
        {
            "modality": "m1",
            "name": "perfect",
            "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
        # Drop one weight (anchor → none).
        {
            "modality": "m1",
            "name": "no_anchor",
            "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "none",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
        # Drop equivalence too.
        {
            "modality": "m1",
            "name": "no_equiv",
            "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": False, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
        # Generic anchor + perfect rest.
        {
            "modality": "m1",
            "name": "generic_anchor",
            "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
        # Profile=mixed dim helper.
        {
            "modality": "m1",
            "name": "live_dyn",
            "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "DISC1",
                "dynamics": "live", "dimensionality": "2D",
            },
        },
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        out = score_recipes(profile, fixtures)

    # Recompute expected scores post-DEFECT-A2-fix (presence-checked
    # match_bool means factorial=False/False contributes 0.0 not 0.30;
    # match_dim(2D, mixed) = 0.7 always when profile is mixed):
    # profile is DISC1 + equivalence + static + dim=mixed (factorial=False)
    # perfect:        0.00 + 0.25 + 0.20 + 0.045 + 0.07 = 0.565
    # no_anchor:      0.00 + 0.25 + 0.00 + 0.045 + 0.07 = 0.365
    # no_equiv:       0.00 + 0.00 + 0.20 + 0.045 + 0.07 = 0.315
    # generic_anchor: 0.00 + 0.25 + 0.10 + 0.045 + 0.07 = 0.465
    # live_dyn:       0.00 + 0.25 + 0.20 + 0.000 + 0.07 = 0.520
    #
    # Threshold (≥0.40) drops no_anchor + no_equiv.  Top-3 survives.
    expected_order = ["perfect", "live_dyn", "generic_anchor"]
    assert [r.name for r in out] == expected_order
    assert out[0].score == pytest.approx(0.565, abs=1e-4)
    assert out[1].score == pytest.approx(0.520, abs=1e-4)
    assert out[2].score == pytest.approx(0.465, abs=1e-4)


# ---------------------------------------------------------------------------
# 5. Worked-example reproduction — the spec's §3.7 scenario.
# ---------------------------------------------------------------------------


def test_spec_worked_example_top_three() -> None:
    """Reproduce the spec's worked example for the DISC1+equivalence+static profile.

    Profile from RECIPE_DISCOVERY_SYSTEM.md §3.7:
      - DISC1 anchor, no factorial, equivalence claims, static dynamics, mixed dim
      - Modalities in scope: biophysics_scaling, actin_microtubule_morphometry
      - Hard filter: compartment_aware == True

    The three fixtures below model the spec's documented top-3 — each one hits
    a partial-anchor + equivalence + static + mixed-dim combination that
    yields the same score so they cluster at the top of the funnel.
    """
    profile = _profile_compartment_aware()

    # Score by hand (post Wave-3 polish: DEFECT-A2 presence-checked
    # match_bool + DEFECT-2 static-baseline + match_dim mixed carve-out):
    #   0.00 (factorial mismatch — presence-checked: profile=False, no credit)
    #   + 0.25 (equivalence presence-checked: True/True)
    #   + 0.20 (DISC1 anchor exact)
    #   + 0.045 (static-baseline 0.3 × 0.15)
    #   + 0.07 (mixed dim carve-out 0.7 × 0.10)
    #   = 0.565
    # This now matches the spec §3.7 documented value EXACTLY.
    spec_top3 = [
        {
            "modality": "biophysics_scaling",
            "name": "scaling_static_compartment",
            "family": "biophysics",
            "answers_question": "Spec top-1 — scaling baseline w/ compartment.",
            "tags": {
                "compartment_aware": True,
                "factorial": True,                # mismatch with profile (False)
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
                "wave": "v1.0",
            },
        },
        {
            "modality": "actin_microtubule_morphometry",
            "name": "morph_static_overlay",
            "family": "morphometry",
            "answers_question": "Spec top-2 — morphometric overlay, static.",
            "tags": {
                "compartment_aware": True,
                "factorial": True,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "2D",
                "wave": "v1.0",
            },
        },
        {
            "modality": "biophysics_scaling",
            "name": "scaling_static_paired",
            "family": "biophysics",
            "answers_question": "Spec top-3 — paired static comparison.",
            "tags": {
                "compartment_aware": True,
                "factorial": True,
                "equivalence": True,
                "anchor": "DISC1",
                "dynamics": "static",
                "dimensionality": "3D",
                "wave": "v1.1.0-beta-001",
            },
        },
        # A noisy distractor that should be filtered out (no compartment tag).
        {
            "modality": "biophysics_scaling",
            "name": "noise_no_gate",
            "family": "biophysics",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        out = score_recipes(profile, spec_top3)
    # All three spec recipes survive the gate.
    assert len(out) == 3
    surviving = [r.name for r in out]
    assert "scaling_static_compartment" in surviving
    assert "morph_static_overlay" in surviving
    assert "scaling_static_paired" in surviving
    # Each scored above the threshold and below 1.0.
    for r in out:
        assert r.score >= MINIMUM_SCORE_FOR_SHORTLIST
        assert r.score < 1.0
    # Post-DEFECT-A2 fix: scoring now reproduces spec §3.7 exactly.
    for r in out:
        assert r.score == pytest.approx(0.565, abs=1e-4)


# ---------------------------------------------------------------------------
# 6. Tie-breakers — identical scores resolved by anchor, modality, wave, name.
# ---------------------------------------------------------------------------


def test_tie_breakers_lexicographic() -> None:
    """Two recipes with identical scores are ordered by the documented chain:
    anchor strength → modality locality → wave (descending) → name (ascending).
    """
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=False,
        equivalence_claims=True,
        dynamics_needed="static",
        dimensionality="mixed",
        modalities_in_scope=("m_big", "m_small"),
        hard_filters={},
    )
    # Two recipes with the exact same baseline score, but differing on
    # anchor strength (one DISC1 exact, one generic).  Anchor wins.
    fixtures = [
        {
            "modality": "m_big", "name": "alpha_recipe", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D", "wave": "v1.0",
            },
        },
        {
            "modality": "m_big", "name": "beta_recipe", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D", "wave": "v1.0",
            },
        },
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        out = score_recipes(profile, fixtures)
    # beta scores higher (DISC1 exact = 0.20) than alpha (generic = 0.10), so
    # beta sorts first by raw score — anchor strength is then a *secondary*
    # signal that matters only when two rows are truly tied.  The truly-tied
    # case is exercised by ``tied_fixtures`` below.
    assert out[0].name == "beta_recipe"

    # Now construct a *truly* tied score — both anchor=generic, but differing
    # modalities (locality tie-break) and wave (alphabetical descending).
    tied_fixtures = [
        # m_big has 3 recipes total → higher locality.
        {
            "modality": "m_big", "name": "z_late", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D",
                "wave": "v1.1.0-beta-002",
            },
        },
        {
            "modality": "m_big", "name": "filler1", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D",
                "wave": "v1.0",
            },
        },
        {
            "modality": "m_big", "name": "filler2", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D",
                "wave": "v1.0",
            },
        },
        # m_small has only 1 recipe → loses locality tie-break.
        {
            "modality": "m_small", "name": "a_early", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "generic",
                "dynamics": "static", "dimensionality": "2D",
                "wave": "v1.0",
            },
        },
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        out2 = score_recipes(profile, tied_fixtures)
    # All four score identically (all generic anchor, same other matches).
    assert all(r.score == pytest.approx(out2[0].score) for r in out2)
    # Locality wins over alphabetical: m_big rows come before the m_small row.
    big_names = [r.name for r in out2 if r.modality == "m_big"]
    small_names = [r.name for r in out2 if r.modality == "m_small"]
    big_positions = [i for i, r in enumerate(out2) if r.modality == "m_big"]
    small_positions = [i for i, r in enumerate(out2) if r.modality == "m_small"]
    assert max(big_positions) < min(small_positions), (
        "Modality locality tie-breaker must place m_big rows before m_small."
    )
    # Within m_big, wave descending alphabetical: v1.1.0-beta-002 sorts AFTER
    # v1.0 (because oldest stable wins per spec).  So "filler*" (v1.0) come
    # before "z_late" (v1.1.0-beta-002) within m_big.
    assert big_names.index("z_late") == len(big_names) - 1
    # Within m_big at v1.0, two fillers tied by wave → alphabetical (asc).
    assert big_names.index("filler1") < big_names.index("filler2")
    # m_small has only one recipe; nothing to disambiguate.
    assert small_names == ["a_early"]


# ---------------------------------------------------------------------------
# 7. Below-threshold case — pool below MINIMUM_SCORE_FOR_SHORTLIST → empty.
# ---------------------------------------------------------------------------


def test_below_threshold_returns_empty_with_warning() -> None:
    """5 recipes all scoring < 0.40 → empty list + a UserWarning."""
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=True,
        equivalence_claims=True,
        dynamics_needed="kymograph",
        dimensionality="3D",
        modalities_in_scope=("m1",),
        hard_filters={},
    )
    # Each fixture matches at most ONE weight (≤ 0.30), keeping it under 0.40.
    fixtures = [
        # 0.30 only (factorial match, nothing else).
        {
            "modality": "m1", "name": "r_factorial_only", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": True, "equivalence": False, "anchor": "none",
                "dynamics": "live", "dimensionality": "2D",
            },
        },
        # 0.25 only (equivalence).
        {
            "modality": "m1", "name": "r_equiv_only", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "none",
                "dynamics": "live", "dimensionality": "2D",
            },
        },
        # 0.20 only (anchor).
        {
            "modality": "m1", "name": "r_anchor_only", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": False, "anchor": "DISC1",
                "dynamics": "live", "dimensionality": "2D",
            },
        },
        # 0.15 only (dynamics).
        {
            "modality": "m1", "name": "r_dyn_only", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": False, "anchor": "none",
                "dynamics": "kymograph", "dimensionality": "2D",
            },
        },
        # 0.10 only (dim).
        {
            "modality": "m1", "name": "r_dim_only", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": False, "anchor": "none",
                "dynamics": "live", "dimensionality": "3D",
            },
        },
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = score_recipes(profile, fixtures)
    assert out == []
    assert any("empty" in str(w.message).lower() for w in caught), (
        "score_recipes must warn when no recipes meet the threshold."
    )


# ---------------------------------------------------------------------------
# Bonus — small property checks that protect downstream callers.
# ---------------------------------------------------------------------------


def test_score_recipes_returns_scored_recipe_dataclasses() -> None:
    # Use a factorial+DISC1 profile so the recipe scores ≥0.40 under
    # post-DEFECT-A2 presence-checked semantics.
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=True,
        equivalence_claims=False,
        dynamics_needed="static",
        dimensionality="2D",
        modalities_in_scope=("m1",),
        hard_filters={},
    )
    fixtures = [
        {
            "modality": "m1", "name": "r", "family": "f",
            "answers_question": "Q",
            "tags": {
                "factorial": True, "equivalence": False, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D",
            },
        },
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        out = score_recipes(profile, fixtures)
    assert len(out) == 1
    assert isinstance(out[0], ScoredRecipe)
    assert out[0].full_name == "m1.r"
    assert out[0].family == "f"
    assert out[0].answers_question == "Q"
    assert isinstance(out[0].tags, dict)


def test_shortlist_size_truncates() -> None:
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=False,
        equivalence_claims=True,
        dynamics_needed="static",
        dimensionality="2D",
        modalities_in_scope=("m1",),
        hard_filters={},
        shortlist_size=2,
    )
    fixtures = [
        {
            "modality": "m1", "name": f"r{i}", "family": "f",
            "answers_question": "",
            "tags": {
                "factorial": False, "equivalence": True, "anchor": "DISC1",
                "dynamics": "static", "dimensionality": "2D",
            },
        }
        for i in range(5)
    ]
    out = score_recipes(profile, fixtures)
    assert len(out) == 2
