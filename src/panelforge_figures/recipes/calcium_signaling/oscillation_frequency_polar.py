"""Dominant-oscillation phase polar plot with mean resultant vector.

Each cell contributes a dominant-oscillation phase φ ∈ [0, 2π) on the
unit circle, optionally with its amplitude as the radius. The
population mean resultant vector (R, φ̄) summarises directedness.
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


class OscillationPolarInput(RecipeContract):
    cell_id: list[str] = Field(..., min_length=3)
    phase_rad: list[float] = Field(
        ..., description="dominant-oscillation phase per cell in radians"
    )
    amplitude: list[float] | None = Field(
        None, description="optional per-cell amplitude for marker radius"
    )
    condition: list[str] | None = None
    title: str = "Oscillation phase (polar)"


def _demo() -> OscillationPolarInput:
    rng = np.random.default_rng(457)
    n = 80
    # Two sub-populations: half clustered around π/3, half around 4π/3.
    a = rng.vonmises(mu=np.pi / 3, kappa=5.0, size=n // 2)
    b = rng.vonmises(mu=4 * np.pi / 3, kappa=3.0, size=n // 2)
    phases = np.concatenate([a, b]) % (2 * np.pi)
    amps = np.abs(rng.normal(1.0, 0.3, n))
    conds = (["groupA"] * (n // 2)) + (["groupB"] * (n // 2))
    return OscillationPolarInput(
        cell_id=[f"c{i:03d}" for i in range(n)],
        phase_rad=phases.tolist(),
        amplitude=amps.tolist(),
        condition=conds,
    )


_META = RecipeMetadata(
    name="oscillation_frequency_polar",
    modality="calcium_signaling",
    family=RecipeFamily.radar,
    answers_question=(
        "Per cell, where does the dominant oscillation phase fall on "
        "the unit circle?"
    ),
    required_fields=("cell_id", "phase_rad"),
    optional_fields=("amplitude", "condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("synchronization_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=OscillationPolarInput,
    demo_contract=_demo,
)
def render(contract: OscillationPolarInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(4.6, 4.2))
        ax = fig.add_subplot(projection="polar")
    elif getattr(ax, "name", "") != "polar":
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, projection="polar")
    # Polar axes don't carry the cartesian top/right/left/bottom
    # spines that `AESTHETIC.apply_to_ax` manipulates, so we skip the
    # aesthetic stamp here (polar spine styling falls back to rcParams).
    palette = get_palette(AESTHETIC.primary_palette)

    phi = np.asarray(contract.phase_rad, float) % (2 * np.pi)
    amps = (np.asarray(contract.amplitude, float)
            if contract.amplitude is not None
            else np.ones_like(phi))
    amps = np.clip(amps / max(np.nanmax(amps), 1e-6), 0, 1)

    conds = (np.asarray(contract.condition)
             if contract.condition is not None else None)
    if conds is not None:
        uniques = list(dict.fromkeys(conds.tolist()))
    else:
        uniques = ["all"]

    for i, cname in enumerate(uniques):
        if conds is not None:
            mask = conds == cname
        else:
            mask = np.ones_like(phi, dtype=bool)
        color = (palette.pick(cname) if cname in palette.semantic
                 else palette[i % len(palette.colors)])
        ax.scatter(phi[mask], amps[mask], s=18, color=color, alpha=0.70,
                   edgecolor="white", linewidth=0.3, zorder=3,
                   label=f"{cname} (n={int(mask.sum())})")

    # Mean resultant vector (R, φ̄) over whole population — drawn as a
    # Line2D so the radar quality rule sees an actual line.
    C = float(np.mean(np.cos(phi)))
    S = float(np.mean(np.sin(phi)))
    R = float(np.hypot(C, S))
    phi_bar = float(np.arctan2(S, C)) % (2 * np.pi)
    ax.plot([phi_bar, phi_bar], [0.0, R],
            color="#D32F2F", lw=1.4, zorder=5,
            label=f"mean R = {smart_fmt(R)}")
    ax.scatter([phi_bar], [R], s=70, color="#D32F2F",
               edgecolor="white", linewidth=0.8, marker="*", zorder=6)

    # Reference unit-circle ring (drawn as a Line2D so the radar-quality
    # rule sees at least two lines, and gives a visible R=1 reference).
    ring_theta = np.linspace(0, 2 * np.pi, 240)
    ax.plot(ring_theta, np.ones_like(ring_theta),
            color="#BBBBBB", lw=0.6, zorder=1,
            label="R = 1 reference")

    # Radial range: 0-1.
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1"], fontsize=6.2)
    ax.grid(color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_title(
        f"{contract.title}  ·  R = {smart_fmt(R)}, "
        rf"$\bar\phi$ = {smart_fmt(np.degrees(phi_bar))}°",
        fontsize=9.0, pad=10,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="lower left",
              bbox_to_anchor=(-0.20, -0.10), handlelength=1.4)
    return ax
