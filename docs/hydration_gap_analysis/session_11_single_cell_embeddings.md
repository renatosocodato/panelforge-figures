# Session 11 — Gap Analysis: `single_cell_embeddings` (7 → 15, +8)

**Branch:** `v1.1/session-11-single_cell_embeddings`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`single_cell_embeddings` powers Targetome scRNA work and any single-
cell omics that lands in the lab. v1.0 ships UMAP-by-cluster with
density contours, UMAP-by-expression, PCA biplot, diffusion map,
pseudotime arrow, cluster-fraction stacks by condition, and gene×
cluster dotplot (7 recipes). Missing are the **multi-condition
density overlay**, **per-sample cluster proportions**, **branching
trajectory**, **per-cluster marker heatmap**, **RNA-velocity field**,
**ligand-receptor signaling dotplot**, **rare-population spotlight**,
and **gene-expression-over-pseudotime** lines.

## Current 7-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `diffusion_map_2d` | `scatter_collapse` | 2-D diffusion map with pseudotime |
| 2 | `expression_dotplot_by_cluster` | `matrix` | gene × cluster dot matrix |
| 3 | `neighborhood_composition_stacked` | `matrix` | cluster fractions **by condition** |
| 4 | `pca_biplot_with_loadings` | `scatter_collapse` | PCA biplot |
| 5 | `trajectory_pseudotime_arrow` | `scatter_collapse` | single summary arrow on UMAP |
| 6 | `umap_categorical_with_density_contours` | `scatter_collapse` | UMAP **by cluster** + per-cluster density |
| 7 | `umap_continuous_expression` | `heatmap` | UMAP coloured by a gene |

## Proposed 8 new recipes

All 8 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### UMAP-space overlays (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S1 | `umap_density_contour_overlay` | Across conditions, how do the density *shapes* of cells shift on the same UMAP embedding? | `umap_categorical_with_density_contours` (**per-cluster** contours within a single dataset) | Measurement: **per-condition density contours** on the same embedding (not per-cluster). A low-alpha grey background scatter + one coloured contour set per condition, with a mean-shift arrow between condition centroids. Different axis semantics (condition × density vs cluster × density). | `scatter_collapse` |
| S2 | `rare_population_highlighted_umap` | Where in UMAP space does a rare population (< 2% of cells) sit, compared to the bulk? | `umap_categorical_with_density_contours` (all clusters equal weight) | **Spotlight** grammar: all non-rare cells greyed to 0.15 alpha, rare population plotted with strong colour + convex hull + median marker + % callout. Different emphasis convention. | `scatter_collapse` |

### Per-sample composition + branching trajectory (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S3 | `cluster_proportion_stacked_by_sample` | Per sample (not per condition), how do cluster proportions vary? | `neighborhood_composition_stacked` (**per-condition** averaged stacks, small N) | Measurement: **per-sample** stacked bars (one bar per biological replicate), with condition-group annotation strip below. Different unit of analysis — finer granularity than condition means. | `matrix` |
| S4 | `trajectory_branching_force_directed` | When the trajectory has multiple branches, where are the branch points and which cells commit to each fate? | `trajectory_pseudotime_arrow` (**single summary arrow**, no branch topology); `diffusion_map_2d` (embedding only, no branch markers) | Measurement: **branching-trajectory topology** with marked branch-points, colour-by-branch and a small legend listing each branch's endpoint cluster. Different visual grammar (branching graph, not arrow). | `conceptual` |

### Gene × cluster / gene × pseudotime (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S5 | `per_cluster_marker_heatmap` | For the top-N marker genes per cluster, what is the z-scored expression pattern across clusters? | `expression_dotplot_by_cluster` (**dot** grammar — size + colour) | Measurement: **z-scored expression matrix** (gene × cluster), no dot sizing. Visual: clean divergent heatmap with a row-cluster annotation strip on the left tagging each marker's cluster of origin. Different visual grammar (heatmap vs dotplot). | `heatmap` |
| S6 | `pseudotime_gene_expression_trajectory` | How do marker genes' expression curves evolve along pseudotime? | `umap_continuous_expression` (spatial, not pseudotime); `expression_dotplot_by_cluster` (discrete cluster, no time axis) | Measurement: **gene(pseudotime)** as a set of smoothed line curves with CI bands per gene; distinct from the discrete-cluster dotplot and the spatial UMAP-colouring recipe. | `timecourse_hierarchical_ci` |

### Velocity + ligand-receptor (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S7 | `rnavelocity_arrow_field` | On top of the UMAP, what is the RNA-velocity arrow field showing cell flow? | `trajectory_pseudotime_arrow` (**single arrow summary**, not a field); `umap_continuous_expression` (scalar colour, no arrows) | Measurement: **per-grid-cell average velocity vectors** (quiver field). Different visual grammar (quiver field over scatter) and different physical quantity (velocity vs pseudotime). | `heatmap` |
| S8 | `receptor_ligand_signaling_dotplot` | Across sender × receiver cell-type pairs, which ligand-receptor interactions are enriched? | `expression_dotplot_by_cluster` (**single-cell-type** gene dot matrix) | Measurement: **(sender × receiver) × LR-pair** dotplot — different axes than gene × cluster. Encodes strength by dot size and significance by colour, matching the standard CellChat / CellPhoneDB output. | `matrix` |

## Distinctness summary

All 8 pass the three distinctness tests:

1. **No name collision** with the 7 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different unit, axis semantics, grammar, or physical quantity).
3. **No grammar duplication** — `scatter_collapse` × 5 after this session but with distinct roles (PCA biplot, diffusion map, cluster UMAP, pseudotime arrow, condition-overlay UMAP, rare-pop spotlight); `matrix` × 4 (dotplot, composition by condition, composition by sample, LR dotplot); `heatmap` × 3 (UMAP expression, marker heatmap, velocity field).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 8 recipes use the existing `ModalityAesthetic` (`microglia_states` palette).
- [x] All 8 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 8 → modality goes from **7 → 15** recipes. Total catalog goes from **233 → 241**. Tests projected: **1216 → ~1256** (5 per recipe × 8).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
