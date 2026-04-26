"""Hazard rate per decoded state — h(tau) curves per state with
kernel-density CI ribbons.

The decision plot for HMM-vs-HSMM: a flat h(tau) per state means
geometric dwells (HMM-compatible); a ramp / peak / decay means age-
dependent durations (HSMM territory).

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
Satisfied by per-state hazard curves with bootstrap CI ribbons.
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


class HazardRatePerStateInput(RecipeContract):
    dwells_by_state: dict[str, list[float]] = Field(...)
    decoder_label: str = "HMM"
    bandwidth_frames: float = 4.0
    n_bootstrap: int = 100
    title: str = "Hazard rate per state"


def _demo() -> HazardRatePerStateInput:
    rng = np.random.default_rng(1729)
    return HazardRatePerStateInput(
        dwells_by_state={
            "homeostatic":
                rng.geometric(p=0.20, size=120).astype(float).tolist(),
            "surveillant":
                rng.gamma(shape=4.0, scale=1.5, size=120).tolist(),
            "activated":
                rng.lognormal(mean=2.0, sigma=0.4, size=120).tolist(),
        },
        decoder_label="HMM",
    )


_META = RecipeMetadata(
    name="hazard_rate_per_state",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per decoded state, does the switch-out hazard depend on age-in-"
        "state (ramp / peak = HSMM) or is it flat (HMM-compatible)?"
    ),
    required_fields=("dwells_by_state",),
    optional_fields=(
        "decoder_label", "bandwidth_frames", "n_bootstrap", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("sojourn_survival_per_state",),
)


@register_recipe(
    metadata=_META,
    contract=HazardRatePerStateInput,
    demo_contract=_demo,
)
def render(contract: HazardRatePerStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    states = list(contract.dwells_by_state.keys())
    palette = _demo_state_palette(states)
    bw = float(contract.bandwidth_frames)
    rng = np.random.default_rng(13)

    # Common tau grid.
    all_vals = np.concatenate([
        np.asarray(v, float)
        for v in contract.dwells_by_state.values()
    ])
    if all_vals.size == 0:
        ax.set_title(contract.title, fontsize=8.4, pad=4)
        return ax
    tau_max = float(np.quantile(all_vals, 0.95)) * 1.1
    tau_grid = np.linspace(0.5, max(tau_max, 5.0), 60)

    bits = []
    for state in states:
        vals = np.asarray(contract.dwells_by_state[state], float)
        if vals.size < 5:
            continue
        h = _kernel_hazard(vals, tau_grid, bw)
        # Bootstrap CI (reuses the survival-clamped hazard).
        boot_curves = []
        for _ in range(contract.n_bootstrap):
            idx = rng.integers(0, vals.size, size=vals.size)
            boot_curves.append(_kernel_hazard(vals[idx], tau_grid, bw))
        boot = np.asarray(boot_curves)
        # Suppress 'All-NaN slice encountered' warning — at right-tail
        # tau bins, ALL bootstrap resamples may have S < floor, which
        # is the intended behaviour (the hazard is undefined there).
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            lo = np.nanquantile(boot, 0.025, axis=0)
            hi = np.nanquantile(boot, 0.975, axis=0)
        colour = palette.get(state, "#555555")
        ax.plot(tau_grid, h, color=colour, lw=1.2, zorder=4, label=state)
        ax.fill_between(tau_grid, lo, hi,
                        color=colour, alpha=0.18, linewidth=0,
                        zorder=2)
        # Flat-vs-ramp diagnostic: relative range over the
        # well-sampled (non-NaN) portion of h(tau).
        h_finite = h[np.isfinite(h)]
        if h_finite.size:
            h_range = float(
                (h_finite.max() - h_finite.min())
                / max(h_finite.mean(), 1e-9)
            )
        else:
            h_range = 0.0
        bits.append(f"{state}: h-range {smart_fmt(h_range)}")

    ax.set_xlabel("age in state tau (frames)")
    ax.set_ylabel("hazard h(tau)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "   ".join(bits),
        fontsize=7.8, pad=4,
    )
    return ax


def _kernel_hazard(vals: np.ndarray, tau_grid: np.ndarray,
                   bandwidth: float,
                   *, survival_floor: float = 0.05) -> np.ndarray:
    """Smoothed hazard: h(t) = f(t) / S(t), kernel density numerator,
    empirical survival denominator. Clamps the hazard to NaN where
    the empirical survival drops below `survival_floor` (default 5 %)
    so the divide-by-near-zero tail doesn't dominate the y-axis."""
    f = np.zeros_like(tau_grid)
    for v in vals:
        f += np.exp(-((tau_grid - v) / bandwidth) ** 2 / 2.0)
    f /= (vals.size * bandwidth * np.sqrt(2 * np.pi))
    sorted_vals = np.sort(vals)
    s = np.array([
        float((sorted_vals > t).sum() / vals.size)
        for t in tau_grid
    ])
    h = np.full_like(tau_grid, np.nan)
    valid = s >= survival_floor
    h[valid] = f[valid] / s[valid]
    return h
