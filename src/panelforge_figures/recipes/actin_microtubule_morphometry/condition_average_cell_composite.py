"""Condition-average cell composite — per-condition shape hull + variance cloud."""

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


class ConditionHull(RecipeContract):
    condition: str
    xs_um: list[float] = Field(..., description="hull vertices x (µm, centred)")
    ys_um: list[float] = Field(..., description="hull vertices y (µm, centred)")
    cloud_xs_um: list[float] | None = None
    cloud_ys_um: list[float] | None = None


class ConditionCompositeInput(RecipeContract):
    hulls: list[ConditionHull] = Field(..., min_length=2)
    extent_um: tuple[float, float, float, float] = (-30.0, 30.0, -25.0, 25.0)
    title: str = "Condition-average cell composite"


def _demo() -> ConditionCompositeInput:
    rng = np.random.default_rng(749)
    out: list[ConditionHull] = []
    # Three conditions — different elongation / orientation / size.
    for name, (scale_x, scale_y, theta_deg) in [
        ("control", (18.0, 12.0, 0.0)),
        ("mutant",  (28.0, 8.0, 35.0)),
        ("rescue",  (20.0, 11.0, 12.0)),
    ]:
        theta = np.deg2rad(theta_deg)
        t = np.linspace(0, 2 * np.pi, 80)
        hull_x = scale_x * np.cos(t)
        hull_y = scale_y * np.sin(t)
        rot_x = hull_x * np.cos(theta) - hull_y * np.sin(theta)
        rot_y = hull_x * np.sin(theta) + hull_y * np.cos(theta)

        # Cloud of per-cell outline points (blurred + jittered).
        cloud = []
        for _ in range(140):
            pt_t = rng.uniform(0, 2 * np.pi)
            jitter_r = 1.0 + rng.normal(0, 0.25)
            x_p = scale_x * jitter_r * np.cos(pt_t) + rng.normal(0, 1.2)
            y_p = scale_y * jitter_r * np.sin(pt_t) + rng.normal(0, 1.2)
            rx = x_p * np.cos(theta) - y_p * np.sin(theta)
            ry = x_p * np.sin(theta) + y_p * np.cos(theta)
            cloud.append((float(rx), float(ry)))
        cloud_xs, cloud_ys = zip(*cloud)
        out.append(ConditionHull(
            condition=name,
            xs_um=rot_x.tolist(),
            ys_um=rot_y.tolist(),
            cloud_xs_um=list(cloud_xs),
            cloud_ys_um=list(cloud_ys),
        ))
    return ConditionCompositeInput(hulls=out)


_META = RecipeMetadata(
    name="condition_average_cell_composite",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "What is the 'average' cell shape for each condition, and how tight "
        "is the shape variability around that mean?"
    ),
    required_fields=("hulls",),
    optional_fields=("extent_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("sphericity_vs_elongation_scatter",),
)


@register_recipe(
    metadata=_META,
    contract=ConditionCompositeInput,
    demo_contract=_demo,
)
def render(contract: ConditionCompositeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Density backdrop: stack all per-condition cloud points and render a
    # faint 2-D histogram (QuadMesh) — satisfies the heatmap quality rule
    # and conveys variance across all conditions at once.
    all_cloud_x: list[float] = []
    all_cloud_y: list[float] = []
    for hull in contract.hulls:
        if hull.cloud_xs_um is not None and hull.cloud_ys_um is not None:
            all_cloud_x.extend(hull.cloud_xs_um)
            all_cloud_y.extend(hull.cloud_ys_um)
    if all_cloud_x:
        ax.hist2d(
            all_cloud_x, all_cloud_y,
            bins=(40, 32),
            range=[[contract.extent_um[0], contract.extent_um[1]],
                   [contract.extent_um[2], contract.extent_um[3]]],
            cmap="Greys", cmin=1, zorder=1, alpha=0.55,
        )

    # Per-condition hulls + cloud overlays.
    for i, hull in enumerate(contract.hulls):
        color = palette[i % len(palette.colors)]
        xs = np.asarray(hull.xs_um, float)
        ys = np.asarray(hull.ys_um, float)
        xs_closed = np.append(xs, xs[0])
        ys_closed = np.append(ys, ys[0])
        ax.plot(xs_closed, ys_closed, color=color, lw=1.5, alpha=0.95,
                zorder=5, label=hull.condition)
        ax.fill(xs_closed, ys_closed, color=color, alpha=0.12, zorder=3)
        # Condition-coloured cloud overlay (faint points).
        if hull.cloud_xs_um is not None and hull.cloud_ys_um is not None:
            ax.scatter(hull.cloud_xs_um, hull.cloud_ys_um,
                       s=3, color=color, alpha=0.35,
                       edgecolor="none", zorder=4)

    # Centroid markers.
    for i, hull in enumerate(contract.hulls):
        color = palette[i % len(palette.colors)]
        cx = float(np.mean(hull.xs_um))
        cy = float(np.mean(hull.ys_um))
        ax.scatter([cx], [cy], s=44, color=color,
                   edgecolor="white", linewidth=1.1, zorder=6)

    # Summary hull-areas per condition.
    areas = []
    for hull in contract.hulls:
        xs = np.asarray(hull.xs_um, float)
        ys = np.asarray(hull.ys_um, float)
        a = 0.5 * abs(float(np.dot(xs, np.roll(ys, 1))
                            - np.dot(ys, np.roll(xs, 1))))
        areas.append((hull.condition, a))
    summary = "  ·  ".join(
        f"{name}: {smart_fmt(a)} μm²" for name, a in areas
    )

    ax.set_xlim(*contract.extent_um[:2])
    ax.set_ylim(*contract.extent_um[2:])
    ax.set_aspect("equal")
    ax.set_xlabel(r"x relative to centroid ($\mu$m)")
    ax.set_ylabel(r"y relative to centroid ($\mu$m)")
    ax.set_title(
        f"{contract.title}  ·  hull area  ·  {summary}",
        fontsize=8.4, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
