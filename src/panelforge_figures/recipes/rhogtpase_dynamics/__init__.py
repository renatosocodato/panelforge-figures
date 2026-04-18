"""RhoGTPase dynamics — phase portraits, potential landscapes, bifurcations."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="rhogtpase_dynamics",
    description=(
        "ODE/PDE landscapes of small-GTPase activity: tristable / bistable / "
        "oscillator phase portraits, 1-D and 2-D potential landscapes, "
        "saddle-node / Hopf / pitchfork bifurcations, nullcline intersections, "
        "quasi-steady-state reductions, timescale-separation diagnostics, "
        "basin-of-attraction maps."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    basin_of_attraction_map,
    bifurcation_hopf,
    bifurcation_pitchfork,
    bifurcation_saddle_node,
    nullcline_intersection_annotated,
    phase_portrait_bistable,
    phase_portrait_oscillator,
    phase_portrait_tristable,
    potential_landscape_1d,
    potential_landscape_2d_heatmap,
    quasi_steady_state_reduction,
    timescale_separation_diagnostic,
)

__all__ = [
    "AESTHETIC",
    "basin_of_attraction_map",
    "bifurcation_hopf",
    "bifurcation_pitchfork",
    "bifurcation_saddle_node",
    "nullcline_intersection_annotated",
    "phase_portrait_bistable",
    "phase_portrait_oscillator",
    "phase_portrait_tristable",
    "potential_landscape_1d",
    "potential_landscape_2d_heatmap",
    "quasi_steady_state_reduction",
    "timescale_separation_diagnostic",
]
