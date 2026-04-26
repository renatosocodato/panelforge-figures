"""Dwell-time distribution per decoded state — split-violin per state
with optional fitted density and a dashed geometric reference for
HMM compatibility.

Diagnostic recipe: if dwells are visibly geometric (mode at 1, decay
e^-lambda*tau), HMM is appropriate; if they are visibly hump-shaped
(gamma / Weibull / lognormal), HSMM is needed. This panel is usually
the deciding plot in the HMM-vs-HSMM choice (companion adjudicator
A.10 quantifies the call).

Split-violin family: >=2 violin bodies + >=1 median marker. Satisfied
by per-state violins (>=2 states required by demo) + per-state
median markers.
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


class DwellTimePerStateInput(RecipeContract):
    dwells_by_state: dict[str, list[float]] = Field(...)
    decoder_label: str = "HMM"
    reference_geometric: bool = True
    fit_family: str | None = Field(
        "gamma",
        description="'gamma' | 'weibull' | 'lognormal' | None",
    )
    title: str = "Dwell-time distribution per state"


def _demo() -> DwellTimePerStateInput:
    rng = np.random.default_rng(1717)
    # Three-state synthesis: S0 geometric, S1 gamma, S2 lognormal.
    return DwellTimePerStateInput(
        dwells_by_state={
            "S0": rng.geometric(p=0.20, size=120).astype(float).tolist(),
            "S1": rng.gamma(shape=4.0, scale=1.5, size=120).tolist(),
            "S2": rng.lognormal(mean=2.0, sigma=0.4, size=120).tolist(),
        },
        decoder_label="HMM",
    )


_META = RecipeMetadata(
    name="dwell_time_distribution_per_state",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per decoded latent state, how are sojourn dwells distributed, "
        "and are they consistent with the HMM geometric assumption?"
    ),
    required_fields=("dwells_by_state",),
    optional_fields=(
        "decoder_label", "reference_geometric", "fit_family", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("velocity_distribution_by_state",),
)


@register_recipe(
    metadata=_META,
    contract=DwellTimePerStateInput,
    demo_contract=_demo,
)
def render(contract: DwellTimePerStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    states = list(contract.dwells_by_state.keys())
    palette = _demo_state_palette(states)
    positions = np.arange(len(states))

    medians: dict[str, float] = {}
    for pos, state in zip(positions, states):
        vals = np.asarray(contract.dwells_by_state[state], float)
        if vals.size == 0:
            continue
        colour = palette.get(state, "#555555")
        parts = ax.violinplot(
            [vals], positions=[pos], widths=0.78,
            showmeans=False, showmedians=False, showextrema=False,
        )
        for pc in parts["bodies"]:
            pc.set_facecolor(colour)
            pc.set_edgecolor("#333333")
            pc.set_alpha(0.55)
        if vals.size >= 4:
            med = float(np.median(vals))
            q1, q3 = np.quantile(vals, [0.25, 0.75])
            ax.plot([pos, pos], [q1, q3],
                    color="black", lw=2.2, zorder=5,
                    solid_capstyle="butt")
            ax.scatter([pos], [med], s=28, facecolor="white",
                       edgecolor="black", linewidth=0.8, zorder=6)
            medians[state] = med

        # Fitted density overlay.
        if contract.fit_family in ("gamma", "weibull", "lognormal"):
            xg = np.linspace(0.1, vals.max() * 1.05, 60)
            density = _fit_density(vals, xg, contract.fit_family)
            # Scale density into ~violin-half-width units.
            density = density / max(density.max(), 1e-12) * 0.35
            ax.fill_betweenx(xg, pos, pos + density,
                             color=colour, alpha=0.25,
                             linewidth=0, zorder=4)
            ax.plot(pos + density, xg,
                    color=colour, lw=0.8, zorder=4)

        # Dashed geometric reference (mean-matched).
        if contract.reference_geometric and vals.mean() > 1.0:
            mean_d = float(vals.mean())
            x_ref = np.arange(1, int(vals.max()) + 1)
            geo = (1 - 1 / mean_d) ** (x_ref - 1) * (1 / mean_d)
            geo_scaled = geo / max(geo.max(), 1e-12) * 0.35
            ax.plot(pos - geo_scaled, x_ref,
                    color="#888888", lw=0.7, ls="--", zorder=3,
                    label="geometric (HMM)" if pos == 0 else None)

    ax.set_xticks(positions)
    ax.set_xticklabels(states, fontsize=7.0)
    ax.set_ylabel("dwell time (frames)")
    ax.set_xlabel("decoded state")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    if contract.reference_geometric:
        ax.legend(fontsize=6.6, frameon=False, loc="upper right",
                  handlelength=1.4)

    bits = [f"{s}: med {smart_fmt(m)}" for s, m in medians.items()]
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax


def _fit_density(vals: np.ndarray, xg: np.ndarray, family: str) -> np.ndarray:
    """MLE-ish fit of one of {gamma, weibull, lognormal}; returns pdf."""
    v = vals[vals > 0]
    if v.size < 3:
        return np.zeros_like(xg)
    if family == "gamma":
        m = float(v.mean())
        var = float(v.var())
        if var <= 0:
            return np.zeros_like(xg)
        shape = m * m / var
        scale = var / m
        from math import gamma as Gamma
        return (xg ** (shape - 1) * np.exp(-xg / scale)
                / (Gamma(shape) * scale ** shape + 1e-12))
    if family == "weibull":
        m = float(v.mean())
        var = float(v.var())
        if m <= 0 or var <= 0:
            return np.zeros_like(xg)
        cv = np.sqrt(var) / m
        shape = float(np.clip(1.0 / cv, 0.5, 5.0))
        from math import gamma as Gamma
        scale = m / Gamma(1.0 + 1.0 / shape)
        return ((shape / scale) * (xg / scale) ** (shape - 1)
                * np.exp(-((xg / scale) ** shape)))
    if family == "lognormal":
        log_v = np.log(v)
        mu = float(log_v.mean())
        sigma = float(log_v.std())
        if sigma <= 0:
            return np.zeros_like(xg)
        return (1 / (xg * sigma * np.sqrt(2 * np.pi) + 1e-12)) \
            * np.exp(-((np.log(xg) - mu) ** 2) / (2 * sigma ** 2))
    return np.zeros_like(xg)
