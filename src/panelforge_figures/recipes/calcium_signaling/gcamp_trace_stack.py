"""GCaMP trace stack — vertically offset per-cell ΔF/F traces."""

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


class GCaMPStackInput(RecipeContract):
    t: list[float] = Field(...)
    traces: list[list[float]] = Field(..., description="per-cell ΔF/F traces")
    cell_ids: list[str] | None = None
    offset: float = 1.5
    title: str = "GCaMP traces"


def _demo() -> GCaMPStackInput:
    rng = np.random.default_rng(227)
    t = np.linspace(0, 60, 400)
    traces = []
    for _ in range(12):
        base = rng.normal(0, 0.05, t.size)
        # Add random calcium events.
        n_events = rng.poisson(3)
        for _k in range(n_events):
            t0 = rng.uniform(2, 58)
            tau = rng.uniform(0.8, 2.0)
            amp = rng.uniform(0.5, 2.0)
            mask = t >= t0
            base[mask] += amp * np.exp(-(t[mask] - t0) / tau)
        traces.append(base.tolist())
    return GCaMPStackInput(
        t=t.tolist(),
        traces=traces,
    )


_META = RecipeMetadata(
    name="gcamp_trace_stack",
    modality="calcium_signaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How do per-cell ΔF/F GCaMP traces look, side by side on a shared time axis?",
    required_fields=("t", "traces"),
    optional_fields=("cell_ids", "offset", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("event_raster_with_rate",),
)


@register_recipe(metadata=_META, contract=GCaMPStackInput, demo_contract=_demo)
def render(contract: GCaMPStackInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    # Alternating colors from the microglia-states palette for visual grouping.
    colors_cycle = [palette.pick("surveillant"), palette.pick("activated"),
                    palette.pick("homeostatic")]

    t = np.array(contract.t, dtype=float)
    offset = contract.offset

    used_labels: set[int] = set()
    state_names = ["surveillant", "activated", "homeostatic"]
    for i, tr in enumerate(contract.traces):
        color_idx = i % len(colors_cycle)
        color = colors_cycle[color_idx]
        y = np.array(tr, dtype=float) + i * offset
        # Label only the first trace of each color so the legend stays compact.
        label = state_names[color_idx] if color_idx not in used_labels else None
        used_labels.add(color_idx)
        ax.plot(t, y, color=color, lw=0.8, zorder=3, label=label)

    # Legend — compact row of the color cycle.
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.08),
              fontsize=6.4, frameon=False, ncol=3,
              handlelength=1.4, columnspacing=0.8)

    # Scale bar for ΔF/F (1.0 unit vertical).
    if contract.traces:
        x_sb = t[-1] + 0.02 * (t[-1] - t[0])
        y_top = (len(contract.traces) - 1) * offset + 1.0
        ax.plot([x_sb, x_sb], [y_top - 1.0, y_top],
                color="#333333", lw=1.5, clip_on=False, zorder=5)
        ax.text(x_sb + 0.005 * (t[-1] - t[0]), y_top - 0.5, r"1 $\Delta$F/F",
                ha="left", va="center", fontsize=6.4, color="#333333",
                clip_on=False)

    ax.set_xlabel("time (s)")
    ax.set_yticks([])
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Cell labels on the left.
    ids = contract.cell_ids or [f"c{i+1:02d}" for i in range(len(contract.traces))]
    for i, nm in enumerate(ids):
        ax.text(t[0] - 0.01 * (t[-1] - t[0]), i * offset,
                nm, ha="right", va="center",
                fontsize=6.4, color="#444444")

    for s in ("left",):
        ax.spines[s].set_visible(False)
    ax.set_xlim(t[0], t[-1])
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
