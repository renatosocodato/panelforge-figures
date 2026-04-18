"""Redox-state transition diagram — boxes for reduced/intermediate/oxidized with rate arrows."""

from __future__ import annotations

import matplotlib.patches as mpatches
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


class RedoxTransitionInput(RecipeContract):
    rate_red_to_int: float = 0.12
    rate_int_to_red: float = 0.20
    rate_int_to_ox: float = 0.08
    rate_ox_to_int: float = 0.06
    steady_state: dict[str, float] = Field(
        default_factory=lambda: {"reduced": 0.55, "intermediate": 0.30, "oxidized": 0.15},
    )
    title: str = "Redox state transitions"


def _demo() -> RedoxTransitionInput:
    return RedoxTransitionInput()


_META = RecipeMetadata(
    name="redox_state_transition_diagram",
    modality="redox_imaging",
    family=RecipeFamily.flow,
    answers_question="What are the rates between reduced / intermediate / oxidized states, and what is the resulting steady-state occupancy?",
    required_fields=("rate_red_to_int", "rate_int_to_red",
                     "rate_int_to_ox", "rate_ox_to_int"),
    optional_fields=("steady_state", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("bistability_hysteresis_loop",),
)


@register_recipe(metadata=_META, contract=RedoxTransitionInput, demo_contract=_demo)
def render(contract: RedoxTransitionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)

    states = [
        ("reduced", 10, 50, palette.pick("reduced")),
        ("intermediate", 45, 50, palette.pick("intermediate")),
        ("oxidized", 80, 50, palette.pick("oxidized")),
    ]
    box_w, box_h = 18, 22
    for name, cx, cy, color in states:
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - box_w / 2, cy - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.014,rounding_size=0.025",
            facecolor=color, edgecolor="white", linewidth=1.3, alpha=0.92,
        ))
        ax.text(cx, cy + 2, name, ha="center", va="center",
                color="white", fontsize=8.4)
        pct = int(100 * contract.steady_state.get(name, 0))
        ax.text(cx, cy - 5,
                f"{pct}%",
                ha="center", va="center",
                color="white", fontsize=7.0, alpha=0.92)

    # Arrow helper.
    def _arrow(x_src, y_src, x_dst, y_dst, color, label, offset=3):
        ax.annotate(
            "",
            xy=(x_dst, y_dst + offset),
            xytext=(x_src, y_src + offset),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0,
                            shrinkA=10, shrinkB=10),
        )
        ax.text(0.5 * (x_src + x_dst), y_src + offset + 3.5,
                label, ha="center", va="bottom",
                fontsize=6.6, color=color,
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.92))

    red_c = palette.pick("reduced")
    ox_c = palette.pick("oxidized")
    inter_c = palette.pick("intermediate")

    _arrow(19, 50, 36, 50, inter_c,
           rf"$k_{{r \to i}}$ = {smart_fmt(contract.rate_red_to_int)}/s",
           offset=7)
    _arrow(36, 50, 19, 50, red_c,
           rf"$k_{{i \to r}}$ = {smart_fmt(contract.rate_int_to_red)}/s",
           offset=-7)
    _arrow(54, 50, 71, 50, ox_c,
           rf"$k_{{i \to o}}$ = {smart_fmt(contract.rate_int_to_ox)}/s",
           offset=7)
    _arrow(71, 50, 54, 50, inter_c,
           rf"$k_{{o \to i}}$ = {smart_fmt(contract.rate_ox_to_int)}/s",
           offset=-7)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
