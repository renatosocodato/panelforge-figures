"""FSC resolution curve — Fourier Shell Correlation with 0.143 criterion line."""

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


class FSCInput(RecipeContract):
    spatial_freq_inv_ang: list[float] = Field(..., description="1/Å spatial frequency")
    fsc_masked: list[float] = Field(...)
    fsc_unmasked: list[float] | None = None
    threshold: float = 0.143
    title: str = "Gold-standard FSC"


def _demo() -> FSCInput:
    freq = np.linspace(0.01, 0.50, 100)
    # Masked FSC falls smoothly through 0.143 at ~0.33 Å^-1 (3 Å).
    fsc_masked = 0.5 * (1 + np.tanh(-(freq - 0.30) * 22))
    fsc_masked = np.clip(fsc_masked, 0, 1)
    # Unmasked drops faster (noise).
    fsc_unmasked = 0.5 * (1 + np.tanh(-(freq - 0.22) * 22))
    fsc_unmasked = np.clip(fsc_unmasked, 0, 1)
    return FSCInput(
        spatial_freq_inv_ang=freq.tolist(),
        fsc_masked=fsc_masked.tolist(),
        fsc_unmasked=fsc_unmasked.tolist(),
    )


_META = RecipeMetadata(
    name="fsc_resolution_curve",
    modality="cryoem_and_structure",
    family=RecipeFamily.diagnostic_curve,
    answers_question="At what spatial frequency does the masked/unmasked FSC cross the 0.143 gold-standard threshold?",
    required_fields=("spatial_freq_inv_ang", "fsc_masked"),
    optional_fields=("fsc_unmasked", "threshold", "title"),
    file_format_hints=("csv", "star"),
    alternatives_in_modality=("angular_distribution_hist",),
)


@register_recipe(metadata=_META, contract=FSCInput, demo_contract=_demo)
def render(contract: FSCInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    freq = np.array(contract.spatial_freq_inv_ang, dtype=float)
    fm = np.array(contract.fsc_masked, dtype=float)

    ax.axhline(contract.threshold, color="#D32F2F", lw=0.7, ls="--",
               zorder=1,
               label=f"FSC = {smart_fmt(contract.threshold)}")
    ax.plot(freq, fm, color=palette[5], lw=1.3, zorder=3, label="masked")

    if contract.fsc_unmasked is not None:
        fu = np.array(contract.fsc_unmasked, dtype=float)
        ax.plot(freq, fu, color=palette[2], lw=1.1, ls="-", zorder=3,
                alpha=0.75, label="unmasked")

    # Resolution at threshold crossing.
    below = np.where(fm < contract.threshold)[0]
    if below.size > 0:
        i = below[0]
        if i > 0:
            # Linear interpolation between freq[i-1] and freq[i].
            f0, f1 = freq[i - 1], freq[i]
            v0, v1 = fm[i - 1], fm[i]
            frac = (contract.threshold - v0) / (v1 - v0) if v1 != v0 else 0.0
            freq_cross = f0 + frac * (f1 - f0)
        else:
            freq_cross = float(freq[i])
        res_ang = 1.0 / max(freq_cross, 1e-6)
        ax.axvline(freq_cross, color="#888888", lw=0.6, ls=":", zorder=2)
        ax.annotate(
            f"resolution = {smart_fmt(float(res_ang))} $\\AA$",
            xy=(freq_cross, 0.55),
            xytext=(6, 0), textcoords="offset points",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
        )

    ax.set_xlabel(r"spatial frequency (1/$\AA$)")
    ax.set_ylabel("FSC")
    ax.set_xlim(0, freq.max())
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
