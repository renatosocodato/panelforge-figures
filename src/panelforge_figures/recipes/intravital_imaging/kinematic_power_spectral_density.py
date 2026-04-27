"""Kinematic power spectral density forest — dominant-frequency
f_peak per (state x condition) computed from per-cell velocity PSDs
+ 95 % CI from bootstrap.

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
from ._shared import KinematicFeatureBundle, _demo_state_palette


class KinematicPSDInput(RecipeContract):
    bundles: list[KinematicFeatureBundle] = Field(..., min_length=4)
    state_by_cell: dict[str, str] = Field(...)
    condition_by_cell: dict[str, str] = Field(...)
    dt_s: float = 1.0
    title: str = "Kinematic power spectral density per state x condition"


def _demo() -> KinematicPSDInput:
    rng = np.random.default_rng(3231)
    bundles: list[KinematicFeatureBundle] = []
    state_by: dict[str, str] = {}
    cond_by: dict[str, str] = {}
    n_t = 256
    t = np.arange(n_t).astype(float)
    # control: clean ~0.05 Hz oscillation; DISC1: broadband.
    for cond in ("control", "DISC1"):
        for state in ("homeostatic", "surveillant", "activated"):
            for k in range(8):
                cell_id = f"{cond}_{state}_C{k}"
                if cond == "control":
                    osc = np.sin(2 * np.pi * 0.05 * t)
                    v = osc * 1.5 + rng.normal(0, 0.5, n_t)
                else:
                    v = rng.normal(0, 1.0, n_t)  # broadband
                bundles.append(KinematicFeatureBundle(
                    cell_id=cell_id, t_s=t.tolist(),
                    velocity_um_per_min=v.tolist(),
                ))
                state_by[cell_id] = state
                cond_by[cell_id] = cond
    return KinematicPSDInput(
        bundles=bundles, state_by_cell=state_by,
        condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="kinematic_power_spectral_density",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per (decoded state, condition), what is the dominant "
        "frequency in tip-velocity power spectral density, and does "
        "it differ between conditions?"
    ),
    required_fields=("bundles", "state_by_cell", "condition_by_cell"),
    optional_fields=("dt_s", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("directional_persistence_autocorr",),
)


@register_recipe(
    metadata=_META,
    contract=KinematicPSDInput,
    demo_contract=_demo,
)
def render(contract: KinematicPSDInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    states = list(dict.fromkeys(contract.state_by_cell.values()))
    palette = _demo_state_palette(states)
    conds = list(dict.fromkeys(contract.condition_by_cell.values()))

    # Group bundles by (state, cond) and compute per-cell f_peak.
    groups: dict[tuple[str, str], list[float]] = {}
    for b in contract.bundles:
        st = contract.state_by_cell.get(b.cell_id, "?")
        cd = contract.condition_by_cell.get(b.cell_id, "?")
        if b.velocity_um_per_min is None:
            continue
        v = np.asarray(b.velocity_um_per_min, float)
        if v.size < 8:
            continue
        v = v - v.mean()
        # rfft -> |X|^2.
        X = np.fft.rfft(v)
        psd = (X * np.conj(X)).real
        freq = np.fft.rfftfreq(v.size, d=contract.dt_s)
        # Drop DC; pick argmax.
        if freq.size > 1:
            f_peak = float(freq[1 + int(np.argmax(psd[1:]))])
        else:
            f_peak = 0.0
        groups.setdefault((st, cd), []).append(f_peak)

    # Build forest rows: (state, cond) sorted state-major then cond-major.
    rows: list[tuple[str, str, float, float, float]] = []
    rng = np.random.default_rng(19)
    for st in states:
        for cd in conds:
            vals = groups.get((st, cd), [])
            if not vals:
                continue
            vals_arr = np.asarray(vals, float)
            mean_f = float(vals_arr.mean())
            boot = [vals_arr[rng.integers(0, vals_arr.size,
                                          vals_arr.size)].mean()
                    for _ in range(200)]
            lo = float(np.quantile(boot, 0.025))
            hi = float(np.quantile(boot, 0.975))
            rows.append((st, cd, mean_f, lo, hi))

    if not rows:
        return ax

    y = np.arange(len(rows))
    # Reference line at f = 0 (no oscillation).
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="f = 0 (no oscillation)")
    for yi, (st, cd, est, lo, hi) in zip(y, rows):
        colour = palette.get(st, "#37474F")
        marker = "o" if cd == "control" else "s"
        ax.plot([lo, hi], [yi, yi], color=colour, lw=1.1,
                alpha=0.85, zorder=3)
        ax.scatter([est], [yi], s=44, marker=marker,
                   facecolor=colour, edgecolor="white", linewidth=0.5,
                   zorder=5)

    tick_labels = [f"{cd}  ·  {st}" for st, cd, *_ in rows]
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel("dominant frequency f_peak (Hz)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="control"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="DISC1"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="f = 0"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=3, handlelength=1.0)

    bits = []
    for st in states:
        ctrl = next(((m, lo, hi)
                     for s, c, m, lo, hi in rows
                     if s == st and c == "control"), None)
        disc = next(((m, lo, hi)
                     for s, c, m, lo, hi in rows
                     if s == st and c == "DISC1"), None)
        if ctrl and disc and ctrl[0] > 0:
            ratio = disc[0] / ctrl[0]
            bits.append(f"{st}: DISC1/ctrl = {smart_fmt(ratio)}x")
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
