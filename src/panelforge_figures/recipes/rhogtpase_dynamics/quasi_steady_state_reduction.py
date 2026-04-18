"""Quasi-steady-state reduction — compare full vs reduced model trajectories."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.integrate import odeint

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class QSSReductionInput(RecipeContract):
    t: list[float] = Field(...)
    x_full: list[float] = Field(..., description="slow variable from full 2-D model")
    x_reduced: list[float] = Field(..., description="slow variable from QSS-reduced model")
    y_fast_full: list[float] | None = None
    epsilon: float = 0.1
    title: str = "QSS reduction"


def _demo() -> QSSReductionInput:
    eps = 0.08
    t = np.linspace(0, 30, 400)

    def full(z, _t, eps):
        x, y = z
        return [x - x ** 3 - y, (x - y) / eps]

    sol = odeint(full, [1.5, 1.5], t, args=(eps,))
    x_full = sol[:, 0]
    y_full = sol[:, 1]
    # QSS: y = x (slow manifold) → dx/dt = x - x^3 - x = -x^3.
    def qss(x, _t):
        return -x ** 3
    sol_q = odeint(qss, [1.5], t)
    return QSSReductionInput(
        t=t.tolist(),
        x_full=x_full.tolist(),
        x_reduced=sol_q[:, 0].tolist(),
        y_fast_full=y_full.tolist(),
        epsilon=eps,
    )


_META = RecipeMetadata(
    name="quasi_steady_state_reduction",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Does the quasi-steady-state (slow-manifold) reduction faithfully reproduce the full 2-D RhoA dynamics?",
    required_fields=("t", "x_full", "x_reduced"),
    optional_fields=("y_fast_full", "epsilon", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=("timescale_separation_diagnostic",),
)


@register_recipe(metadata=_META, contract=QSSReductionInput, demo_contract=_demo)
def render(contract: QSSReductionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.array(contract.t, dtype=float)
    xf = np.array(contract.x_full, dtype=float)
    xr = np.array(contract.x_reduced, dtype=float)

    ax.plot(t, xf, color=palette.pick("HOME"), lw=1.3, zorder=4,
            label="full 2-D")
    ax.plot(t, xr, color="#333333", lw=1.0, ls="--", zorder=3,
            label="QSS reduced")

    if contract.y_fast_full is not None:
        yf = np.array(contract.y_fast_full, dtype=float)
        ax.plot(t, yf, color=palette.pick("TRAP"), lw=0.8,
                alpha=0.6, zorder=2, label="fast variable")

    # Error-band in lower inset slot via secondary annotation.
    err = np.abs(xf - xr)
    ax.text(0.99, 0.02,
            f"max |full − reduced| = {smart_fmt(float(err.max()))}\n"
            f"ε = {smart_fmt(contract.epsilon)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)

    ax.set_xlabel("time")
    ax.set_ylabel("x (slow)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
