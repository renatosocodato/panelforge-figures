"""Protrusion / retraction kymograph — signed edge velocity over (arc, time)."""

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


class ProtrusionKymographInput(RecipeContract):
    arc_length_um: list[float] = Field(...)
    time_s: list[float] = Field(...)
    edge_velocity: list[list[float]] = Field(
        ..., description="signed edge velocity (µm/s); +protrusion / -retraction"
    )
    title: str = "Protrusion / retraction kymograph"


def _demo() -> ProtrusionKymographInput:
    rng = np.random.default_rng(821)
    arc = np.linspace(0, 50, 100)
    t = np.linspace(0, 240, 120)
    AA, TT = np.meshgrid(arc, t, indexing="ij")
    # Travelling protrusion wave + opposing retraction pocket.
    wave = 0.25 * np.sin(AA * 0.4 - TT * 0.05) * np.exp(-((AA - 20) ** 2) / 220.0)
    pocket = -0.20 * np.exp(-((AA - 35) ** 2 + (TT - 160) ** 2) / 120.0)
    baseline = 0.02 * np.sin(TT * 0.02)
    V = baseline + wave + pocket + rng.normal(0, 0.03, AA.shape)
    return ProtrusionKymographInput(
        arc_length_um=arc.tolist(),
        time_s=t.tolist(),
        edge_velocity=V.tolist(),
    )


_META = RecipeMetadata(
    name="protrusion_retraction_kymograph",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Along the cell edge over time, where are protrusions vs. retractions "
        "(signed edge velocity)?"
    ),
    required_fields=("arc_length_um", "time_s", "edge_velocity"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=(
        "skeleton_overlay_kymograph",
        "edge_velocity_spatial_correlation",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ProtrusionKymographInput,
    demo_contract=_demo,
)
def render(contract: ProtrusionKymographInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    arc = np.asarray(contract.arc_length_um, float)
    t = np.asarray(contract.time_s, float)
    V = np.asarray(contract.edge_velocity, float)

    # RdBu_r anchored at 0 (protrusion positive → red, retraction → blue).
    vmax = max(float(np.max(np.abs(V))), 0.01)
    extent = (float(t.min()), float(t.max()),
              float(arc.max()), float(arc.min()))
    im = ax.imshow(
        V, origin="upper", extent=extent, aspect="auto",
        cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=-vmax, vmax=vmax,
        interpolation="bilinear",
    )

    # Iso-contour at v = 0 (the protrusion/retraction boundary).
    TT, AA = np.meshgrid(t, arc)
    try:
        cs = ax.contour(TT, AA, V, levels=[0.0], colors="#111111",
                        linewidths=0.7, zorder=3)
        ax.clabel(cs, fontsize=5.6, fmt="%.2f", inline=True)
    except Exception:
        pass

    # Time-averaged edge velocity strip on right.
    ax_r = ax.inset_axes([1.02, 0, 0.14, 1.0], sharey=ax)
    mean_v = V.mean(axis=1)
    ax_r.plot(mean_v, arc, color="#111111", lw=0.9)
    ax_r.axvline(0, color="#888888", lw=0.5, ls=":", zorder=1)
    ax_r.set_ylim(arc.max(), arc.min())
    ax_r.set_xlabel(r"$\langle v \rangle$", fontsize=6.0)
    ax_r.tick_params(axis="both", labelsize=5.8)
    ax_r.set_yticks([])

    cbar = ax.figure.colorbar(im, ax=[ax, ax_r], fraction=0.05, pad=0.08,
                              location="right")
    cbar.set_label(r"edge velocity ($\mu$m/s)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Summary: protruded vs retracted area fractions.
    frac_protrude = float(np.mean(V > 0.02))
    frac_retract = float(np.mean(V < -0.02))
    ax.set_xlabel("time (s)")
    ax.set_ylabel(r"arc length along edge ($\mu$m)")
    ax.set_title(
        f"{contract.title}  ·  protruding {smart_fmt(frac_protrude * 100)}%,  "
        f"retracting {smart_fmt(frac_retract * 100)}%",
        fontsize=8.4, pad=4,
    )
    return ax
