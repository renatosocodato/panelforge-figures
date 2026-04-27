"""Territory contact network overlay — per-cell territory map with
contact-patch graph nodes (at centroids) + edges (as connectivity
lines) overlaid; per-cell network density / connectivity callout.

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
from ._shared import (
    CellWithContactNetwork,
    ContactPatchNetwork,
    ZoneTerritoryMap,
    _demo_zone_label_map,
    _demo_zone_palette,
)


class TerritoryContactNetworkInput(RecipeContract):
    cells: list[CellWithContactNetwork] = Field(..., min_length=2)
    title: str = "Territory contact network overlay"


def _demo() -> TerritoryContactNetworkInput:
    rng = np.random.default_rng(541)
    cells: list[CellWithContactNetwork] = []
    H, W = 80, 80
    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.sqrt((yy - H / 2) ** 2 + (xx - W / 2) ** 2)

    for cell_id, cond, n_nodes, edge_p in (
        ("WT_2", "WT", 8, 0.18),
        ("LI_12", "LI", 14, 0.40),
    ):
        # Zone map: contact / desert / intermediate / far.
        zones = np.full((H, W), 3, int)
        zones[radial < 32] = 2
        zones[radial < 22] = 1
        zones[radial < 14] = 0

        # Place nodes within contact zone (zone == 0) for clarity.
        nodes = []
        for _ in range(n_nodes):
            angle = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(2, 14)
            x = W / 2 + r * np.cos(angle)
            y = H / 2 + r * np.sin(angle)
            nodes.append([float(x), float(y)])

        # Edges: random with probability p between every pair.
        edges = []
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                if rng.random() < edge_p:
                    edges.append([i, j])

        # ROI polygon: rough cell outline.
        theta = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        roi = []
        for t in theta:
            r0 = 30 + rng.normal(0, 1.5)
            roi.append([float(W / 2 + r0 * np.cos(t)),
                        float(H / 2 + r0 * np.sin(t))])

        cells.append(CellWithContactNetwork(
            territory=ZoneTerritoryMap(
                cell_id=cell_id,
                zone_grid=zones.tolist(),
                zone_label_map=_demo_zone_label_map(),
                pixel_um=0.5,
            ),
            network=ContactPatchNetwork(
                cell_id=cell_id,
                node_xy_um=nodes,
                edges=edges,
                node_weights=[
                    float(rng.uniform(2, 8)) for _ in range(n_nodes)
                ],
                roi_polygon_um=roi,
            ),
        ))
    return TerritoryContactNetworkInput(cells=cells)


_META = RecipeMetadata(
    name="territory_contact_network_overlay",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Per cell, how do contact patches and their connectivity "
        "edges overlay on the zone-resolved territory map, and "
        "does network density differ between conditions?"
    ),
    required_fields=("cells",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("territory_change_pre_post",
                              "actin_mt_ratio_spatial_map"),
)


@register_recipe(
    metadata=_META,
    contract=TerritoryContactNetworkInput,
    demo_contract=_demo,
)
def render(contract: TerritoryContactNetworkInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.cells)

    # Sentinel imshow for heatmap family rule (parked off-axes).
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap="cividis", aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    pad_left = 0.06
    pad_right = 0.04
    pad_bottom = 0.08
    pad_top = 0.18
    gap = 0.04
    panel_w = (1.0 - pad_left - pad_right - gap * (n - 1)) / n
    panel_h = 1.0 - pad_bottom - pad_top

    palette = _demo_zone_palette()
    from matplotlib.colors import ListedColormap
    zone_keys = sorted(palette)
    zone_cmap = ListedColormap([palette[k] for k in zone_keys])

    bits = []
    for i, cell in enumerate(contract.cells):
        x_lo = pad_left + i * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)

        zones = np.asarray(cell.territory.zone_grid, int)
        sub.imshow(zones, cmap=zone_cmap, alpha=0.55,
                   vmin=min(zone_keys) - 0.5,
                   vmax=max(zone_keys) + 0.5,
                   aspect="equal", interpolation="nearest", zorder=2)

        # Network edges first (so they sit under nodes).
        nodes = np.asarray(cell.network.node_xy_um, float)
        n_edges = len(cell.network.edges)
        # Edge linewidth shrinks with edge count to avoid clutter.
        edge_lw = max(0.4, 1.4 / max(np.sqrt(max(n_edges, 1)), 1))
        for (a, b) in cell.network.edges:
            sub.plot([nodes[a, 0], nodes[b, 0]],
                     [nodes[a, 1], nodes[b, 1]],
                     color="#FFFFFF", lw=edge_lw, alpha=0.9, zorder=4)
            sub.plot([nodes[a, 0], nodes[b, 0]],
                     [nodes[a, 1], nodes[b, 1]],
                     color="#222222", lw=edge_lw * 0.5, alpha=0.85,
                     zorder=5)

        # Nodes on top.
        node_sizes = (np.asarray(cell.network.node_weights, float) * 6.0
                      if cell.network.node_weights is not None
                      else np.full(nodes.shape[0], 24.0))
        sub.scatter(nodes[:, 0], nodes[:, 1],
                    s=node_sizes,
                    facecolor="#FFFFFF", edgecolor="#222222",
                    linewidth=0.7, zorder=6)

        # ROI polygon outline.
        if cell.network.roi_polygon_um is not None:
            roi = np.asarray(cell.network.roi_polygon_um, float)
            roi_closed = np.vstack([roi, roi[0:1]])
            sub.plot(roi_closed[:, 0], roi_closed[:, 1],
                     color="#222222", lw=0.7, ls="--", zorder=3)

        sub.set_xticks([])
        sub.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            sub.spines[side].set_visible(False)
        sub.set_aspect("equal")

        n_nodes = len(cell.network.node_xy_um)
        density = (2.0 * n_edges
                   / max(n_nodes * (n_nodes - 1), 1))
        sub.set_title(
            f"{cell.territory.cell_id}  ·  "
            f"{n_nodes}n  ·  {n_edges}e  ·  "
            f"density {smart_fmt(density)}",
            fontsize=7.0, pad=2,
        )
        bits.append(f"{cell.territory.cell_id}: density "
                    f"{smart_fmt(density)}")

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
