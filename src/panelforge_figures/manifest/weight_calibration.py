"""Offline weight-calibration tooling — companion to ``scoring.py``.

This module implements §4 and §5 of ``docs/spec_active_learning.md``.  It is a
**post-hoc analysis tool**: given an aggregated ``usage.jsonl`` produced by
opted-in users, it grid-searches small perturbations of the locked weight
vector and reports the candidate that maximises top-3 hit rate on a held-out
test split.  The tool never edits source files — its only output is a JSON
proposal that a maintainer reviews by hand before bumping
``SCORING_RUBRIC_VERSION``.

Design notes:

- Determinism is non-negotiable.  All randomness routes through a single
  ``random.Random(seed)`` so the same input file always yields the same
  proposal (acceptance criterion §13.3).
- The grid is intentionally narrow (``±0.05`` per weight).  Larger jumps are
  out of scope; the tool is checking for *miscalibration*, not searching for
  a global optimum.
- Re-scoring rows from the JSONL does NOT re-invoke the scoring funnel; we
  read the already-computed per-tag sub-scores out of ``scored_top_5`` and
  combine them with the candidate weight vector.  This means the proposal
  is conditioned on the historical recipe tags as recorded at log time —
  exactly what we want when calibrating against past pick behaviour.
"""

from __future__ import annotations

import json
import random
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from .scoring import SCORING_RUBRIC_VERSION, WEIGHTS_HISTORY

__all__ = [
    "CalibrationInput",
    "CalibrationOutput",
    "load_telemetry_rows",
    "split_train_test",
    "iter_weight_grid",
    "evaluate_weights",
    "suggest_weights",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Order matters — this is the canonical key order used everywhere weight
# vectors are emitted (output JSON, grid iteration) so diffs against golden
# snapshots are stable.
_WEIGHT_KEYS: tuple[str, ...] = (
    "factorial",
    "equivalence",
    "anchor",
    "dynamics",
    "dimensionality",
)

# Default cross-validation parameters (§4 of the spec).
_DEFAULT_TEST_FRAC: float = 0.20
_DEFAULT_DELTAS: tuple[float, ...] = (-0.05, 0.0, 0.05)
_DEFAULT_FLOOR: float = 0.05
_TOP_K_FOR_HIT_RATE: int = 3


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationInput:
    """Calibration job description — pre-filtered telemetry rows + seed."""

    rows: list[dict]                 # filtered, with user_picked != null
    seed: int = 42


@dataclass(frozen=True)
class CalibrationOutput:
    """Result emitted by :func:`suggest_weights`.

    Field semantics match the JSON schema in §5 of the spec.  ``uplift`` is
    the suggested top-3 hit rate minus the current top-3 hit rate, both
    measured on the held-out test split.
    """

    n_rows: int
    n_train: int
    n_test: int
    current_weights_version: str
    current_weights: Mapping[str, float]
    current_top3_hit_rate: float
    suggested_weights: Mapping[str, float]
    suggested_top3_hit_rate: float
    uplift: float
    seed: int

    def to_dict(self) -> dict:
        """Return a plain ``dict`` suitable for ``json.dump``.

        Weight mappings are converted to ordinary dicts in the canonical
        ``_WEIGHT_KEYS`` order so golden-snapshot tests are byte-stable.
        """
        return {
            "n_rows": self.n_rows,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "current_weights_version": self.current_weights_version,
            "current_weights": _ordered_weight_dict(self.current_weights),
            "current_top3_hit_rate": self.current_top3_hit_rate,
            "suggested_weights": _ordered_weight_dict(self.suggested_weights),
            "suggested_top3_hit_rate": self.suggested_top3_hit_rate,
            "uplift": self.uplift,
            "seed": self.seed,
        }


# ---------------------------------------------------------------------------
# Loaders / splitters
# ---------------------------------------------------------------------------


def load_telemetry_rows(jsonl_path: Path) -> list[dict]:
    """Read a JSONL file and return rows that carry calibration signal.

    A row carries calibration signal iff:

    1. ``user_picked`` is not null, **and**
    2. ``rejected_higher_scored`` is non-empty (otherwise the user picked the
       top-ranked recipe and the row tells us nothing about miscalibration).

    Malformed lines (invalid JSON, missing keys) are skipped with a
    ``UserWarning``.  An empty file returns an empty list silently — the
    caller decides whether that should be an error.
    """
    path = Path(jsonl_path)
    rows: list[dict] = []
    if not path.exists():
        # Treat a missing file the same as an empty one — caller decides.
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.warn(
                    f"{path}:{lineno}: skipping malformed JSON line",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            if not isinstance(row, dict):
                warnings.warn(
                    f"{path}:{lineno}: expected JSON object, got {type(row).__name__}",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            if row.get("user_picked") in (None, ""):
                continue
            rejected = row.get("rejected_higher_scored")
            if not rejected:
                continue
            rows.append(row)
    return rows


def split_train_test(
    rows: list[dict],
    *,
    test_frac: float = _DEFAULT_TEST_FRAC,
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Deterministic 80/20 split.

    Uses ``random.Random(seed).shuffle`` on a copy of the list so the input
    is not mutated.  The split point is ``floor(len(rows) * (1 - test_frac))``
    — i.e. anything left over after the train slice goes to test.
    Edge cases:

    - 0 rows → two empty lists.
    - 1 row → one row in train, zero in test (test_frac too small to allocate).
    """
    if not 0.0 < test_frac < 1.0:
        raise ValueError(f"test_frac must be in (0, 1); got {test_frac!r}")
    shuffled = list(rows)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * (1.0 - test_frac))
    return shuffled[:n_train], shuffled[n_train:]


# ---------------------------------------------------------------------------
# Grid search
# ---------------------------------------------------------------------------


def iter_weight_grid(
    base_weights: Mapping[str, float],
    *,
    deltas: tuple[float, ...] = _DEFAULT_DELTAS,
    floor: float = _DEFAULT_FLOOR,
) -> Iterable[Mapping[str, float]]:
    """Yield candidate weight vectors around ``base_weights``.

    For each combination of per-key deltas (cartesian product over the five
    keys), build a perturbed vector, re-normalise so the entries sum to 1.0,
    and skip vectors whose minimum entry is below ``floor``.  ``3**5 = 243``
    raw combinations, ~120 after floor — small enough to brute-force.

    The base vector is always yielded first when ``0.0`` is in ``deltas``
    (because ``itertools.product`` starts at the all-zeros corner with the
    canonical key order).  Yielded mappings are plain dicts; the caller may
    treat them as immutable.
    """
    missing = [k for k in _WEIGHT_KEYS if k not in base_weights]
    if missing:
        raise KeyError(f"base_weights missing keys: {missing!r}")

    seen: set[tuple[float, ...]] = set()
    for combo in product(deltas, repeat=len(_WEIGHT_KEYS)):
        raw = {k: base_weights[k] + d for k, d in zip(_WEIGHT_KEYS, combo)}
        # Reject any pre-normalisation negative — happens only with very
        # large deltas, but defensive.
        if any(v <= 0.0 for v in raw.values()):
            continue
        total = sum(raw.values())
        if total <= 0.0:
            continue
        normed = {k: v / total for k, v in raw.items()}
        if min(normed.values()) < floor:
            continue
        # Dedup: rounding to 6 dp collapses floating-point variants of the
        # same vector into a single yielded candidate.
        key = tuple(round(normed[k], 6) for k in _WEIGHT_KEYS)
        if key in seen:
            continue
        seen.add(key)
        yield normed


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_weights(
    rows: list[dict],
    weights: Mapping[str, float],
) -> float:
    """Top-3 hit rate of ``weights`` against ``rows``.

    For each row, recompute a score per recipe in ``scored_top_5`` as
    ``sum(weights[k] * tags[k])``, sort descending, and check whether
    ``user_picked`` lands in the top 3.  Returns the fraction of rows
    where the pick is in the top-3 predicted set.

    Rows without a usable ``scored_top_5`` (missing key, empty list, or
    missing ``user_picked``) contribute 0 to both numerator and denominator
    — the function returns ``hits / max(considered, 1)`` so an all-empty
    input yields 0.0 instead of raising.
    """
    if not rows:
        return 0.0

    hits = 0
    considered = 0
    for row in rows:
        picked = row.get("user_picked")
        scored = row.get("scored_top_5") or []
        if not picked or not scored:
            continue

        ranked: list[tuple[float, str]] = []
        for entry in scored:
            tags = entry.get("tags") or {}
            full_name = entry.get("full_name", "")
            score = 0.0
            for k in _WEIGHT_KEYS:
                tag_score = tags.get(k)
                if tag_score is None:
                    continue
                score += weights[k] * float(tag_score)
            ranked.append((score, full_name))

        if not ranked:
            continue

        # Sort desc by score.  Stable sort means ties keep their original
        # ``scored_top_5`` order, which is what the funnel emitted.
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        top_names = {name for _, name in ranked[:_TOP_K_FOR_HIT_RATE]}

        considered += 1
        if picked in top_names:
            hits += 1

    if considered == 0:
        return 0.0
    return hits / considered


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------


def suggest_weights(
    input: CalibrationInput,
    *,
    base_weights: Mapping[str, float] | None = None,
    base_weights_version: str | None = None,
) -> CalibrationOutput:
    """Run the full suggestion pipeline against ``input``.

    Steps (matching §4 of the spec):

    1. Split ``input.rows`` into 80% train / 20% test using
       ``random.Random(input.seed)``.
    2. Build the candidate grid around ``base_weights`` (defaulting to the
       latest ``WEIGHTS_HISTORY`` entry).
    3. For each candidate, evaluate top-3 hit rate on the **test** split.
       Among ties for the highest hit rate, prefer the candidate whose
       L1 distance from the base vector is smallest (i.e. prefer "no
       change"); secondary tie-break is the canonical key order.
    4. Compare the suggested hit rate to the base hit rate (both measured
       on the same test split).
    5. Return a :class:`CalibrationOutput`.

    ``base_weights`` and ``base_weights_version`` are mutually optional;
    when both are ``None`` the function falls back to
    ``SCORING_RUBRIC_VERSION``.  Passing ``base_weights`` without a version
    string records the version as ``"custom"`` in the output.
    """
    if base_weights is None and base_weights_version is None:
        base_weights_version = SCORING_RUBRIC_VERSION
        base_weights = WEIGHTS_HISTORY[base_weights_version]
    elif base_weights is None:
        # version supplied → look it up
        base_weights = WEIGHTS_HISTORY[base_weights_version]  # type: ignore[index]
    elif base_weights_version is None:
        base_weights_version = "custom"

    base_weights_dict = _ordered_weight_dict(base_weights)

    train, test = split_train_test(
        input.rows, test_frac=_DEFAULT_TEST_FRAC, seed=input.seed
    )

    base_hit_rate = evaluate_weights(test, base_weights_dict)

    best_weights: Mapping[str, float] = base_weights_dict
    best_hit_rate = base_hit_rate
    best_distance = 0.0

    for candidate in iter_weight_grid(base_weights_dict):
        hit_rate = evaluate_weights(test, candidate)
        distance = sum(
            abs(candidate[k] - base_weights_dict[k]) for k in _WEIGHT_KEYS
        )
        # Prefer higher hit rate; on ties prefer the candidate closer to
        # the base vector (i.e. minimal change).  The base vector itself
        # has distance 0.0 and is always considered first when ``0.0`` is
        # in the deltas, so it wins automatically when no candidate beats it.
        if hit_rate > best_hit_rate or (
            hit_rate == best_hit_rate and distance < best_distance
        ):
            best_weights = candidate
            best_hit_rate = hit_rate
            best_distance = distance

    suggested = _ordered_weight_dict(best_weights)
    return CalibrationOutput(
        n_rows=len(input.rows),
        n_train=len(train),
        n_test=len(test),
        current_weights_version=base_weights_version,  # type: ignore[arg-type]
        current_weights=base_weights_dict,
        current_top3_hit_rate=round(base_hit_rate, 6),
        suggested_weights=suggested,
        suggested_top3_hit_rate=round(best_hit_rate, 6),
        uplift=round(best_hit_rate - base_hit_rate, 6),
        seed=input.seed,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordered_weight_dict(weights: Mapping[str, float]) -> dict[str, float]:
    """Return a plain dict with keys in the canonical ``_WEIGHT_KEYS`` order.

    Round to 6 dp so JSON output is stable across platforms and the L1
    tie-break in :func:`suggest_weights` doesn't see floating-point dust.
    """
    return {k: round(float(weights[k]), 6) for k in _WEIGHT_KEYS}
