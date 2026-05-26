"""Power spectral density with active-gel band overlay and a motor-
band deviation inset.

The main axes show log-log PSD per channel x group with CI ribbons,
the active-gel frequency band shaded, and a reference omega^-2 slope.
The inset panel (upper-right) compares per-group deviation in the
motor band from the omega^-2 scaling — the biophysical ask is whether
genotype shifts the motor band, separately from the bulk spectrum.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean line.
Satisfied by the per-group PSD mean + CI ribbon.
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
from ._shared import PSDCurve

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "WT_motor": "#0D47A1", "LI_motor": "#B71C1C"}


class PSDActiveGelInput(RecipeContract):
    psds: list[PSDCurve] = Field(..., min_length=2)
    active_gel_band_hz: tuple[float, float] = (0.1, 2.0)
    motor_band_hz: tuple[float, float] = (3.0, 12.0)
    reference_slope: float = Field(
        -2.0,
        description="omega^slope reference (active gel = -2)",
    )
    title: str = "PSD with active-gel band and motor inset"


def _demo() -> PSDActiveGelInput:
    freq = np.logspace(np.log10(0.05), np.log10(30.0), 80)
    # omega^-2 baseline + motor-band bump around 4-8 Hz.
    def _psd(mu_motor: float, amp_motor: float) -> tuple[list[float], list[float], list[float]]:
        base = 1e-1 * freq ** -2.0
        motor = amp_motor * np.exp(
            -((np.log10(freq) - np.log10(mu_motor)) / 0.18) ** 2
        )
        signal = base + motor
        noise = 0.10 * signal
        lo = (signal - 1.96 * noise).tolist()
        hi = (signal + 1.96 * noise).tolist()
        return signal.tolist(), lo, hi

    wt, wt_lo, wt_hi = _psd(mu_motor=5.5, amp_motor=0.010)
    li, li_lo, li_hi = _psd(mu_motor=5.7, amp_motor=0.011)
    return PSDActiveGelInput(
        psds=[
            PSDCurve(label="WT", freq_hz=freq.tolist(),
                     psd=wt, ci_lo=wt_lo, ci_hi=wt_hi,
                     active_gel_band_hz=(0.1, 2.0)),
            PSDCurve(label="LI", freq_hz=freq.tolist(),
                     psd=li, ci_lo=li_lo, ci_hi=li_hi,
                     active_gel_band_hz=(0.1, 2.0)),
        ],
        active_gel_band_hz=(0.1, 2.0),
        motor_band_hz=(3.0, 12.0),
    )


_META = RecipeMetadata(
    name="psd_active_gel_overlay_with_motor_inset",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does the active-gel PSD (omega^-2) differ between groups, and "
        "separately, does the motor band show a genotype-dependent "
        "deviation from bulk scaling?"
    ),
    required_fields=("psds",),
    optional_fields=(
        "active_gel_band_hz", "motor_band_hz", "reference_slope", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("log_log_with_theory_line",),
)


@register_recipe(
    metadata=_META,
    contract=PSDActiveGelInput,
    demo_contract=_demo,
)
def render(contract: PSDActiveGelInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    # Active-gel band shading.
    ag_lo, ag_hi = contract.active_gel_band_hz
    ax.axvspan(ag_lo, ag_hi, color="#2E7D32", alpha=0.08,
               linewidth=0, zorder=1)
    # Motor-band shading.
    mb_lo, mb_hi = contract.motor_band_hz
    ax.axvspan(mb_lo, mb_hi, color="#FF6F00", alpha=0.08,
               linewidth=0, zorder=1)

    # omega^-2 reference line.
    f_ref = np.logspace(-1, 1.5, 30)
    # Anchor the reference to pass through (1, 1e-1).
    ref = 1e-1 * f_ref ** contract.reference_slope
    ax.plot(f_ref, ref, color="#555555", lw=0.8, ls="--", zorder=2,
            label=f"omega^{smart_fmt(contract.reference_slope)}")

    # Per-group PSD + CI ribbon.
    motor_dev_by_group: dict[str, float] = {}
    for curve in contract.psds:
        colour = curve.color or _GROUP_COLOURS.get(curve.label, "#333333")
        f = np.asarray(curve.freq_hz, float)
        p = np.asarray(curve.psd, float)
        ax.plot(f, p, color=colour, lw=1.2, zorder=5, label=curve.label)
        if curve.ci_lo is not None and curve.ci_hi is not None:
            lo = np.asarray(curve.ci_lo, float)
            hi = np.asarray(curve.ci_hi, float)
            ax.fill_between(f, np.clip(lo, 1e-12, None),
                            np.clip(hi, 1e-12, None),
                            color=colour, alpha=0.15, linewidth=0,
                            zorder=3)
        # Motor-band deviation (signal / reference in the motor band).
        mask = (f >= mb_lo) & (f <= mb_hi)
        if mask.any():
            ref_mb = 1e-1 * f[mask] ** contract.reference_slope
            dev = float(np.median(p[mask] / ref_mb))
            motor_dev_by_group[curve.label] = dev

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("PSD (arb. units)")
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    # Legend placed upper-right (the PSD is monotonically decreasing on
    # log-log, so the upper-right quadrant is the empty corner with no
    # curves).
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)

    # Inset: motor-band deviation per group. Anchored to lower-left
    # (the only quadrant that never overlaps a falling power-law PSD
    # curve); the per-curve legend already sits just above it, also
    # lower-left, so we place this inset slightly inboard and shrink
    # it so the two don't collide.
    if motor_dev_by_group:
        inset = ax.inset_axes([0.08, 0.08, 0.26, 0.26])
        groups = list(motor_dev_by_group.keys())
        devs = [motor_dev_by_group[g] for g in groups]
        colours = [_GROUP_COLOURS.get(g, "#333333") for g in groups]
        x = np.arange(len(groups))
        inset.bar(x, devs, color=colours, edgecolor="white",
                  linewidth=0.6, alpha=0.92, zorder=3)
        inset.axhline(1.0, color="#888888", lw=0.5, ls="--", zorder=2)
        inset.set_xticks(x)
        inset.set_xticklabels(groups, fontsize=6.2)
        inset.set_ylabel("motor / ref", fontsize=6.2)
        inset.tick_params(axis="y", labelsize=6.0)
        inset.set_title("motor band ratio", fontsize=6.4, pad=2)
        for side in ("top", "right"):
            inset.spines[side].set_visible(False)

    # Title — fold-change in motor band between groups.
    dev_tag = ""
    if len(motor_dev_by_group) == 2:
        g0, g1 = list(motor_dev_by_group.keys())
        dev_tag = (f"  ·  motor band ratio "
                   f"{g1} / {g0} = "
                   f"{smart_fmt(motor_dev_by_group[g1] / motor_dev_by_group[g0])}")
    ax.set_title(
        f"{contract.title}{dev_tag}",
        fontsize=8.2, pad=4,
    )
    return ax
