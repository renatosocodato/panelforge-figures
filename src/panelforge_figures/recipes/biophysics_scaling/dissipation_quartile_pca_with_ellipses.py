"""Dissipation-quartile PCA with ellipses — per-cell PCA scatter in
the dissipation-proxy space, coloured by dissipation quartile, with
per-quartile 95%-probability ellipse boundary as the fit line.

Renders one ellipse per quartile (1..4) computed from the per-quartile
covariance matrix; the scatter shows individual cells coloured by
quartile membership. Per-quartile centroid markers sit at the centre
of each ellipse for quick comparison.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the per-cell scatter + per-quartile ellipse boundary lines.
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
from ._shared import DissipationProxyRow


class DissipationQuartilePCAInput(RecipeContract):
    points: list[DissipationProxyRow] = Field(..., min_length=8)
    pc1_label: str = "PC1 (dissipation proxy)"
    pc2_label: str = "PC2 (geometry proxy)"
    title: str = "Dissipation-quartile PCA"


def _demo() -> DissipationQuartilePCAInput:
    rng = np.random.default_rng(833)
    # Per-quartile centre + spread; quartile-1 (low dissipation) anchors
    # the lower-left, quartile-4 (high) the upper-right.
    centres = [
        (-1.20, -0.80),  # Q1
        (-0.40, -0.20),  # Q2
        ( 0.50,  0.50),  # Q3
        ( 1.30,  1.20),  # Q4
    ]
    cond_choices = ["female · CTL", "female · CKO",
                    "male · CTL", "male · CKO"]
    points: list[DissipationProxyRow] = []
    for q, (cx, cy) in enumerate(centres, start=1):
        for k in range(20):
            jitter = rng.normal(0.0, 0.40, 2)
            x = float(cx + jitter[0])
            y = float(cy + jitter[1])
            cond = cond_choices[(q + k) % 4]
            points.append(DissipationProxyRow(
                cell_id=f"Q{q}-C{k:02d}",
                condition=cond,
                pc1=x, pc2=y,
                dissipation_quartile=q,
            ))
    return DissipationQuartilePCAInput(points=points)


_META = RecipeMetadata(
    name="dissipation_quartile_pca_with_ellipses",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "In the dissipation-proxy PCA space, how do cells cluster by "
        "dissipation quartile, and how do the per-quartile 95% "
        "probability ellipses separate?"
    ),
    required_fields=("points",),
    optional_fields=("pc1_label", "pc2_label", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("phase_diagram_by_genotype",),
)


def _ellipse_xy(cx, cy, cov, n_sigma=2.0, n_pts=80):
    """Return (n_pts, 2) ellipse boundary at n_sigma covariance contour.

    n_sigma=2.0 ≈ 95% probability mass under bivariate normal.
    """
    # Eigendecompose cov.
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    theta = np.linspace(0.0, 2.0 * np.pi, n_pts)
    a = n_sigma * np.sqrt(max(vals[0], 1e-9))
    b = n_sigma * np.sqrt(max(vals[1], 1e-9))
    unit_circle = np.stack([a * np.cos(theta), b * np.sin(theta)], axis=1)
    rotated = unit_circle @ vecs.T
    return rotated + np.array([cx, cy])


@register_recipe(
    metadata=_META,
    contract=DissipationQuartilePCAInput,
    demo_contract=_demo,
)
def render(contract: DissipationQuartilePCAInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.2))
    AESTHETIC.apply_to_ax(ax)

    quartiles = sorted({p.dissipation_quartile for p in contract.points})
    import matplotlib as mpl
    cmap = mpl.colormaps["viridis"].resampled(len(quartiles))
    palette = {q: cmap(i) for i, q in enumerate(quartiles)}

    centroids: list[tuple[int, float, float]] = []
    for q in quartiles:
        sub = [p for p in contract.points if p.dissipation_quartile == q]
        xs = np.array([p.pc1 for p in sub], float)
        ys = np.array([p.pc2 for p in sub], float)
        if xs.size < 2:
            continue
        # Per-cell scatter.
        ax.scatter(xs, ys, s=22, color=palette[q], alpha=0.62,
                   edgecolor="white", linewidth=0.4, zorder=3,
                   label=f"Q{q} (n={xs.size})")

        # Per-quartile 95% ellipse boundary (the fit line for the
        # scatter_collapse family rule).
        cov = np.cov(np.stack([xs, ys], axis=0))
        cx = float(xs.mean())
        cy = float(ys.mean())
        ell = _ellipse_xy(cx, cy, cov, n_sigma=2.0)
        ax.plot(ell[:, 0], ell[:, 1], color=palette[q], lw=1.4,
                alpha=0.92, zorder=4)
        # Centroid marker.
        ax.scatter([cx], [cy], s=80, marker="X",
                   facecolor=palette[q], edgecolor="white",
                   linewidth=1.0, zorder=5)
        centroids.append((q, cx, cy))

    # Connect per-quartile centroids to surface the dissipation gradient.
    if len(centroids) >= 2:
        cx_arr = np.array([c[1] for c in sorted(centroids, key=lambda c: c[0])])
        cy_arr = np.array([c[2] for c in sorted(centroids, key=lambda c: c[0])])
        ax.plot(cx_arr, cy_arr, color="#222222", lw=0.8, ls=":",
                alpha=0.6, zorder=4)

    ax.set_xlabel(contract.pc1_label)
    ax.set_ylabel(contract.pc2_label)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(fontsize=6.4, frameon=False,
              loc="upper left", handlelength=1.4)

    # Title summary: separation distance Q1 → Q4.
    if len(centroids) >= 2:
        c_first = centroids[0]
        c_last = centroids[-1]
        sep = float(np.hypot(c_last[1] - c_first[1],
                             c_last[2] - c_first[2]))
        ax.set_title(
            f"{contract.title}  ·  Q{c_first[0]} to Q{c_last[0]} "
            f"centroid separation = {smart_fmt(sep)}",
            fontsize=8.2, pad=4,
        )
    else:
        ax.set_title(contract.title, fontsize=8.2, pad=4)
    return ax
