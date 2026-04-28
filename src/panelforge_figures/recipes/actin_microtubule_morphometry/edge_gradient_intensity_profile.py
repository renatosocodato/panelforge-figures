"""Edge-gradient intensity profile — per-channel mean intensity vs
signed distance from the cell edge (positive = inside cell), with
bootstrap CI ribbons per condition.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
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
from ._shared import EdgeIntensityProfile

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}

_CHANNEL_LINESTYLE = {
    "F-actin": "-",
    "MT": "--",
}


class EdgeGradientProfileInput(RecipeContract):
    profiles: list[EdgeIntensityProfile] = Field(..., min_length=4)
    title: str = "Edge-gradient intensity profile"


def _demo() -> EdgeGradientProfileInput:
    rng = np.random.default_rng(651)
    profiles: list[EdgeIntensityProfile] = []
    distance_grid = np.linspace(-2.0, 6.0, 40)
    for cond in ("WT", "LI"):
        # WT: smooth cortical enrichment.
        # LI: stronger F-actin shift toward edge; MT slightly elevated.
        actin_peak_d = -0.2 if cond == "WT" else -0.5
        actin_peak_h = 0.85 if cond == "WT" else 1.10
        mt_peak_d = 0.5 if cond == "WT" else 0.2
        mt_peak_h = 0.75 if cond == "WT" else 0.92
        for k in range(25):
            actin = (actin_peak_h
                     * np.exp(-((distance_grid - actin_peak_d) / 1.0) ** 2)
                     + rng.normal(0, 0.04, distance_grid.size))
            mt = (mt_peak_h
                  * np.exp(-((distance_grid - mt_peak_d) / 1.5) ** 2)
                  + rng.normal(0, 0.04, distance_grid.size))
            profiles.append(EdgeIntensityProfile(
                cell_id=f"{cond}_{k:02d}",
                condition=cond, channel="F-actin",
                signed_distance_um=distance_grid.tolist(),
                intensity=actin.tolist(),
            ))
            profiles.append(EdgeIntensityProfile(
                cell_id=f"{cond}_{k:02d}",
                condition=cond, channel="MT",
                signed_distance_um=distance_grid.tolist(),
                intensity=mt.tolist(),
            ))
    return EdgeGradientProfileInput(profiles=profiles)


_META = RecipeMetadata(
    name="edge_gradient_intensity_profile",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How does per-channel intensity (F-actin, MT) vary with "
        "signed distance from cell edge, and does the cortical "
        "enrichment differ between conditions?"
    ),
    required_fields=("profiles",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("intensity_radial_profile",),
)


@register_recipe(
    metadata=_META,
    contract=EdgeGradientProfileInput,
    demo_contract=_demo,
)
def render(contract: EdgeGradientProfileInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Group by (condition, channel) and compute per-condition mean + bootstrap CI.
    distance_arr = np.asarray(contract.profiles[0].signed_distance_um,
                              float)

    # Edge reference at distance = 0.
    ax.axvline(0, color="#222222", lw=0.7, ls=":", zorder=2,
               label="cell edge")

    bits = []
    rng = np.random.default_rng(99)
    by_group: dict[tuple[str, str], list[np.ndarray]] = {}
    for p in contract.profiles:
        by_group.setdefault((p.condition, p.channel), []).append(
            np.asarray(p.intensity, float)
        )
    for (cond, channel), curves in by_group.items():
        arr = np.asarray(curves)
        mean_curve = arr.mean(axis=0)
        boot = []
        for _ in range(200):
            idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
            boot.append(arr[idx].mean(axis=0))
        boot_arr = np.asarray(boot)
        lo = np.quantile(boot_arr, 0.025, axis=0)
        hi = np.quantile(boot_arr, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ls = _CHANNEL_LINESTYLE.get(channel, "-")
        ax.fill_between(distance_arr, lo, hi,
                        color=colour, alpha=0.16,
                        linewidth=0, zorder=2)
        ax.plot(distance_arr, mean_curve,
                color=colour, lw=1.4, ls=ls, zorder=4,
                label=f"{cond} · {channel}")
        peak_d = distance_arr[int(np.argmax(mean_curve))]
        bits.append(f"{cond}/{channel}: peak at "
                    f"{smart_fmt(float(peak_d))} um")

    ax.set_xlabel("signed distance from edge (um)  "
                  "(+ = inside cell)")
    ax.set_ylabel("intensity (a.u.)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.4, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
