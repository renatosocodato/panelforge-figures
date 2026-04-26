"""Ornstein-Uhlenbeck heading-dynamics fit per state — forest of
(tau, sigma) per state x condition with 95 % CI.

Coef-forest family: >=3 markers + >=1 reference line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import _demo_state_palette


class OUFitRow(RecipeContract):
    state: str
    condition: str
    tau_s: float
    tau_lo: float
    tau_hi: float
    sigma: float
    sigma_lo: float
    sigma_hi: float


class OUFitPerStateInput(RecipeContract):
    fits: list[OUFitRow] = Field(..., min_length=3)
    show_param: str = Field(
        "tau",
        description="'tau' | 'sigma'",
    )
    title: str = "Ornstein-Uhlenbeck heading-dynamics fit per state"


def _demo() -> OUFitPerStateInput:
    rng = np.random.default_rng(3051)
    rows: list[OUFitRow] = []
    # Per-state tau: homeostatic short, surveillant medium, activated long.
    base = {"homeostatic": 8.0, "surveillant": 18.0, "activated": 30.0}
    sigma_base = {"homeostatic": 25.0, "surveillant": 18.0, "activated": 12.0}
    for cond, scale in (("control", 1.0), ("DISC1", 1.4)):
        for state in base:
            tau = base[state] * scale + rng.normal(0, 1.2)
            tau_h = 0.18 * tau
            sigma = sigma_base[state] * (1.1 if cond == "DISC1" else 1.0) \
                + rng.normal(0, 1.0)
            sigma_h = 0.20 * sigma
            rows.append(OUFitRow(
                state=state, condition=cond,
                tau_s=float(tau), tau_lo=float(tau - tau_h),
                tau_hi=float(tau + tau_h),
                sigma=float(sigma), sigma_lo=float(sigma - sigma_h),
                sigma_hi=float(sigma + sigma_h),
            ))
    return OUFitPerStateInput(fits=rows)


_META = RecipeMetadata(
    name="ornstein_uhlenbeck_fit_per_state",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per (decoded state, condition) cell, what are the OU "
        "heading dynamics parameters (tau, sigma)?"
    ),
    required_fields=("fits",),
    optional_fields=("show_param", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("directional_persistence_autocorr",),
)


@register_recipe(
    metadata=_META,
    contract=OUFitPerStateInput,
    demo_contract=_demo,
)
def render(contract: OUFitPerStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    states = list(dict.fromkeys(r.state for r in contract.fits))
    palette = _demo_state_palette(states)
    n_rows = len(contract.fits)
    y = np.arange(n_rows)

    # Reference line at 0 (no autocorrelation).
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="no persistence")

    # Per-row segments + markers.
    for yi, row in zip(y, contract.fits):
        if contract.show_param == "tau":
            est, lo, hi = row.tau_s, row.tau_lo, row.tau_hi
        else:
            est, lo, hi = row.sigma, row.sigma_lo, row.sigma_hi
        colour = palette.get(row.state, "#37474F")
        marker = "o" if row.condition == "control" else "s"
        ax.plot([lo, hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
        ax.scatter([est], [yi], s=44, marker=marker,
                   facecolor=colour, edgecolor="white", linewidth=0.5,
                   zorder=5)

    tick_labels = [f"{r.condition}  ·  {r.state}" for r in contract.fits]
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel(f"{contract.show_param} (s)" if contract.show_param == "tau"
                  else f"{contract.show_param} (deg)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888",
               markeredgecolor="white", markersize=6,
               label="control"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="#888888",
               markeredgecolor="white", markersize=6,
               label="DISC1"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="no persistence"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=3, handlelength=1.0)

    bits = []
    for state in states:
        ctrl = next((r for r in contract.fits
                     if r.state == state and r.condition == "control"),
                    None)
        disc = next((r for r in contract.fits
                     if r.state == state and r.condition == "DISC1"),
                    None)
        if ctrl and disc:
            ratio = (disc.tau_s / ctrl.tau_s) if ctrl.tau_s > 0 else float("nan")
            bits.append(f"{state}: DISC1/ctrl tau = {smart_fmt(ratio)}x")
    ax.set_title(
        f"{contract.title}  ·  showing {contract.show_param}  ·  "
        + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
