"""Donor/acceptor dual-channel view — side-by-side intensity images."""

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


class DonorAcceptorInput(RecipeContract):
    donor: list[list[float]] = Field(..., description="donor intensity image")
    acceptor: list[list[float]] = Field(..., description="acceptor intensity image")
    pixel_size_um: float = 0.2
    title: str = "Donor / acceptor channels"


def _demo() -> DonorAcceptorInput:
    rng = np.random.default_rng(179)
    H, W = 100, 140
    yy, xx = np.mgrid[:H, :W]
    donor = 250 + 180 * np.exp(-((xx - 55) ** 2 + (yy - 55) ** 2) / 900) + \
            rng.normal(0, 15, (H, W))
    acceptor = 80 + 240 * np.exp(-((xx - 55) ** 2 + (yy - 55) ** 2) / 900) + \
               rng.normal(0, 14, (H, W))
    return DonorAcceptorInput(
        donor=donor.tolist(),
        acceptor=acceptor.tolist(),
        pixel_size_um=0.2,
    )


_META = RecipeMetadata(
    name="donor_acceptor_dual_channel",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question="How do the raw donor and acceptor intensity images look, side by side, for a FRET acquisition?",
    required_fields=("donor", "acceptor"),
    optional_fields=("pixel_size_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("ratio_heatmap_over_field",),
)


@register_recipe(metadata=_META, contract=DonorAcceptorInput, demo_contract=_demo)
def render(contract: DonorAcceptorInput, ax=None, **_):
    """Split host axis into side-by-side donor | acceptor pair."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.6, 2.8))
        gs = fig.add_gridspec(1, 2, wspace=0.12)
        ax_d = fig.add_subplot(gs[0, 0])
        ax_a = fig.add_subplot(gs[0, 1])
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(1, 2, wspace=0.12)
        ax_d = fig.add_subplot(sub[0, 0])
        ax_a = fig.add_subplot(sub[0, 1])

    AESTHETIC.apply_to_ax(ax_d)
    AESTHETIC.apply_to_ax(ax_a)
    palette = get_palette(AESTHETIC.primary_palette)

    D = np.array(contract.donor, dtype=float)
    A = np.array(contract.acceptor, dtype=float)

    from matplotlib.colors import LinearSegmentedColormap
    donor_cmap = LinearSegmentedColormap.from_list(
        "donor", ["black", palette.pick("donor")], N=128,
    )
    acc_cmap = LinearSegmentedColormap.from_list(
        "acceptor", ["black", palette.pick("acceptor")], N=128,
    )

    extent = (0, D.shape[1] * contract.pixel_size_um,
              0, D.shape[0] * contract.pixel_size_um)
    ax_d.imshow(D, cmap=donor_cmap, aspect="equal",
                extent=extent, interpolation="nearest")
    ax_a.imshow(A, cmap=acc_cmap, aspect="equal",
                extent=extent, interpolation="nearest")

    for a, name in [(ax_d, "donor"), (ax_a, "acceptor")]:
        a.set_xticks([])
        a.set_yticks([])
        a.text(0.03, 0.97, name, transform=a.transAxes,
               ha="left", va="top", fontsize=7.0, color="white",
               bbox=dict(boxstyle="round,pad=0.16", fc="#333333",
                         ec="none", alpha=0.7),
               zorder=5)

    # Shared scale bar on donor panel (10 μm).
    x_sb = extent[1] * 0.05
    y_sb = extent[3] * 0.08
    ax_d.plot([x_sb, x_sb + 10], [y_sb, y_sb],
              color="white", lw=2.5, solid_capstyle="butt", zorder=6)
    ax_d.text(x_sb + 5, y_sb + 1.0, "10 μm",
              ha="center", va="bottom", fontsize=6.4, color="white",
              bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                        ec="none", alpha=0.65))

    fig.suptitle(contract.title, fontsize=9.6, y=1.02)
    return ax_d
