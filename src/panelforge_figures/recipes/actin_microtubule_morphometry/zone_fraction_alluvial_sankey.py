"""Zone-fraction alluvial Sankey — alluvial Sankey diagram of
zone-fraction redistribution between conditions (e.g. WT → LI).
Each ribbon is a zone; ribbon thickness = zone fraction at each
condition; ribbons connect left and right via Bezier curves.

Flow family: pure matplotlib `PathPatch` ribbons (no networkx).
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import matplotlib.path as mpath
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import _demo_zone_palette


class ZoneFractionAlluvialInput(RecipeContract):
    fractions_by_condition: dict[str, dict[str, float]] = Field(
        ..., description="condition → {zone_label: fraction}",
    )
    zone_order: list[str] | None = None
    title: str = "Zone-fraction alluvial Sankey"


def _demo() -> ZoneFractionAlluvialInput:
    # WT distribution heavy on desert + intermediate (sparse contact).
    # LI distribution heavy on contact (territory reorganization).
    return ZoneFractionAlluvialInput(
        fractions_by_condition={
            "WT": {"contact": 0.18, "intermediate": 0.30,
                   "desert": 0.34, "far": 0.18},
            "LI": {"contact": 0.42, "intermediate": 0.30,
                   "desert": 0.18, "far": 0.10},
        },
        zone_order=["contact", "intermediate", "desert", "far"],
    )


_META = RecipeMetadata(
    name="zone_fraction_alluvial_sankey",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.flow,
    answers_question=(
        "Between two conditions, how does the territory zone-"
        "fraction composition redistribute (which zones grow vs "
        "shrink)?"
    ),
    required_fields=("fractions_by_condition",),
    optional_fields=("zone_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("territory_change_pre_post",),
)


def _ribbon_path(x_lo: float, x_hi: float,
                 y_l_top: float, y_l_bot: float,
                 y_r_top: float, y_r_bot: float) -> mpath.Path:
    """Build a closed Bezier ribbon between left and right columns."""
    cx = (x_lo + x_hi) / 2
    verts = [
        (x_lo, y_l_top),                        # left top start
        (cx, y_l_top), (cx, y_r_top), (x_hi, y_r_top),   # top edge cubic
        (x_hi, y_r_bot),                        # right bottom corner
        (cx, y_r_bot), (cx, y_l_bot), (x_lo, y_l_bot),   # bottom edge cubic
        (x_lo, y_l_top),                        # close
    ]
    codes = [
        mpath.Path.MOVETO,
        mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
        mpath.Path.LINETO,
        mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4,
        mpath.Path.CLOSEPOLY,
    ]
    return mpath.Path(verts, codes)


@register_recipe(
    metadata=_META,
    contract=ZoneFractionAlluvialInput,
    demo_contract=_demo,
)
def render(contract: ZoneFractionAlluvialInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    conditions = list(contract.fractions_by_condition.keys())
    if len(conditions) < 2:
        raise ValueError("Need at least 2 conditions for an alluvial Sankey.")
    cond_left, cond_right = conditions[0], conditions[1]

    # Resolve zone order.
    if contract.zone_order is not None:
        zones = list(contract.zone_order)
    else:
        # Union of zone keys.
        seen: list[str] = []
        for cond in (cond_left, cond_right):
            for k in contract.fractions_by_condition[cond]:
                if k not in seen:
                    seen.append(k)
        zones = seen

    # Stack fractions top-down on each side; ribbons go zone→zone
    # along the same zone (no cross-flows) for a true alluvial.
    fl = contract.fractions_by_condition[cond_left]
    fr = contract.fractions_by_condition[cond_right]

    # Normalise to sum=1 in case of rounding.
    sl = sum(fl.get(k, 0) for k in zones) or 1.0
    sr = sum(fr.get(k, 0) for k in zones) or 1.0
    fl_n = {k: fl.get(k, 0) / sl for k in zones}
    fr_n = {k: fr.get(k, 0) / sr for k in zones}

    # Coordinates.  Wider stub columns so multi-syllable zone labels
    # (e.g. "intermediate") fit inside the boxes without truncation.
    x_left_outer = 0.05
    x_left_inner = 0.22
    x_right_inner = 0.78
    x_right_outer = 0.95
    y_top = 0.95
    y_bot = 0.05

    # Build per-zone left-y bracket [bot, top] and right-y bracket.
    palette = _demo_zone_palette()
    # Map zone names to colours via the demo zone palette + label map.
    label_to_int = {"contact": 0, "desert": 1,
                    "intermediate": 2, "far": 3}

    def colour_for_zone(z: str) -> str:
        i = label_to_int.get(z, hash(z) % 4)
        return palette.get(i, "#888888")

    # Left column rectangles.
    left_brackets: dict[str, tuple[float, float]] = {}
    cur_top = y_top
    for z in zones:
        h = fl_n[z] * (y_top - y_bot)
        left_brackets[z] = (cur_top - h, cur_top)
        cur_top -= h

    # Right column rectangles.
    right_brackets: dict[str, tuple[float, float]] = {}
    cur_top = y_top
    for z in zones:
        h = fr_n[z] * (y_top - y_bot)
        right_brackets[z] = (cur_top - h, cur_top)
        cur_top -= h

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Ribbons.
    for z in zones:
        l_bot, l_top = left_brackets[z]
        r_bot, r_top = right_brackets[z]
        path = _ribbon_path(x_left_inner, x_right_inner,
                            l_top, l_bot, r_top, r_bot)
        colour = colour_for_zone(z)
        ax.add_patch(mpatches.PathPatch(
            path, facecolor=colour, edgecolor="white",
            linewidth=0.6, alpha=0.65, zorder=2,
        ))

    # Left rectangles + labels.
    for z in zones:
        l_bot, l_top = left_brackets[z]
        ax.add_patch(mpatches.Rectangle(
            (x_left_outer, l_bot),
            x_left_inner - x_left_outer,
            l_top - l_bot,
            facecolor=colour_for_zone(z),
            edgecolor="white", linewidth=0.6, zorder=4,
        ))
        # Zone label inside.
        ax.text((x_left_outer + x_left_inner) / 2,
                (l_top + l_bot) / 2,
                f"{z}\n{smart_fmt(fl_n[z] * 100)}%",
                ha="center", va="center", fontsize=6.4,
                color="white", fontweight="bold", zorder=5)

    # Right rectangles + labels.
    for z in zones:
        r_bot, r_top = right_brackets[z]
        ax.add_patch(mpatches.Rectangle(
            (x_right_inner, r_bot),
            x_right_outer - x_right_inner,
            r_top - r_bot,
            facecolor=colour_for_zone(z),
            edgecolor="white", linewidth=0.6, zorder=4,
        ))
        ax.text((x_right_inner + x_right_outer) / 2,
                (r_top + r_bot) / 2,
                f"{z}\n{smart_fmt(fr_n[z] * 100)}%",
                ha="center", va="center", fontsize=6.4,
                color="white", fontweight="bold", zorder=5)

    # Column headers.
    ax.text((x_left_outer + x_left_inner) / 2, y_top + 0.02,
            cond_left, ha="center", va="bottom", fontsize=8.2,
            color="#222222", fontweight="bold")
    ax.text((x_right_inner + x_right_outer) / 2, y_top + 0.02,
            cond_right, ha="center", va="bottom", fontsize=8.2,
            color="#222222", fontweight="bold")

    # Direction arrow under the ribbons.
    ax.annotate("", xy=(x_right_inner - 0.005, 0.02),
                xytext=(x_left_inner + 0.005, 0.02),
                arrowprops=dict(arrowstyle="->", color="#888888",
                                lw=1.0))
    ax.text(0.5, 0.02, f"{cond_left} -> {cond_right}",
            ha="center", va="bottom", fontsize=6.4,
            color="#666666", zorder=4)

    # Headline: largest delta.
    deltas = [(z, fr_n[z] - fl_n[z]) for z in zones]
    biggest = max(deltas, key=lambda kv: abs(kv[1]))
    sign = "+" if biggest[1] > 0 else "-"
    ax.set_title(
        f"{contract.title}  ·  largest shift: {biggest[0]} "
        f"{sign}{smart_fmt(abs(biggest[1]) * 100)}pp",
        fontsize=8.4, pad=8,
    )
    return ax
