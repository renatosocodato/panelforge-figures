"""PERMANOVA null-distribution utility (permutation-shuffle inline shim).

Replaces a `scikit-bio` dep with ~50 LOC of pure numpy. Used by
cytoskeletal_morphometry_companion beta-pack recipe W4.4
(`permanova_null_distribution`).

Algorithm: compute the observed pseudo-F / R² for a label
partition of a feature matrix X, then build a null distribution
by shuffling the labels `n_perms` times and recomputing R² each
time. The empirical p-value is the fraction of permutations whose
null R² ≥ the observed R².

Reference: Anderson (2001) for PERMANOVA; the implementation is
intentionally tight (~50 LOC) for inline-shim sanity. Distance
matrix uses squared Euclidean by default.
"""

from __future__ import annotations

import numpy as np

__all__ = ["permanova_null_distribution"]


def _r2_from_distance(D: np.ndarray, labels: np.ndarray) -> float:
    """PERMANOVA R² = 1 - SS_within / SS_total on a distance matrix.

    Uses the dispersion identity: SS_total = (1/n) * sum_{i<j} d_ij²
    (over all pairs); SS_within = sum over groups of (1/n_g) *
    sum over pairs in group of d_ij².
    """
    n = D.shape[0]
    if n < 2:
        return 0.0
    # SS_total uses squared distances over all unique pairs.
    iu = np.triu_indices(n, k=1)
    ss_total = float((D[iu] ** 2).sum() / n)
    if ss_total <= 0:
        return 0.0
    ss_within = 0.0
    for lab in np.unique(labels):
        idx = np.where(labels == lab)[0]
        n_g = idx.size
        if n_g < 2:
            continue
        sub_iu = np.triu_indices(n_g, k=1)
        sub_d = D[np.ix_(idx, idx)]
        ss_within += float((sub_d[sub_iu] ** 2).sum() / n_g)
    return float(max(0.0, 1.0 - ss_within / ss_total))


def permanova_null_distribution(
    X: np.ndarray | list[list[float]],
    labels: np.ndarray | list[str],
    *,
    n_perms: int = 999,
    seed: int = 0,
) -> tuple[float, np.ndarray, float]:
    """Estimate the PERMANOVA null distribution by label shuffles.

    Parameters
    ----------
    X : array-like, shape (n_samples, n_features)
        Feature matrix.  Rows are observations.
    labels : array-like, shape (n_samples,)
        Group labels (any hashable type).
    n_perms : int
        Number of permutation shuffles for the null distribution.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    R2_obs : float
        Observed R² for the input label partition.
    R2_null : ndarray, shape (n_perms,)
        Null-distribution R² values (one per permutation).
    p_perm : float
        Empirical p-value: fraction of permutations whose null R²
        is ≥ R2_obs (with the +1 / +1 small-sample correction).
    """
    Xa = np.asarray(X, float)
    labels_arr = np.asarray(labels)
    if Xa.shape[0] != labels_arr.size:
        raise ValueError("X and labels must have matching first dim.")
    n = Xa.shape[0]
    if n < 3:
        raise ValueError("Need at least 3 samples for PERMANOVA.")
    # Compute the squared-Euclidean distance matrix once.
    sq_norms = (Xa ** 2).sum(axis=1)
    D2 = sq_norms[:, None] + sq_norms[None, :] - 2.0 * Xa @ Xa.T
    D2 = np.clip(D2, 0, None)
    D = np.sqrt(D2)

    R2_obs = _r2_from_distance(D, labels_arr)

    rng = np.random.default_rng(seed)
    null_R2 = np.zeros(n_perms)
    perm_labels = labels_arr.copy()
    for k in range(n_perms):
        rng.shuffle(perm_labels)
        null_R2[k] = _r2_from_distance(D, perm_labels)

    # +1 / +1 small-sample correction (Phipson & Smyth 2010).
    p_perm = float((np.sum(null_R2 >= R2_obs) + 1) / (n_perms + 1))
    return float(R2_obs), null_R2, p_perm
