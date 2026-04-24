"""Geometric mediation path diagram — three-node DAG showing whether
a mediator absorbs the direct effect.

X (predictor) -> Y (outcome) is the direct path; X -> M -> Y is the
indirect path. Path beta +/- 95 % CI annotated on each arrow. If the
direct beta's CI crosses 0 while the indirect beta's CI excludes 0,
the mediator absorbs the direct effect (full mediation).

Conceptual family: >=3 texts + >=2 patches. Satisfied by 3 node
labels + 3 path-beta annotations + 3 node circle patches + 3
FancyArrowPatch edges (patches too).
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import MediationPathEstimate


class MediationDiagramInput(RecipeContract):
    path: MediationPathEstimate
    collapsed_direct_style: str = Field(
        "dashed",
        description="'strikethrough' | 'inflated_ci' | 'dashed'",
    )
    annotate_p: bool = True
    title: str = "Geometric mediation"


def _demo() -> MediationDiagramInput:
    # Manuscript-consistent example: genotype -> cell_area -> standoff.
    # Direct effect collapses; indirect effect is significant.
    return MediationDiagramInput(
        path=MediationPathEstimate(
            predictor_label="genotype (LI vs WT)",
            mediator_label="cell area (um^2)",
            outcome_label="standoff (um)",
            direct_beta=0.08,
            direct_ci=(-0.12, 0.28),
            direct_p_value=0.42,
            indirect_beta=0.41,
            indirect_ci=(0.22, 0.62),
            mediator_path_beta=0.58,
            mediator_path_ci=(0.40, 0.76),
            outcome_path_beta=0.71,
            outcome_path_ci=(0.54, 0.88),
            n_bootstrap=2000,
        ),
    )


_META = RecipeMetadata(
    name="geometric_mediation_path_diagram",
    modality="biophysics_scaling",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Does the putative mediator absorb the direct effect of "
        "predictor on outcome (path diagram with bootstrap CIs)?"
    ),
    required_fields=("path",),
    optional_fields=("collapsed_direct_style", "annotate_p", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("shared_manifold_scatter_with_residuals",),
)


def _ci_excludes_zero(lo: float, hi: float) -> bool:
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


@register_recipe(
    metadata=_META,
    contract=MediationDiagramInput,
    demo_contract=_demo,
)
def render(contract: MediationDiagramInput, ax=None, **_):
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    path = contract.path
    direct_abs = _ci_excludes_zero(*path.direct_ci)
    indirect_abs = _ci_excludes_zero(*path.indirect_ci)

    # Node positions (data coords 0..1).
    # X at lower-left, M at top-center, Y at lower-right.
    x_pos = (0.08, 0.30)
    m_pos = (0.50, 0.78)
    y_pos = (0.92, 0.30)

    node_r = 0.085
    node_face = {"X": "#1565C0", "M": "#E65100", "Y": "#6A1B9A"}

    for key, (pos, label, beta_in, beta_out) in (
        ("X", (x_pos, path.predictor_label, None, None)),
        ("M", (m_pos, path.mediator_label, None, None)),
        ("Y", (y_pos, path.outcome_label, None, None)),
    ):
        ax.add_patch(mpatches.Circle(
            pos, node_r,
            facecolor=node_face[key], edgecolor="white",
            linewidth=1.2, zorder=5,
        ))
        ax.text(pos[0], pos[1], key,
                ha="center", va="center", fontsize=9.6,
                color="white", fontweight="bold", zorder=6)
        # External label — X and Y go BELOW the node, M goes ABOVE
        # (M sits above the diagonal edges, which otherwise overlap
        # a below-node label).
        if key == "M":
            ax.text(pos[0], pos[1] + node_r + 0.04, label,
                    ha="center", va="bottom", fontsize=6.6,
                    color=node_face[key], fontweight="bold", zorder=6)
        else:
            ax.text(pos[0], pos[1] - node_r - 0.06, label,
                    ha="center", va="top", fontsize=6.6,
                    color=node_face[key], fontweight="bold", zorder=6)
        _ = beta_in, beta_out  # labels are drawn on edges below

    def _edge(a, b, colour, lw, style, beta, ci, p=None, label_above=True):
        arrow = FancyArrowPatch(
            a, b,
            arrowstyle="->", mutation_scale=16,
            color=colour, lw=lw, linestyle=style,
            shrinkA=node_r * 72 * 0.5, shrinkB=node_r * 72 * 0.5,
            zorder=4,
        )
        ax.add_patch(arrow)
        # Midpoint label.
        mx = (a[0] + b[0]) / 2
        my = (a[1] + b[1]) / 2
        off = 0.04 if label_above else -0.04
        label = (f"beta = {smart_fmt(beta)}  "
                 f"[{smart_fmt(ci[0])}, {smart_fmt(ci[1])}]")
        if contract.annotate_p and p is not None:
            label += f"   p = {smart_fmt(p)}"
        ax.text(mx, my + off, label,
                ha="center", va="bottom" if label_above else "top",
                fontsize=6.4, color=colour, zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec=colour, lw=0.4, alpha=0.85))

    # X -> M (solid, emphasised if CI excludes 0).
    _edge(x_pos, m_pos,
          colour="#333333", lw=1.1 + (0.6 if indirect_abs else 0),
          style="-", beta=path.mediator_path_beta,
          ci=path.mediator_path_ci, label_above=True)
    # M -> Y (solid, emphasised if CI excludes 0).
    _edge(m_pos, y_pos,
          colour="#333333", lw=1.1 + (0.6 if indirect_abs else 0),
          style="-", beta=path.outcome_path_beta,
          ci=path.outcome_path_ci, label_above=True)
    # X -> Y (direct path — dashed / de-emphasised if collapsed).
    direct_style = "-" if direct_abs else "--"
    direct_lw = 1.4 if direct_abs else 0.7
    direct_colour = "#333333" if direct_abs else "#999999"
    _edge(x_pos, y_pos,
          colour=direct_colour, lw=direct_lw, style=direct_style,
          beta=path.direct_beta, ci=path.direct_ci,
          p=path.direct_p_value, label_above=False)

    # Footer callout: verdict.
    if indirect_abs and not direct_abs:
        verdict = ("mediation supported: indirect CI excludes 0; "
                   "direct CI crosses 0")
    elif direct_abs and indirect_abs:
        verdict = ("partial mediation: both paths active")
    elif direct_abs and not indirect_abs:
        verdict = "no mediation: direct path active, indirect CI crosses 0"
    else:
        verdict = "inconclusive: both CIs cross 0"

    ax.text(0.5, 0.05, verdict,
            ha="center", va="center", fontsize=6.6,
            color="#333333", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.28", fc="#F5F5F5",
                      ec="#BBBBBB", lw=0.4),
            zorder=7)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    ax.set_title(
        f"{contract.title}  ·  bootstrap n = {path.n_bootstrap}",
        fontsize=8.4, pad=4,
    )
    return ax
