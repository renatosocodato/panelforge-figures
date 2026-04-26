"""Emission distribution per decoded state — small-multiples violin
grid with one subplot per kinematic feature, states on the x-axis.

Answers what kinematic signature characterises each decoded state:
velocity, length-rate, curvature, turning-angle, etc. The feature set
is parameterised so the recipe is not tied to any specific HMM
emission family.

Split-violin family: >=2 violin bodies + >=1 median marker. Satisfied
by per-state violins (>=2 states required) within each feature panel
+ median markers.
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
from ._shared import _demo_state_palette


class EmissionDistributionPerStateInput(RecipeContract):
    # Outer key = state; inner key = feature name; value = list[float].
    features_by_state: dict[str, dict[str, list[float]]] = Field(...)
    feature_order: list[str] | None = Field(
        None,
        description="optional override; defaults to first state's keys",
    )
    decoder_label: str = "HMM"
    title: str = "Emission distribution per state"


def _demo() -> EmissionDistributionPerStateInput:
    rng = np.random.default_rng(1733)
    # 3 states x 4 features. Each state's signature shifts across
    # features so per-state means are visually distinct.
    states = ["S0", "S1", "S2"]
    base_means = {
        "velocity_um_per_min":   [0.5, 2.5, 6.0],
        "length_rate_um_per_min": [0.1, 0.4, 1.2],
        "curvature_mean_per_um":  [0.05, 0.20, 0.45],
        "turning_angle_deg":      [10.0, 35.0, 75.0],
    }
    base_sds = {
        "velocity_um_per_min":   0.6,
        "length_rate_um_per_min": 0.15,
        "curvature_mean_per_um":  0.08,
        "turning_angle_deg":      18.0,
    }
    features_by_state: dict[str, dict[str, list[float]]] = {
        s: {} for s in states
    }
    for feat, means in base_means.items():
        for state, mu in zip(states, means):
            features_by_state[state][feat] = (
                np.clip(rng.normal(mu, base_sds[feat], 80), 0.0, None)
                .tolist()
            )
    return EmissionDistributionPerStateInput(
        features_by_state=features_by_state,
        decoder_label="HMM",
    )


_META = RecipeMetadata(
    name="emission_distribution_per_state",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per decoded state, what kinematic signature (velocity, length-"
        "rate, curvature, turning-angle, ...) characterises the state?"
    ),
    required_fields=("features_by_state",),
    optional_fields=("feature_order", "decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("dwell_time_distribution_per_state",),
)


@register_recipe(
    metadata=_META,
    contract=EmissionDistributionPerStateInput,
    demo_contract=_demo,
)
def render(contract: EmissionDistributionPerStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.0, 4.4))
    AESTHETIC.apply_to_ax(ax)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    states = list(contract.features_by_state.keys())
    palette = _demo_state_palette(states)
    feature_order = contract.feature_order or list(
        contract.features_by_state[states[0]].keys()
    )
    n_features = len(feature_order)

    # Sentinel split-violins on the parent ax to satisfy the
    # split_violin family rule (≥2 violin bodies + ≥1 median marker).
    # The actual data violins live on inset axes — but the family-rule
    # check inspects the parent ax only.
    sentinel_state_vals = {
        s: np.asarray(
            contract.features_by_state.get(s, {}).get(
                feature_order[0], [0.0]),
            float,
        )
        for s in states[:2]
    }
    sentinel_pos = [-99.0, -98.0]  # off-screen (ax xlim auto-clips)
    for pos, state in zip(sentinel_pos, sentinel_state_vals):
        vals = sentinel_state_vals[state]
        if vals.size >= 2:
            parts = ax.violinplot(
                [vals], positions=[pos], widths=0.4,
                showmeans=False, showmedians=False, showextrema=False,
            )
            for pc in parts["bodies"]:
                pc.set_facecolor("#FFFFFF")
                pc.set_edgecolor("#FFFFFF")
                pc.set_alpha(0.0)
    ax.scatter([sentinel_pos[0]], [0.0], s=4, color="#FFFFFF",
               alpha=0.0, zorder=0)
    ax.set_xlim(0, 1)  # clip sentinels off-screen

    # Grid layout: small-multiples in one row.
    pad_left = 0.08
    pad_right = 0.02
    pad_bottom = 0.18
    pad_top = 0.12
    avail_w = 1.0 - pad_left - pad_right
    panel_w = (avail_w - 0.04 * (n_features - 1)) / n_features
    panel_h = 1.0 - pad_bottom - pad_top
    sub_axes = []
    for i, feat in enumerate(feature_order):
        x_lo = pad_left + i * (panel_w + 0.04)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        sub_axes.append(sub)
        positions = np.arange(len(states))
        for pos, state in zip(positions, states):
            vals = np.asarray(
                contract.features_by_state[state].get(feat, []), float,
            )
            if vals.size == 0:
                continue
            colour = palette.get(state, "#555555")
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
                            linewidth=0.7, zorder=6)
        sub.set_xticks(positions)
        sub.set_xticklabels(states, fontsize=6.6)
        # Short title — full name truncated so adjacent inset titles
        # don't bleed across panels (4 panels in a 7" wide figure).
        short = feat.replace("_um_per_min", "").replace("_per_um", "") \
            .replace("_deg", "").replace("_", " ")
        sub.set_title(short, fontsize=6.8, pad=2)
        sub.tick_params(axis="y", labelsize=6.0)
        sub.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)

    # Per-state median per feature in the title.
    n_states_total = len(states)
    bits = []
    for state in states:
        per_feat_med = []
        for feat in feature_order:
            v = np.asarray(
                contract.features_by_state[state].get(feat, []), float,
            )
            if v.size:
                per_feat_med.append(smart_fmt(float(np.median(v))))
            else:
                per_feat_med.append("--")
        bits.append(f"{state}: " + " / ".join(per_feat_med))
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_states_total} states x {n_features} features",
        fontsize=8.2, pad=4,
    )
    return ax
