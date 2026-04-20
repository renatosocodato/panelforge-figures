# Session 09 — Gap Analysis: `omics_differential` (10 → 16, +6)

**Branch:** `v1.1/session-09-omics_differential`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`omics_differential` is the most heavily used modality in the
Targetome + general omics pipelines. v1.0 ships volcano (labelled + MA
+ multi-contrast grid), GSEA running-enrichment, ORA dotplot, UpSet,
differential rank ladder, pathway flux bubble, effect-size-vs-
significance scatter, annotated cluster heatmap (10 recipes). Missing
are the **proteome-specific pathway-labelled volcano**, **replicate-
concordance scatter**, **Euler overlap** (area-proportional
complement to UpSet), **cross-study rank-product meta-analysis**,
**shrinkage-vs-raw effect-size diagnostic**, and **pathway-module
activity heatmap** (module × sample, not gene × sample).

## Current 10-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `annotated_cluster_heatmap` | `heatmap` | **gene × sample** clustered expression |
| 2 | `differential_rank_ladder` | `ladder` | top-N up/down ranked bars |
| 3 | `effect_size_vs_significance` | `scatter_collapse` | effect vs p-value |
| 4 | `gsea_running_enrichment` | `diagnostic_curve` | GSEA running-enrichment |
| 5 | `ma_plot_with_lowess` | `volcano` | MA plot with lowess bias curve |
| 6 | `multi_contrast_volcano_grid` | `volcano` | grid of volcanos across contrasts |
| 7 | `ora_dotplot_by_ontology` | `matrix` | ORA dots sized by gene ratio |
| 8 | `pathway_flux_bubble` | `matrix` | pathway flux bubble matrix |
| 9 | `upset_set_comparisons` | `matrix` | UpSet intersection bars |
| 10 | `volcano_labeled_repelled` | `volcano` | generic volcano w/ repelled labels |

## Proposed 6 new recipes

All 6 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Volcano / effect-size grammar (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| O1 | `proteome_volcano_labeled_pathways` | On a proteome-scale volcano, which pathways (not individual genes) are most enriched among the significant hits? | `volcano_labeled_repelled` (labels **individual genes**); `multi_contrast_volcano_grid` (grid of per-contrast volcanos, **no pathway overlay**) | Measurement: **pathway-group color coding** with one label per pathway group at the group centroid + top-pathway legend. Different annotation unit (pathway, not gene). | `volcano` |
| O2 | `effect_size_replicate_concordance` | Across biological replicates of the same contrast, how well do effect-size estimates agree per gene? | `effect_size_vs_significance` (effect **vs p-val**, not rep-vs-rep) | Measurement: **rep1 vs rep2 effect size** scatter per gene with identity line, Pearson r, and the 95 % agreement band. Different axes (rep × rep, not effect × p). | `scatter_collapse` |
| O3 | `shrinkage_estimate_scatter` | How does an empirical-Bayes-shrunken effect estimate compare to the raw MLE estimate, and where does shrinkage matter most? | `effect_size_vs_significance` (raw effect vs p, no shrinkage); `volcano_labeled_repelled` (p-val volcano, not shrinkage) | Measurement: **raw vs shrunken log2FC** per gene with identity line, shrinkage-ratio colour coding, and a "|Δ| > threshold" callout. Different diagnostic grammar. | `scatter_collapse` |

### Overlap / meta-analysis (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| O4 | `contrast_overlap_euler` | Across two or three contrasts, how do the significant-hit sets overlap (area-proportional Euler diagram)? | `upset_set_comparisons` (UpSet **bar** view of intersections, not area-proportional) | Measurement: **area-proportional Euler circles** with counts per region; complements the UpSet view with the spatial-set grammar reviewers often ask for. | `conceptual` |
| O5 | `rank_product_meta_analysis` | Across multiple studies, which genes are consistently high-ranking by the rank-product meta-analysis statistic? | `differential_rank_ladder` (**single-study** top-N); `multi_contrast_volcano_grid` (per-contrast volcanos, not a combined statistic) | Measurement: **combined rank-product** (or rank-sum) score across N studies per gene, with permutation FDR markers for significance. Different statistic (meta-analysis combined, not per-study ranked). | `ladder` |

### Pathway-module grammar (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| O6 | `pathway_module_activity_heatmap` | Across samples, how does each pathway module's summarised activity score compare? | `annotated_cluster_heatmap` (**gene × sample** expression); `pathway_flux_bubble` (pathway × condition, but bubble grammar + flux direction) | Measurement: **module × sample** activity-score matrix (gene-set summary per sample), not per-gene expression and not flux. Different unit (module-level summary) and different grammar (clean heatmap, not bubble). | `heatmap` |

## Distinctness summary

All 6 pass the three distinctness tests:

1. **No name collision** with the 10 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different annotation unit, rep-vs-rep axes, shrinkage diagnostic, area-proportional vs UpSet, meta-analysis vs single-study, module- vs gene-level).
3. **No grammar duplication** — `volcano` appears 4× after this session but each is a distinct annotation grammar (generic labelled / MA / multi-contrast grid / pathway-grouped); `scatter_collapse` × 3 with distinct axes; `heatmap` × 2 with distinct unit of analysis.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 6 recipes use the existing `ModalityAesthetic` (`journal_neutral` palette, RdBu_r ratio cmap).
- [x] All 6 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 6 → modality goes from **10 → 16** recipes. Total catalog goes from **218 → 224**. Tests projected: **1141 → ~1171** (5 per recipe × 6).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
