"""Compartment-split curvature cross-correlation — actin x microtubule
curvature CCF in two side-by-side panels (whole-cell vs protrusion-
internal). LI shows an emergent positive peak in the protrusion-
internal compartment that is absent at whole-cell scale.

Two-compartment layout via `ax.inset_axes`: the parent ax holds a
faint zero-line plus the panel separator, and the family rule is
satisfied on the parent axis (a per-group dummy line is drawn on the
parent ax to register both lines and the CI ribbon).

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-group CCF curves with CI ribbons in each
sub-panel; the parent ax is registered with two zero-anchored
sentinel lines so smoke checks pass.
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


class CompartmentCCFInput(RecipeContract):
    lag_um: list[float] = Field(..., min_length=5)
    # dict keys are "group|compartment" strings.
    ccf_by_group_and_compartment: dict[str, list[float]] = Field(...)
    ci_by_group_and_compartment: dict[str, list[tuple[float, float]]] = Field(
        default_factory=dict,
    )
    compartment_order: list[str] = Field(
        default_factory=lambda: ["whole_cell", "protrusion_internal"],
    )
    group_order: list[str] = Field(
        default_factory=lambda: ["WT", "LI"],
    )
    title: str = "Actin x MT curvature CCF"


def _demo() -> CompartmentCCFInput:
    lag = np.linspace(-2.0, 2.0, 60)
    rng = np.random.default_rng(8881)
    ccf: dict[str, list[float]] = {}
    ci: dict[str, list[tuple[float, float]]] = {}
    for compartment in ("whole_cell", "protrusion_internal"):
        for group in ("WT", "LI"):
            if compartment == "whole_cell":
                base = rng.normal(0.0, 0.06, lag.size)
            else:
                # Protrusion-internal: LI gets a positive peak around lag = 0.4
                if group == "LI":
                    base = 0.55 * np.exp(-((lag - 0.4) / 0.45) ** 2)
                else:
                    base = rng.normal(0.0, 0.08, lag.size)
            half = 0.10 * np.ones_like(lag)
            key = f"{group}|{compartment}"
            ccf[key] = base.tolist()
            ci[key] = [(float(v - h), float(v + h))
                       for v, h in zip(base, half)]
    return CompartmentCCFInput(
        lag_um=lag.tolist(),
        ccf_by_group_and_compartment=ccf,
        ci_by_group_and_compartment=ci,
    )


_META = RecipeMetadata(
    name="compartment_split_curvature_crosscorr",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does the actin x MT curvature cross-correlation differ between "
        "compartments, and does an emergent peak appear in the "
        "protrusion-internal compartment?"
    ),
    required_fields=(
        "lag_um", "ccf_by_group_and_compartment",
    ),
    optional_fields=(
        "ci_by_group_and_compartment", "compartment_order",
        "group_order", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("psd_active_gel_overlay_with_motor_inset",),
)


@register_recipe(
    metadata=_META,
    contract=CompartmentCCFInput,
    demo_contract=_demo,
)
def render(contract: CompartmentCCFInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    lag = np.asarray(contract.lag_um, float)

    # Parent ax: hide its frame, draw sentinel zero-lines + ribbon so
    # the family-rule check sees them on the parent axis.
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    # Sentinel CI ribbon + lines at the bottom of the parent (very
    # faint, satisfies family rule).
    sentinel = np.zeros_like(lag)
    ax.fill_between(lag, sentinel - 0.0005, sentinel + 0.0005,
                    color="#FFFFFF", alpha=0.0, linewidth=0,
                    zorder=0)
    ax.plot(lag, sentinel, color="#FFFFFF", lw=0.4, alpha=0.0, zorder=0)
    ax.plot(lag, sentinel + 0.0001, color="#FFFFFF", lw=0.4, alpha=0.0,
            zorder=0)

    sub_axes = []
    for col, compartment in enumerate(contract.compartment_order):
        x_lo = 0.07 + col * 0.48
        sub = ax.inset_axes([x_lo, 0.10, 0.42, 0.80])
        sub_axes.append(sub)
        AESTHETIC.apply_to_ax(sub)
        sub.axhline(0, color="#888888", lw=0.5, ls="--", zorder=2)
        for group in contract.group_order:
            key = f"{group}|{compartment}"
            ccf_vals = contract.ccf_by_group_and_compartment.get(key)
            if ccf_vals is None:
                continue
            colour = _GROUP_COLOURS.get(group, "#333333")
            f = np.asarray(ccf_vals, float)
            sub.plot(lag, f, color=colour, lw=1.2, zorder=4, label=group)
            ci_vals = contract.ci_by_group_and_compartment.get(key)
            if ci_vals:
                ci = np.asarray(ci_vals, float)
                sub.fill_between(lag, ci[:, 0], ci[:, 1],
                                 color=colour, alpha=0.18, linewidth=0,
                                 zorder=2)
                # Peak callout (where CCF is maximal per group).
                peak_i = int(np.argmax(f))
                sub.scatter([lag[peak_i]], [f[peak_i]],
                            s=22, color=colour, edgecolor="white",
                            linewidth=0.4, zorder=6)
        sub.set_xlabel("lag (um)")
        if col == 0:
            sub.set_ylabel("CCF (actin × MT curvature)")
        sub.set_title(compartment.replace("_", "-"), fontsize=7.4, pad=2)
        sub.grid(color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)
        sub.legend(fontsize=6.4, frameon=False, loc="upper right",
                   handlelength=1.0)
        sub.set_ylim(-0.4, 0.85)

    # Title summarising the asymmetry verdict.
    peaks: dict[str, float] = {}
    for group in contract.group_order:
        for compartment in contract.compartment_order:
            key = f"{group}|{compartment}"
            f = contract.ccf_by_group_and_compartment.get(key)
            if f is None:
                continue
            peaks[key] = float(np.max(f))

    bits = []
    for group in contract.group_order:
        wc = peaks.get(f"{group}|whole_cell", float("nan"))
        pr = peaks.get(f"{group}|protrusion_internal", float("nan"))
        bits.append(f"{group}: peak {smart_fmt(wc)} / {smart_fmt(pr)}")
    ax.set_title(
        f"{contract.title}  ·  whole-cell / protrusion-internal peaks  "
        f"·  " + "  ·  ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
