"""Angular distribution — 2D histogram of particle Euler angles (rot × tilt)."""

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


class AngularInput(RecipeContract):
    rot_deg: list[float] = Field(..., description="φ / rotation angles in degrees")
    tilt_deg: list[float] = Field(..., description="θ / tilt angles in degrees")
    title: str = "Angular distribution"


def _demo() -> AngularInput:
    rng = np.random.default_rng(443)
    # Preferred orientations: two angular clusters + some background.
    cluster1 = np.column_stack([
        rng.normal(-60, 18, 900), rng.normal(30, 10, 900)
    ])
    cluster2 = np.column_stack([
        rng.normal(80, 22, 700), rng.normal(55, 14, 700)
    ])
    background = np.column_stack([
        rng.uniform(-180, 180, 600), rng.uniform(0, 90, 600)
    ])
    pts = np.vstack([cluster1, cluster2, background])
    return AngularInput(
        rot_deg=pts[:, 0].tolist(),
        tilt_deg=np.clip(pts[:, 1], 0, 90).tolist(),
    )


_META = RecipeMetadata(
    name="angular_distribution_hist",
    modality="cryoem_and_structure",
    family=RecipeFamily.heatmap,
    answers_question="Do particle orientations cover the rotational sphere evenly, or do preferred orientations cause bias?",
    required_fields=("rot_deg", "tilt_deg"),
    optional_fields=("title",),
    file_format_hints=("star", "csv"),
    alternatives_in_modality=("fsc_resolution_curve",),
)


@register_recipe(metadata=_META, contract=AngularInput, demo_contract=_demo)
def render(contract: AngularInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)

    rot = np.array(contract.rot_deg, dtype=float)
    tilt = np.clip(np.array(contract.tilt_deg, dtype=float), 0, 90)

    H, xe, ye = np.histogram2d(rot, tilt, bins=(36, 18),
                               range=[[-180, 180], [0, 90]])
    im = ax.imshow(
        H.T, origin="lower", extent=(-180, 180, 0, 90),
        cmap=AESTHETIC.continuous_cmap, aspect="auto",
        interpolation="nearest",
    )
    # Mark bin with maximum particle count.
    iy, ix = np.unravel_index(int(np.argmax(H.T)), H.T.shape)
    mx = 0.5 * (xe[ix] + xe[ix + 1])
    my = 0.5 * (ye[iy] + ye[iy + 1])
    ax.scatter([mx], [my], s=48, facecolor="none", edgecolor="white",
               linewidth=1.4, zorder=4)

    ax.set_xlabel(r"$\varphi$ (rotation, deg)")
    ax.set_ylabel(r"$\theta$ (tilt, deg)")
    ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_yticks([0, 30, 60, 90])
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("particles / bin", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_title(
        f"{contract.title}  ·  N = {rot.size}  peak {int(H.max())}/bin at ({smart_fmt(mx)}, {smart_fmt(my)})",
        fontsize=8.4, pad=4,
    )
    return ax
