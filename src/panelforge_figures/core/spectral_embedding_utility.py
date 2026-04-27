"""Spectral embedding utility (Laplacian-eigenmaps inline shim).

Replaces a `umap-learn` dep with ~50 LOC of scipy/numpy. Used by
intravital_imaging beta-pack recipe C.12
(`state_kinematic_spectral_embedding`).

Algorithm: build a kNN graph on the input feature vectors, weight
each edge by a Gaussian kernel on Euclidean distance, form the
symmetric normalised graph Laplacian, and read the 2nd and 3rd
smallest eigenvectors (the smallest is the trivial constant). The
output is a 2-D embedding that preserves local neighbourhoods of the
input — visually similar to UMAP for dense kinematic-feature
clusters, with no numba / sklearn dependency.

Reference: Belkin & Niyogi (2003) for Laplacian Eigenmaps; Coifman
& Lafon (2006) for the symmetric-normalisation step.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigh
from scipy.spatial.distance import cdist

__all__ = ["embed_2d"]


def embed_2d(
    X: np.ndarray | list[list[float]],
    *,
    n_neighbors: int = 15,
    sigma: float | None = None,
) -> tuple[np.ndarray, dict]:
    """Compute a 2-D Laplacian-eigenmap embedding of X.

    Parameters
    ----------
    X : array-like, shape (n_samples, n_features)
        Input feature matrix. Rows are observations, columns are
        features. Will be standardised (zero-mean, unit-variance per
        column) before graph construction.
    n_neighbors : int
        Number of neighbours per sample in the kNN graph.
    sigma : float, optional
        Gaussian kernel bandwidth. If None, set to the median pairwise
        distance among kNN edges (a robust adaptive choice).

    Returns
    -------
    E : ndarray, shape (n_samples, 2)
        2-D embedding coordinates.
    info : dict
        Diagnostic info: 'eigenvalues' (3 smallest), 'sigma' (used),
        'n_neighbors' (used), 'n_components_solver' (eigenvectors
        actually computed).
    """
    Xa = np.asarray(X, float)
    n = Xa.shape[0]
    if n < 3:
        raise ValueError("Need at least 3 samples for a 2-D embedding.")
    k = int(min(n_neighbors, n - 1))
    # Standardise per column.
    mu = Xa.mean(axis=0)
    sd = Xa.std(axis=0) + 1e-9
    Xs = (Xa - mu) / sd

    # Pairwise distances + kNN selection.
    D = cdist(Xs, Xs)
    np.fill_diagonal(D, np.inf)
    knn_idx = np.argsort(D, axis=1)[:, :k]
    knn_dist = np.take_along_axis(D, knn_idx, axis=1)

    if sigma is None:
        sigma = float(np.median(knn_dist) + 1e-9)

    # Build sparse-ish symmetric weight matrix (densely — n is small
    # for the demos that drive this utility).
    W = np.zeros((n, n))
    for i in range(n):
        for j_pos, j in enumerate(knn_idx[i]):
            w = float(np.exp(-knn_dist[i, j_pos] ** 2 / (2.0 * sigma ** 2)))
            W[i, j] = max(W[i, j], w)
    W = 0.5 * (W + W.T)  # symmetrise (mutual-kNN average)

    # Symmetric normalised Laplacian L = I - D^{-1/2} W D^{-1/2}.
    deg = W.sum(axis=1) + 1e-9
    Dinv_sqrt = 1.0 / np.sqrt(deg)
    L = np.eye(n) - (Dinv_sqrt[:, None] * W * Dinv_sqrt[None, :])
    # Ensure symmetry (numerical safety).
    L = 0.5 * (L + L.T)

    # Smallest 3 eigenvectors; drop the trivial first (constant).
    n_components = min(3, n - 1)
    eigvals, eigvecs = eigh(L, subset_by_index=[0, n_components])
    # Use eigvecs[:, 1:3] as the 2-D embedding.
    E = eigvecs[:, 1:3]
    if E.shape[1] < 2:
        # Pathological tiny-n: pad with zeros so callers always get 2-D.
        pad = np.zeros((n, 2 - E.shape[1]))
        E = np.hstack([E, pad])
    info = {
        "eigenvalues": eigvals[: n_components + 1].tolist(),
        "sigma": sigma,
        "n_neighbors": k,
        "n_components_solver": n_components + 1,
    }
    return E, info
