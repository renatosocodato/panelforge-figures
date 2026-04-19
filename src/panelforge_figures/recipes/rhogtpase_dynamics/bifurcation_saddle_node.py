"""Saddle-node bifurcation — stable/unstable branches merging at turn points."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    saddle_node_star,
    shaded_regime,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SaddleNodeInput(RecipeContract):
    control_param: list[float] = Field(...)
    stable_branches: list[list[float | None]] = Field(
        ..., description="list of stable branches; each is x[i] or None where absent"
    )
    unstable_branch: list[float | None] = Field(...)
    sn1_param: float
    sn2_param: float
    control_label: str = "control parameter"
    title: str = "Saddle-node bifurcation"


def _demo() -> SaddleNodeInput:
    # Hysteresis: lower stable [−1.5, -0.5], upper stable [0.5, 1.5], unstable middle.
    p = np.linspace(0.0, 1.0, 200)
    sn1 = 0.30
    sn2 = 0.70
    # Lower branch exists for p <= sn2.
    lower = np.where(p <= sn2, -1 + 0.8 * (p - sn1), np.nan)
    # Upper branch exists for p >= sn1.
    upper = np.where(p >= sn1, 0.8 * (p - sn2) + 1, np.nan)
    # Unstable middle for sn1 <= p <= sn2.
    unstable = np.where((p >= sn1) & (p <= sn2),
                        0.5 * (lower + upper) * 0.0 + (p - 0.5) * 0.2,
                        np.nan)
    return SaddleNodeInput(
        control_param=p.tolist(),
        stable_branches=[lower.tolist(), upper.tolist()],
        unstable_branch=unstable.tolist(),
        sn1_param=sn1, sn2_param=sn2,
        control_label="RhoGDI release rate",
    )


_META = RecipeMetadata(
    name="bifurcation_saddle_node",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.bifurcation,
    answers_question="Where do the RhoA steady-state branches collide in a saddle-node, and where is the hysteresis region?",
    required_fields=("control_param", "stable_branches", "unstable_branch",
                     "sn1_param", "sn2_param"),
    optional_fields=("control_label", "title"),
    file_format_hints=("pickle", "npz", "csv"),
    alternatives_in_modality=("bifurcation_hopf", "bifurcation_pitchfork"),
)


@register_recipe(metadata=_META, contract=SaddleNodeInput, demo_contract=_demo)
def render(contract: SaddleNodeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = ("#2E7D32", "#1565C0", "#6A1B9A", "#EF6C00")

    p = np.array(contract.control_param, dtype=float)

    # Shaded hysteresis region.
    shaded_regime(ax, contract.sn1_param, contract.sn2_param,
                  color="#FFEBEE", alpha=0.55, label="hysteresis")

    # Stable branches.
    for i, b in enumerate(contract.stable_branches):
        arr = np.array([np.nan if v is None else v for v in b], dtype=float)
        ax.plot(p, arr, color=palette[i % len(palette)],
                lw=1.3, zorder=3,
                label=f"stable {i+1}")

    # Unstable middle.
    unst = np.array([np.nan if v is None else v for v in contract.unstable_branch],
                    dtype=float)
    ax.plot(p, unst, color="#333333", lw=0.8, ls="--",
            zorder=2, label="unstable")

    # Saddle-node stars.
    # Locate y near sn1 and sn2 on the branches.
    idx1 = int(np.argmin(np.abs(p - contract.sn1_param)))
    idx2 = int(np.argmin(np.abs(p - contract.sn2_param)))
    lower = np.array([np.nan if v is None else v
                      for v in contract.stable_branches[0]], dtype=float)
    upper = np.array([np.nan if v is None else v
                      for v in contract.stable_branches[1]], dtype=float)
    y_sn1 = upper[idx1] if not np.isnan(upper[idx1]) else lower[idx1]
    y_sn2 = lower[idx2] if not np.isnan(lower[idx2]) else upper[idx2]
    saddle_node_star(ax, contract.sn1_param, y_sn1)
    saddle_node_star(ax, contract.sn2_param, y_sn2)

    ax.set_xlabel(contract.control_label)
    ax.set_ylabel("steady state")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)

    # Tag the SN coordinates — anchored in axes fraction so they never clip.
    ax.annotate(
        f"$SN_1$={smart_fmt(contract.sn1_param)}",
        xy=(contract.sn1_param, 0.04),
        xycoords=("data", "axes fraction"),
        ha="center", va="bottom", fontsize=6.2, color="#D32F2F",
    )
    ax.annotate(
        f"$SN_2$={smart_fmt(contract.sn2_param)}",
        xy=(contract.sn2_param, 0.04),
        xycoords=("data", "axes fraction"),
        ha="center", va="bottom", fontsize=6.2, color="#D32F2F",
    )

    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
