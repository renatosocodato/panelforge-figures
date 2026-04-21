"""Network and pathway figures — hive, chord, Sankey, force layout, hubs, crosstalk, KEGG, regulons."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="network_and_pathway",
    description=(
        "Regulatory-network hive plots, directed force-layout graphs, "
        "interaction chord diagrams, hub-gene radials, PPI seed-"
        "expansion two-shells, pathway-flux Sankey-like flows and "
        "temporal streamgraphs, module eigengene heatmaps, TF-regulon "
        "activity heatmaps, pathway crosstalk matrices, KEGG-style "
        "enrichment overlays, centrality-degree distributions, "
        "centrality-vs-effect scatters, module-preservation Zsummary "
        "ladders, differential subnetworks."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    centrality_degree_distribution,
    centrality_vs_effect_scatter,
    directed_network_force_layout,
    hub_gene_radial,
    interaction_chord_diagram,
    kegg_overlay_enrichment,
    module_eigengene_heatmap,
    module_preservation_zsummary,
    pathway_crosstalk_matrix,
    pathway_flux_sankey_like,
    pathway_flux_streamgraph,
    ppi_seed_expansion,
    regulatory_network_hive,
    regulon_activity_heatmap,
    subnetwork_comparison_diff,
)

__all__ = [
    "AESTHETIC",
    "centrality_degree_distribution",
    "centrality_vs_effect_scatter",
    "directed_network_force_layout",
    "hub_gene_radial",
    "interaction_chord_diagram",
    "kegg_overlay_enrichment",
    "module_eigengene_heatmap",
    "module_preservation_zsummary",
    "pathway_crosstalk_matrix",
    "pathway_flux_sankey_like",
    "pathway_flux_streamgraph",
    "ppi_seed_expansion",
    "regulatory_network_hive",
    "regulon_activity_heatmap",
    "subnetwork_comparison_diff",
]
