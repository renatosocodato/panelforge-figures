"""Intensity radial profile — mean ± SEM per channel vs radius from centroid."""

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


class ChannelProfile(RecipeContract):
    mean: list[float]
    sem: list[float]


class IntensityRadialProfileInput(RecipeContract):
    radius_um: list[float] = Field(...)
    intensity_by_channel: dict[str, ChannelProfile] = Field(
        ..., description="channel name → {'mean': [...], 'sem': [...]}"
    )
    title: str = "Radial intensity profile"


def _demo() -> IntensityRadialProfileInput:
    rng = np.random.default_rng(775)
    radius = np.linspace(0.0, 18.0, 25)
    # Actin peaks mid-radius, MT concentrated near centre, myosin flat.
    actin_mean = 0.3 + 0.7 * np.exp(-((radius - 9.0) / 4.5) ** 2) + rng.normal(0, 0.02, radius.size)
    mt_mean = 0.9 * np.exp(-radius / 5.0) + rng.normal(0, 0.02, radius.size)
    myosin_mean = 0.45 + 0.08 * np.cos(radius * 0.35) + rng.normal(0, 0.015, radius.size)
    sem = 0.04 * np.ones_like(radius)
    return IntensityRadialProfileInput(
        radius_um=radius.tolist(),
        intensity_by_channel={
            "actin":       ChannelProfile(mean=actin_mean.tolist(), sem=sem.tolist()),
            "microtubule": ChannelProfile(mean=mt_mean.tolist(), sem=sem.tolist()),
            "myosin":      ChannelProfile(mean=myosin_mean.tolist(), sem=(sem * 0.8).tolist()),
        },
    )


_META = RecipeMetadata(
    name="intensity_radial_profile",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "From the cell centroid outward, how does intensity vary radially "
        "for each channel?"
    ),
    required_fields=("radius_um", "intensity_by_channel"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cortical_thickness_by_region",),
)


@register_recipe(
    metadata=_META,
    contract=IntensityRadialProfileInput,
    demo_contract=_demo,
)
def render(contract: IntensityRadialProfileInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.asarray(contract.radius_um, float)
    for i, (ch_name, profile) in enumerate(contract.intensity_by_channel.items()):
        mean = np.asarray(profile.mean, float)
        sem = np.asarray(profile.sem, float)
        color = (palette.pick(ch_name) if ch_name in palette.semantic
                 else palette[i % len(palette.colors)])
        ax.fill_between(r, mean - sem, mean + sem,
                        color=color, alpha=0.18, linewidth=0,
                        zorder=2)
        ax.plot(r, mean, color=color, lw=1.3, zorder=3,
                label=f"{ch_name} (peak {smart_fmt(float(mean.max()))} at "
                      f"r = {smart_fmt(float(r[int(np.argmax(mean))]))} $\\mu$m)")

    ax.set_xlabel(r"radial distance from centroid ($\mu$m)")
    ax.set_ylabel("normalised intensity")
    ax.set_xlim(float(r.min()), float(r.max()))
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
