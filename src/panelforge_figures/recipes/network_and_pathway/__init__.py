"""Network and pathway figures — hive, chord, Sankey-like, module heatmap, centrality."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="network_and_pathway",
    description=(
        "Regulatory-network hive plots, interaction chord diagrams, pathway-"
        "flux Sankey-like flows, module eigengene heatmaps, centrality-degree "
        "distribution ladders."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    centrality_degree_distribution,
    interaction_chord_diagram,
    module_eigengene_heatmap,
    pathway_flux_sankey_like,
    regulatory_network_hive,
)

__all__ = [
    "AESTHETIC",
    "centrality_degree_distribution",
    "interaction_chord_diagram",
    "module_eigengene_heatmap",
    "pathway_flux_sankey_like",
    "regulatory_network_hive",
]
