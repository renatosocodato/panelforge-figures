"""Two-parameter (codimension-2) bifurcation map.

The v1.0 roster has 1-parameter Hopf / saddle-node / pitchfork recipes
— each a slice through a larger bifurcation structure. This recipe
renders the joint (μ, ν)-plane that *organizes* those slices: curves of
saddle-node and Hopf bifurcations, their intersections at codimension-2
points (Bogdanov–Takens, cusp), and the regime shading that labels the
qualitatively distinct dynamical behaviours.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
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


class Codim2Point(RecipeContract):
    label: str
    mu: float
    nu: float


class Codim2Curve(RecipeContract):
    kind: str = Field(..., description="'saddle_node' | 'hopf' | 'pitchfork' | 'heteroclinic'")
    mu: list[float]
    nu: list[float]


class Codim2RegimeRegion(RecipeContract):
    label: str
    polygon_mu: list[float]
    polygon_nu: list[float]


class Codim2Input(RecipeContract):
    mu_range: tuple[float, float]
    nu_range: tuple[float, float]
    curves: list[Codim2Curve]
    codim2_points: list[Codim2Point] = Field(default_factory=list)
    regime_regions: list[Codim2RegimeRegion] = Field(default_factory=list)
    mu_label: str = r"$\mu$"
    nu_label: str = r"$\nu$"
    title: str = "Codimension-2 bifurcation map"


def _demo() -> Codim2Input:
    # Cusp catastrophe: x^3 + mu*x + nu = 0.
    # Discriminant 4*mu^3 + 27*nu^2 = 0 → SN curves ν = ±(2/√27) (−μ)^(3/2)
    # for μ < 0, meeting at the cusp at the origin.
    mu_sn = np.linspace(-1.6, 0.0, 200)
    nu_sn_upper = (2.0 / np.sqrt(27.0)) * (-mu_sn) ** 1.5
    nu_sn_lower = -nu_sn_upper

    # A synthetic Hopf curve: ν = 0.4 + 0.25 μ for μ ∈ [-0.5, 1.2], ending
    # at a Bogdanov-Takens point where it meets the upper SN branch.
    mu_hopf = np.linspace(-0.45, 1.4, 160)
    nu_hopf = 0.40 + 0.25 * mu_hopf

    # A synthetic pitchfork line at ν = 0 for μ > 0 (symmetric regime).
    mu_pf = np.linspace(0.0, 1.5, 80)
    nu_pf = np.zeros_like(mu_pf)

    # Regime regions (approximate convex polygons for shading).
    # "tristable" sits inside the cusp (small |mu|, |nu| < SN curves).
    theta = np.linspace(0.0, 2.0 * np.pi, 60)
    mu_wedge = -0.8 + 0.8 * np.cos(theta) * 0.9
    nu_wedge = 0.0 + 0.25 * np.sin(theta)
    tristable = Codim2RegimeRegion(
        label="tristable",
        polygon_mu=mu_wedge.tolist(),
        polygon_nu=nu_wedge.tolist(),
    )

    # Oscillatory region: above the Hopf curve, to the right.
    mu_osc = np.array([-0.45, 1.4, 1.4, -0.45])
    nu_osc = np.array([0.40 - 0.25 * 0.45, 0.40 + 0.25 * 1.4,
                       1.2, 1.2])
    oscillatory = Codim2RegimeRegion(
        label="oscillatory",
        polygon_mu=mu_osc.tolist(),
        polygon_nu=nu_osc.tolist(),
    )

    codim2_pts = [
        Codim2Point(label="cusp", mu=0.0, nu=0.0),
        Codim2Point(label="BT", mu=-0.45, nu=0.40 - 0.25 * 0.45),
    ]

    curves = [
        Codim2Curve(kind="saddle_node", mu=mu_sn.tolist(),
                    nu=nu_sn_upper.tolist()),
        Codim2Curve(kind="saddle_node", mu=mu_sn.tolist(),
                    nu=nu_sn_lower.tolist()),
        Codim2Curve(kind="hopf", mu=mu_hopf.tolist(), nu=nu_hopf.tolist()),
        Codim2Curve(kind="pitchfork", mu=mu_pf.tolist(), nu=nu_pf.tolist()),
    ]

    return Codim2Input(
        mu_range=(-1.8, 1.6),
        nu_range=(-0.6, 1.2),
        curves=curves,
        codim2_points=codim2_pts,
        regime_regions=[tristable, oscillatory],
    )


_META = RecipeMetadata(
    name="codim2_bifurcation_map",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.bifurcation,
    answers_question=(
        "In the two-parameter (μ, ν) plane, where are the saddle-node / Hopf / "
        "pitchfork curves and the codimension-2 organizing points?"
    ),
    required_fields=("mu_range", "nu_range", "curves"),
    optional_fields=("codim2_points", "regime_regions", "mu_label", "nu_label", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=(
        "bifurcation_saddle_node",
        "bifurcation_hopf",
        "bifurcation_pitchfork",
    ),
)


_CURVE_STYLE = {
    "saddle_node": {"color": "#D32F2F", "lw": 1.4, "ls": "-", "label": "saddle-node"},
    "hopf":        {"color": "#1565C0", "lw": 1.4, "ls": "-", "label": "Hopf"},
    "pitchfork":   {"color": "#6A1B9A", "lw": 1.4, "ls": "--", "label": "pitchfork"},
    "heteroclinic": {"color": "#333333", "lw": 1.2, "ls": ":", "label": "heteroclinic"},
}


@register_recipe(
    metadata=_META,
    contract=Codim2Input,
    demo_contract=_demo,
)
def render(contract: Codim2Input, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Regime regions as soft shaded polygons under the curves.
    regime_palette_keys = list(palette.semantic.keys())
    for i, region in enumerate(contract.regime_regions):
        color = (palette.pick(regime_palette_keys[i % len(regime_palette_keys)])
                 if regime_palette_keys else palette[i % len(palette.colors)])
        ax.add_patch(mpatches.Polygon(
            list(zip(region.polygon_mu, region.polygon_nu)),
            facecolor=color, edgecolor="none", alpha=0.14, zorder=1,
        ))
        # Label at polygon centroid (approx).
        cx = float(np.mean(region.polygon_mu))
        cy = float(np.mean(region.polygon_nu))
        ax.text(cx, cy, region.label, ha="center", va="center",
                fontsize=6.8, color="#333333", fontweight="normal",
                bbox=dict(boxstyle="round,pad=0.16", fc="white",
                          ec="none", alpha=0.75), zorder=4)

    # Bifurcation curves.
    seen_kinds: set[str] = set()
    for curve in contract.curves:
        style = _CURVE_STYLE.get(curve.kind, {
            "color": "#555555", "lw": 1.1, "ls": "-", "label": curve.kind,
        })
        label = style["label"] if curve.kind not in seen_kinds else None
        seen_kinds.add(curve.kind)
        ax.plot(curve.mu, curve.nu,
                color=style["color"], lw=style["lw"], ls=style["ls"],
                zorder=3, label=label)

    # Codim-2 points: hollow circles with a halo'd label.
    for pt in contract.codim2_points:
        ax.scatter([pt.mu], [pt.nu], s=56, facecolor="white",
                   edgecolor="black", linewidth=1.2, zorder=6)
        ax.annotate(
            pt.label,
            xy=(pt.mu, pt.nu),
            xytext=(6, 6), textcoords="offset points",
            fontsize=6.8, color="#111111",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7,
        )

    ax.axhline(0, color="#CCCCCC", lw=0.4, zorder=0)
    ax.axvline(0, color="#CCCCCC", lw=0.4, zorder=0)
    ax.set_xlim(*contract.mu_range)
    ax.set_ylim(*contract.nu_range)
    ax.set_xlabel(contract.mu_label)
    ax.set_ylabel(contract.nu_label)
    ax.set_title(
        f"{contract.title}  ·  {len(contract.codim2_points)} codim-2 pts,  "
        f"{len(contract.curves)} curves",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    _ = smart_fmt
    return ax
