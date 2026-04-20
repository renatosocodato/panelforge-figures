"""Stochastic-resonance SNR(σ) signature — non-monotonic peak vs noise.

Scatters the SNR as a function of noise amplitude σ across a sweep,
with a parabolic fit around the peak. The optimal σ* and peak SNR are
annotated.
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


class StochasticResonanceInput(RecipeContract):
    noise_amplitude: list[float] = Field(..., min_length=5)
    snr: list[float] = Field(...)
    snr_sem: list[float] | None = None
    title: str = "Stochastic-resonance signature"


def _demo() -> StochasticResonanceInput:
    rng = np.random.default_rng(601)
    sig = np.linspace(0.05, 2.5, 24)
    # Bell-shaped SNR with peak at σ ~ 0.8.
    peak = 0.85
    snr = 1.5 * np.exp(-((sig - peak) / 0.55) ** 2) + 0.10
    snr_noisy = snr + rng.normal(0, 0.06, sig.size)
    sem = rng.uniform(0.03, 0.08, sig.size)
    return StochasticResonanceInput(
        noise_amplitude=sig.tolist(),
        snr=snr_noisy.tolist(),
        snr_sem=sem.tolist(),
    )


_META = RecipeMetadata(
    name="stochastic_resonance_signature",
    modality="gillespie_stochastic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "As the noise amplitude grows, does the signal-to-noise ratio "
        "show a non-monotonic peak (stochastic resonance)?"
    ),
    required_fields=("noise_amplitude", "snr"),
    optional_fields=("snr_sem", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("noise_power_spectrum",),
)


@register_recipe(
    metadata=_META,
    contract=StochasticResonanceInput,
    demo_contract=_demo,
)
def render(contract: StochasticResonanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    sig = np.asarray(contract.noise_amplitude, float)
    snr = np.asarray(contract.snr, float)
    sem = (np.asarray(contract.snr_sem, float)
           if contract.snr_sem is not None else None)

    data_color = palette.pick("GATE") if "GATE" in palette.semantic else palette[0]

    if sem is not None:
        for xi, yi, ei in zip(sig, snr, sem):
            ax.plot([xi, xi], [yi - ei, yi + ei],
                    color="#555555", lw=0.6, zorder=2)
    ax.scatter(sig, snr, s=30, color=data_color,
               edgecolor="white", linewidth=0.6, zorder=3,
               label="SNR(σ)")

    # Parabolic fit on the top portion for peak estimate.
    try:
        coefs = np.polyfit(sig, snr, 2)
        p = np.poly1d(coefs)
        xs = np.linspace(sig.min(), sig.max(), 240)
        ax.plot(xs, p(xs), color="#111111", lw=1.2, zorder=4,
                label="parabolic fit")
        # Vertex at -b/(2a) if a<0.
        if coefs[0] < 0:
            sigma_star = -coefs[1] / (2 * coefs[0])
        else:
            sigma_star = float(sig[int(np.argmax(snr))])
        peak_snr = float(p(sigma_star))
    except np.linalg.LinAlgError:
        sigma_star = float(sig[int(np.argmax(snr))])
        peak_snr = float(np.max(snr))

    # Optimal σ* vertical.
    ax.axvline(sigma_star, color="#D32F2F", lw=0.8, ls="--", zorder=5,
               label=f"σ* = {smart_fmt(float(sigma_star))}")
    # Peak marker.
    ax.scatter([sigma_star], [peak_snr], s=60, marker="*",
               color="#D32F2F", edgecolor="white", linewidth=0.8,
               zorder=6)

    ax.set_xlabel("noise amplitude σ")
    ax.set_ylabel("SNR")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(sig.min(), sig.max())
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.02, 0.97,
            f"peak SNR = {smart_fmt(peak_snr)} at σ* = {smart_fmt(float(sigma_star))}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=7)
    return ax
