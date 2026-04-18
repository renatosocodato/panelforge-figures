"""Detect the fast-varying subspace via eigen-decomposition of the Sobol ST covariance."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    callout_box,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class FastSubspaceInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=3)
    sensitivity_matrix: list[list[float]] = Field(
        ..., description="rows = outputs, cols = parameters; ST-like indices"
    )
    top_k: int = 2


def _demo() -> FastSubspaceInput:
    rng = np.random.default_rng(23)
    params = ["k_on", "k_off", "V_max", "Km", "D", "alpha", "beta", "gamma"]
    outputs = 12
    M = np.abs(rng.normal(0.1, 0.2, (outputs, len(params))))
    # Force a dominant 2D subspace spanned by k_on and Km.
    M[:, 0] += np.linspace(0.6, 0.2, outputs)
    M[:, 3] += np.linspace(0.0, 0.4, outputs)
    return FastSubspaceInput(
        parameter_names=params,
        sensitivity_matrix=M.tolist(),
        top_k=2,
    )


_META = RecipeMetadata(
    name="fast_subspace_detection",
    modality="sensitivity_analysis",
    family=RecipeFamily.contour,
    answers_question="Is the output variance driven by a low-dimensional subspace of parameters (active subspace)?",
    required_fields=("parameter_names", "sensitivity_matrix"),
    optional_fields=("top_k",),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("morris_elementary_effects", "parameter_scan_2d_contour"),
)


@register_recipe(metadata=_META, contract=FastSubspaceInput, demo_contract=_demo)
def render(contract: FastSubspaceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    M = np.array(contract.sensitivity_matrix, dtype=float)
    # Outputs-weighted covariance of the parameters.
    cov = M.T @ M / max(M.shape[0], 1)
    evals, evecs = np.linalg.eigh(cov)
    # Descending order.
    evals = evals[::-1]
    evecs = evecs[:, ::-1]
    lam_frac = evals / max(evals.sum(), 1e-12)

    # ── Inset: scree ──────────────────────────────────────────────
    inset = ax.inset_axes([0.62, 0.62, 0.32, 0.32])
    xi = np.arange(1, len(evals) + 1)
    inset.bar(xi, lam_frac, color="#1565C0", alpha=0.9, edgecolor="white", linewidth=0.4)
    inset.plot(xi, np.cumsum(lam_frac), color="#D32F2F", marker="o", ms=3, lw=1.1)
    inset.set_xticks(xi)
    inset.set_xticklabels([str(i) for i in xi], fontsize=5.4)
    inset.set_yticks([0, 0.5, 1])
    inset.set_yticklabels(["0", ".5", "1"], fontsize=5.2)
    inset.tick_params(axis="both", labelsize=5.2)
    inset.set_title("scree", fontsize=6.6, pad=2)
    inset.set_ylim(0, 1.05)

    # ── Main axis: loadings for top_k eigenvectors ────────────────
    k = max(2, min(contract.top_k, evecs.shape[1]))
    loadings = evecs[:, :k]
    names = contract.parameter_names
    # Bar per parameter, grouped by PC.
    width = 0.8 / k
    xpos = np.arange(len(names))
    import matplotlib.cm as mcm
    cmap = mcm.get_cmap(AESTHETIC.continuous_cmap)
    for j in range(k):
        color = cmap(0.2 + 0.7 * j / max(k - 1, 1))
        ax.bar(
            xpos + (j - (k - 1) / 2) * width,
            loadings[:, j],
            width=width,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            label=f"PC{j+1} ({lam_frac[j]*100:.0f}%)",
            alpha=0.9,
        )

    ax.set_xticks(xpos)
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7.0)
    ax.set_ylabel("eigenvector loading")
    ax.axhline(0, color="#555555", lw=0.6)
    ax.set_title(
        f"Active subspace — top {k} PCs explain "
        f"{lam_frac[:k].sum()*100:.0f}% of output variance",
        fontsize=8.4,
        fontweight="bold",
    )
    ax.legend(fontsize=6.8, frameon=False, loc="upper left", ncol=1)

    # Halo-labeled dominant loading per PC.
    for j in range(k):
        i_max = int(np.argmax(np.abs(loadings[:, j])))
        add_halo_label(
            ax,
            xpos[i_max] + (j - (k - 1) / 2) * width,
            loadings[i_max, j] * 1.08,
            f"PC{j+1}:{names[i_max]}",
            fontsize=6.4,
            fontweight="bold",
            color="#222222",
            halo_width=2.4,
            ha="center",
            va="bottom" if loadings[i_max, j] > 0 else "top",
        )

    callout_box(
        ax,
        0.02,
        0.03,
        f"Effective dim. ≈ {smart_fmt(1.0 / (lam_frac**2).sum())}",
        accent=AESTHETIC.annotation_style.callout_accent,
        transform=ax.transAxes,
    )
    return ax
