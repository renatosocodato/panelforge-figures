"""FAST (Fourier Amplitude Sensitivity Test) power spectrum.

Plots the power spectrum of a scalar model output under harmonic
parameter forcing. Each parameter is assigned a fundamental frequency
ωᵢ; the variance at ωᵢ and its harmonics is the first-order FAST index,
while the residual variance after stripping all assigned fundamentals
is the "interaction + noise" floor shown as a dashed reference.

Visually distinct from `sobol_first_total_pair` (bars, variance-based)
and `morris_elementary_effects` (μ*/σ scatter, OAT screening).
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


class FASTSpectrumInput(RecipeContract):
    frequencies: list[float] = Field(..., description="ω grid")
    power: list[float] = Field(..., description="|Ŷ(ω)|² at each ω")
    parameter_names: list[str] = Field(..., min_length=2)
    parameter_freqs: list[float] = Field(
        ..., description="fundamental frequency assigned to each parameter"
    )
    n_harmonics: int = 4
    noise_floor: float | None = None
    output_label: str = "scalar output"
    title: str = "FAST sensitivity spectrum"


def _demo() -> FASTSpectrumInput:
    rng = np.random.default_rng(13)
    # Frequencies ω_i for each parameter (unrelated integers per FAST design).
    names = ["k_on", "k_off", "V_max", "Km", "alpha"]
    base = [11.0, 17.0, 23.0, 29.0, 37.0]
    heights = [0.36, 0.08, 0.22, 0.04, 0.12]
    n_harm = 4
    omega = np.linspace(0.5, 160.0, 2400)
    power = np.full_like(omega, 0.004)
    power += rng.gamma(1.2, 0.004, size=omega.size)
    for f, h in zip(base, heights):
        for k in range(1, n_harm + 1):
            sigma = 0.32
            power += h * (1 / (k ** 1.4)) * np.exp(-((omega - k * f) ** 2) / (2 * sigma ** 2))
    return FASTSpectrumInput(
        frequencies=omega.tolist(),
        power=power.tolist(),
        parameter_names=names,
        parameter_freqs=base,
        n_harmonics=n_harm,
        noise_floor=0.02,
        output_label="steady-state activity",
    )


_META = RecipeMetadata(
    name="fast_sensitivity_spectrum",
    modality="sensitivity_analysis",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "In the FAST decomposition, what does the frequency spectrum of "
        "the output reveal about each parameter's contribution?"
    ),
    required_fields=("frequencies", "power", "parameter_names", "parameter_freqs"),
    optional_fields=("n_harmonics", "noise_floor", "output_label", "title"),
    file_format_hints=("parquet", "npz"),
    n_points_typical="5-15 parameters, ~1-10 k freqs",
    alternatives_in_modality=("sobol_first_total_pair", "morris_elementary_effects"),
)


@register_recipe(
    metadata=_META,
    contract=FASTSpectrumInput,
    demo_contract=_demo,
)
def render(contract: FASTSpectrumInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    omega = np.asarray(contract.frequencies, float)
    power = np.asarray(contract.power, float)

    ax.plot(omega, power, color="#333333", lw=0.9, zorder=3,
            label="|Ŷ(ω)|²")

    # Stem the fundamentals + harmonics per parameter, colour-coded.
    n_harm = max(contract.n_harmonics, 1)
    tops = []
    for i, (name, f0) in enumerate(
        zip(contract.parameter_names, contract.parameter_freqs)
    ):
        color = palette[i % len(palette.colors)]
        # Fundamental.
        idx = int(np.argmin(np.abs(omega - f0)))
        peak = float(power[idx])
        tops.append((name, f0, peak))
        ax.plot([f0, f0], [0, peak], color=color, lw=1.3, zorder=4)
        ax.scatter([f0], [peak], s=28, color=color,
                   edgecolor="white", linewidth=0.7, zorder=5)
        # Harmonics (shorter stems).
        for k in range(2, n_harm + 1):
            if k * f0 > omega.max():
                break
            idx_k = int(np.argmin(np.abs(omega - k * f0)))
            pk = float(power[idx_k])
            ax.plot([k * f0, k * f0], [0, pk], color=color,
                    lw=0.7, alpha=0.65, zorder=3)
        # Name label above the fundamental.
        ax.text(f0, peak, f" {name}", ha="left", va="bottom",
                fontsize=6.6, color=color, zorder=6)

    # Noise / interaction floor.
    if contract.noise_floor is not None:
        ax.axhline(contract.noise_floor, color="#888888", lw=0.8,
                   ls="--", zorder=2, label="noise / interaction floor")

    ax.set_xlabel("ω (arb. units)")
    ax.set_ylabel("|Ŷ(ω)|²")
    tops.sort(key=lambda t: -t[2])
    top_line = ", ".join(
        f"{n}(ω={smart_fmt(f)})" for n, f, _ in tops[:3]
    )
    ax.set_title(
        f"{contract.title} · {contract.output_label}",
        fontsize=9.0, pad=4,
    )
    # Top-drivers pill anchored to upper-right ABOVE the plot in figure
    # space so it never collides with the legend or spectrum peaks.
    fig = ax.figure
    fig.text(
        0.5, -0.16, f"top: {top_line}",
        ha="center", va="top", fontsize=6.8, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.24", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    ax.set_xlim(0, omega.max())
    ax.set_ylim(0, max(power.max() * 1.15, 0.01))
    ax.legend(fontsize=6.6, frameon=False, loc="center right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
