"""Airyscan → skeleton → zone-territory triptych — three-panel
processed-image triptych per cell showing the multiscale workflow:
raw Airyscan intensity → skeleton overlay → zone-resolved territory
map. One row per representative cell.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC
from ._shared import AiryscanTriptychBundle, _demo_zone_label_map, _demo_zone_palette


class AiryscanTriptychInput(RecipeContract):
    bundles: list[AiryscanTriptychBundle] = Field(..., min_length=1)
    title: str = "Airyscan to zone-territory triptych"


def _demo() -> AiryscanTriptychInput:
    rng = np.random.default_rng(521)
    bundles: list[AiryscanTriptychBundle] = []
    H, W = 96, 96
    cy, cx = H // 2, W // 2
    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    for cell_id, cond, ar in (("WT_2", "WT", 1.05),
                              ("LI_12", "LI", 1.5)):
        # Raw: blob + ramified processes.
        blob = np.exp(-((radial / 22) ** 2))
        proc = np.zeros((H, W))
        n_proc = 6 if cond == "WT" else 4
        for k in range(n_proc):
            ang = 2 * np.pi * k / n_proc
            for t in np.linspace(0, 1, 50):
                px = int(cx + t * 32 * ar * np.cos(ang))
                py = int(cy + t * 32 * np.sin(ang))
                if 0 <= px < W and 0 <= py < H:
                    proc[py, px] = max(proc[py, px], 0.9 - t * 0.3)
        proc = np.clip(proc + rng.normal(0, 0.02, (H, W)), 0, 1)
        raw = np.clip(blob * 0.6 + proc, 0, 1)

        # Skeleton: thinned-line approximation.
        skel = np.zeros((H, W))
        for k in range(n_proc):
            ang = 2 * np.pi * k / n_proc
            for t in np.linspace(0, 1, 80):
                px = int(cx + t * 32 * ar * np.cos(ang))
                py = int(cy + t * 32 * np.sin(ang))
                if 0 <= px < W and 0 <= py < H:
                    skel[py, px] = 1.0
        # Skeleton crosses + central body shape.
        skel = np.maximum(skel, blob > 0.4)

        # Zone map: 0=contact, 1=desert, 2=intermediate, 3=far.
        # Concentric zones from cell core outward.
        zones = np.full((H, W), 3, int)
        zones[radial < 36] = 2
        zones[radial < 24] = 1
        zones[blob > 0.45] = 0  # contact patch interior
        # Add some genotype-specific structure: LI has more contact extent.
        if cond == "LI":
            zones[(radial < 30) & (blob > 0.25)] = 0
        bundles.append(AiryscanTriptychBundle(
            cell_id=cell_id, condition=cond,
            raw_image=raw.tolist(),
            skeleton_overlay=skel.tolist(),
            zone_map=zones.tolist(),
            zone_label_map=_demo_zone_label_map(),
            pixel_um=0.18,
        ))
    return AiryscanTriptychInput(bundles=bundles)


_META = RecipeMetadata(
    name="airyscan_to_zone_territory_triptych",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per representative cell, what is the multiscale workflow "
        "from raw Airyscan intensity, through skeleton overlay, to "
        "the zone-resolved territory map?"
    ),
    required_fields=("bundles",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("airyscan_segmentation_mosaic",),
)


@register_recipe(
    metadata=_META,
    contract=AiryscanTriptychInput,
    demo_contract=_demo,
)
def render(contract: AiryscanTriptychInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    n_rows = len(contract.bundles)
    n_cols = 3   # raw / skeleton / zone

    # Sentinel imshow on parent ax for matrix family rule; parked
    # off-axes so it never paints the parent's display area.
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap="Greys", aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    pad_left = 0.04
    pad_right = 0.02
    pad_bottom = 0.06
    pad_top = 0.18
    h_gap = 0.03
    v_gap = 0.10
    panel_w = (1.0 - pad_left - pad_right - h_gap * (n_cols - 1)) \
        / n_cols
    panel_h = (1.0 - pad_bottom - pad_top - v_gap * (n_rows - 1)) \
        / n_rows

    panel_titles = ["raw Airyscan", "skeleton overlay",
                    "zone-resolved territory"]
    zone_palette = _demo_zone_palette()

    # Build a categorical colormap for the zone map from the palette.
    from matplotlib.colors import ListedColormap
    zone_keys = sorted(zone_palette)
    zone_cmap = ListedColormap([zone_palette[k] for k in zone_keys])

    for row, bundle in enumerate(contract.bundles):
        # Top-down row order: row 0 at top.
        y_lo = pad_bottom + (n_rows - 1 - row) * (panel_h + v_gap)

        for col, name in enumerate(panel_titles):
            x_lo = pad_left + col * (panel_w + h_gap)
            sub = ax.inset_axes([x_lo, y_lo, panel_w, panel_h])
            AESTHETIC.apply_to_ax(sub)

            if col == 0:
                img = np.asarray(bundle.raw_image, float)
                sub.imshow(img, cmap="magma", aspect="equal", zorder=2)
            elif col == 1:
                # Skeleton: white skeleton on translucent raw.
                raw = np.asarray(bundle.raw_image, float)
                skel = np.asarray(bundle.skeleton_overlay, float)
                sub.imshow(raw, cmap="magma", aspect="equal",
                           alpha=0.55, zorder=2)
                sub.imshow(skel, cmap="Greys",
                           aspect="equal", alpha=skel * 0.85,
                           vmin=0, vmax=1, zorder=3)
            else:
                zones = np.asarray(bundle.zone_map, int)
                sub.imshow(zones, cmap=zone_cmap, aspect="equal",
                           vmin=min(zone_keys) - 0.5,
                           vmax=max(zone_keys) + 0.5,
                           interpolation="nearest", zorder=2)

            sub.set_xticks([])
            sub.set_yticks([])
            for side in ("top", "right", "left", "bottom"):
                sub.spines[side].set_visible(False)

            # Per-row label on the left-most panel.
            if col == 0:
                sub.set_ylabel(
                    f"{bundle.cell_id}\n({bundle.condition})",
                    fontsize=6.6, rotation=0,
                    ha="right", va="center", labelpad=22,
                )
            # Column header on top row.
            if row == 0:
                sub.set_title(name, fontsize=7.0, pad=2)

    # Zone legend strip below the bottom row.
    zone_label_map = (contract.bundles[0].zone_label_map
                      if contract.bundles else _demo_zone_label_map())
    legend_ax = ax.inset_axes([pad_left, 0.005,
                               1.0 - pad_left - pad_right, 0.04])
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        legend_ax.spines[side].set_visible(False)
    n_z = len(zone_keys)
    for i, k in enumerate(zone_keys):
        x_pos = (i + 0.5) / n_z
        legend_ax.add_patch(
            __import__("matplotlib").patches.Rectangle(
                (x_pos - 0.04, 0.30), 0.06, 0.40,
                facecolor=zone_palette[k], edgecolor="white",
                linewidth=0.4, zorder=3, transform=legend_ax.transAxes,
            )
        )
        legend_ax.text(x_pos + 0.04, 0.50,
                       zone_label_map.get(k, str(k)),
                       transform=legend_ax.transAxes,
                       ha="left", va="center", fontsize=6.4,
                       color="#333333", zorder=4)

    ax.set_title(
        f"{contract.title}  ·  {n_rows} cell"
        f"{'s' if n_rows != 1 else ''}",
        fontsize=8.4, pad=6,
    )
    return ax
