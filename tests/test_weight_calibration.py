"""Weight-calibration tests (Sprint 3B — v1.13.0).

Covers ``manifest/weight_calibration.py``: the offline cross-validation
pipeline that turns aggregated telemetry into a weight proposal.

Tests are organized into:

* row loading + filtering
* deterministic train/test split
* weight grid (floor + renorm)
* synthetic-data recovery — when rows are generated under a planted
  weight vector, ``suggest_weights`` should recover an emphasis on the
  planted dimension.
* deterministic output under a fixed ``--seed``.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from panelforge_figures.manifest.scoring import (
    SCORING_RUBRIC_VERSION,
    WEIGHTS,
    WEIGHTS_HISTORY,
)
from panelforge_figures.manifest.weight_calibration import (
    CalibrationInput,
    CalibrationOutput,
    evaluate_weights,
    iter_weight_grid,
    load_telemetry_rows,
    split_train_test,
    suggest_weights,
)

# ──────────────────────────────────────────────────────────────────────────
# Synthetic-row helpers
# ──────────────────────────────────────────────────────────────────────────


_WEIGHT_KEYS = ("factorial", "equivalence", "anchor", "dynamics", "dimensionality")


def _synthetic_row(
    picked_idx: int,
    n_recipes: int = 5,
    rng: random.Random = random.Random(1),
) -> dict:
    """Build a fake telemetry row with ``n_recipes`` scored entries.

    The user is recorded as picking the recipe at sorted-index
    ``picked_idx`` (0 = highest-scored).  The other entries become
    ``rejected_higher_scored`` automatically.
    """
    recipes = []
    for i in range(n_recipes):
        recipes.append(
            {
                "full_name": f"r{i}",
                "score": rng.random(),
                "tags": {k: rng.random() for k in _WEIGHT_KEYS},
            }
        )
    recipes.sort(key=lambda r: r["score"], reverse=True)
    picked = recipes[picked_idx]["full_name"]
    rejected = [
        r["full_name"]
        for r in recipes
        if r["score"] > recipes[picked_idx]["score"]
    ]
    return {
        "session_id": "abcd" * 4,
        "timestamp": "2026-01-01T00:00:00Z",
        "panelforge_version": "1.13.0",
        "scoring_rubric_version": SCORING_RUBRIC_VERSION,
        "profile": {"modality": "live_imaging_2d"},
        "scored_top_5": recipes[:5],
        "user_picked": picked,
        "rejected_higher_scored": rejected,
    }


def _planted_row(
    truth_weights: dict[str, float],
    n_recipes: int = 5,
    rng: random.Random = random.Random(1),
) -> dict:
    """Build a row where the user picks the recipe maximizing ``truth_weights``.

    The recipe ``score`` is recorded as the locked-rubric default score
    (random, just to give the row some shape) but ``user_picked`` reflects
    the *planted* preference — i.e. the recipe that would top the funnel
    if we re-scored against ``truth_weights``.
    """
    recipes = []
    for i in range(n_recipes):
        tags = {k: rng.random() for k in _WEIGHT_KEYS}
        # The "score" column carries the *default-weights* score so it
        # mirrors what telemetry would store on a real run.
        score_default = sum(WEIGHTS[k] * tags[k] for k in _WEIGHT_KEYS)
        recipes.append(
            {
                "full_name": f"r{i}",
                "score": score_default,
                "tags": tags,
            }
        )
    # Pick the recipe whose tags maximize the truth-weighted score.
    truth_scored = sorted(
        recipes,
        key=lambda r: sum(truth_weights[k] * r["tags"][k] for k in _WEIGHT_KEYS),
        reverse=True,
    )
    picked = truth_scored[0]["full_name"]
    # Rejected = recipes with higher *default-rubric* score than the pick.
    pick_score = next(r["score"] for r in recipes if r["full_name"] == picked)
    rejected = [r["full_name"] for r in recipes if r["score"] > pick_score]
    # Now sort by default score descending (telemetry shape).
    recipes.sort(key=lambda r: r["score"], reverse=True)
    return {
        "session_id": "abcd" * 4,
        "timestamp": "2026-01-01T00:00:00Z",
        "panelforge_version": "1.13.0",
        "scoring_rubric_version": SCORING_RUBRIC_VERSION,
        "profile": {"modality": "live_imaging_2d"},
        "scored_top_5": recipes[:5],
        "user_picked": picked,
        "rejected_higher_scored": rejected,
    }


# ──────────────────────────────────────────────────────────────────────────
# load_telemetry_rows
# ──────────────────────────────────────────────────────────────────────────


def test_load_filters_unpicked(tmp_path: Path) -> None:
    """Rows without ``user_picked`` are filtered out by ``load_telemetry_rows``."""
    p = tmp_path / "u.jsonl"
    rng = random.Random(0)
    rows = [_synthetic_row(2, rng=rng) for _ in range(5)]
    rows[0]["user_picked"] = None  # poison one
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    out = load_telemetry_rows(p)
    assert len(out) == 4


def test_load_handles_blank_lines(tmp_path: Path) -> None:
    """Blank / whitespace-only JSONL lines are silently skipped."""
    p = tmp_path / "u.jsonl"
    rng = random.Random(0)
    rows = [_synthetic_row(2, rng=rng) for _ in range(3)]
    text = "\n".join(json.dumps(r) for r in rows)
    p.write_text(f"\n{text}\n\n\n")
    out = load_telemetry_rows(p)
    assert len(out) == 3


# ──────────────────────────────────────────────────────────────────────────
# split_train_test
# ──────────────────────────────────────────────────────────────────────────


def test_split_is_deterministic() -> None:
    """``split_train_test(seed=42)`` is byte-stable across two calls."""
    rows = [{"i": i} for i in range(100)]
    a1, b1 = split_train_test(rows, seed=42)
    a2, b2 = split_train_test(rows, seed=42)
    assert a1 == a2
    assert b1 == b2


def test_split_default_is_80_20() -> None:
    """The default holdout split is roughly 80% train / 20% test."""
    rows = [{"i": i} for i in range(100)]
    train, test = split_train_test(rows, seed=42)
    assert len(train) == 80
    assert len(test) == 20
    # Train + test must be a partition of the input.
    train_keys = {r["i"] for r in train}
    test_keys = {r["i"] for r in test}
    assert train_keys.isdisjoint(test_keys)
    assert train_keys | test_keys == set(range(100))


# ──────────────────────────────────────────────────────────────────────────
# iter_weight_grid
# ──────────────────────────────────────────────────────────────────────────


def test_grid_skips_below_floor() -> None:
    """Grid candidates below ``floor`` are dropped after renormalization."""
    # Use the canonical _WEIGHT_KEYS — Build-B's grid is locked to those
    # five names, not arbitrary letters.
    near_floor = {
        "factorial": 0.06,
        "equivalence": 0.06,
        "anchor": 0.06,
        "dynamics": 0.40,
        "dimensionality": 0.42,
    }
    grid = list(iter_weight_grid(near_floor, floor=0.05))
    assert grid, "grid must not be empty for a near-floor input"
    for w in grid:
        assert min(w.values()) >= 0.05
        assert abs(sum(w.values()) - 1.0) < 1e-9


def test_grid_centered_on_locked_weights() -> None:
    """Locked weights must always remain in the grid (the no-perturbation point)."""
    grid = list(iter_weight_grid(dict(WEIGHTS), floor=0.05))
    found = False
    for w in grid:
        if all(abs(w[k] - WEIGHTS[k]) < 1e-9 for k in WEIGHTS):
            found = True
            break
    assert found, "locked-weights vector must be present in grid"


def test_grid_keys_match_input() -> None:
    """Every grid candidate has the same keys as the input weight vector."""
    grid = list(iter_weight_grid(dict(WEIGHTS), floor=0.05))
    for w in grid:
        assert set(w.keys()) == set(WEIGHTS.keys())


# ──────────────────────────────────────────────────────────────────────────
# evaluate_weights
# ──────────────────────────────────────────────────────────────────────────


def test_evaluate_with_truth_weights_recovers_high_hit_rate() -> None:
    """Hit rate against the planted truth vector exceeds 0.9 on synthetic rows.

    Generates 200 rows where the user always picks the max under the
    planted vector, then asks ``evaluate_weights`` to score the planted
    vector against those rows.  The planted vector should land the pick
    in the top-3 of its own ranking on (essentially) every row.
    """
    truth = {
        "factorial": 0.40,
        "equivalence": 0.20,
        "anchor": 0.15,
        "dynamics": 0.15,
        "dimensionality": 0.10,
    }
    rng = random.Random(42)
    rows = [_planted_row(truth, rng=rng) for _ in range(200)]
    # Build-B's signature is evaluate_weights(rows, weights).
    hit_rate = evaluate_weights(rows, truth)
    assert hit_rate > 0.9


def test_evaluate_returns_zero_to_one_value() -> None:
    """``evaluate_weights`` returns a hit rate in [0, 1]."""
    rng = random.Random(0)
    rows = [_synthetic_row(2, rng=rng) for _ in range(50)]
    # Build-B's signature is evaluate_weights(rows, weights).
    rate = evaluate_weights(rows, dict(WEIGHTS))
    assert 0.0 <= rate <= 1.0


# ──────────────────────────────────────────────────────────────────────────
# suggest_weights
# ──────────────────────────────────────────────────────────────────────────


def _planted_rows(truth: dict[str, float], n: int, seed: int) -> list[dict]:
    """Generate ``n`` planted rows under one RNG seed."""
    rng = random.Random(seed)
    return [_planted_row(truth, rng=rng) for _ in range(n)]


def test_suggest_weights_deterministic_under_seed() -> None:
    """Two ``suggest_weights`` runs with the same seed produce identical output."""
    truth = {
        "factorial": 0.40,
        "equivalence": 0.20,
        "anchor": 0.15,
        "dynamics": 0.15,
        "dimensionality": 0.10,
    }
    rows = _planted_rows(truth, n=200, seed=7)

    out_a: CalibrationOutput = suggest_weights(
        CalibrationInput(rows=rows, seed=42)
    )
    out_b: CalibrationOutput = suggest_weights(
        CalibrationInput(rows=rows, seed=42)
    )
    assert out_a.suggested_weights == out_b.suggested_weights
    assert out_a.suggested_top3_hit_rate == out_b.suggested_top3_hit_rate
    assert out_a.current_top3_hit_rate == out_b.current_top3_hit_rate
    assert out_a.n_train == out_b.n_train
    assert out_a.n_test == out_b.n_test


def test_suggest_weights_recovers_factorial_emphasis() -> None:
    """A planted ``factorial=0.40`` truth lifts the proposal above 0.30 (locked).

    Per spec §11: when synthetic rows are generated using factorial=0.40,
    the grid search should return a vector with factorial > 0.30 (i.e.
    moves *towards* the planted vector relative to the locked rubric).
    """
    truth = {
        "factorial": 0.40,
        "equivalence": 0.20,
        "anchor": 0.15,
        "dynamics": 0.15,
        "dimensionality": 0.10,
    }
    rows = _planted_rows(truth, n=500, seed=11)

    out: CalibrationOutput = suggest_weights(
        CalibrationInput(rows=rows, seed=42)
    )
    assert out.suggested_weights["factorial"] > 0.30


def test_suggest_weights_writes_full_metadata() -> None:
    """``CalibrationOutput`` includes counts, hit-rates, and the seed echo."""
    truth = {
        "factorial": 0.32,
        "equivalence": 0.23,
        "anchor": 0.20,
        "dynamics": 0.15,
        "dimensionality": 0.10,
    }
    rows = _planted_rows(truth, n=100, seed=3)

    out = suggest_weights(CalibrationInput(rows=rows, seed=42))

    assert out.n_rows >= 1
    assert out.n_train + out.n_test == out.n_rows
    assert out.current_weights_version == SCORING_RUBRIC_VERSION
    assert set(out.current_weights.keys()) == set(WEIGHTS.keys())
    assert set(out.suggested_weights.keys()) == set(WEIGHTS.keys())
    assert 0.0 <= out.current_top3_hit_rate <= 1.0
    assert 0.0 <= out.suggested_top3_hit_rate <= 1.0
    assert out.seed == 42


def test_weights_history_remains_monotonic() -> None:
    """Acceptance criterion 7: ``WEIGHTS_HISTORY`` is append-only.

    A simple invariant: the current ``SCORING_RUBRIC_VERSION`` must
    appear in the history table; the locked weights returned by
    ``WEIGHTS`` must equal ``WEIGHTS_HISTORY[SCORING_RUBRIC_VERSION]``.
    """
    assert SCORING_RUBRIC_VERSION in WEIGHTS_HISTORY
    locked = WEIGHTS_HISTORY[SCORING_RUBRIC_VERSION]
    assert dict(locked) == dict(WEIGHTS)
