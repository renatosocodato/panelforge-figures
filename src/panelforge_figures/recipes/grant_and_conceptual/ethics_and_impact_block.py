"""Ethics & impact block — two-column panel with ethics sub-sections
(data protection, animal welfare, DEI) and impact sub-sections
(scientific, societal, economic).

Conceptual family: ≥3 text artists + ≥2 patches.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class EthicsImpactSection(RecipeContract):
    heading: str
    bullets: list[str] = Field(..., min_length=1, max_length=4)


class EthicsImpactInput(RecipeContract):
    ethics_sections: list[EthicsImpactSection] = Field(..., min_length=2, max_length=4)
    impact_sections: list[EthicsImpactSection] = Field(..., min_length=2, max_length=4)
    title: str = "Ethics & impact"


def _demo() -> EthicsImpactInput:
    return EthicsImpactInput(
        ethics_sections=[
            EthicsImpactSection(
                heading="Data protection",
                bullets=["GDPR-compliant pipelines",
                         "Pseudonymised IDs, local lock-boxes",
                         "Institutional DPIA filed"],
            ),
            EthicsImpactSection(
                heading="Animal welfare",
                bullets=["3Rs adherence, FELASA B trained staff",
                         "Ethics approval ORBEA/DGAV",
                         "In vivo work limited to WP3"],
            ),
            EthicsImpactSection(
                heading="DEI & open science",
                bullets=["50/50 gender target on trainees",
                         "All code + data released CC-BY-4.0"],
            ),
        ],
        impact_sections=[
            EthicsImpactSection(
                heading="Scientific",
                bullets=["First sex-stratified microglial map",
                         "New molecular-gate framework",
                         "3 Q1 publications + dataset"],
            ),
            EthicsImpactSection(
                heading="Societal",
                bullets=["Patient-advocate sounding board",
                         "Open outreach kit (Portuguese + English)"],
            ),
            EthicsImpactSection(
                heading="Economic",
                bullets=["Industry LoI for a Phase-0 spinout",
                         "2 patent-ready assays by M30"],
            ),
        ],
    )


_META = RecipeMetadata(
    name="ethics_and_impact_block",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question=(
        "What are the ethics safeguards and societal-impact pathways "
        "of this proposal?"
    ),
    required_fields=("ethics_sections", "impact_sections"),
    optional_fields=("title",),
    file_format_hints=("yaml", "toml"),
    alternatives_in_modality=("executive_summary_tile",),
)


@register_recipe(
    metadata=_META,
    contract=EthicsImpactInput,
    demo_contract=_demo,
)
def render(contract: EthicsImpactInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 4.2))
    AESTHETIC.apply_to_ax(ax)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)

    # Two-column split: left ethics, right impact.
    col_width = 0.46
    col_x = [0.02, 0.52]
    col_headings = ["ETHICS", "IMPACT"]
    col_colors = ["#5D4037", "#0277BD"]

    # Column header banners.
    for i, (x, heading, color) in enumerate(
        zip(col_x, col_headings, col_colors)
    ):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, 0.91), col_width, 0.07,
            boxstyle="round,pad=0.005,rounding_size=0.012",
            facecolor=color, edgecolor="none", alpha=0.92,
            zorder=3,
        ))
        ax.text(x + col_width / 2, 0.945, heading,
                ha="center", va="center", fontsize=8.6,
                color="white", fontweight="bold", zorder=4)

    # Populate sections per column.
    for i, (x, sections, color) in enumerate(
        zip(col_x, [contract.ethics_sections, contract.impact_sections],
            col_colors)
    ):
        n_sec = len(sections)
        # Allocate vertical space 0.05 to 0.88.
        y_top = 0.88
        y_bot = 0.05
        sec_h = (y_top - y_bot - 0.02 * (n_sec - 1)) / n_sec
        for j, sec in enumerate(sections):
            y = y_top - (j + 1) * sec_h - j * 0.02
            ax.add_patch(mpatches.FancyBboxPatch(
                (x, y), col_width, sec_h,
                boxstyle="round,pad=0.004,rounding_size=0.010",
                facecolor="#FAFAFA", edgecolor="#BBBBBB",
                linewidth=0.6, zorder=3,
            ))
            # Section heading accent bar.
            ax.add_patch(mpatches.Rectangle(
                (x, y + sec_h - 0.02), col_width, 0.02,
                facecolor=color, edgecolor="none", alpha=0.85, zorder=4,
            ))
            ax.text(x + 0.01, y + sec_h - 0.035, sec.heading,
                    ha="left", va="top", fontsize=7.4,
                    color=color, fontweight="bold", zorder=5)
            # Bullets — wrap at a width that matches the column width
            # comfortably and never breaks on hyphens (so tokens like
            # "CC-BY-4.0" or "lock-boxes" stay intact).
            import textwrap
            bullet_y0 = y + sec_h - 0.08
            line_dy = 0.024
            cur_y = bullet_y0
            for b in sec.bullets[:3]:
                lines = textwrap.wrap(
                    b, width=36, break_on_hyphens=False,
                    break_long_words=False,
                )
                for li, line in enumerate(lines):
                    prefix = "• " if li == 0 else "  "
                    ax.text(x + 0.018, cur_y,
                            f"{prefix}{line}",
                            ha="left", va="top", fontsize=6.4,
                            color="#333333", zorder=5)
                    cur_y -= line_dy
                cur_y -= 0.010   # extra gap between bullets

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
