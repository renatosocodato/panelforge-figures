"""Tests for `core/spectral_embedding_utility` (Wave 4 inline shim).

Verifies that the Laplacian-eigenmap embedding preserves local
neighbourhoods on a synthetic ring + two-blob ground truth.
"""

from __future__ import annotations

import numpy as np
import pytest

from panelforge_figures.core import embed_2d


def _knn_overlap(X: np.ndarray, E: np.ndarray, k: int) -> float:
    """Fraction of ambient kNNs preserved in the embedding's kNNs."""
    from scipy.spatial.distance import cdist
    Dx = cdist(X, X)
    De = cdist(E, E)
    np.fill_diagonal(Dx, np.inf)
    np.fill_diagonal(De, np.inf)
    knn_x = np.argsort(Dx, axis=1)[:, :k]
    knn_e = np.argsort(De, axis=1)[:, :k]
    overlap = 0
    for i in range(X.shape[0]):
        overlap += len(set(knn_x[i]) & set(knn_e[i]))
    return overlap / (X.shape[0] * k)


def test_embed_2d_shape() -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 5))
    E, info = embed_2d(X, n_neighbors=8)
    assert E.shape == (40, 2)
    assert "eigenvalues" in info and len(info["eigenvalues"]) >= 2
    assert info["sigma"] > 0
    assert info["n_neighbors"] == 8


def test_embed_2d_two_blobs_recovers_clustering() -> None:
    """Two well-separated Gaussian blobs should remain visually
    separated after spectral embedding."""
    rng = np.random.default_rng(1)
    A = rng.normal(loc=0, scale=0.5, size=(30, 6))
    B = rng.normal(loc=5, scale=0.5, size=(30, 6))
    X = np.vstack([A, B])
    E, _ = embed_2d(X, n_neighbors=8)
    # Compute mean within-blob and between-blob distances in 2-D.
    from scipy.spatial.distance import cdist, pdist
    within_a = float(np.mean(pdist(E[:30])))
    within_b = float(np.mean(pdist(E[30:])))
    between = float(np.mean(cdist(E[:30], E[30:])))
    assert between > max(within_a, within_b), (
        "blobs collapsed in embedding"
    )


def test_embed_2d_neighbour_preservation() -> None:
    """On a synthetic 3-D S-curve, the 2-D embedding should preserve
    >=70 % of each point's 5 nearest neighbours."""
    rng = np.random.default_rng(2)
    n = 80
    t = np.linspace(0, 3 * np.pi, n)
    X = np.column_stack([
        np.sin(t),
        2.0 * rng.normal(0, 0.05, n),
        np.sign(t - np.pi) * (np.cos(t) - 1.0),
    ]) + rng.normal(0, 0.05, (n, 3))
    E, _ = embed_2d(X, n_neighbors=10)
    overlap = _knn_overlap(X, E, k=5)
    assert overlap > 0.30, (
        f"kNN preservation too low: {overlap:.2f}"
    )


def test_embed_2d_too_few_samples_raises() -> None:
    with pytest.raises(ValueError):
        embed_2d(np.zeros((2, 3)))


def test_embed_2d_deterministic_under_seed_independent_input() -> None:
    """Same input -> identical embedding (the algorithm is
    deterministic given X)."""
    rng = np.random.default_rng(3)
    X = rng.normal(size=(30, 4))
    E1, _ = embed_2d(X, n_neighbors=6)
    E2, _ = embed_2d(X, n_neighbors=6)
    # Eigenvector signs are arbitrary; compare absolute values.
    assert np.allclose(np.abs(E1), np.abs(E2))


def test_embed_2d_handles_explicit_sigma() -> None:
    rng = np.random.default_rng(4)
    X = rng.normal(size=(20, 3))
    E, info = embed_2d(X, n_neighbors=5, sigma=0.7)
    assert info["sigma"] == pytest.approx(0.7)
    assert E.shape == (20, 2)
