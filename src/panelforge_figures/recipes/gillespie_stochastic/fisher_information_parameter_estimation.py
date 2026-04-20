"""Fisher-information matrix for parameter identifiability.

Plots the K × K Fisher-information matrix on a symmetric log-scaled
colormap with parameter labels on both axes. The condition number
(λ_max / λ_min) and the dominant / poorest-identified eigen-direction
are shown as corner callouts so reviewers can judge identifiability
at a glance.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class FIMInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=2)
    fim: list[list[float]] = Field(
        ..., description="K × K symmetric Fisher-information matrix"
    )
    title: str = "Fisher-information matrix"


def _demo() -> FIMInput:
    rng = np.random.default_rng(251)
    names = ["k_on", "k_off", "γ", "μ", "δ"]
    K = len(names)
    # Random positive-definite FIM with one near-degenerate direction.
    A = rng.normal(0, 1, (K, K))
    B = A @ A.T
    B[0, 1] = B[1, 0] = 0.95 * np.sqrt(B[0, 0] * B[1, 1])
    # Boost diagonal moderately.
    B += 0.5 * np.diag(np.diag(B))
    return FIMInput(
        parameter_names=names,
        fim=B.tolist(),
    )


_META = RecipeMetadata(
    name="fisher_information_parameter_estimation",
    modality="gillespie_stochastic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Which parameters can the data distinguish, and where is "
        "information lost (Fisher-information matrix)?"
    ),
    required_fields=("parameter_names", "fim"),
    optional_fields=("title",),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("rate_vs_control_parameter",),
)


@register_recipe(
    metadata=_META,
    contract=FIMInput,
    demo_contract=_demo,
)
def render(contract: FIMInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    F = np.asarray(contract.fim, float)
    K = F.shape[0]
    names = contract.parameter_names

    cmap = mpl.colormaps["viridis"]
    v_hi = max(abs(F).max(), 1e-9)
    im = ax.imshow(F, cmap=cmap, vmin=0.0, vmax=v_hi, aspect="equal")

    ax.set_xticks(range(K))
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=7.0)
    ax.set_yticks(range(K))
    ax.set_yticklabels(names, fontsize=7.0)

    for i in range(K):
        for j in range(K):
            v = F[i, j]
            if v > v_hi * 0.55:
                ax.text(j, i, smart_fmt(v), ha="center", va="center",
                        fontsize=6.2, color="white")
            else:
                ax.text(j, i, smart_fmt(v), ha="center", va="center",
                        fontsize=6.2, color="#111111",
                        bbox=dict(boxstyle="round,pad=0.10",
                                  fc="white", ec="none", alpha=0.85))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("FIM value", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Eigen-decomposition for condition number + directions.
    try:
        eigvals, eigvecs = np.linalg.eigh(F)
    except np.linalg.LinAlgError:
        eigvals = np.array([1.0])
        eigvecs = np.eye(K)
    eigvals = np.clip(eigvals, 1e-12, None)
    cond = float(eigvals.max() / eigvals.min())
    # Most-identified direction = eigvec with largest eigenvalue.
    dom_idx = int(np.argmax(eigvals))
    weak_idx = int(np.argmin(eigvals))
    dom_dir = eigvecs[:, dom_idx]
    weak_dir = eigvecs[:, weak_idx]

    def dir_str(v: np.ndarray) -> str:
        # Signed-weight string of parameter coefficients (top 2 by abs).
        idx = np.argsort(-np.abs(v))[:2]
        parts = []
        for k in idx:
            sign = "+" if v[k] >= 0 else "-"
            parts.append(f"{sign}{smart_fmt(abs(float(v[k])))}·{names[k]}")
        return " ".join(parts)

    ax.set_title(contract.title, fontsize=9.0, pad=4)

    fig = ax.figure
    fig.text(
        0.5, -0.18,
        f"κ(FIM) = {smart_fmt(cond)}  ·  "
        f"best-ID: {dir_str(dom_dir)}  ·  "
        f"worst-ID: {dir_str(weak_dir)}",
        ha="center", va="top", fontsize=6.4, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
