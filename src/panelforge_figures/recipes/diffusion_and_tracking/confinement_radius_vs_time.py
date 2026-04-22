"""Per-track confinement-radius vs time — timecourse_hierarchical_ci
with mean ± CI band across tracks. Distinct from `confinement_radius_map`
(spatial static snapshot).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class RConfVsTimeInput(RecipeContract):
    time_s: list[float] = Field(..., min_length=5)
    R_conf_per_track: list[list[float]] = Field(
        ...,
        description="(n_tracks × n_t) per-track confinement radius",
    )
    condition_per_track: list[str] | None = Field(
        None, description="optional condition label per track"
    )
    title: str = "Confinement radius over time"


def _demo() -> RConfVsTimeInput:
    rng = np.random.default_rng(2411)
    t = np.linspace(0, 30, 80)
    n_tracks = 40
    R = []
    cond = []
    for i in range(n_tracks):
        if i < n_tracks // 2:
            # Control: roughly stable R ≈ 0.6 μm.
            r0 = 0.6 + rng.normal(0, 0.08)
            drift = 0.02 * rng.normal(0, 1, t.size).cumsum() / np.sqrt(t.size)
            r = r0 + drift + rng.normal(0, 0.04, t.size)
            cond.append("control")
        else:
            # Treated: starts confined (0.3), expands after t=15.
            r = 0.3 + 0.5 * (1.0 / (1 + np.exp(-(t - 15) / 2.0)))
            r += rng.normal(0, 0.06, t.size)
            cond.append("treated")
        R.append(np.clip(r, 0.05, None).tolist())
    return RConfVsTimeInput(
        time_s=t.tolist(),
        R_conf_per_track=R,
        condition_per_track=cond,
    )


_META = RecipeMetadata(
    name="confinement_radius_vs_time",
    modality="diffusion_and_tracking",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does a track's confinement radius evolve over time — "
        "e.g. from confined to free?"
    ),
    required_fields=("time_s", "R_conf_per_track"),
    optional_fields=("condition_per_track", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("confinement_radius_map",),
)


@register_recipe(
    metadata=_META,
    contract=RConfVsTimeInput,
    demo_contract=_demo,
)
def render(contract: RConfVsTimeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.asarray(contract.time_s, float)
    R = np.asarray(contract.R_conf_per_track, float)   # (n_tracks, n_t)
    conds = (contract.condition_per_track
             if contract.condition_per_track is not None
             else ["all"] * R.shape[0])
    unique = list(dict.fromkeys(conds))

    for i, cond in enumerate(unique):
        mask = np.array([c == cond for c in conds])
        if mask.sum() == 0:
            continue
        color = palette[i % len(palette.colors)]
        sub = R[mask]
        mean = np.mean(sub, axis=0)
        se = np.std(sub, axis=0, ddof=1) / np.sqrt(max(sub.shape[0], 1))
        ci = 1.96 * se
        ax.fill_between(t, mean - ci, mean + ci,
                        color=color, alpha=0.2, linewidth=0, zorder=2)
        ax.plot(t, mean, color=color, lw=1.2, zorder=4,
                label=f"{cond}  (n = {int(mask.sum())})")

    # Reference lines for interpretation.
    ax.axhline(0.5, color="#888888", lw=0.6, ls=":", zorder=1,
               label="R = 0.5 μm (ref)")

    ax.set_xlabel("time (s)")
    ax.set_ylabel(r"R$_{\rm conf}$ (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # End-of-record summary.
    mean_start = float(np.mean(R[:, :3]))
    mean_end = float(np.mean(R[:, -3:]))
    ax.text(0.98, 0.04,
            f"ΔR_conf (start -> end) = {smart_fmt(mean_end - mean_start)} μm",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
