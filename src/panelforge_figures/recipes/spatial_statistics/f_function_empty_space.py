"""F function — empty-space distance distribution F(r) with CSR
reference F_CSR(r) = 1 − exp(−λπr²) and Monte-Carlo envelope.

F probes empty-space from random test points to the nearest observed
point — distinct from G (observed-to-observed NN distance).
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


class FFunctionInput(RecipeContract):
    r_um: list[float] = Field(..., min_length=5)
    f_observed: list[float] = Field(..., description="observed F(r)")
    csr_envelope_lo: list[float] = Field(...)
    csr_envelope_hi: list[float] = Field(...)
    intensity_lambda: float = Field(..., description="λ = N / A, points per μm²")
    title: str = "F function — empty space"


def _demo() -> FFunctionInput:
    rng = np.random.default_rng(1117)
    r = np.linspace(0, 30, 60)
    lam = 0.05
    # Clustered pattern: empty-space is larger than CSR (F below theoretical).
    f_csr = 1 - np.exp(-lam * np.pi * r ** 2)
    f_obs = f_csr * 0.7 + rng.normal(0, 0.01, r.size)
    f_obs = np.clip(f_obs, 0, 1)
    envelope_w = np.clip(0.03 + 0.002 * r, 0, None)
    return FFunctionInput(
        r_um=r.tolist(),
        f_observed=f_obs.tolist(),
        csr_envelope_lo=np.clip(f_csr - envelope_w, 0, 1).tolist(),
        csr_envelope_hi=np.clip(f_csr + envelope_w, 0, 1).tolist(),
        intensity_lambda=lam,
    )


_META = RecipeMetadata(
    name="f_function_empty_space",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Is there more empty space in the point pattern (regions far "
        "from any observed point) than CSR predicts?"
    ),
    required_fields=(
        "r_um", "f_observed", "csr_envelope_lo", "csr_envelope_hi",
        "intensity_lambda",
    ),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("nearest_neighbor_distance_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=FFunctionInput,
    demo_contract=_demo,
)
def render(contract: FFunctionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.asarray(contract.r_um, float)
    f_obs = np.asarray(contract.f_observed, float)
    lo = np.asarray(contract.csr_envelope_lo, float)
    hi = np.asarray(contract.csr_envelope_hi, float)
    lam = float(contract.intensity_lambda)

    # CSR analytical reference.
    f_csr = 1 - np.exp(-lam * np.pi * r ** 2)

    ax.fill_between(r, lo, hi, color="#BBBBBB", alpha=0.35,
                    linewidth=0, zorder=1, label="CSR envelope")
    ax.plot(r, f_csr, color="#666666", lw=0.8, ls="--", zorder=2,
            label=r"CSR: $1 - e^{-\lambda\pi r^2}$")
    ax.plot(r, f_obs, color=palette[1], lw=1.3, zorder=4,
            label="observed")

    # Interpretation flags.
    if np.nanmean(f_obs - f_csr) < -0.03:
        interp = "clustered (empty space > CSR)"
        interp_color = "#C62828"
    elif np.nanmean(f_obs - f_csr) > 0.03:
        interp = "dispersed (empty space < CSR)"
        interp_color = "#2E7D32"
    else:
        interp = "compatible with CSR"
        interp_color = "#555555"

    # Median deviation callout.
    med_dev = float(np.median(f_obs - f_csr))
    ax.text(0.02, 0.97,
            f"λ = {smart_fmt(lam)} pts/μm²\n"
            f"median (F_obs - F_CSR) = {smart_fmt(med_dev)}\n"
            f"→ {interp}".replace("→", "->"),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color=interp_color,
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.set_xlabel(r"r (μm)")
    ax.set_ylabel(r"F(r)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
