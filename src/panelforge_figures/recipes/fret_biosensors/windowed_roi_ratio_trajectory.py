"""Windowed-ROI ratio trajectories — per-sub-region time-series colored by position."""

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


class WindowedROIInput(RecipeContract):
    time_s: list[float] = Field(...)
    window_positions: list[float] = Field(
        ..., description="arc-length or distance position of each window (μm)"
    )
    ratio_matrix: list[list[float]] = Field(
        ..., description="[n_windows × n_time] per-window ratio trajectories"
    )
    window_labels: list[str] | None = None
    title: str = "Windowed ROI · ratio trajectories"


def _demo() -> WindowedROIInput:
    rng = np.random.default_rng(613)
    n_win = 14
    positions = np.linspace(0.0, 28.0, n_win)  # arc length along a leading edge, μm
    times = np.linspace(0.0, 180.0, 90)
    # Edge windows (low position) respond fast and large; interior windows
    # respond slower and smaller — a canonical leading-edge signature.
    rise_t = 40.0 + positions * 1.5           # later rise further from edge
    amp = 0.45 * np.exp(-positions / 14.0)     # attenuated inward
    rows = []
    for w in range(n_win):
        traj = (1.0
                + amp[w] / (1.0 + np.exp(-(times - rise_t[w]) / 10.0))
                + rng.normal(0, 0.012, times.size))
        rows.append(traj.tolist())
    return WindowedROIInput(
        time_s=times.tolist(),
        window_positions=positions.tolist(),
        ratio_matrix=rows,
        window_labels=[f"w{w:02d}" for w in range(n_win)],
    )


_META = RecipeMetadata(
    name="windowed_roi_ratio_trajectory",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Along a migrating cell's leading edge or a chosen perimeter path, "
        "how does the FRET ratio in each of N windowed sub-ROIs evolve over time?"
    ),
    required_fields=("time_s", "window_positions", "ratio_matrix"),
    optional_fields=("window_labels", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=(
        "single_cell_ratio_trajectories",
        "roi_ratio_summary_grid",
    ),
)


@register_recipe(
    metadata=_META,
    contract=WindowedROIInput,
    demo_contract=_demo,
)
def render(contract: WindowedROIInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_s, dtype=float)
    positions = np.asarray(contract.window_positions, dtype=float)
    M = np.asarray(contract.ratio_matrix, dtype=float)
    n_win = M.shape[0]

    # Colour each window by its arc-length position: viridis edge → interior.
    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    pos_min, pos_max = float(positions.min()), float(positions.max())
    span = max(pos_max - pos_min, 1e-9)
    # The colorbar and the inset schematic together communicate window
    # identity — an additional per-line legend would only overlap the
    # high-response traces in the upper-right quadrant.
    for w in range(n_win):
        frac = (positions[w] - pos_min) / span
        ax.plot(t, M[w], color=cmap(frac), lw=1.0, alpha=0.9, zorder=3)

    # Reference neutral line at ratio = 1.0.
    ax.axhline(1.0, color="#888888", lw=0.5, ls=":", zorder=1)

    # Position colorbar proxy.
    sm = mpl.cm.ScalarMappable(
        norm=mpl.colors.Normalize(vmin=pos_min, vmax=pos_max),
        cmap=cmap,
    )
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label(r"window position ($\mu$m · edge $\to$ interior)",
                   fontsize=6.4)
    cbar.ax.tick_params(labelsize=6.0)

    # Small inset schematic showing N windows tiled along a line.
    # Positioned in the upper-left quadrant where traces are still near
    # the baseline at small t — the earlier lower-left placement sat on
    # top of the traces and the baseline guide.
    inset = ax.inset_axes([0.06, 0.76, 0.32, 0.18])
    inset.set_xlim(0, 1)
    inset.set_ylim(0, 1)
    inset.set_xticks([])
    inset.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        inset.spines[side].set_visible(False)
    for w in range(n_win):
        frac = w / max(n_win - 1, 1)
        inset.add_patch(
            mpl.patches.Rectangle(
                (0.04 + 0.90 * frac - 0.03, 0.30),
                0.06, 0.40,
                facecolor=cmap(frac), edgecolor="white", linewidth=0.4,
            )
        )
    inset.text(0.04, 0.84, "windows", ha="left", va="top",
               fontsize=5.8, color="#444444")
    inset.text(0.05, 0.12, "edge", ha="left", va="bottom",
               fontsize=5.6, color="#666666")
    inset.text(0.95, 0.12, "interior", ha="right", va="bottom",
               fontsize=5.6, color="#666666")

    # Per-window peak Δ at the end.
    max_delta = float(np.max(M[:, -1] - M[:, 0]))
    ax.set_xlabel("time (s)")
    ax.set_ylabel(r"F$_A$/F$_D$")
    ax.set_xlim(float(t.min()), float(t.max()))
    ax.set_title(
        f"{contract.title}  ·  N = {n_win} windows, "
        f"peak $\\Delta$ = {smart_fmt(max_delta)}",
        fontsize=9.0, pad=4,
    )
    # Minimal legend proxy: single entry explaining the line colouring
    # (the per-window legend would overlap the high-response traces).
    from matplotlib.lines import Line2D
    ax.legend(
        handles=[Line2D([0], [0], color=cmap(0.5), lw=1.2,
                        label=f"per-window ratio trace (N = {n_win})")],
        fontsize=6.4, frameon=False, loc="lower right", handlelength=1.6,
    )
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
