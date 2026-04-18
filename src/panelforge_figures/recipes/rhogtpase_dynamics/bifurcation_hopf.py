"""Hopf bifurcation — amplitude of limit cycle grows from a critical parameter."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    shaded_regime,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class HopfInput(RecipeContract):
    control_param: list[float] = Field(...)
    fixed_point: list[float] = Field(..., description="fixed-point amplitude (0 until Hopf)")
    cycle_amplitude: list[float | None] = Field(
        ..., description="limit-cycle amplitude where it exists, None otherwise"
    )
    hopf_param: float
    control_label: str = "control parameter"
    title: str = "Hopf bifurcation"


def _demo() -> HopfInput:
    p = np.linspace(0.0, 2.0, 200)
    hopf = 0.8
    fixed_point = np.zeros_like(p)
    # Supercritical Hopf: cycle amplitude ~ sqrt(p - hopf) above threshold.
    cycle = np.where(p >= hopf, 1.2 * np.sqrt(np.clip(p - hopf, 0, None)), np.nan)
    return HopfInput(
        control_param=p.tolist(),
        fixed_point=fixed_point.tolist(),
        cycle_amplitude=cycle.tolist(),
        hopf_param=hopf,
        control_label=r"$\mu$ (excitation strength)",
    )


_META = RecipeMetadata(
    name="bifurcation_hopf",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.bifurcation,
    answers_question="At what control-parameter value does the RhoA system transition to sustained oscillation via a Hopf bifurcation?",
    required_fields=("control_param", "fixed_point", "cycle_amplitude", "hopf_param"),
    optional_fields=("control_label", "title"),
    file_format_hints=("pickle", "npz", "csv"),
    alternatives_in_modality=("bifurcation_saddle_node", "phase_portrait_oscillator"),
)


@register_recipe(metadata=_META, contract=HopfInput, demo_contract=_demo)
def render(contract: HopfInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)

    p = np.array(contract.control_param, dtype=float)
    fp = np.array(contract.fixed_point, dtype=float)
    cyc = np.array([np.nan if v is None else v for v in contract.cycle_amplitude],
                   dtype=float)

    shaded_regime(ax, contract.hopf_param, p.max(),
                  color="#E3F2FD", alpha=0.5, label="oscillatory")

    # Fixed point: solid before Hopf, dashed after (unstable focus).
    pre = p <= contract.hopf_param
    post = p > contract.hopf_param
    ax.plot(p[pre], fp[pre], color="#1565C0", lw=1.3,
            zorder=3, label="stable fixed point")
    ax.plot(p[post], fp[post], color="#1565C0", lw=1.0, ls="--",
            zorder=3, label="unstable fixed point")

    # Limit cycle branches (+/- amplitude).
    ax.plot(p, cyc, color="#D84315", lw=1.3, zorder=4,
            label="limit cycle (+)")
    ax.plot(p, -cyc, color="#D84315", lw=1.3, zorder=4)

    # Fill limit-cycle envelope.
    ax.fill_between(p, cyc, -cyc, color="#D84315", alpha=0.08, zorder=2)

    # Hopf marker.
    ax.scatter([contract.hopf_param], [0], s=72, color="#6A1B9A",
               edgecolor="white", linewidth=1.2, zorder=5, marker="*")
    ax.text(contract.hopf_param, 0.05, f"Hopf\n{smart_fmt(contract.hopf_param)}",
            ha="center", va="bottom", fontsize=6.4, color="#6A1B9A",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92))

    ax.set_xlabel(contract.control_label)
    ax.set_ylabel("amplitude")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
