"""Cell-track trajectory field — XY tracks colored by cell state."""

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


class TrackField(RecipeContract):
    track_id: str
    x_um: list[float]
    y_um: list[float]
    state: str


class TrackFieldInput(RecipeContract):
    tracks: list[TrackField] = Field(..., min_length=3)
    extent_um: tuple[float, float, float, float] = (0.0, 200.0, 0.0, 200.0)
    title: str = "Cell-track trajectories"


def _demo() -> TrackFieldInput:
    rng = np.random.default_rng(461)
    tracks = []
    for i in range(24):
        state = rng.choice(["homeostatic", "surveillant", "activated"],
                           p=[0.45, 0.35, 0.20])
        n = int(rng.integers(40, 120))
        x0, y0 = rng.uniform(30, 170), rng.uniform(30, 170)
        drift = {"activated": 0.6, "surveillant": 0.25, "homeostatic": 0.05}[state]
        step_size = {"activated": 1.4, "surveillant": 0.9, "homeostatic": 0.4}[state]
        theta = rng.uniform(0, 2 * np.pi)
        xs, ys = [x0], [y0]
        for _ in range(n):
            dx = drift * np.cos(theta) + rng.normal(0, step_size)
            dy = drift * np.sin(theta) + rng.normal(0, step_size)
            theta += rng.normal(0, 0.2)
            xs.append(xs[-1] + dx)
            ys.append(ys[-1] + dy)
        tracks.append(TrackField(
            track_id=f"t{i:02d}", x_um=xs, y_um=ys, state=state,
        ))
    return TrackFieldInput(tracks=tracks)


_META = RecipeMetadata(
    name="cell_track_trajectory_field",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question="How do individual cells move across a tissue field, and does motility differ by state?",
    required_fields=("tracks",),
    optional_fields=("extent_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("migration_rose_diagram",),
)


@register_recipe(metadata=_META, contract=TrackFieldInput, demo_contract=_demo)
def render(contract: TrackFieldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x0, x1, y0, y1 = contract.extent_um
    states_seen: set[str] = set()
    for tr in contract.tracks:
        color = (palette.pick(tr.state)
                 if tr.state in palette.semantic else palette[0])
        label = tr.state if tr.state not in states_seen else None
        states_seen.add(tr.state)
        xs = np.array(tr.x_um, dtype=float)
        ys = np.array(tr.y_um, dtype=float)
        ax.plot(xs, ys, color=color, lw=0.7, alpha=0.8, zorder=3, label=label)
        ax.scatter([xs[0]], [ys[0]], s=10, facecolor=color,
                   edgecolor="white", linewidth=0.4, zorder=4)
        ax.scatter([xs[-1]], [ys[-1]], s=20, marker="*",
                   facecolor=color, edgecolor="white", linewidth=0.5, zorder=5)

    # Scale bar (20 μm).
    sb_x, sb_y = x0 + 10, y0 + 8
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y], color="#111111",
            lw=2.2, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 10, sb_y + 2, r"20 $\mu$m",
            ha="center", va="bottom", fontsize=6.4, color="#111111")

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  N tracks = {len(contract.tracks)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4, title=f"open circle = start; star = end (t ~ {smart_fmt(100)} steps)",
              title_fontsize=5.8)
    return ax
