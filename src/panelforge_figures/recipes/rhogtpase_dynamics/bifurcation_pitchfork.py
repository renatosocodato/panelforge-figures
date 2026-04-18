"""Pitchfork bifurcation — a symmetric fixed-point splits into two at p=p_c."""

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


class PitchforkInput(RecipeContract):
    control_param: list[float] = Field(...)
    central_branch: list[float] = Field(...)
    upper_branch: list[float | None] = Field(...)
    lower_branch: list[float | None] = Field(...)
    pitchfork_param: float
    supercritical: bool = True
    control_label: str = "control parameter"
    title: str = "Pitchfork bifurcation"


def _demo() -> PitchforkInput:
    p = np.linspace(-1.0, 1.5, 200)
    pc = 0.0
    central = np.zeros_like(p)
    upper = np.where(p > pc, np.sqrt(np.clip(p - pc, 0, None)), np.nan)
    lower = -upper
    return PitchforkInput(
        control_param=p.tolist(),
        central_branch=central.tolist(),
        upper_branch=upper.tolist(),
        lower_branch=lower.tolist(),
        pitchfork_param=pc,
        supercritical=True,
        control_label=r"$r$ (symmetry-breaking)",
    )


_META = RecipeMetadata(
    name="bifurcation_pitchfork",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.bifurcation,
    answers_question="Where does the symmetric (non-polarized) RhoA state lose stability and split into polarized front/back states?",
    required_fields=("control_param", "central_branch", "upper_branch",
                     "lower_branch", "pitchfork_param"),
    optional_fields=("supercritical", "control_label", "title"),
    file_format_hints=("pickle", "npz", "csv"),
    alternatives_in_modality=("bifurcation_saddle_node", "bifurcation_hopf"),
)


@register_recipe(metadata=_META, contract=PitchforkInput, demo_contract=_demo)
def render(contract: PitchforkInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)

    p = np.array(contract.control_param, dtype=float)
    central = np.array(contract.central_branch, dtype=float)
    upper = np.array([np.nan if v is None else v for v in contract.upper_branch],
                     dtype=float)
    lower = np.array([np.nan if v is None else v for v in contract.lower_branch],
                     dtype=float)

    shaded_regime(ax, contract.pitchfork_param, p.max(),
                  color="#E8F5E9", alpha=0.5, label="polarized")

    pc = contract.pitchfork_param
    # Central branch: solid below pc, dashed above (unstable).
    ax.plot(p[p <= pc], central[p <= pc], color="#1565C0", lw=1.3,
            zorder=3, label="symmetric (stable)")
    ax.plot(p[p > pc], central[p > pc], color="#1565C0", lw=1.0, ls="--",
            zorder=3, label="symmetric (unstable)")

    # Polarized branches.
    ax.plot(p, upper, color="#D84315", lw=1.3, zorder=4,
            label="polarized (+)")
    ax.plot(p, lower, color="#2E7D32", lw=1.3, zorder=4,
            label="polarized (−)")

    # Pitchfork point.
    ax.scatter([pc], [0], s=72, color="#6A1B9A",
               edgecolor="white", linewidth=1.2, zorder=5, marker="*")
    ax.text(pc, 0.08, f"PF\n{smart_fmt(pc)}",
            ha="center", va="bottom", fontsize=6.4, color="#6A1B9A",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92))

    ax.set_xlabel(contract.control_label)
    ax.set_ylabel("steady state")
    kind = "super" if contract.supercritical else "sub"
    ax.set_title(f"{kind}critical {contract.title.lower()}",
                 fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
