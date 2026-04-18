"""Noise power spectrum — PSD of a stochastic time-series with 1/f / Lorentzian fits."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import signal

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PSDInput(RecipeContract):
    t: list[float] = Field(...)
    signal_trace: list[float] = Field(...)
    sampling_rate: float | None = None
    title: str = "Noise power spectrum"


def _demo() -> PSDInput:
    rng = np.random.default_rng(131)
    fs = 100.0
    t = np.arange(0, 40, 1 / fs)
    # Ornstein-Uhlenbeck-like process with correlation time tau.
    tau = 0.8
    dt = 1 / fs
    x = np.zeros(t.size)
    for i in range(1, t.size):
        x[i] = x[i - 1] + (-x[i - 1] / tau) * dt + np.sqrt(2 * dt / tau) * rng.normal()
    return PSDInput(
        t=t.tolist(),
        signal_trace=x.tolist(),
        sampling_rate=fs,
    )


_META = RecipeMetadata(
    name="noise_power_spectrum",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What is the frequency structure of the noise — white, Lorentzian, or 1/f?",
    required_fields=("t", "signal_trace"),
    optional_fields=("sampling_rate", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("waiting_time_ecdf_fitted",),
)


@register_recipe(metadata=_META, contract=PSDInput, demo_contract=_demo)
def render(contract: PSDInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.signal_trace, dtype=float)
    t = np.array(contract.t, dtype=float)
    fs = contract.sampling_rate or 1.0 / np.median(np.diff(t))

    freqs, psd = signal.welch(x, fs=fs, nperseg=min(512, x.size // 4))

    ax.loglog(freqs[1:], psd[1:], color=palette.pick("HOME"),
              lw=1.0, zorder=3, label="Welch PSD")

    # Lorentzian fit: psd(f) = A / (1 + (f/fc)^2). Estimate fc as freq at half-max.
    half = psd[1:].max() / 2
    idx = np.argmax(psd[1:] <= half)
    fc = freqs[1 + idx] if idx > 0 else freqs[1]
    A = psd[1]
    ax.loglog(freqs[1:], A / (1 + (freqs[1:] / fc) ** 2),
              color="#D32F2F", lw=1.0, ls="--", zorder=4,
              label=f"Lorentzian (fc={smart_fmt(float(fc))} Hz)")

    # 1/f reference line for visual comparison.
    ax.loglog(freqs[1:], A * freqs[1] / freqs[1:],
              color="#888888", lw=0.7, ls=":", zorder=2, label="1/f reference")

    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("power")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left",
              handlelength=1.8)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Corner-frequency callout.
    ax.text(0.99, 0.97,
            f"fc = {smart_fmt(float(fc))} Hz\n"
            rf"τ ≈ 1/(2πfc) = {smart_fmt(1 / (2 * np.pi * fc))} s",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
