"""RhoGTPase dynamics — phase portraits, potential landscapes, bifurcations."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="rhogtpase_dynamics",
    description=(
        "ODE/PDE landscapes of small-GTPase activity: tristable / bistable / "
        "oscillator / excitable phase portraits, 1-D and 2-D potential "
        "landscapes (including Waddington 3-D surfaces), saddle-node / Hopf / "
        "pitchfork / codimension-2 bifurcations, nullcline intersections, "
        "quasi-steady-state reductions, slow-manifold projections, "
        "timescale-separation diagnostics, basin-of-attraction maps, and "
        "Poincaré first-return maps."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    basin_of_attraction_map,
    bifurcation_hopf,
    bifurcation_pitchfork,
    bifurcation_saddle_node,
    codim2_bifurcation_map,
    excitability_threshold_diagram,
    nullcline_intersection_annotated,
    phase_portrait_bistable,
    phase_portrait_oscillator,
    phase_portrait_tristable,
    phase_portrait_with_trajectories,
    poincare_first_return_map,
    potential_landscape_1d,
    potential_landscape_2d_heatmap,
    potential_landscape_waddington_3d,
    quasi_steady_state_reduction,
    slow_manifold_projection,
    timescale_separation_diagnostic,
)

__all__ = [
    "AESTHETIC",
    "basin_of_attraction_map",
    "bifurcation_hopf",
    "bifurcation_pitchfork",
    "bifurcation_saddle_node",
    "codim2_bifurcation_map",
    "excitability_threshold_diagram",
    "nullcline_intersection_annotated",
    "phase_portrait_bistable",
    "phase_portrait_oscillator",
    "phase_portrait_tristable",
    "phase_portrait_with_trajectories",
    "poincare_first_return_map",
    "potential_landscape_1d",
    "potential_landscape_2d_heatmap",
    "potential_landscape_waddington_3d",
    "quasi_steady_state_reduction",
    "slow_manifold_projection",
    "timescale_separation_diagnostic",
]
