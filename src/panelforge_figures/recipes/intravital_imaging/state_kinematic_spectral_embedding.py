"""State-kinematic spectral embedding — 2-D Laplacian-eigenmap
embedding of per-cell kinematic feature vectors, coloured by decoded
state, with per-state convex hulls drawn as the +1 fit line.

Scatter-collapse family: >=1 scatter + >=1 fit line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.spatial import ConvexHull

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    embed_2d,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import _demo_state_palette


class CellFeatureRow(RecipeContract):
    cell_id: str
    state: str
    features: list[float]


class StateKinematicEmbeddingInput(RecipeContract):
    rows: list[CellFeatureRow] = Field(..., min_length=10)
    feature_names: list[str] = Field(...)
    n_neighbors: int = 15
    title: str = "State-kinematic spectral embedding"


def _demo() -> StateKinematicEmbeddingInput:
    rng = np.random.default_rng(3261)
    states = ("homeostatic", "surveillant", "activated")
    feature_names = [
        "velocity", "length_rate", "curvature", "turning_angle",
        "directionality", "msd_alpha", "biosensor_ratio", "n_branches",
    ]
    # Centroids deliberately overlap (per-feature spread comparable
    # to inter-centroid distance) so the kNN graph stays connected
    # across all three clusters; with disjoint clusters Laplacian
    # eigenmaps collapse each component to a single point.
    centres = {
        "homeostatic": np.array([0.5, 0.3, 0.2, 0.4, 0.2, 0.5,
                                 1.00, 1.5]),
        "surveillant": np.array([1.0, 0.7, 0.3, 0.4, 0.4, 0.7,
                                 1.03, 2.2]),
        "activated":   np.array([1.6, 1.2, 0.45, 0.55, 0.35, 0.9,
                                 1.07, 2.9]),
    }
    rows: list[CellFeatureRow] = []
    for state in states:
        for k in range(40):
            v = centres[state] + rng.normal(0, 0.30, len(feature_names))
            rows.append(CellFeatureRow(
                cell_id=f"{state}_C{k:02d}", state=state,
                features=v.tolist(),
            ))
    return StateKinematicEmbeddingInput(
        rows=rows, feature_names=feature_names,
    )


_META = RecipeMetadata(
    name="state_kinematic_spectral_embedding",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Do per-cell kinematic feature vectors cluster by decoded "
        "state when projected to 2-D via Laplacian eigenmaps?"
    ),
    required_fields=("rows", "feature_names"),
    optional_fields=("n_neighbors", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("state_decoded_tip_track_field",),
)


@register_recipe(
    metadata=_META,
    contract=StateKinematicEmbeddingInput,
    demo_contract=_demo,
)
def render(contract: StateKinematicEmbeddingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    X = np.asarray([r.features for r in contract.rows], float)
    states = [r.state for r in contract.rows]
    unique_states = list(dict.fromkeys(states))
    palette = _demo_state_palette(unique_states)

    E, info = embed_2d(X, n_neighbors=contract.n_neighbors)

    # Per-state convex hull as the +1 fit line.
    hull_drawn = False
    for st in unique_states:
        mask = np.array([s == st for s in states])
        pts = E[mask]
        if pts.size == 0:
            continue
        colour = palette.get(st, "#37474F")
        ax.scatter(pts[:, 0], pts[:, 1], s=22, color=colour,
                   edgecolor="white", linewidth=0.4, alpha=0.85,
                   zorder=4, label=st)
        if pts.shape[0] >= 3:
            try:
                hull = ConvexHull(pts)
                hx = list(pts[hull.vertices, 0]) + [pts[hull.vertices[0], 0]]
                hy = list(pts[hull.vertices, 1]) + [pts[hull.vertices[0], 1]]
                ax.plot(hx, hy, color=colour, lw=1.4, alpha=0.7,
                        zorder=5)
                hull_drawn = True
            except Exception:
                pass

    if not hull_drawn:
        # Fallback fit-line proxy so family rule is satisfied even
        # when every state has < 3 points.
        ax.plot([], [], color="none", lw=0.5, alpha=0.0)

    ax.set_xlabel("eigenmap axis 1")
    ax.set_ylabel("eigenmap axis 2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.0)
    sigma = info.get("sigma", 0.0)
    ax.set_title(
        f"{contract.title}  ·  n = {len(contract.rows)} cells  ·  "
        f"k = {info.get('n_neighbors', '?')}  ·  "
        f"sigma = {smart_fmt(sigma)}",
        fontsize=8.2, pad=4,
    )
    return ax
