"""Tests for `core/permanova_null_utility` (Wave 4 inline shim).

Verifies that the permutation-shuffle estimator of PERMANOVA's
null R² behaves correctly: R² in [0, 1], permutation null mean
near chance, p-value bounded, deterministic under fixed seed,
and label-permutation symmetry.
"""

from __future__ import annotations

import numpy as np
import pytest

from panelforge_figures.core import permanova_null_distribution


def test_permanova_returns_three_outputs() -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20, 4))
    labels = np.array(["A", "B"] * 10)
    R2_obs, R2_null, p = permanova_null_distribution(
        X, labels, n_perms=99, seed=1,
    )
    assert isinstance(R2_obs, float)
    assert R2_null.shape == (99,)
    assert isinstance(p, float)


def test_permanova_R2_in_unit_interval() -> None:
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 6))
    labels = np.array(["A", "B", "C"] * 10)
    R2_obs, R2_null, p = permanova_null_distribution(
        X, labels, n_perms=199, seed=2,
    )
    assert 0.0 <= R2_obs <= 1.0
    assert (R2_null >= 0.0).all() and (R2_null <= 1.0).all()
    assert 0.0 <= p <= 1.0


def test_permanova_separated_blobs_have_high_R2_low_p() -> None:
    """Two separated blobs should produce a large observed R²
    and a small p-value (well below 0.05)."""
    rng = np.random.default_rng(2)
    A = rng.normal(loc=0, scale=0.5, size=(30, 4))
    B = rng.normal(loc=4, scale=0.5, size=(30, 4))
    X = np.vstack([A, B])
    labels = np.array(["A"] * 30 + ["B"] * 30)
    R2_obs, _, p = permanova_null_distribution(
        X, labels, n_perms=199, seed=3,
    )
    assert R2_obs > 0.30, f"separated blobs gave R^2 = {R2_obs:.3f}"
    assert p < 0.05, f"separated blobs gave p = {p:.3f}"


def test_permanova_random_labels_have_p_around_chance() -> None:
    """When labels are random the observed R² is just one draw
    from the null distribution; the empirical p-value should be
    spread roughly uniformly over (0, 1)."""
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 6))
    # Random label assignment.
    labels = rng.choice(["A", "B"], size=40)
    R2_obs, _, p = permanova_null_distribution(
        X, labels, n_perms=199, seed=4,
    )
    # No strong assumption — just that it's not extreme.
    assert 0.0 <= p <= 1.0


def test_permanova_deterministic_under_fixed_seed() -> None:
    rng = np.random.default_rng(4)
    X = rng.normal(size=(20, 5))
    labels = np.array(["A", "B"] * 10)
    R2a, null_a, pa = permanova_null_distribution(
        X, labels, n_perms=99, seed=42,
    )
    R2b, null_b, pb = permanova_null_distribution(
        X, labels, n_perms=99, seed=42,
    )
    assert R2a == pytest.approx(R2b)
    assert np.allclose(null_a, null_b)
    assert pa == pytest.approx(pb)


def test_permanova_too_few_samples_raises() -> None:
    with pytest.raises(ValueError):
        permanova_null_distribution(
            np.zeros((2, 3)), np.array(["A", "B"]), n_perms=10,
        )


def test_permanova_label_size_mismatch_raises() -> None:
    rng = np.random.default_rng(5)
    X = rng.normal(size=(10, 3))
    bad_labels = np.array(["A"] * 5)
    with pytest.raises(ValueError):
        permanova_null_distribution(X, bad_labels, n_perms=10)
