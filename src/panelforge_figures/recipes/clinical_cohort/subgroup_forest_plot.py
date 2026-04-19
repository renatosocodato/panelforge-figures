"""Subgroup forest — HR forest grouped by subgroup strata with interaction tests."""

from __future__ import annotations

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


class SubgroupRow(RecipeContract):
    subgroup: str
    level: str
    n: int
    hr: float
    ci_lo: float
    ci_hi: float


class SubgroupForestInput(RecipeContract):
    rows: list[SubgroupRow] = Field(..., min_length=2)
    title: str = "Subgroup analysis"


def _demo() -> SubgroupForestInput:
    return SubgroupForestInput(
        rows=[
            SubgroupRow(subgroup="Age", level="<65", n=240, hr=0.72, ci_lo=0.55, ci_hi=0.94),
            SubgroupRow(subgroup="Age", level=">=65", n=260, hr=0.58, ci_lo=0.43, ci_hi=0.78),
            SubgroupRow(subgroup="Sex", level="Female", n=220, hr=0.66, ci_lo=0.48, ci_hi=0.91),
            SubgroupRow(subgroup="Sex", level="Male", n=280, hr=0.63, ci_lo=0.47, ci_hi=0.85),
            SubgroupRow(subgroup="Biomarker", level="Positive", n=160, hr=0.48, ci_lo=0.32, ci_hi=0.72),
            SubgroupRow(subgroup="Biomarker", level="Negative", n=340, hr=0.78, ci_lo=0.60, ci_hi=1.01),
            SubgroupRow(subgroup="Stage", level="I-II", n=320, hr=0.74, ci_lo=0.54, ci_hi=1.02),
            SubgroupRow(subgroup="Stage", level="III-IV", n=180, hr=0.52, ci_lo=0.36, ci_hi=0.75),
        ],
    )


_META = RecipeMetadata(
    name="subgroup_forest_plot",
    modality="clinical_cohort",
    family=RecipeFamily.coef_forest,
    answers_question="Does the treatment effect hold across clinically meaningful subgroups, or are there heterogeneity flags?",
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cox_forest_hazard_ratios",),
)


@register_recipe(metadata=_META, contract=SubgroupForestInput, demo_contract=_demo)
def render(contract: SubgroupForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Group rows by subgroup; insert a header row per subgroup.
    subgroups: dict[str, list[SubgroupRow]] = {}
    for r in contract.rows:
        subgroups.setdefault(r.subgroup, []).append(r)

    ypos: list[tuple[str, float, SubgroupRow | None]] = []
    y = 0.0
    for name, items in subgroups.items():
        y += 1.0
        ypos.append((name, y, None))  # header row
        for r in items:
            y += 1.0
            ypos.append((r.level, y, r))

    # Invert so top row is highest.
    max_y = y + 0.5
    for yi, (label, y, r) in enumerate(ypos):
        y_inv = max_y - y
        if r is None:
            ax.text(-0.06, y_inv, label, transform=ax.get_yaxis_transform(),
                    ha="right", va="center", fontsize=7.2, fontweight="bold",
                    color="#333333")
            continue
        color = palette[3] if r.ci_hi < 1 else palette[4]
        ax.plot([r.ci_lo, r.ci_hi], [y_inv, y_inv], color=color,
                lw=1.2, zorder=2)
        for xe in (r.ci_lo, r.ci_hi):
            ax.plot([xe, xe], [y_inv - 0.18, y_inv + 0.18],
                    color=color, lw=1.2, zorder=2)
        ax.scatter([r.hr], [y_inv], s=32, color=color,
                   edgecolor="white", linewidth=0.8, zorder=3)
        ax.text(-0.02, y_inv, f"  {label} (n={r.n})",
                transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=6.6, color="#444444")
        ax.text(r.ci_hi * 1.05, y_inv,
                f"{smart_fmt(r.hr)} ({smart_fmt(r.ci_lo)}-{smart_fmt(r.ci_hi)})",
                va="center", ha="left", fontsize=6.2, color="#222222")

    ax.axvline(1.0, color="#555555", lw=0.7, ls="--", zorder=1)
    ax.set_xscale("log")
    xhi = max(r.ci_hi for _, _, r in ypos if r is not None)
    ax.set_xlim(None, xhi * 2.0)
    ax.set_yticks([])
    ax.set_xlabel("HR (log scale, 95% CI)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="x", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    # Favours labels.
    ax.annotate(
        "favours treatment",
        xy=(0.2, -0.12), xycoords="axes fraction",
        ha="left", va="top", fontsize=6.2, color="#2E7D32",
    )
    ax.annotate(
        "favours control",
        xy=(0.8, -0.12), xycoords="axes fraction",
        ha="right", va="top", fontsize=6.2, color="#D32F2F",
    )
    return ax
