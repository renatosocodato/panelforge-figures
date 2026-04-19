"""Partial residuals vs a single continuous predictor.

Partial residuals (Cook & Weisberg) for predictor x_k are
    e_ij + β̂_k · x_ij
which isolates the *specific* effect of x_k after removing the other
terms. Overlayed: the fitted partial effect (β̂_k · x), a per-group LOESS
smoother, and a guideline for mis-specification (bowed LOESS → nonlinear
term needed).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PartialResidualsInput(RecipeContract):
    predictor: list[float] = Field(...)
    partial_residual: list[float] = Field(...)
    group: list[str] | None = None
    beta_k: float = Field(
        default=1.0,
        description="fitted coefficient for the predictor — the line slope",
    )
    predictor_label: str = "predictor"
    outcome_label: str = "partial residual"
    title: str = "Partial residuals vs predictor"


def _demo() -> PartialResidualsInput:
    rng = np.random.default_rng(507)
    n = 200
    x = rng.uniform(-2.5, 2.5, n)
    groups = rng.choice(["control", "mutant", "rescue"], n,
                        p=[0.38, 0.34, 0.28])
    # True effect has a mild quadratic curvature — exposes mis-specification.
    truth = 0.58 * x + 0.12 * x**2
    noise = rng.normal(0, 0.35, n)
    # Group-level offsets absorbed by other terms; small leftover.
    group_off = np.where(groups == "mutant", 0.05,
                         np.where(groups == "rescue", -0.04, 0.0))
    resid = truth + noise + group_off
    return PartialResidualsInput(
        predictor=x.tolist(),
        partial_residual=resid.tolist(),
        group=groups.tolist(),
        beta_k=0.58,
        predictor_label="age_z",
        outcome_label="partial residual (Δ outcome)",
    )


def _loess_1d(x: np.ndarray, y: np.ndarray, frac: float = 0.35,
              grid_n: int = 80) -> tuple[np.ndarray, np.ndarray]:
    """Tricube-weighted local linear smoother (lightweight LOESS, no SciPy)."""
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    n = xs.size
    k = max(int(np.ceil(frac * n)), 5)
    xg = np.linspace(xs.min(), xs.max(), grid_n)
    yg = np.zeros_like(xg)
    for i, xi in enumerate(xg):
        d = np.abs(xs - xi)
        idx = np.argsort(d)[:k]
        dmax = d[idx].max() + 1e-9
        w = (1 - (d[idx] / dmax) ** 3) ** 3
        X = np.stack([np.ones(k), xs[idx]]).T
        W = np.diag(w)
        try:
            beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ ys[idx])
            yg[i] = beta[0] + beta[1] * xi
        except np.linalg.LinAlgError:
            yg[i] = ys[idx].mean()
    return xg, yg


_META = RecipeMetadata(
    name="partial_residuals_vs_predictor",
    modality="mixed_effects_models",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "For a given continuous predictor, what is the predictor-specific "
        "partial-residual pattern, and does the fitted term capture it?"
    ),
    required_fields=("predictor", "partial_residual"),
    optional_fields=("group", "beta_k", "predictor_label", "outcome_label", "title"),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=(
        "mixed_model_residual_diagnostic",
        "marginal_effects_ribbon",
    ),
)


@register_recipe(
    metadata=_META,
    contract=PartialResidualsInput,
    demo_contract=_demo,
)
def render(contract: PartialResidualsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.predictor, float)
    r = np.asarray(contract.partial_residual, float)
    groups = (np.asarray(contract.group)
              if contract.group is not None
              else np.array(["all"] * x.size))
    uniques = list(dict.fromkeys(groups.tolist()))

    # Zero reference.
    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=1,
               label="_nolegend_")

    # Scatter per group.
    for i, g in enumerate(uniques):
        m = groups == g
        color = palette[i % len(palette.colors)]
        ax.scatter(x[m], r[m], s=11, color=color, alpha=0.55,
                   edgecolor="white", linewidth=0.25, zorder=3,
                   label=f"{g} (n={int(m.sum())})")

    # Per-group LOESS overlays.
    for i, g in enumerate(uniques):
        m = groups == g
        if m.sum() >= 10:
            color = palette[i % len(palette.colors)]
            xg, yg = _loess_1d(x[m], r[m], frac=0.45)
            ax.plot(xg, yg, color=color, lw=1.1, alpha=0.9, zorder=4)

    # Fitted partial effect line (β̂_k · x), anchored at the data mean.
    xs = np.linspace(x.min(), x.max(), 80)
    ax.plot(xs, contract.beta_k * (xs - x.mean()),
            color="#111111", lw=1.3, linestyle="--", zorder=5,
            label=f"β̂·x (slope={smart_fmt(contract.beta_k)})")

    ax.set_xlabel(contract.predictor_label)
    ax.set_ylabel(contract.outcome_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
