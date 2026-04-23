# Session 18 — Gap Analysis: `meta_and_diagnostic` (4 → 15, +11)

**Branch:** `v1.1/session-18-meta_and_diagnostic`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`meta_and_diagnostic` is the pre-submission QC modality used across
every manuscript. v1.0 ships **missing-data pattern matrix**, **power
× effect-size curve**, **QC-metric radar**, and **sample-size decision
ladder** (4 recipes). Missing are the **PRISMA flow**, **funnel plot**,
**heterogeneity forest**, **leave-one-out sensitivity**, **replication
matrix**, **per-sample QC heatmap**, **missingness UpSet**, **outlier
detection scatter**, **retention Sankey**, **reproducibility
correlogram**, and **batch-effect PCA** reviewers expect.

## Current 4-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `missing_data_pattern_matrix` | `matrix` | co-missingness of variables |
| 2 | `power_analysis_by_effect_size` | `diagnostic_curve` | power × ES curves |
| 3 | `qc_metric_radar` | `radar` | per-sample QC pass / fail |
| 4 | `sample_size_decision_ladder` | `ladder` | n required per ES tier |

## Proposed 11 new recipes

All 11 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Meta-analysis (+4)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `prisma_flow_diagram` | How many records survive each stage of the systematic-review screening funnel? | None | PRISMA-2020 style flow with per-stage n/excluded counts and arrowed transitions between boxes. | `flow` |
| N2 | `effect_size_funnel_plot` | Is there **publication bias** in the meta-analysis (asymmetric funnel)? | None | ES vs SE scatter with triangular 95 % pseudo-confidence cone; Egger's test p-value callout. | `scatter_collapse` |
| N3 | `heterogeneity_forest` | Across studies, what is the pooled effect and how heterogeneous is it (I², τ²)? | `sample_size_decision_ladder` (planning, not meta) | **Per-study ES ± CI** forest with a diamond for the pooled estimate and an I² / τ² / Q-statistic callout. | `coef_forest` |
| N4 | `sensitivity_leave_one_out` | Does **any single study** drive the pooled effect (leave-one-out)? | `heterogeneity_forest` (all studies); no LOO recipe | LOO forest where each row shows the pooled ES computed WITHOUT that study, with original pooled line. | `coef_forest` |

### QC & missingness (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N5 | `data_quality_heatmap` | Per sample × QC metric, which cells fail a threshold? | `qc_metric_radar` (sample aggregate, polar); `missing_data_pattern_matrix` (co-missingness) | **Sample × QC-metric** heatmap with per-cell z-score / threshold flag colouring — different axis grammar (continuous-heatmap, per-metric). | `heatmap` |
| N6 | `missingness_upset` | Which **combinations** of variables are co-missing most often, and how large is each set? | `missing_data_pattern_matrix` (variables × co-missingness counts pairwise) | UpSet-style: top per-set size bar + dotted combination matrix below. Different grammar (set intersections, not pairwise). | `matrix` |
| N7 | `outlier_detection_scatter` | Given a 2-D feature plane, which points are **outliers** (Mahalanobis / IQR)? | `qc_metric_radar` (sample-level pass/fail aggregate) | 2-D feature scatter with outlier cloud / boundary contour and flagged-marker annotations; distinct grammar (spatial outlier, not aggregate flag). | `scatter_collapse` |

### Cohort & flow (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `retention_vs_attrition_sankey` | How do **participants / samples** flow through enrolment, drop-outs, and analysis stages? | None; `prisma_flow_diagram` (literature, not participants) | Sankey-like cohort flow with per-stage retention counts and attrition reasons branching off. Different content type. | `flow` |

### Replication & reproducibility (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N9 | `replication_retrospective_matrix` | Across **study × replication attempt**, which attempts succeeded and by how much? | None | Study × attempt grid with per-cell success / failure colouring + ES magnitude overlay. Different axis (study × attempt, not co-missingness). | `matrix` |
| N10 | `reproducibility_correlogram` | Pairwise, how **correlated** are replicate runs or replicate samples? | None; `missing_data_pattern_matrix` (co-missingness, not correlation) | Replicate × replicate Pearson r heatmap with lower-triangle numeric labels; different statistic (r). | `matrix` |
| N11 | `batch_effect_diagnostic_pca` | Do samples cluster by **batch** rather than condition (batch-effect diagnostic)? | `qc_metric_radar` (per-sample multi-metric) | PC1 × PC2 scatter coloured by batch with convex-hull / ellipse per batch; distinct axis grammar (embedding, not QC radar). | `scatter_collapse` |

## Distinctness summary

All 11 pass the three distinctness tests:

1. **No name collision** with the 4 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (PRISMA flow, funnel bias, pooled heterogeneity, LOO sensitivity, per-cell QC threshold flag, set-intersection missingness, 2-D outlier detection, cohort flow, study × replication success, replicate × replicate correlation, PC1 × PC2 batch effect).
3. **No grammar duplication** — `flow` × 2 (PRISMA literature vs cohort Sankey) distinct; `matrix` × 3 (UpSet vs replication vs correlogram) distinct axis pairs; `scatter_collapse` × 3 (funnel ES×SE, outlier 2-D, PCA) distinct axis semantics; `coef_forest` × 2 (heterogeneity vs LOO).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 11 recipes use the existing `ModalityAesthetic`.
- [x] All 11 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 11 → modality goes from **4 → 15** recipes. Total catalog goes from **299 → 310**. Tests projected: **1546 → ~1601** (5 per recipe × 11).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
