"""Territory zone overlay (intravital) — multi-channel intravital
field rendered as RGB composite with per-pixel territory-zone
contour outlines drawn on top.

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
)
from ...recipes.actin_microtubule_morphometry._shared import (
    MultiChannelField,
    ZoneTerritoryMap,
    _demo_zone_label_map,
    _demo_zone_palette,
)
from ._aesthetic import AESTHETIC


class TerritoryZoneOverlayInput(RecipeContract):
    field: MultiChannelField = Field(...)
    zone_map: ZoneTerritoryMap = Field(...)
    title: str = "Territory zone overlay (intravital)"


def _demo() -> TerritoryZoneOverlayInput:
    rng = np.random.default_rng(531)
    H, W = 128, 128
    yy, xx = np.mgrid[0:H, 0:W]
    # Three cells at different field positions.
    centres = [(40, 30), (80, 60), (95, 95)]
    radii = [22, 28, 18]
    actin = np.zeros((H, W))
    mt = np.zeros((H, W))
    nuc = np.zeros((H, W))
    for (cy, cx), r0 in zip(centres, radii):
        d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        actin += np.exp(-((d / r0) ** 2)) * 0.9
        mt += np.exp(-((d / (r0 * 0.85)) ** 2)) * 0.65
        nuc += np.exp(-((d / (r0 * 0.4)) ** 2)) * 0.85
    actin = np.clip(actin + rng.normal(0, 0.02, (H, W)), 0, 1)
    mt = np.clip(mt + rng.normal(0, 0.02, (H, W)), 0, 1)
    nuc = np.clip(nuc + rng.normal(0, 0.02, (H, W)), 0, 1)

    # Zone map: 0=contact (cell interior), 1=desert, 2=intermediate,
    # 3=far (background).
    zones = np.full((H, W), 3, int)
    for (cy, cx), r0 in zip(centres, radii):
        d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        zones[d < r0 * 1.6] = 2
        zones[d < r0 * 1.1] = 1
        zones[d < r0 * 0.7] = 0

    return TerritoryZoneOverlayInput(
        field=MultiChannelField(
            field_id="FOV01",
            red_channel=actin.tolist(),
            green_channel=mt.tolist(),
            blue_channel=nuc.tolist(),
            pixel_um=0.4,
            channel_labels={"red": "F-actin", "green": "MT",
                            "blue": "DAPI"},
        ),
        zone_map=ZoneTerritoryMap(
            cell_id="FOV01",
            zone_grid=zones.tolist(),
            zone_label_map=_demo_zone_label_map(),
            pixel_um=0.4,
        ),
    )


_META = RecipeMetadata(
    name="territory_zone_overlay_intravital",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across an intravital field, how do multi-channel cell "
        "signals overlay onto territory zones (contact / desert / "
        "intermediate / far)?"
    ),
    required_fields=("field", "zone_map"),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("multi_channel_intravital_overlay",),
)


@register_recipe(
    metadata=_META,
    contract=TerritoryZoneOverlayInput,
    demo_contract=_demo,
)
def render(contract: TerritoryZoneOverlayInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    R = np.asarray(contract.field.red_channel, float)
    G = np.asarray(contract.field.green_channel, float)
    B = (np.asarray(contract.field.blue_channel, float)
         if contract.field.blue_channel is not None
         else np.zeros_like(R))
    # Per-channel normalisation (avoid one channel saturating the others).

    def _norm(x: np.ndarray) -> np.ndarray:
        lo, hi = float(np.percentile(x, 2)), float(np.percentile(x, 98))
        if hi <= lo:
            return np.clip(x, 0, 1)
        return np.clip((x - lo) / (hi - lo), 0, 1)

    rgb = np.stack([_norm(R), _norm(G), _norm(B)], axis=-1)
    ax.imshow(rgb, aspect="equal", zorder=2,
              interpolation="nearest")

    # Zone-contour overlay.
    zones = np.asarray(contract.zone_map.zone_grid, int)
    palette = _demo_zone_palette()
    label_map = contract.zone_map.zone_label_map
    # Draw per-zone-boundary contour (each integer zone) using
    # contour() at half-integer levels.
    H, W = zones.shape
    yy, xx = np.mgrid[0:H, 0:W]
    levels = sorted(set(zones.ravel().tolist()))
    for k in levels:
        if k == max(levels):
            continue   # outermost zone (background) — no inner boundary
        mask = (zones <= k).astype(float)
        ax.contour(xx, yy, mask, levels=[0.5],
                   colors=palette.get(k, "#FFFFFF"),
                   linewidths=1.2, zorder=4)

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    # Channel-label legend (top-right inside frame).
    ch_labels = contract.field.channel_labels
    legend_lines = [f"R: {ch_labels.get('red', 'red')}",
                    f"G: {ch_labels.get('green', 'green')}",
                    f"B: {ch_labels.get('blue', 'blue')}"]
    ax.text(0.97, 0.03, "  ·  ".join(legend_lines),
            transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.4,
            color="white", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.30",
                      fc="#222222", ec="none", alpha=0.65),
            zorder=6)

    # Zone legend (bottom strip).
    legend_ax = ax.inset_axes([0.0, -0.10, 1.0, 0.06])
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        legend_ax.spines[side].set_visible(False)
    sorted_levels = sorted(label_map)
    n_z = len(sorted_levels)
    import matplotlib.patches as mpatches
    for i, k in enumerate(sorted_levels):
        x_pos = (i + 0.5) / n_z
        legend_ax.add_patch(mpatches.Rectangle(
            (x_pos - 0.05, 0.30), 0.025, 0.40,
            facecolor=palette.get(k, "#FFFFFF"),
            edgecolor="white", linewidth=0.5,
            zorder=3, transform=legend_ax.transAxes,
        ))
        legend_ax.text(x_pos - 0.015, 0.50, label_map.get(k, str(k)),
                       transform=legend_ax.transAxes,
                       ha="left", va="center", fontsize=6.6,
                       color="#333333", zorder=4)

    zone_summary = ", ".join(
        f"{label_map.get(k, str(k))}: "
        f"{int((zones == k).sum() * 100 / zones.size)}%"
        for k in sorted_levels
    )
    ax.set_title(
        f"{contract.title}  ·  {contract.field.field_id}  ·  {zone_summary}",
        fontsize=8.2, pad=4,
    )
    return ax
