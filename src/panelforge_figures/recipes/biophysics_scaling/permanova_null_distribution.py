"""PERMANOVA null distribution — histogram of permutation-shuffle
null R² values with observed R² as a vertical reference and
p-value tail-shaded for visual percentile read-off.

Diagnostic-curve family: >=2 curves + >=1 legend.
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
from ...core import (
    permanova_null_distribution as compute_permanova_null,
)
from ._aesthetic import AESTHETIC


class PermanovaNullInput(RecipeContract):
    null_R2: list[float] | None = Field(
        default=None,
        description="If None, will be computed from X + labels via "
        "core.permanova_null_distribution.",
    )
    observed_R2: float | None = None
    p_perm: float | None = None
    X: list[list[float]] | None = None
    labels: list[str] | None = None
    n_perms: int = 999
    title: str = "PERMANOVA null distribution"


def _demo() -> PermanovaNullInput:
    rng = np.random.default_rng(704)
    # Two well-separated blobs so observed R² is large.
    A = rng.normal(loc=0, scale=0.5, size=(30, 6))
    B = rng.normal(loc=2.0, scale=0.5, size=(30, 6))
    X = np.vstack([A, B])
    labels = np.array(["WT"] * 30 + ["LI"] * 30)
    R2_obs, null, p = compute_permanova_null(X, labels, n_perms=499)
    return PermanovaNullInput(
        null_R2=null.tolist(),
        observed_R2=float(R2_obs),
        p_perm=float(p),
        n_perms=499,
    )


_META = RecipeMetadata(
    name="permanova_null_distribution",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Where does the observed PERMANOVA R² sit relative to the "
        "permutation-shuffle null distribution, and what is the "
        "empirical p-value?"
    ),
    required_fields=("null_R2", "observed_R2"),
    optional_fields=("p_perm", "X", "labels", "n_perms", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("scale_stratified_permanova_r2",),
)


@register_recipe(
    metadata=_META,
    contract=PermanovaNullInput,
    demo_contract=_demo,
)
def render(contract: PermanovaNullInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Resolve null distribution + observed R² (compute if missing).
    null = contract.null_R2
    R2_obs = contract.observed_R2
    p_perm = contract.p_perm
    if null is None or R2_obs is None:
        if contract.X is None or contract.labels is None:
            raise ValueError("Must supply null_R2 + observed_R2 OR X + labels.")
        R2_obs, null_arr, p_perm = compute_permanova_null(
            contract.X, contract.labels, n_perms=contract.n_perms,
        )
        null = null_arr.tolist()
    null_arr = np.asarray(null, float)

    # Histogram of null distribution.
    n_bins = max(20, len(null_arr) // 30)
    counts, edges = np.histogram(null_arr, bins=n_bins, density=True)
    bin_mids = 0.5 * (edges[:-1] + edges[1:])
    ax.fill_between(bin_mids, 0, counts,
                    color="#37474F", alpha=0.18, zorder=2,
                    label="null distribution")
    ax.plot(bin_mids, counts, color="#37474F", lw=1.0,
            zorder=3, label=None)

    # Tail shading for the p-value (R² >= observed).
    tail_mask = bin_mids >= R2_obs
    if tail_mask.any():
        ax.fill_between(bin_mids[tail_mask], 0, counts[tail_mask],
                        color="#EF5350", alpha=0.55, zorder=4,
                        label="tail (R² >= observed)")

    # Observed R² vertical reference.
    ax.axvline(R2_obs, color="#EF5350", lw=1.4, ls="--", zorder=5,
               label=f"observed R² = {smart_fmt(R2_obs)}")

    ax.set_xlabel("R² (PERMANOVA)")
    ax.set_ylabel("density")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)

    p_str = smart_fmt(p_perm) if p_perm is not None else "?"
    ax.set_title(
        f"{contract.title}  ·  observed R² = "
        f"{smart_fmt(R2_obs)}  ·  p_perm = {p_str}  ·  "
        f"{len(null_arr)} perms",
        fontsize=8.2, pad=4,
    )
    return ax
