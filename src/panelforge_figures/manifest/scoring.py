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

__all__ = [
    # Locked rubric constants
    "SCORING_RUBRIC_VERSION",
    "WEIGHTS",
    "WEIGHTS_HISTORY",
    "MINIMUM_SCORE_FOR_SHORTLIST",
    "DEFAULT_SHORTLIST_SIZE",
    # Value types
    "ProjectProfile",
    "ScoredRecipe",
    # Scoring API
    "score_recipes",
    "scoring_rubric_dict",
    # Per-dimension match helpers
    "match_bool",
    "match_anchor",
    "match_dynamics",
    "match_dim",
]

# ---------------------------------------------------------------------------
# Locked constants — spec amendments only.
# ---------------------------------------------------------------------------

SCORING_RUBRIC_VERSION: str = "1.0.0"

# Append-only registry of historical weight tables.  Adding a new entry
# requires bumping ``SCORING_RUBRIC_VERSION`` and shipping a release; entries
# are never removed.  See ``docs/spec_active_learning.md`` §6 for the
# versioning policy.
WEIGHTS_HISTORY: dict[str, Mapping[str, float]] = {
    "1.0.0": MappingProxyType(
        {
            "factorial": 0.30,
            "equivalence": 0.25,
            "anchor": 0.20,
            "dynamics": 0.15,
            "dimensionality": 0.10,
        }
    ),
    # E7 (v3.0.0rc2) — shadow-mode rubric with manuscript_alignment term.
    # Not the default; users opt in via ``--weights-version 1.1.0``.
    "1.1.0": MappingProxyType(
        {
            "factorial": 0.27,
            "equivalence": 0.23,
            "anchor": 0.18,
            "dynamics": 0.13,
            "dimensionality": 0.09,
            "manuscript_alignment": 0.10,
        }
    ),
}

# ``WEIGHTS`` is the default-version view into ``WEIGHTS_HISTORY``; callers
# that don't pass ``weights_version`` to ``score_recipes`` see the entry
# pinned to ``SCORING_RUBRIC_VERSION``.  Keeping this alias lets existing
# importers continue to read ``scoring.WEIGHTS`` unchanged.
WEIGHTS: Mapping[str, float] = WEIGHTS_HISTORY[SCORING_RUBRIC_VERSION]

WEIGHTS_SUM_CHECK: float = 1.00
MINIMUM_SCORE_FOR_SHORTLIST: float = 0.40
DEFAULT_SHORTLIST_SIZE: int = 12

# Internal sanity check — fires at import time if the table is ever edited
# without re-summing.  ``abs() < 1e-9`` to be robust to FP noise.
assert abs(sum(WEIGHTS.values()) - WEIGHTS_SUM_CHECK) < 1e-9, (
    f"WEIGHTS must sum to {WEIGHTS_SUM_CHECK}; got {sum(WEIGHTS.values())}"
)
# Every entry in ``WEIGHTS_HISTORY`` must independently sum to 1.0 — protects
# against typos when a future maintainer appends a new rubric version.
for _wv, _w in WEIGHTS_HISTORY.items():
    assert abs(sum(_w.values()) - WEIGHTS_SUM_CHECK) < 1e-9, (
        f"WEIGHTS_HISTORY[{_wv!r}] must sum to {WEIGHTS_SUM_CHECK}; "
        f"got {sum(_w.values())}"
    )
del _wv, _w


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
    """Presence-checked match: 1.0 ONLY when profile==True AND recipe==True.

    DEFECT-A2 fix (Wave-3 polish): the function is intentionally
    asymmetric.  A recipe tagged ``factorial: false`` in a non-factorial
    project contributes 0.0 — not 1.0 — because "I don't need factorial
    support" should not credit a recipe just for not having it.  Only
    affirmative alignment (``factorial: true`` recipe in a factorial
    project) earns the weight.

    This matches the worked-example arithmetic in
    ``RECIPE_SELECTION.md`` (DISC1 example: factorial contribution 0.0
    despite both profile and recipe being False).
    """
    if profile_value is True and recipe_value is True:
        return 1.0
    return 0.0


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

    DEFECT-2 fix (Wave-2 polish): static/static lands on the 0.3
    baseline branch, NOT 1.0.  This matches the prose arithmetic in
    ``RECIPE_SELECTION.md`` worked examples (Example 1's static profile
    contributes 0.045 = 0.15 × 0.3, not 0.15 × 1.0) and reflects the
    semantic intent that "I want static" = "I have no temporal signal
    to discriminate on" — so dynamics should never contribute full
    weight when both sides are static.

    Order of precedence:
      - both ``static`` → 0.3 (static baseline; carve-out before exact-match)
      - exact match (non-static) → 1.0
      - profile is ``mixed`` and recipe is non-empty → 0.8 (any-match)
      - recipe is ``static`` (and profile is non-static, non-mixed) → 0.3
      - otherwise → 0.0
    """
    r = (recipe_dyn or "").strip()
    p = (profile_dyn or "").strip()
    # Carve-out: both static → baseline weight, not exact-match.
    if r == "static" and p == "static":
        return 0.3
    if r == p and r != "":
        return 1.0
    if p == "mixed" and r:
        return 0.8
    if r == "static":
        return 0.3
    return 0.0


def match_dim(recipe_dim: str | None, profile_dim: str) -> float:
    """Dimensionality-match heuristic.

    DEFECT-A2 follow-on: profile=``mixed`` ALWAYS scores 0.7 regardless
    of recipe dim (carve-out before the exact-match check), matching
    ``RECIPE_SELECTION.md`` Example-1 arithmetic (0.10 × 0.7 = 0.07).
    The semantic intent: "I have mixed-dim data" means "any single-dim
    recipe gives me partial value, never full" — even a ``mixed/mixed``
    pairing because the user's profile didn't commit to one dim.

    Order:
      - profile is ``mixed`` AND recipe is non-empty → 0.7 (mixed credit)
      - exact match (non-mixed) → 1.0
      - otherwise → 0.0
    """
    r = (recipe_dim or "").strip()
    p = (profile_dim or "").strip()
    # Mixed-profile carve-out: applies before the exact-match branch.
    if p == "mixed" and r:
        return 0.7
    if r == p and r != "":
        return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------------


def _passes_hard_filters(
    tags: Mapping[str, Any],
    modality: str,
    profile: ProjectProfile,
) -> bool:
    """Return True iff recipe meets every hard filter.

    DEFECT-1 fix (Wave-2 polish): filter requires the tag value to be
    *literally* True.  Recipes with ``"unknown"`` sentinels or missing
    keys are dropped — otherwise ``bool("unknown") is True`` would let
    untagged recipes silently pass a ``compartment_aware: True`` filter,
    breaking the documented "narrow 100 → 31" funnel.

    DEFECT-4 fix: the ``factorial_only`` slug from intake is aliased to
    the ``factorial`` tag key; selecting it requires ``factorial: True``.
    """
    if profile.modalities_in_scope and modality not in profile.modalities_in_scope:
        return False
    for key, required in profile.hard_filters.items():
        if not required:
            continue                              # only True-valued keys are gates
        # DEFECT-4 alias: factorial_only → factorial.
        tag_key = "factorial" if key == "factorial_only" else key
        if tags.get(tag_key) is not True:
            return False
    return True


def _score_one(
    tags: Mapping[str, Any],
    profile: ProjectProfile,
    weights: Mapping[str, float] = WEIGHTS,
) -> float:
    """Apply the given (or default) weights to a single recipe's tags."""
    return (
        weights["factorial"]
        * match_bool(tags.get("factorial"), profile.factorial_design)
        + weights["equivalence"]
        * match_bool(tags.get("equivalence"), profile.equivalence_claims)
        + weights["anchor"]
        * match_anchor(tags.get("anchor"), profile.manuscript_anchor)
        + weights["dynamics"]
        * match_dynamics(tags.get("dynamics"), profile.dynamics_needed)
        + weights["dimensionality"]
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
    *,
    weights_version: str = SCORING_RUBRIC_VERSION,
) -> list[ScoredRecipe]:
    """Apply hard filters + soft scoring + tie-breakers + threshold.

    Parameters
    ----------
    profile : ProjectProfile
        The user's project snapshot.
    recipes_with_tags : Iterable[dict]
        Each dict must carry ``modality``, ``name``, ``family``,
        ``answers_question``, and ``tags``.  Extra keys are ignored.
    weights_version : str, keyword-only
        Selects which entry of ``WEIGHTS_HISTORY`` to score against.  Defaults
        to ``SCORING_RUBRIC_VERSION`` so existing callers see no change.
        Raises ``KeyError`` if the version is not present in
        ``WEIGHTS_HISTORY``.

    Returns
    -------
    list[ScoredRecipe]
        Up to ``profile.shortlist_size`` rows, descending by score with
        deterministic tie-breakers applied.  Empty list is a valid result.
    """
    weights = WEIGHTS_HISTORY[weights_version]
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
        s = _score_one(tags, profile, weights)
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
            "wave_oldest_first",
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
