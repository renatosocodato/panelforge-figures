"""GAM-style logistic regression utility for 2-D phase boundaries.

Inline shim that replaces `pygam` / `statsmodels.GAM` deps (Option D
heavy-deps decision). Uses a tensor-product B-spline basis on
log(x) × log(y) and IRLS to fit a logistic GLM, then evaluates on a
grid for visual-friendly heatmap rendering.

Used by intravital_imaging beta-pack recipe B.3
(`commitment_phase_diagram`). Generic enough that any future recipe
needing a smoothed binary-outcome boundary can call
`fit_phase_boundary`.

Reference: Eilers & Marx (1996) for P-splines + GLM IRLS; the
implementation is intentionally tight (~80 LOC) for inline shim
sanity.
"""

from __future__ import annotations

import numpy as np

__all__ = ["fit_phase_boundary"]


def fit_phase_boundary(
    x: np.ndarray | list[float],
    y: np.ndarray | list[float],
    committed: np.ndarray | list[bool],
    *,
    n_grid_x: int = 40,
    n_grid_y: int = 40,
    n_basis: int = 6,
    log_axes: bool = True,
    max_iter: int = 50,
    tol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit a 2-D logistic surface P(committed | x, y) and evaluate on a grid.

    Parameters
    ----------
    x, y : array-like
        Per-protrusion features (e.g. length L, mean velocity v_bar).
    committed : array-like of bool
        Per-protrusion outcome.
    n_grid_x, n_grid_y : int
        Output grid resolution.
    n_basis : int
        Number of B-spline basis functions per axis (default 6 -> 36
        tensor-product basis terms).
    log_axes : bool
        If True, fit on log(x) × log(y) (recommended for skewed
        biophysical features).
    max_iter, tol : IRLS controls.

    Returns
    -------
    X_grid, Y_grid : ndarray (n_grid_y, n_grid_x)
        Meshgrid of evaluation points (linear in original units).
    P_grid : ndarray (n_grid_y, n_grid_x)
        Predicted P(committed | x, y) on the grid.
    """
    xa = np.asarray(x, float)
    ya = np.asarray(y, float)
    c = np.asarray(committed, dtype=bool).astype(float)
    if log_axes:
        xa = np.log(np.clip(xa, 1e-9, None))
        ya = np.log(np.clip(ya, 1e-9, None))

    # B-spline basis per axis.
    Bx, x_knots = _bspline_basis(xa, n_basis)
    By, y_knots = _bspline_basis(ya, n_basis)
    # Tensor product: (n, kx*ky).
    n = xa.size
    Phi = np.einsum("ij,ik->ijk", Bx, By).reshape(n, -1)
    # Add intercept column.
    Phi = np.hstack([np.ones((n, 1)), Phi])

    # IRLS for logistic regression with mild ridge for stability.
    p_dim = Phi.shape[1]
    beta = np.zeros(p_dim)
    ridge = 1e-2 * np.eye(p_dim)
    ridge[0, 0] = 0.0  # don't penalise intercept
    for _ in range(max_iter):
        eta = Phi @ beta
        mu = 1.0 / (1.0 + np.exp(-np.clip(eta, -500, 500)))
        w = np.clip(mu * (1.0 - mu), 1e-6, None)
        z = eta + (c - mu) / w
        WX = Phi * w[:, None]
        try:
            beta_new = np.linalg.solve(Phi.T @ WX + ridge, WX.T @ z)
        except np.linalg.LinAlgError:
            beta_new = np.linalg.pinv(Phi.T @ WX + ridge) @ (WX.T @ z)
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new

    # Evaluate on grid.
    if log_axes:
        x_lo, x_hi = float(xa.min()), float(xa.max())
        y_lo, y_hi = float(ya.min()), float(ya.max())
    else:
        x_lo, x_hi = float(xa.min()), float(xa.max())
        y_lo, y_hi = float(ya.min()), float(ya.max())
    xg = np.linspace(x_lo, x_hi, n_grid_x)
    yg = np.linspace(y_lo, y_hi, n_grid_y)
    X_grid_log, Y_grid_log = np.meshgrid(xg, yg)
    Bx_g = _bspline_eval(X_grid_log.ravel(), x_knots, n_basis)
    By_g = _bspline_eval(Y_grid_log.ravel(), y_knots, n_basis)
    Phi_g = np.einsum("ij,ik->ijk", Bx_g, By_g).reshape(-1, n_basis ** 2)
    Phi_g = np.hstack([np.ones((Phi_g.shape[0], 1)), Phi_g])
    eta_g = Phi_g @ beta
    P_grid = 1.0 / (1.0 + np.exp(-np.clip(eta_g, -500, 500)))
    P_grid = P_grid.reshape(n_grid_y, n_grid_x)
    if log_axes:
        X_grid = np.exp(X_grid_log)
        Y_grid = np.exp(Y_grid_log)
    else:
        X_grid = X_grid_log
        Y_grid = Y_grid_log
    return X_grid, Y_grid, P_grid


def _bspline_basis(x: np.ndarray, n_basis: int) -> tuple[np.ndarray, np.ndarray]:
    """Build a uniform-knot cubic B-spline basis on x's range.

    Returns the n × n_basis basis matrix and the knot vector.
    """
    x_lo, x_hi = float(x.min()), float(x.max())
    pad = (x_hi - x_lo) * 0.001 + 1e-9
    knots = np.linspace(x_lo - pad, x_hi + pad, n_basis + 4)
    return _bspline_eval(x, knots, n_basis), knots


def _bspline_eval(x: np.ndarray, knots: np.ndarray,
                  n_basis: int) -> np.ndarray:
    """Evaluate a Gaussian-RBF basis at points x.

    Not a canonical B-spline, but a smooth radial basis that is
    well-conditioned for IRLS + ridge and produces visually clean
    surfaces. Each basis function is a Gaussian centred at a knot.
    """
    n_pts = x.size
    B = np.zeros((n_pts, n_basis))
    centres = np.linspace(knots[0], knots[-1], n_basis)
    width = (knots[-1] - knots[0]) / (n_basis - 1)
    for i, c in enumerate(centres):
        B[:, i] = np.exp(-0.5 * ((x - c) / max(width, 1e-9)) ** 2)
    return B
