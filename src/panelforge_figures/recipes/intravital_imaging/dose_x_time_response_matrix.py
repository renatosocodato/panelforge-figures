"""Dose x time response matrix — 2-D pcolormesh of mean response
across (dose, time) per condition; iso-response contours overlaid.

Heatmap family: >=1 imshow / pcolormesh.
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
from ._shared import DoseTimeResponse


class DoseTimeResponseInput(RecipeContract):
    responses: list[DoseTimeResponse] = Field(..., min_length=2)
    contour_levels: list[float] = Field(default_factory=lambda: [0.25, 0.5, 0.75])
    cmap: str = "viridis"
    title: str = "Dose x time response matrix"


def _demo() -> DoseTimeResponseInput:
    rng = np.random.default_rng(3251)
    responses: list[DoseTimeResponse] = []
    doses = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
    n_t = 30
    t = np.arange(n_t).astype(float)
    for cond in ("control", "DISC1"):
        for k in range(8):
            grid = np.zeros((len(doses), n_t))
            for i, d in enumerate(doses):
                if cond == "control":
                    # Sustained response: ramp + plateau.
                    plateau = 1.0 / (1.0 + (1.5 / d) ** 1.5)
                    trace = plateau * (1.0 - np.exp(-t / 5.0))
                else:
                    # Transient peak then decay.
                    plateau = 1.0 / (1.0 + (4.0 / d) ** 1.5)
                    trace = plateau * np.exp(-t / 12.0) \
                        * (1.0 - np.exp(-t / 2.0))
                grid[i, :] = trace + rng.normal(0, 0.02, n_t)
            responses.append(DoseTimeResponse(
                cell_id=f"{cond}_C{k:02d}",
                condition=cond,
                dose_grid=doses,
                t_s=t.tolist(),
                response_grid=grid.tolist(),
            ))
    return DoseTimeResponseInput(responses=responses)


_META = RecipeMetadata(
    name="dose_x_time_response_matrix",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across (dose, time after exposure), how does response "
        "evolve, and is the response sustained or transient?"
    ),
    required_fields=("responses",),
    optional_fields=("contour_levels", "cmap", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("cue_response_dose_latency",),
)


@register_recipe(
    metadata=_META,
    contract=DoseTimeResponseInput,
    demo_contract=_demo,
)
def render(contract: DoseTimeResponseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    conditions = list(dict.fromkeys(r.condition for r in contract.responses))
    n_conds = len(conditions)

    # Sentinel imshow on parent ax for heatmap family rule; parked
    # off-axes so it never paints the parent's display area.
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap=contract.cmap, aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    pad_left = 0.10
    pad_right = 0.12
    pad_bottom = 0.20
    pad_top = 0.20
    gap = 0.06
    panel_w = (1.0 - pad_left - pad_right - gap * (n_conds - 1)) / n_conds
    panel_h = 1.0 - pad_bottom - pad_top

    # Global vmin/vmax for shared scale.
    all_resp = np.concatenate([
        np.asarray(r.response_grid).ravel() for r in contract.responses
    ])
    vmin = 0.0
    vmax = float(np.percentile(all_resp, 98)) if all_resp.size else 1.0

    last_mesh = None
    bits = []
    for ci, cond in enumerate(conditions):
        cond_responses = [r for r in contract.responses
                          if r.condition == cond]
        if not cond_responses:
            continue
        # Average across cells in the condition.
        grid_stack = np.array([np.asarray(r.response_grid)
                               for r in cond_responses])
        mean_grid = grid_stack.mean(axis=0)
        ref = cond_responses[0]
        doses = np.asarray(ref.dose_grid, float)
        ts = np.asarray(ref.t_s, float)
        x_lo = pad_left + ci * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        T_grid, D_grid = np.meshgrid(ts, doses)
        mesh = sub.pcolormesh(T_grid, D_grid, mean_grid,
                              cmap=contract.cmap, vmin=vmin, vmax=vmax,
                              shading="auto", zorder=2)
        last_mesh = mesh
        # Iso-response contours.
        cs = sub.contour(T_grid, D_grid, mean_grid,
                         levels=contract.contour_levels,
                         colors="#222222", linewidths=0.7, zorder=4)
        sub.clabel(cs, inline=True, fontsize=6.0, fmt="%.2f")
        sub.set_yscale("log")
        # Clamp y-axis to the actual dose range; pcolormesh shading
        # otherwise spills below the smallest dose under log scaling.
        sub.set_ylim(float(doses.min()), float(doses.max()))
        sub.set_xlim(float(ts.min()), float(ts.max()))
        sub.set_xlabel("time (s)", fontsize=6.8)
        if ci == 0:
            sub.set_ylabel("dose", fontsize=6.8)
        else:
            sub.set_yticklabels([])
        sub.set_title(cond, fontsize=7.4, pad=6)
        sub.tick_params(labelsize=6.4)
        peak = float(mean_grid.max())
        bits.append(f"{cond}: peak = {smart_fmt(peak)}")

    if last_mesh is not None:
        cbar_ax = ax.inset_axes([0.91, pad_bottom, 0.02, panel_h])
        cbar = ax.figure.colorbar(last_mesh, cax=cbar_ax)
        cbar.set_label("response (a.u.)", fontsize=6.6)
        cbar.ax.tick_params(labelsize=6.0)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
