"""Cue-to-reorientation latency (tau_reorient) — split-violin per
condition.

How long after cue onset does a cell's heading first align with the
cue direction (within an alignment-threshold cone)?

Split-violin family: >=2 violin bodies + >=1 median marker. Same
shape as launch_to_commitment_latency.
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
from ._shared import LatencyDistribution

_CONDITION_PALETTE = {
    "control": "#37474F",
    "DISC1":   "#EF5350",
    "treated": "#26A69A",
    "rescue":  "#AB47BC",
    "WT":      "#37474F",
    "LI":      "#EF5350",
}


class CueToReorientationInput(RecipeContract):
    latencies: list[LatencyDistribution] = Field(..., min_length=2)
    alignment_threshold_deg: float = 30.0
    log_y: bool = False
    title: str = "Cue -> reorientation latency (tau_reorient)"


def _demo() -> CueToReorientationInput:
    rng = np.random.default_rng(2807)
    return CueToReorientationInput(
        latencies=[
            LatencyDistribution(
                label="tau_reorient", condition="control",
                values_s=rng.gamma(shape=2.5, scale=4.0, size=70).tolist(),
                n_subjects=70,
            ),
            LatencyDistribution(
                label="tau_reorient", condition="DISC1",
                values_s=rng.gamma(shape=2.0, scale=8.0, size=80).tolist(),
                n_subjects=80,
            ),
        ],
    )


_META = RecipeMetadata(
    name="cue_to_reorientation_latency",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How long after cue onset does a cell's heading first align "
        "with the cue direction (within the alignment-threshold cone)?"
    ),
    required_fields=("latencies",),
    optional_fields=("alignment_threshold_deg", "log_y", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("launch_to_commitment_latency",),
)


@register_recipe(
    metadata=_META,
    contract=CueToReorientationInput,
    demo_contract=_demo,
)
def render(contract: CueToReorientationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    conditions = [lat.condition for lat in contract.latencies]
    positions = np.arange(len(conditions))
    medians: dict[str, float] = {}
    for pos, lat in zip(positions, contract.latencies):
        vals = np.asarray(lat.values_s, float)
        if vals.size == 0:
            continue
        colour = _CONDITION_PALETTE.get(lat.condition, "#37474F")
        parts = ax.violinplot([vals], positions=[pos], widths=0.78,
                              showmeans=False, showmedians=False,
                              showextrema=False)
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
            medians[lat.condition] = med

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel("tau_reorient (s)")
    ax.set_xlabel("condition")
    if contract.log_y:
        ax.set_yscale("log")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    bits = [f"{c}: med {smart_fmt(m)} s" for c, m in medians.items()]
    n_total = sum((lat.n_subjects or len(lat.values_s))
                  for lat in contract.latencies)
    ax.set_title(
        f"{contract.title}  ·  alignment within "
        f"{smart_fmt(contract.alignment_threshold_deg)} deg  ·  "
        f"n = {n_total}  ·  " + "   ".join(bits),
        fontsize=7.6, pad=4,
    )
    return ax
