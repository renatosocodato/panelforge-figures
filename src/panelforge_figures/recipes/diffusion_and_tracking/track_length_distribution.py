"""Track-length distribution — CCDF of track duration (seconds) per
condition with photobleaching-censoring marker. Distinct from
`track_persistence_hist` (which measures spatial straightness, not
temporal duration).
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


class TrackLengthInput(RecipeContract):
    duration_s_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → list of track durations (seconds)"
    )
    censor_s: float | None = Field(
        None,
        description="acquisition-length cutoff (tracks censored beyond this)",
    )
    title: str = "Track-duration CCDF"


def _demo() -> TrackLengthInput:
    rng = np.random.default_rng(1623)
    return TrackLengthInput(
        duration_s_by_condition={
            "control":   rng.exponential(4.5, 300).tolist(),
            "stabilised": rng.exponential(7.2, 300).tolist(),
            "destabilised": rng.exponential(2.6, 300).tolist(),
        },
        censor_s=15.0,
    )


_META = RecipeMetadata(
    name="track_length_distribution",
    modality="diffusion_and_tracking",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How long do tracks persist across conditions, and is there a "
        "photobleaching / censoring bias at the acquisition cutoff?"
    ),
    required_fields=("duration_s_by_condition",),
    optional_fields=("censor_s", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("track_persistence_hist",),
)


@register_recipe(
    metadata=_META,
    contract=TrackLengthInput,
    demo_contract=_demo,
)
def render(contract: TrackLengthInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    for i, (name, durs) in enumerate(contract.duration_s_by_condition.items()):
        v = np.sort(np.asarray(durs, float))
        ccdf = 1.0 - np.arange(1, len(v) + 1) / len(v)
        color = palette[i % len(palette.colors)]
        med = float(np.median(v))
        ax.plot(v, ccdf, color=color, lw=1.2, zorder=4,
                label=f"{name}  (med {smart_fmt(med)} s)")

    if contract.censor_s is not None:
        ax.axvline(contract.censor_s, color="#888888", lw=0.8, ls="--",
                   zorder=3,
                   label=f"censor at {smart_fmt(float(contract.censor_s))} s")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("track duration (s)")
    ax.set_ylabel("P(duration > t)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
