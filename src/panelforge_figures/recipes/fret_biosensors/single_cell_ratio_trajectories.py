"""Single-cell ratio trajectories — stack of per-cell traces, grouped by response type."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class SingleCellTrajectoriesInput(RecipeContract):
    t: list[float] = Field(...)
    groups: dict[str, list[list[float]]] = Field(
        ..., description="group → list of per-cell traces"
    )
    stim_time_s: float | None = None
    y_label: str = r"F$_\mathrm{A}$/F$_\mathrm{D}$"
    title: str = "Single-cell trajectories"


def _demo() -> SingleCellTrajectoriesInput:
    rng = np.random.default_rng(193)
    t = np.linspace(-15, 90, 160)
    groups: dict[str, list[list[float]]] = {
        "responder": [],
        "weak responder": [],
        "non-responder": [],
    }
    for _ in range(15):
        r = 1.0 + 0.45 * np.tanh(np.clip(t / 8, 0, None)) + rng.normal(0, 0.02, t.size)
        groups["responder"].append(r.tolist())
    for _ in range(15):
        r = 1.0 + 0.15 * np.tanh(np.clip(t / 8, 0, None)) + rng.normal(0, 0.02, t.size)
        groups["weak responder"].append(r.tolist())
    for _ in range(10):
        r = 1.0 + 0.02 * np.tanh(np.clip(t / 8, 0, None)) + rng.normal(0, 0.025, t.size)
        groups["non-responder"].append(r.tolist())
    return SingleCellTrajectoriesInput(
        t=t.tolist(),
        groups=groups,
        stim_time_s=0.0,
    )


_META = RecipeMetadata(
    name="single_cell_ratio_trajectories",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How do per-cell ratio trajectories separate into responder / weak-responder / non-responder populations?",
    required_fields=("t", "groups"),
    optional_fields=("stim_time_s", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("stimulus_response_fan",),
)


@register_recipe(metadata=_META, contract=SingleCellTrajectoriesInput, demo_contract=_demo)
def render(contract: SingleCellTrajectoriesInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    # Map groups to stable colors.
    fallback_colors = [palette.pick("ratio_up"), palette.pick("acceptor"),
                       palette.pick("ratio_down")]

    t = np.array(contract.t, dtype=float)

    if contract.stim_time_s is not None:
        ax.axvline(contract.stim_time_s, color="#888888", lw=0.6, ls="--", zorder=1)

    ax.axhline(1.0, color="#AAAAAA", lw=0.5, ls=":", zorder=1)

    for i, (name, traces) in enumerate(contract.groups.items()):
        color = fallback_colors[i % len(fallback_colors)]
        for tr in traces:
            ax.plot(t, tr, color=color, lw=0.5, alpha=0.35, zorder=3)
        # Mean line for this group — boost contrast.
        stacked = np.vstack([np.array(tr) for tr in traces])
        mean = stacked.mean(axis=0)
        ax.plot(t, mean, color=color, lw=1.4, zorder=5, label=name)

    ax.set_xlabel("time from stim (s)")
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
