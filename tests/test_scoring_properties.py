"""Property-based tests for the locked-weight scorer (Hypothesis).

These complement the hand-written fixture tests in
``test_scoring_locked_weights.py`` by exhaustively probing mathematical
invariants of the scorer that a finite fixture set cannot easily prove:

  1. Score is in [0, 1] — for ANY valid (profile, recipe) pair.
  2. Each match function returns a value in [0, 1].
  3. Score is monotonic in tag alignment — adding a matching tag never
     decreases the score (locked-weight non-negativity).
  4. Tie-breakers are deterministic — running ``score_recipes`` twice on
     the same input yields byte-identical output.
  5. Hard filter is total — when ``hard_filters = {"compartment_aware": True}``
     no recipe in the result has ``tags.get("compartment_aware") != True``.
     (DEFECT-1 regression gate from PR #55.)
  6. Threshold is total — no recipe in the shortlist scores below
     ``MINIMUM_SCORE_FOR_SHORTLIST`` (0.40).
  7. Shortlist size respected — ``len(scored) <= profile.shortlist_size``.
  8. Empty pool returns empty.
  9. WEIGHTS sum to 1.0 exactly.

All tests use the closed-taxonomy values from
``panelforge_figures.manifest.tag_taxonomy`` plus the ``"unknown"`` sentinel
emitted by the auto-tagger, matching the universe of values that hit the
scorer at runtime.
"""

from __future__ import annotations

import warnings
from typing import Any

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from panelforge_figures.manifest.scoring import (
    MINIMUM_SCORE_FOR_SHORTLIST,
    WEIGHTS,
    WEIGHTS_SUM_CHECK,
    ProjectProfile,
    match_anchor,
    match_bool,
    match_dim,
    match_dynamics,
    score_recipes,
)

# ---------------------------------------------------------------------------
# Strategies — closed-taxonomy values + "unknown" sentinel.
# ---------------------------------------------------------------------------

anchor_st = st.sampled_from(
    ["DISC1", "CDC42", "DISC1+CDC42", "RhoA", "RAC1", "generic", "unknown"]
)
dim_st = st.sampled_from(["2D", "3D", "1D", "scalar", "unknown"])
dynamics_st = st.sampled_from(
    ["static", "kymograph", "live", "ordered_pseudotime", "unknown"]
)
wave_st = st.sampled_from(
    [
        "v1.0",
        "v1.1.0-beta-biophysics_scaling",
        "v1.2.0-beta-actin_microtubule_morphometry",
        "v1.3.0-beta-intravital_imaging",
        "v1.4.0-beta-cytoskeletal_morphometry_companion",
        "v1.5.0-beta-factorial_design_companion",
    ]
)

# Boolean tags can also be the "unknown" sentinel per PR #57.
bool_or_unknown = st.one_of(st.booleans(), st.just("unknown"))

# Full tag dict — every key the scorer reads.
tag_dict_st = st.fixed_dictionaries(
    {
        "anchor": anchor_st,
        "dimensionality": dim_st,
        "dynamics": dynamics_st,
        "wave": wave_st,
        "factorial": bool_or_unknown,
        "equivalence": bool_or_unknown,
        "compartment_aware": bool_or_unknown,
        "scale_aware": bool_or_unknown,
    }
)

profile_st = st.builds(
    ProjectProfile,
    manuscript_anchor=st.sampled_from(["DISC1", "CDC42", "both", "none"]),
    factorial_design=st.booleans(),
    equivalence_claims=st.booleans(),
    dynamics_needed=st.sampled_from(
        ["static", "kymograph", "live", "ordered_pseudotime", "mixed"]
    ),
    dimensionality=st.sampled_from(["2D", "3D", "mixed"]),
    modalities_in_scope=st.just(()),  # empty = no modality scoping
    hard_filters=st.just({}),  # default: no hard filters
    shortlist_size=st.integers(min_value=1, max_value=20),
)

recipe_st = st.builds(
    lambda mod, name, tags: {
        "modality": mod,
        "name": name,
        "family": "f",
        "answers_question": "Q",
        "tags": tags,
    },
    mod=st.sampled_from(["m1", "m2", "m3"]),
    name=st.text(min_size=1, max_size=20, alphabet="abcdef"),
    tags=tag_dict_st,
)

recipes_st = st.lists(recipe_st, min_size=0, max_size=20)


def _silent_score(profile: ProjectProfile, recipes: list[dict[str, Any]]):
    """Run ``score_recipes`` while suppressing the underfill/empty UserWarnings.

    The pytest config promotes warnings to errors, so we need to mute the
    informational UserWarnings the scorer emits when a shortlist is short or
    empty — those are documented behavior, not failures.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return score_recipes(profile, recipes)


# ---------------------------------------------------------------------------
# Property 1 — score is in [0, 1] for every surviving recipe.
# ---------------------------------------------------------------------------


@given(profile=profile_st, recipes=recipes_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_score_in_unit_interval(profile, recipes):
    scored = _silent_score(profile, recipes)
    for sr in scored:
        assert 0.0 <= sr.score <= 1.0, f"score out of [0,1]: {sr.score} for {sr.full_name}"


# ---------------------------------------------------------------------------
# Property 2 — each match function returns a value in [0, 1].
# ---------------------------------------------------------------------------


@given(
    recipe_val=bool_or_unknown,
    profile_val=st.booleans(),
)
@settings(max_examples=200)
def test_match_bool_unit_interval(recipe_val, profile_val):
    # match_bool only treats the recipe-side as bool|None; "unknown" is
    # neither True nor False and should land in the 0.0 fallthrough.
    rv = recipe_val if isinstance(recipe_val, bool) else None
    val = match_bool(rv, profile_val)
    assert 0.0 <= val <= 1.0


@given(recipe_anchor=anchor_st, profile_anchor=st.sampled_from(["DISC1", "CDC42", "both", "none"]))
@settings(max_examples=200)
def test_match_anchor_unit_interval(recipe_anchor, profile_anchor):
    val = match_anchor(recipe_anchor, profile_anchor)
    assert 0.0 <= val <= 1.0


@given(
    recipe_dyn=dynamics_st,
    profile_dyn=st.sampled_from(["static", "kymograph", "live", "ordered_pseudotime", "mixed"]),
)
@settings(max_examples=200)
def test_match_dynamics_unit_interval(recipe_dyn, profile_dyn):
    val = match_dynamics(recipe_dyn, profile_dyn)
    assert 0.0 <= val <= 1.0


@given(recipe_dim=dim_st, profile_dim=st.sampled_from(["2D", "3D", "mixed"]))
@settings(max_examples=200)
def test_match_dim_unit_interval(recipe_dim, profile_dim):
    val = match_dim(recipe_dim, profile_dim)
    assert 0.0 <= val <= 1.0


# ---------------------------------------------------------------------------
# Property 3 — score is monotonic in tag alignment.
#
# With locked weights and presence-checked match functions, replacing a
# bool tag's value with the profile-aligned value (i.e. flipping it from
# False/"unknown"→True when the profile expects True) cannot decrease the
# score: every weighted contribution is non-negative.  We test this by
# constructing a recipe-A whose bool tags are ALL True (full alignment
# with a True-True profile) and a recipe-B that is identical except one
# bool is False — then score(A) >= score(B).
# ---------------------------------------------------------------------------


@given(
    profile=profile_st,
    base_tags=tag_dict_st,
    flip_key=st.sampled_from(["factorial", "equivalence"]),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_score_monotonic_in_bool_alignment(profile, base_tags, flip_key):
    # Force the profile to want this bool true so the True/True branch
    # actually contributes weight; otherwise both variants score identically
    # (which would still satisfy the property, but is uninteresting).
    profile = ProjectProfile(
        manuscript_anchor=profile.manuscript_anchor,
        factorial_design=True if flip_key == "factorial" else profile.factorial_design,
        equivalence_claims=True if flip_key == "equivalence" else profile.equivalence_claims,
        dynamics_needed=profile.dynamics_needed,
        dimensionality=profile.dimensionality,
        modalities_in_scope=profile.modalities_in_scope,
        hard_filters=profile.hard_filters,
        shortlist_size=profile.shortlist_size,
    )

    aligned_tags = dict(base_tags)
    aligned_tags[flip_key] = True
    misaligned_tags = dict(base_tags)
    misaligned_tags[flip_key] = False

    recipe_aligned = {
        "modality": "m1",
        "name": "aligned",
        "family": "f",
        "answers_question": "Q",
        "tags": aligned_tags,
    }
    recipe_misaligned = {
        "modality": "m1",
        "name": "misaligned",
        "family": "f",
        "answers_question": "Q",
        "tags": misaligned_tags,
    }

    aligned_score = _silent_score(profile, [recipe_aligned])
    misaligned_score = _silent_score(profile, [recipe_misaligned])

    # If both pass threshold, aligned must score >= misaligned.  If only
    # aligned passes threshold, that's also consistent with monotonicity.
    # If neither passes, the property is vacuously true.
    a = aligned_score[0].score if aligned_score else 0.0
    b = misaligned_score[0].score if misaligned_score else 0.0
    assert a >= b, (
        f"monotonicity violated: aligned={a} misaligned={b} flip_key={flip_key}"
    )


# ---------------------------------------------------------------------------
# Property 4 — deterministic output (identical input → byte-identical output).
# ---------------------------------------------------------------------------


@given(profile=profile_st, recipes=recipes_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_score_recipes_is_deterministic(profile, recipes):
    out_a = _silent_score(profile, recipes)
    out_b = _silent_score(profile, recipes)
    assert len(out_a) == len(out_b)
    for a, b in zip(out_a, out_b, strict=True):
        assert a.full_name == b.full_name
        assert a.score == b.score
        assert a.tags == b.tags


# ---------------------------------------------------------------------------
# Property 5 — hard filter is total (DEFECT-1 regression gate).
# ---------------------------------------------------------------------------


@given(recipes=recipes_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_hard_filter_compartment_aware_is_total(recipes):
    profile = ProjectProfile(
        manuscript_anchor="DISC1",
        factorial_design=True,
        equivalence_claims=True,
        dynamics_needed="mixed",
        dimensionality="mixed",
        modalities_in_scope=(),
        hard_filters={"compartment_aware": True},
        shortlist_size=20,
    )
    scored = _silent_score(profile, recipes)
    for sr in scored:
        assert sr.tags.get("compartment_aware") is True, (
            f"recipe {sr.full_name} survived a compartment_aware hard filter "
            f"with tag value {sr.tags.get('compartment_aware')!r}"
        )


# ---------------------------------------------------------------------------
# Property 6 — threshold is total: no shortlisted recipe scores below 0.40.
# ---------------------------------------------------------------------------


@given(profile=profile_st, recipes=recipes_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_threshold_is_total(profile, recipes):
    scored = _silent_score(profile, recipes)
    for sr in scored:
        assert sr.score >= MINIMUM_SCORE_FOR_SHORTLIST, (
            f"recipe {sr.full_name} survived the threshold with score "
            f"{sr.score} < {MINIMUM_SCORE_FOR_SHORTLIST}"
        )


# ---------------------------------------------------------------------------
# Property 7 — shortlist size always respected.
# ---------------------------------------------------------------------------


@given(profile=profile_st, recipes=recipes_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_shortlist_size_respected(profile, recipes):
    scored = _silent_score(profile, recipes)
    assert len(scored) <= profile.shortlist_size, (
        f"shortlist of size {len(scored)} exceeded cap {profile.shortlist_size}"
    )


# ---------------------------------------------------------------------------
# Property 8 — empty pool returns empty list.
# ---------------------------------------------------------------------------


@given(profile=profile_st)
@settings(max_examples=50)
def test_empty_pool_returns_empty(profile):
    # No warning is expected for an empty input — the scorer skips the
    # "empty shortlist" warning when the input itself was empty.
    out = score_recipes(profile, [])
    assert out == []


# ---------------------------------------------------------------------------
# Property 9 — WEIGHTS sum to 1.0 exactly (regression-proof).
#
# Property-style restatement: for every random ordering of the WEIGHTS
# items, the float sum still equals 1.0 within FP tolerance.  Catches a
# future edit that adds/removes a weight key without re-summing.
# ---------------------------------------------------------------------------


@given(perm=st.permutations(list(WEIGHTS.items())))
@settings(max_examples=50)
def test_weights_sum_invariant(perm):
    s = sum(v for _, v in perm)
    assert abs(s - WEIGHTS_SUM_CHECK) < 1e-9, f"weights sum {s} != {WEIGHTS_SUM_CHECK}"
    # Spot-check the key invariant the scorer relies on.
    assert WEIGHTS_SUM_CHECK == 1.00


# ---------------------------------------------------------------------------
# Bonus property — when hard_filters is empty AND shortlist_size is large,
# every survivor's score must equal the deterministic _score_one output
# computed independently.  This guards against any silent normalization
# drift introduced into the scoring pipeline.
# ---------------------------------------------------------------------------


@given(profile=profile_st, recipes=recipes_st)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_score_matches_independent_recompute(profile, recipes):
    assume(len(recipes) <= profile.shortlist_size)
    scored = _silent_score(profile, recipes)
    for sr in scored:
        # Recompute by summing weighted match values, mirroring _score_one.
        tags = sr.tags
        expected = (
            WEIGHTS["factorial"] * match_bool(tags.get("factorial"), profile.factorial_design)
            + WEIGHTS["equivalence"]
            * match_bool(tags.get("equivalence"), profile.equivalence_claims)
            + WEIGHTS["anchor"] * match_anchor(tags.get("anchor"), profile.manuscript_anchor)
            + WEIGHTS["dynamics"] * match_dynamics(tags.get("dynamics"), profile.dynamics_needed)
            + WEIGHTS["dimensionality"] * match_dim(tags.get("dimensionality"), profile.dimensionality)
        )
        assert abs(sr.score - round(expected, 4)) < 1e-9, (
            f"score drift for {sr.full_name}: stored {sr.score}, recomputed {expected}"
        )
