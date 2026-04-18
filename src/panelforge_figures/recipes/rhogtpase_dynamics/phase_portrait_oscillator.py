"""Oscillator phase portrait — limit-cycle surrounding an unstable focus."""

from __future__ import annotations

import numpy as np
from scipy.integrate import odeint

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    fixed_point_marker,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class OscillatorPortraitInput(RecipeContract):
    mu: float = 0.6
    coupling_eps: float = 0.08
    title: str = "Van der Pol-like oscillator"


def _demo() -> OscillatorPortraitInput:
    return OscillatorPortraitInput()


_META = RecipeMetadata(
    name="phase_portrait_oscillator",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question="When does RhoA oscillate, and where is the limit cycle in phase space?",
    required_fields=("mu",),
    optional_fields=("coupling_eps", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=("phase_portrait_bistable", "bifurcation_hopf"),
)


@register_recipe(metadata=_META, contract=OscillatorPortraitInput, demo_contract=_demo)
def render(contract: OscillatorPortraitInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    mu = contract.mu
    xg = np.linspace(-2.5, 2.5, 28)
    yg = np.linspace(-2.5, 2.5, 28)
    X, Y = np.meshgrid(xg, yg)
    # Van der Pol: dx/dt = y, dy/dt = mu * (1 - x^2) * y - x.
    Vx = Y
    Vy = mu * (1 - X ** 2) * Y - X
    speed = np.hypot(Vx, Vy)
    ax.streamplot(X, Y, Vx, Vy, color=speed, cmap=AESTHETIC.continuous_cmap,
                  density=1.0, linewidth=0.7, arrowsize=0.7, zorder=2)

    # Integrate a few trajectories from distinct ICs to trace the limit cycle.
    t = np.linspace(0, 40, 2000)

    def vdp(z, _t):
        return [z[1], mu * (1 - z[0] ** 2) * z[1] - z[0]]

    for ic, col in [((2.0, 0.0), palette.pick("TRAP")),
                    ((-0.2, 0.1), palette.pick("HOME")),
                    ((0.1, 2.2), palette.pick("GATE"))]:
        sol = odeint(vdp, ic, t, full_output=False)
        # Only draw the final half (after transient).
        ax.plot(sol[-800:, 0], sol[-800:, 1], color=col,
                lw=1.1, alpha=0.9, zorder=3)

    # Unstable focus at origin.
    fixed_point_marker(ax, 0, 0, "unstable", label="origin")

    ax.set_xlabel("x (RhoA activity)")
    ax.set_ylabel("y (derivative)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(xg.min(), xg.max())
    ax.set_ylim(yg.min(), yg.max())
    ax.text(0.99, 0.02,
            f"μ = {mu:.2f}  (unstable focus + limit cycle)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
