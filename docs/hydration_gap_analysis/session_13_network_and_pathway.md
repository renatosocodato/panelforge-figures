# Session 13 — Gap Analysis: `network_and_pathway` (5 → 15, +10)

**Branch:** `v1.1/session-13-network_and_pathway`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`network_and_pathway` powers the **Commentary** and **Targetome**
network vocabulary. v1.0 ships the hive, chord, Sankey-like flow,
module eigengene heatmap and centrality-degree distribution (5
recipes). Missing are the **direction-aware force layout**, **pathway
crosstalk matrix**, **hub-centred radial**, **module preservation
Zsummary**, **centrality-vs-effect scatter**, **differential
subnetwork**, **KEGG-style enrichment overlay**, **TF-regulon heatmap**,
**seed-expansion PPI**, and **pathway-flux streamgraph** reviewers
expect.

## Current 5-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `centrality_degree_distribution` | `diagnostic_curve` | degree CCDF with hub annotation |
| 2 | `interaction_chord_diagram` | `flow` | chord ring of interactions |
| 3 | `module_eigengene_heatmap` | `heatmap` | module × sample expression |
| 4 | `pathway_flux_sankey_like` | `matrix` | Sankey-like flow |
| 5 | `regulatory_network_hive` | `scatter_collapse` | hive axes layout |

## Proposed 10 new recipes

All 10 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Network topology (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `directed_network_force_layout` | In a directed regulatory network, how do nodes cluster spatially and what are the dominant directed hubs? | `regulatory_network_hive` (**axis-based** hive layout, not force-directed); `interaction_chord_diagram` (chord ring) | Spring-layout force-directed graph with **arrowed directed edges**, node size ∝ out-degree, colour ∝ mechanism class. Different visual (force vs hive). | `conceptual` |
| N2 | `hub_gene_radial` | Around a single hub gene, what are its immediate neighbours and their edge weights? | `regulatory_network_hive` (global hive); `centrality_degree_distribution` (aggregate statistic, not a neighbourhood) | Hub at the centre with N neighbours arranged on a circle, radius ∝ edge weight, colour by interaction sign. Different axis grammar (egocentric vs global). | `conceptual` |
| N3 | `ppi_seed_expansion` | Starting from a seed gene set, what does the first-neighbour expansion look like? | `regulatory_network_hive` (global); `directed_network_force_layout` (global) | **Two-shell** layout: seed nodes tight centre, expanded neighbours ring. Different emphasis (seed-expansion convention). | `conceptual` |

### Pathway-level matrices / overlays (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N4 | `pathway_crosstalk_matrix` | How strongly does each pathway "talk" to each other (shared genes, correlated activity)? | `module_eigengene_heatmap` (**module × sample**, not pathway × pathway); `pathway_flux_sankey_like` (flow, not crosstalk score) | Symmetric **pathway × pathway** crosstalk heatmap with clustered rows + top-pair callout. Different axis (pathway × pathway vs module × sample). | `matrix` |
| N5 | `kegg_overlay_enrichment` | For a candidate KEGG pathway, which nodes are enriched in my hit list? | None — no pathway-diagram overlay exists | KEGG-style schematic node map with per-node colour ∝ −log10(p_adj) and size ∝ gene count. Stylised box-and-arrow grammar. | `conceptual` |
| N6 | `regulon_activity_heatmap` | How does each TF-regulon's activity score vary across samples / conditions? | `module_eigengene_heatmap` (**module** eigengene, not regulon activity); `pathway_flux_sankey_like` (flow) | **Regulon × sample** heatmap with a TF-name column on the left and a condition annotation strip. Distinct axis (TF × sample). | `heatmap` |

### Differential networks + metrics (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N7 | `module_preservation_zsummary` | How strongly is each module preserved across studies / datasets, by WGCNA Zsummary? | `centrality_degree_distribution` (single statistic on one graph); `module_eigengene_heatmap` (activity, not preservation) | **Module × Zsummary** horizontal ladder with preservation thresholds (Z=2, Z=10) marked. Different statistic (preservation) and different axis (per-module, no samples). | `ladder` |
| N8 | `centrality_vs_effect_scatter` | Do the most-central nodes have the largest effect sizes? | `centrality_degree_distribution` (degree only, no effect); no effect-vs-centrality scatter currently exists | **Centrality × effect-size** scatter with labelled top-right genes and Pearson r callout. Different grammar (correlation vs distribution). | `scatter_collapse` |
| N9 | `subnetwork_comparison_diff` | Between conditions, which edges gain / lose weight (differential subnetwork)? | `regulatory_network_hive` (single condition); `directed_network_force_layout` (single) | **Differential graph** with per-edge colour ∝ Δ-weight (gain / loss), node size ∝ total degree, legend for gain / loss. Different quantity (Δ vs static). | `conceptual` |

### Pathway temporal dynamics (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N10 | `pathway_flux_streamgraph` | How does pathway-activity flux redistribute across pathways over time? | `pathway_flux_sankey_like` (**static** flow, not temporal); `module_eigengene_heatmap` (activity) | **Streamgraph** of pathway flux(t) stacked and normalised, with dominant-pathway bands colour-coded. Different visual grammar (streamgraph) and different axis (time). | `timecourse_hierarchical_ci` |

## Distinctness summary

All 10 pass the three distinctness tests:

1. **No name collision** with the 5 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different topology, axis, statistic, or temporal).
3. **No grammar duplication** — `conceptual` × 4 (force-directed, hub-radial, seed-expansion, diff-network) all with distinct layouts; `matrix` × 2 (Sankey-flow, crosstalk); `heatmap` × 2 (eigengene, regulon).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 10 recipes use the existing `ModalityAesthetic` (`mechanism_class` palette).
- [x] All 10 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 10 → modality goes from **5 → 15** recipes. Total catalog goes from **251 → 261**. Tests projected: **1306 → ~1356** (5 per recipe × 10).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
