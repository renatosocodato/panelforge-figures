"""Recipe-discovery scorer — locked-weight rubric, hard filters, tie-breakers.

This module implements §3 of ``RECIPE_DISCOVERY_SYSTEM.md``.  The weights below
are **frozen constants**: changing them is a spec amendment, not a refactor.
Behavior of the funnel is:

1. Hard filters (modality scope + boolean tag requirements) narrow the pool.
2. Soft scoring with the locked weights produces a score in [0, 1].
3. Lexicographic tie-breakers resolve ties (anchor strength → modality locality
   → wave (alphabetical descending) → recipe name (alphabetical ascending)).
4. Recipes below ``MINIMUM_SCORE_FOR_SHORTLIST`` are dropped.  If the surviving
   pool is smaller than ``profile.shortlist_size`` an explicit warning is
   emitted (Python ``warnings.warn``) but the call still returns the truncated
   pool — the caller is responsible for surfacing the warning to the user.

The public API is intentionally narrow: ``ProjectProfile`` (input dataclass),
``ScoredRecipe`` (output row), ``score_recipes`` (the funnel), and
``scoring_rubric_dict`` (the rubric block embedded into ``recipes_index.json``
by the catalog integrator).
"""

from __future__ import annotations

import warnings
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

# ---------------------------------------------------------------------------
# Locked constants — spec amendments only.
# ---------------------------------------------------------------------------

WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "factorial": 0.30,
        "equivalence": 0.25,
        "anchor": 0.20,
        "dynamics": 0.15,
        "dimensionality": 0.10,
    }
)

WEIGHTS_SUM_CHECK: float = 1.00
SCORING_RUBRIC_VERSION: str = "1.0.0"
MINIMUM_SCORE_FOR_SHORTLIST: float = 0.40
DEFAULT_SHORTLIST_SIZE: int = 12

# Internal sanity check — fires at import time if the table is ever edited
# without re-summing.  ``abs() < 1e-9`` to be robust to FP noise.
assert abs(sum(WEIGHTS.values()) - WEIGHTS_SUM_CHECK) < 1e-9, (
    f"WEIGHTS must sum to {WEIGHTS_SUM_CHECK}; got {sum(WEIGHTS.values())}"
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectProfile:
    """Snapshot of the user's project, fed into the scorer.

    Field semantics match RECIPE_DISCOVERY_SYSTEM.md §3.2.
    """

    manuscript_anchor: str                        # "DISC1" | "CDC42" | "both" | "none"
    factorial_design: bool
    equivalence_claims: bool
    dynamics_needed: str                          # static | kymograph | live | ordered_pseudotime | mixed
    dimensionality: str                           # "2D" | "3D" | "mixed"
    modalities_in_scope: tuple[str, ...]
    hard_filters: Mapping[str, bool] = field(default_factory=dict)
    shortlist_size: int = DEFAULT_SHORTLIST_SIZE


@dataclass(frozen=True)
class ScoredRecipe:
    """A single row of the funnel's output."""

    full_name: str        # "{modality}.{name}"
    modality: str
    name: str
    family: str
    answers_question: str
    score: float
    tags: dict[str, Any]


# ---------------------------------------------------------------------------
# Match functions — each returns a value in [0, 1].
# ---------------------------------------------------------------------------


def match_bool(recipe_value: bool | None, profile_value: bool) -> float:
    """1.0 if recipe == profile (both True, or both False); else 0.0.

    Note: a recipe with ``factorial: false`` in a factorial project returns
    0.0 — *no penalty*, just no contribution.  The function is symmetric.
    """
    return 1.0 if bool(recipe_value) == bool(profile_value) else 0.0


def match_anchor(recipe_anchor: str | None, profile_anchor: str) -> float:
    """Anchor-overlap heuristic.

    - exact match → 1.0
    - recipe is "generic" → 0.5 (always partially useful)
    - profile is "both" and recipe is one of {"DISC1", "CDC42"} → 0.7
    - otherwise → 0.0
    """
    r = (recipe_anchor or "").strip()
    p = (profile_anchor or "").strip()
    if r == p and r != "":
        return 1.0
    if r == "generic":
        return 0.5
    if p == "both" and r in {"DISC1", "CDC42"}:
        return 0.7
    return 0.0


def match_dynamics(recipe_dyn: str | None, profile_dyn: str) -> float:
    """Dynamics-match heuristic.

    - exact match → 1.0
    - profile is "mixed" and recipe is non-empty → 0.8 (any-match)
    - recipe is "static" → 0.3 (baselines always useful)
    - otherwise → 0.0
    """
    r = (recipe_dyn or "").strip()
    p = (profile_dyn or "").strip()
    if r == p and r != "":
        return 1.0
    if p == "mixed" and r:
        return 0.8
    if r == "static":
        return 0.3
    return 0.0


def match_dim(recipe_dim: str | None, profile_dim: str) -> float:
    """Dimensionality-match heuristic.

    - exact match → 1.0
    - profile is "mixed" → 0.7 always
    - otherwise → 0.0
    """
    r = (recipe_dim or "").strip()
    p = (profile_dim or "").strip()
    if r == p and r != "":
        return 1.0
    if p == "mixed":
        return 0.7
    return 0.0


# ---------------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------------


def _passes_hard_filters(
    tags: Mapping[str, Any],
    modality: str,
    profile: ProjectProfile,
) -> bool:
    """Return True iff recipe meets every hard filter."""
    if profile.modalities_in_scope and modality not in profile.modalities_in_scope:
        return False
    for key, required in profile.hard_filters.items():
        if not required:
            continue                              # only True-valued keys are gates
        if not bool(tags.get(key, False)):
            return False
    return True


def _score_one(tags: Mapping[str, Any], profile: ProjectProfile) -> float:
    """Apply the locked weights to a single recipe's tags."""
    return (
        WEIGHTS["factorial"]
        * match_bool(tags.get("factorial"), profile.factorial_design)
        + WEIGHTS["equivalence"]
        * match_bool(tags.get("equivalence"), profile.equivalence_claims)
        + WEIGHTS["anchor"]
        * match_anchor(tags.get("anchor"), profile.manuscript_anchor)
        + WEIGHTS["dynamics"]
        * match_dynamics(tags.get("dynamics"), profile.dynamics_needed)
        + WEIGHTS["dimensionality"]
        * match_dim(tags.get("dimensionality"), profile.dimensionality)
    )


def _anchor_strength(tags: Mapping[str, Any], profile: ProjectProfile) -> int:
    """Tie-breaker rank for anchor: 2 = exact, 1 = generic/both-overlap, 0 = none."""
    a = tags.get("anchor")
    if a == profile.manuscript_anchor and a not in (None, ""):
        return 2
    if a == "generic":
        return 1
    if profile.manuscript_anchor == "both" and a in {"DISC1", "CDC42"}:
        return 1
    return 0


def score_recipes(
    profile: ProjectProfile,
    recipes_with_tags: Iterable[dict[str, Any]],
) -> list[ScoredRecipe]:
    """Apply hard filters + soft scoring + tie-breakers + threshold.

    Parameters
    ----------
    profile : ProjectProfile
        The user's project snapshot.
    recipes_with_tags : Iterable[dict]
        Each dict must carry ``modality``, ``name``, ``family``,
        ``answers_question``, and ``tags``.  Extra keys are ignored.

    Returns
    -------
    list[ScoredRecipe]
        Up to ``profile.shortlist_size`` rows, descending by score with
        deterministic tie-breakers applied.  Empty list is a valid result.
    """
    recipes = list(recipes_with_tags)

    # Step 1 — hard filters.
    survivors: list[dict[str, Any]] = [
        r for r in recipes
        if _passes_hard_filters(r.get("tags", {}) or {}, r.get("modality", ""), profile)
    ]

    # Step 2 — soft score.
    scored: list[tuple[ScoredRecipe, dict[str, Any]]] = []
    for r in survivors:
        tags = r.get("tags", {}) or {}
        s = _score_one(tags, profile)
        if s < MINIMUM_SCORE_FOR_SHORTLIST:
            continue
        modality = r.get("modality", "")
        name = r.get("name", "")
        scored.append(
            (
                ScoredRecipe(
                    full_name=f"{modality}.{name}",
                    modality=modality,
                    name=name,
                    family=r.get("family", ""),
                    answers_question=r.get("answers_question", ""),
                    score=round(s, 4),
                    tags=dict(tags),
                ),
                dict(tags),
            )
        )

    # Step 3 — tie-breakers (lexicographic).
    # Modality locality is computed *after* hard filtering: the modality with
    # the most surviving recipes earns the highest locality rank.
    locality_counter = Counter(sr.modality for sr, _ in scored)

    def _sort_key(item: tuple[ScoredRecipe, dict[str, Any]]) -> tuple[Any, ...]:
        sr, tags = item
        anchor_rank = _anchor_strength(tags, profile)
        locality_rank = locality_counter[sr.modality]
        wave = str(tags.get("wave", ""))         # missing wave sorts after populated
        # Sort key: descending score, descending anchor_rank, descending
        # locality, then wave (oldest stable first per spec — lex-ascending
        # over the version string), then ascending recipe name.
        return (
            -sr.score,
            -anchor_rank,
            -locality_rank,
            _wave_sort_inv(wave),
            sr.name,
        )

    scored.sort(key=_sort_key)

    # Step 4 — shortlist.
    out = [sr for sr, _ in scored[: profile.shortlist_size]]
    if 0 < len(out) < profile.shortlist_size:
        warnings.warn(
            f"shortlist underfilled: {len(out)} recipes returned, "
            f"expected up to {profile.shortlist_size}",
            UserWarning,
            stacklevel=2,
        )
    elif len(out) == 0 and recipes:
        warnings.warn(
            "shortlist is empty: no recipes survived hard filters + score >= "
            f"{MINIMUM_SCORE_FOR_SHORTLIST}",
            UserWarning,
            stacklevel=2,
        )
    return out


def _wave_sort_inv(wave: str) -> tuple[int, str]:
    """Sort key for wave — older stable releases come first.

    Spec preference chain (``>`` reads as "preferred over"):
        "v1.0" > "v1.1.0-beta-..." > "v1.2.0-..."

    Lexicographically these are *ascending* (``"v1.0" < "v1.1.0-..."``), so
    Python's natural string sort yields the documented ordering.  Empty wave
    strings are tagged ``(1, "")`` so they fall after every populated wave.
    """
    if not wave:
        return (1, "")                           # tie-broken last
    return (0, wave)


# ---------------------------------------------------------------------------
# Rubric block — for embedding in recipes_index.json.
# ---------------------------------------------------------------------------


def scoring_rubric_dict() -> dict[str, Any]:
    """Return the rubric block consumed by the catalog integrator.

    Shape is stable across additive changes; bumping
    ``SCORING_RUBRIC_VERSION`` indicates a breaking change to weights or
    match-function semantics.
    """
    return {
        "version": SCORING_RUBRIC_VERSION,
        "weights": dict(WEIGHTS),
        "weights_sum": WEIGHTS_SUM_CHECK,
        "minimum_score_for_shortlist": MINIMUM_SCORE_FOR_SHORTLIST,
        "default_shortlist_size": DEFAULT_SHORTLIST_SIZE,
        "tie_breakers": [
            "anchor_match_strength",
            "modality_locality",
            "wave_alphabetical_descending",
            "recipe_name_alphabetical",
        ],
        "match_functions": {
            "factorial": "exact_bool",
            "equivalence": "exact_bool",
            "anchor": "exact|generic=0.5|both_overlap=0.7",
            "dynamics": "exact|profile_mixed=0.8|static_baseline=0.3",
            "dimensionality": "exact|profile_mixed=0.7",
        },
    }
