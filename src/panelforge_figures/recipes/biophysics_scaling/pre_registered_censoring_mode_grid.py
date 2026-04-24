"""Pre-registered censoring mode grid — feature x mode traffic-light
matrix showing whether each effect's direction and significance hold
across all pre-registered quality-gating modes.

Renders the manuscript's pre-registration audit in one panel: every
feature that 'approaches but does not cross the significance threshold'
is exposed row-by-row across permissive / standard / quality_gated /
strict (or user-specified) modes.

Matrix family: >=1 imshow OR >=4 cell patches. Satisfied by the 2-D
cell grid (rows x modes).
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
from ._shared import CensoringMode, CensoringResult


_TRAFFIC_LIGHT = {
    "green":  "#2E7D32",   # direction preserved + passes threshold
    "amber":  "#F9A825",   # direction preserved, sub-threshold
    "red":    "#C62828",   # direction flipped or opposite-sign sig
    "grey":   "#BDBDBD",   # excluded at this mode
}


class CensoringModeGridInput(RecipeContract):
    results: list[CensoringResult] = Field(..., min_length=4)
    modes: list[CensoringMode] = Field(..., min_length=2)
    features: list[str] = Field(..., min_length=2)
    mode_order: list[str] | None = Field(
        None,
        description="override display order; defaults to `modes` order",
    )
    traffic_light: bool = True
    annotate_d: bool = True
    title: str = "Pre-registered censoring audit"


def _demo() -> CensoringModeGridInput:
    rng = np.random.default_rng(4421)
    features = [
        "standoff_distance", "protrusion_width", "orientation_alpha",
        "cell_area", "territory_radius", "curvature_ccf_peak",
        "persistence_length_actin", "psd_motor_band",
    ]
    modes = [
        CensoringMode(label="permissive",
                      n_cells_retained=26, pre_registered=True,
                      description="outliers kept"),
        CensoringMode(label="standard",
                      n_cells_retained=23, pre_registered=True,
                      description="default"),
        CensoringMode(label="quality_gated",
                      n_cells_retained=20, pre_registered=True,
                      description="SNR>3 required"),
        CensoringMode(label="strict",
                      n_cells_retained=17, pre_registered=True,
                      description="SNR>5 + motion<2px"),
    ]
    # Direction of true effect per feature (+1 for LI>WT, -1 for LI<WT).
    true_dir = {
        "standoff_distance": +1, "protrusion_width": +1,
        "orientation_alpha": +1, "cell_area": +1,
        "territory_radius": +1, "curvature_ccf_peak": +1,
        "persistence_length_actin": 0, "psd_motor_band": 0,
    }
    results: list[CensoringResult] = []
    for feature in features:
        tdir = true_dir[feature]
        base_d = tdir * rng.uniform(0.4, 0.9)
        for m in modes:
            # Adjust d with a small mode-dependent shrink.
            shrink = {"permissive": 1.1, "standard": 1.0,
                      "quality_gated": 0.9, "strict": 0.7}[m.label]
            d = base_d * shrink + rng.normal(0, 0.06)
            ci_half = 0.18 + (0.1 if m.label == "strict" else 0.0)
            ci_lo = d - ci_half
            ci_hi = d + ci_half
            passes = (ci_lo > 0.0) or (ci_hi < 0.0)
            if tdir == 0:
                # Null features: intentionally not passing threshold;
                # direction integer = sign of d.
                p_val = rng.uniform(0.05, 0.9)
                passes = False
            else:
                p_val = rng.uniform(0.0005, 0.15)
            results.append(CensoringResult(
                feature=feature,
                mode_label=m.label,
                direction=int(np.sign(d)),
                d=float(d),
                ci_lo=float(ci_lo),
                ci_hi=float(ci_hi),
                p_value=float(p_val),
                passes_threshold=bool(passes),
            ))
    return CensoringModeGridInput(
        results=results,
        modes=modes,
        features=features,
    )


_META = RecipeMetadata(
    name="pre_registered_censoring_mode_grid",
    modality="biophysics_scaling",
    family=RecipeFamily.matrix,
    answers_question=(
        "Does each feature's conclusion survive all four pre-registered "
        "censoring modes (permissive, standard, quality-gated, strict)?"
    ),
    required_fields=("results", "modes", "features"),
    optional_fields=("mode_order", "traffic_light", "annotate_d", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=CensoringModeGridInput,
    demo_contract=_demo,
)
def render(contract: CensoringModeGridInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 4.4))
    AESTHETIC.apply_to_ax(ax)

    mode_order = contract.mode_order or [m.label for m in contract.modes]
    mode_by_label = {m.label: m for m in contract.modes}
    features = list(contract.features)

    # Build a lookup (feature, mode) -> result.
    lookup: dict[tuple[str, str], CensoringResult] = {}
    for r in contract.results:
        lookup[(r.feature, r.mode_label)] = r

    # Determine per-feature reference direction (from the most-permissive
    # mode that has a result). We then score downstream modes against it.
    ref_dir: dict[str, int] = {}
    for feature in features:
        for mode_label in mode_order:
            r = lookup.get((feature, mode_label))
            if r is not None and r.direction != 0:
                ref_dir[feature] = r.direction
                break
        ref_dir.setdefault(feature, 0)

    # Populate cell colours + annotations.
    n_f = len(features)
    n_m = len(mode_order)
    for i, feature in enumerate(features):
        for j, mode_label in enumerate(mode_order):
            r = lookup.get((feature, mode_label))
            if r is None:
                colour = _TRAFFIC_LIGHT["grey"]
                text = "--"
            else:
                if r.direction == 0:
                    # Reference-direction is undefined (null feature).
                    colour = _TRAFFIC_LIGHT["grey"]
                elif r.direction != ref_dir[feature]:
                    colour = _TRAFFIC_LIGHT["red"]
                elif r.passes_threshold:
                    colour = _TRAFFIC_LIGHT["green"]
                else:
                    colour = _TRAFFIC_LIGHT["amber"]
                text = f"{smart_fmt(r.d)}" if contract.annotate_d else ""
            ax.add_patch(mpatches.Rectangle(
                (j - 0.5, i - 0.5), 1.0, 1.0,
                facecolor=colour, edgecolor="white",
                linewidth=1.1, alpha=0.90, zorder=2,
            ))
            if text:
                ax.text(j, i, text,
                        ha="center", va="center", fontsize=6.4,
                        color="white", fontweight="bold", zorder=4)

    ax.set_xticks(range(n_m))
    ax.set_xticklabels(
        [f"{m}\nn={mode_by_label[m].n_cells_retained or '?'}"
         for m in mode_order],
        fontsize=6.8,
    )
    ax.set_yticks(range(n_f))
    ax.set_yticklabels(features, fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xlim(-0.6, n_m - 0.4)
    ax.set_ylim(n_f - 0.4, -0.6)
    ax.set_xlabel("censoring mode (permissive -> strict)")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

    # Legend.
    proxies = [
        mpatches.Patch(facecolor=_TRAFFIC_LIGHT["green"],
                       label="direction + sig"),
        mpatches.Patch(facecolor=_TRAFFIC_LIGHT["amber"],
                       label="direction, sub-sig"),
        mpatches.Patch(facecolor=_TRAFFIC_LIGHT["red"],
                       label="flipped / opposite"),
        mpatches.Patch(facecolor=_TRAFFIC_LIGHT["grey"],
                       label="null / excluded"),
    ]
    ax.legend(handles=proxies, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncols=4, handlelength=1.0)

    # Per-feature survival summary in title.
    greens = sum(
        1 for r in contract.results
        if r.direction != 0
        and r.direction == ref_dir.get(r.feature, 0)
        and r.passes_threshold
    )
    total_non_null = sum(1 for r in contract.results
                         if r.direction != 0 and ref_dir.get(r.feature, 0) != 0)
    survival = (greens / total_non_null) if total_non_null else 0.0
    ax.set_title(
        f"{contract.title}  ·  {n_f} features x {n_m} modes  ·  "
        f"{smart_fmt(survival * 100)} % cell-wise survival "
        f"(direction + sig)",
        fontsize=8.2, pad=4,
    )
    return ax
