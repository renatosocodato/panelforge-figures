"""Timescale separation diagnostic — Jacobian eigenvalue ratio vs parameter."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    shaded_regime,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class TimescaleSeparationInput(RecipeContract):
    param: list[float] = Field(...)
    fast_scale: list[float] = Field(..., description="|Re(λ_fast)|")
    slow_scale: list[float] = Field(..., description="|Re(λ_slow)|")
    ratio_threshold: float = 10.0
    param_label: str = "parameter"
    title: str = "Timescale separation"


def _demo() -> TimescaleSeparationInput:
    p = np.linspace(0.01, 1.0, 200)
    # Example: fast rate scales as 1/ε, slow as O(1). ε changes with p.
    eps = 0.02 + 0.3 * (1 - p)
    fast = 1 / eps
    slow = 1 + 0.2 * p
    return TimescaleSeparationInput(
        param=p.tolist(),
        fast_scale=fast.tolist(),
        slow_scale=slow.tolist(),
        ratio_threshold=10.0,
        param_label="activation level",
    )


_META = RecipeMetadata(
    name="timescale_separation_diagnostic",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Is there a clean separation of fast and slow timescales, and over what parameter range?",
    required_fields=("param", "fast_scale", "slow_scale"),
    optional_fields=("ratio_threshold", "param_label", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("quasi_steady_state_reduction",),
)


@register_recipe(metadata=_META, contract=TimescaleSeparationInput, demo_contract=_demo)
def render(contract: TimescaleSeparationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    p = np.array(contract.param, dtype=float)
    fast = np.array(contract.fast_scale, dtype=float)
    slow = np.array(contract.slow_scale, dtype=float)
    ratio = fast / np.maximum(slow, 1e-12)

    ax.plot(p, fast, color=palette.pick("TRAP"), lw=1.2, zorder=3, label="|λ fast|")
    ax.plot(p, slow, color=palette.pick("HOME"), lw=1.2, zorder=3, label="|λ slow|")

    # Shade the good-separation region where ratio > threshold.
    good = np.where(ratio >= contract.ratio_threshold, p, np.nan)
    if np.any(~np.isnan(good)):
        p_lo = np.nanmin(good)
        p_hi = np.nanmax(good)
        shaded_regime(ax, p_lo, p_hi, color="#E8F5E9", alpha=0.4,
                      label=f"ratio ≥ {smart_fmt(contract.ratio_threshold)}")

    ax.set_yscale("log")
    ax.set_xlabel(contract.param_label)
    ax.set_ylabel("|Re(λ)|")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.6)

    # Summary callout.
    med_ratio = float(np.median(ratio))
    ax.text(0.99, 0.02,
            f"median ratio = {smart_fmt(med_ratio)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
