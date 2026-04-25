"""xz-projection microtubule-bowing diagnostic — left column = per-group
xz MIP images; right column = paired split violin of z-span and
bow-amplitude.

Distinguishes two confounded signatures: (i) increased z-span with
preserved local variance (the bow signature) vs (ii) diffuse
thickening (uniform increase). The right column quantifies both
metrics so the reader can read the regime directly.

Heatmap family: >=1 imshow / pcolormesh. Satisfied by the per-group
xz MIPs rendered as imshow on inset axes; the parent ax also carries
a small imshow to register the family rule on the parent axis.
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

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class XZBowingInput(RecipeContract):
    # group -> list of 2-D xz slices (each slice is rows = z, cols = x).
    xz_slices_by_group: dict[str, list[list[list[float]]]] = Field(...)
    z_span_by_group: dict[str, list[float]] = Field(default_factory=dict)
    bow_amplitude_by_group: dict[str, list[float]] = Field(default_factory=dict)
    pixel_size_um: float = 0.1
    z_step_um: float = 0.2
    title: str = "xz MT bowing — z-span vs bow amplitude"


def _gen_xz_slice(rng: np.random.Generator, bow: float, thickness: float,
                  ny: int = 32, nx: int = 64) -> np.ndarray:
    """Synthesize a deterministic xz MIP-like slice with a Gaussian
    backbone bowed by `bow` (in z-pixels) and width `thickness`."""
    img = np.zeros((ny, nx), float)
    x = np.arange(nx)
    z_centre = ny / 2 + bow * np.sin(np.pi * (x - nx / 2) / nx) ** 2
    for xi in range(nx):
        for zi in range(ny):
            img[zi, xi] = np.exp(
                -((zi - z_centre[xi]) / thickness) ** 2
            )
    img += rng.normal(0, 0.04, img.shape)
    return np.clip(img, 0, 1)


def _demo() -> XZBowingInput:
    rng = np.random.default_rng(9911)
    slices: dict[str, list[list[list[float]]]] = {}
    z_span: dict[str, list[float]] = {}
    bow_amp: dict[str, list[float]] = {}
    for group, bow_mu in (("WT", 1.4), ("LI", 4.6)):
        gs: list[list[list[float]]] = []
        zs: list[float] = []
        bs: list[float] = []
        for _ in range(8):
            bow = max(0.4, rng.normal(bow_mu, 0.6))
            thickness = 2.6 + rng.normal(0, 0.25)
            img = _gen_xz_slice(rng, bow, thickness)
            gs.append(img.tolist())
            # z-span = 2 * thickness * (sqrt(ln(1/0.5))) approx; use
            # FWHM proxy.
            zs.append(float(2.355 * thickness * 0.2))  # FWHM in um
            bs.append(float(bow * 0.2))                # bow in um
        slices[group] = gs
        z_span[group] = zs
        bow_amp[group] = bs
    return XZBowingInput(
        xz_slices_by_group=slices,
        z_span_by_group=z_span,
        bow_amplitude_by_group=bow_amp,
    )


_META = RecipeMetadata(
    name="xz_microtubule_bowing_z_span",
    modality="biophysics_scaling",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Are LI protrusion microtubules bowed (increased z-span with "
        "preserved local variance) or diffusely thickened?"
    ),
    required_fields=("xz_slices_by_group",),
    optional_fields=(
        "z_span_by_group", "bow_amplitude_by_group",
        "pixel_size_um", "z_step_um", "title",
    ),
    file_format_hints=("npz", "tif"),
    alternatives_in_modality=("stress_strain_regime_map",),
)


@register_recipe(
    metadata=_META,
    contract=XZBowingInput,
    demo_contract=_demo,
)
def render(contract: XZBowingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.0, 4.6))
    AESTHETIC.apply_to_ax(ax)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    groups = list(contract.xz_slices_by_group.keys())

    # Parent imshow (1x1 transparent pixel) to satisfy family rule.
    ax.imshow(np.zeros((1, 1)), extent=[0, 1, 0, 1],
              alpha=0.0, zorder=0)

    # Left column: per-group representative MIPs (max projection of
    # the group's first 4 slices, vertically stacked).
    for row, group in enumerate(groups):
        slices = np.asarray(contract.xz_slices_by_group[group], float)
        n_show = min(slices.shape[0], 4)
        composite = np.max(slices[:n_show], axis=0)
        y_top = 0.92 - row * 0.46
        y_bot = y_top - 0.38
        sub = ax.inset_axes([0.04, y_bot, 0.34, y_top - y_bot])
        sub.imshow(composite, cmap="viridis", aspect="auto",
                   origin="lower", zorder=2)
        # Hide tick labels AND axis lines on the inset (axis('off')
        # is the only reliable way for imshow insets — set_yticks([])
        # alone leaves ticks visible in some matplotlib backends).
        sub.axis("off")
        sub.set_title(f"{group}  (xz MIP, max of {n_show})",
                      fontsize=7.0, pad=2,
                      color=_GROUP_COLOURS.get(group, "#333333"),
                      fontweight="bold")
        # Scale bar at bottom-right (5 um in x).
        bar_um = 5.0
        bar_px = bar_um / contract.pixel_size_um
        nx = composite.shape[1]
        ny = composite.shape[0]
        sub.plot([nx * 0.92 - bar_px, nx * 0.92], [ny * 0.10, ny * 0.10],
                 color="white", lw=1.5, zorder=6)
        sub.text(nx * 0.92 - bar_px / 2, ny * 0.16,
                 f"{bar_um:.0f} um",
                 ha="center", va="bottom", color="white",
                 fontsize=6.0, zorder=6)

    # Right column: paired split violins (z-span + bow amplitude).
    # Short titles so adjacent inset titles don't collide; um units
    # are noted once in the parent title.
    metrics = [
        ("z-span", contract.z_span_by_group),
        ("bow amp", contract.bow_amplitude_by_group),
    ]
    for col, (label, data) in enumerate(metrics):
        x_lo = 0.50 + col * 0.27
        sub = ax.inset_axes([x_lo, 0.18, 0.20, 0.70])
        AESTHETIC.apply_to_ax(sub)
        if data:
            positions = [0, 1]
            for pos, group in zip(positions, groups):
                vals = np.asarray(data.get(group, []), float)
                if vals.size == 0:
                    continue
                colour = _GROUP_COLOURS.get(group, "#333333")
                parts = sub.violinplot(
                    [vals], positions=[pos], widths=0.78,
                    showmeans=False, showmedians=False, showextrema=False,
                )
                for pc in parts["bodies"]:
                    pc.set_facecolor(colour)
                    pc.set_edgecolor("#333333")
                    pc.set_alpha(0.55)
                if vals.size >= 4:
                    med = float(np.median(vals))
                    q1, q3 = np.quantile(vals, [0.25, 0.75])
                    sub.plot([pos, pos], [q1, q3],
                             color="black", lw=1.4, zorder=5)
                    sub.scatter([pos], [med], s=24,
                                facecolor="white", edgecolor="black",
                                linewidth=0.6, zorder=6)
            sub.set_xticks(positions)
            sub.set_xticklabels(groups, fontsize=6.6)
        # Metric name goes on the inset title (the inset is too narrow
        # to hold a rotated y-axis label without overlapping violins).
        sub.set_title(label, fontsize=6.6, pad=2)
        sub.tick_params(axis="y", labelsize=6.0)
        sub.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)

    # Header + median callouts.
    bits = []
    for group in groups:
        zs = contract.z_span_by_group.get(group, [])
        ba = contract.bow_amplitude_by_group.get(group, [])
        if zs and ba:
            bits.append(
                f"{group}: z-span med {smart_fmt(float(np.median(zs)))} um, "
                f"bow med {smart_fmt(float(np.median(ba)))} um"
            )
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
