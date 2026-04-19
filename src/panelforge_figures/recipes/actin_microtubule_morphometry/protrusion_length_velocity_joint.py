"""Protrusion length × velocity joint scatter — kinematic phase-plane."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ProtrusionJointInput(RecipeContract):
    length_um: list[float] = Field(...)
    velocity_um_per_s: list[float] = Field(...)
    state: list[str] | None = None
    title: str = "Protrusion length vs velocity"


def _demo() -> ProtrusionJointInput:
    rng = np.random.default_rng(493)
    n = 450
    # Homeostatic: short, slow.
    hg_len = rng.lognormal(0.8, 0.4, 200)
    hg_vel = rng.normal(0.05, 0.05, 200)
    # Activated: long, fast (with correlation).
    act_len = rng.lognormal(1.6, 0.3, 180)
    act_vel = 0.04 * act_len + rng.normal(0.1, 0.06, 180)
    # Stalled: long, slow.
    st_len = rng.lognormal(1.2, 0.35, 70)
    st_vel = rng.normal(0.02, 0.03, 70)
    L = np.concatenate([hg_len, act_len, st_len])
    V = np.concatenate([hg_vel, act_vel, st_vel])
    state = (["homeostatic"] * len(hg_len) + ["activated"] * len(act_len)
             + ["stalled"] * len(st_len))
    # Ensure we have exactly n points (may have small off-by-one).
    L = L[:n] if L.size >= n else np.concatenate([L, np.full(n - L.size, L.mean())])
    V = V[:n] if V.size >= n else np.concatenate([V, np.full(n - V.size, V.mean())])
    state = (state + ["homeostatic"] * n)[:n]
    return ProtrusionJointInput(
        length_um=L.tolist(),
        velocity_um_per_s=V.tolist(),
        state=state,
    )


_META = RecipeMetadata(
    name="protrusion_length_velocity_joint",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question="Do protrusion length and instantaneous velocity cluster into kinematic regimes, and how do those regimes relate to cell state?",
    required_fields=("length_um", "velocity_um_per_s"),
    optional_fields=("state", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("persistence_length_fit",),
)


@register_recipe(metadata=_META, contract=ProtrusionJointInput, demo_contract=_demo)
def render(contract: ProtrusionJointInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette("microglia_states")

    L = np.array(contract.length_um, dtype=float)
    V = np.array(contract.velocity_um_per_s, dtype=float)

    if contract.state is not None:
        states = np.array(contract.state)
        for s in sorted(set(states)):
            mask = states == s
            color = (palette.pick(s) if s in palette.semantic
                     else palette[0])
            alpha = density_alpha(L[mask], V[mask]) if mask.any() else 0.8
            ax.scatter(L[mask], V[mask], s=10, color=color,
                       alpha=alpha, edgecolor="none",
                       zorder=3, label=f"{s} (n={int(mask.sum())})")
    else:
        alpha = density_alpha(L, V)
        ax.scatter(L, V, s=10, color=palette[0], alpha=alpha,
                   edgecolor="none", zorder=3)

    # Trend line.
    slope, intercept = np.polyfit(L, V, 1)
    xs = np.linspace(L.min(), L.max(), 80)
    ax.plot(xs, slope * xs + intercept, color="#333333",
            lw=1.1, ls="--", zorder=4,
            label=f"linear fit (slope={smart_fmt(float(slope))} s$^{{-1}}$)")

    ax.set_xscale("log")
    ax.set_xlabel(r"protrusion length ($\mu$m, log)")
    ax.set_ylabel(r"velocity ($\mu$m/s)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
