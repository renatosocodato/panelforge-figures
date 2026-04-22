# Session 16 — Gap Analysis: `spatial_statistics` (6 → 15, +9, Path 2)

**Branch:** `v1.1/session-16-spatial_statistics`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`spatial_statistics` backs `intravital_imaging` and `actin_microtubule_
morphometry` with point-pattern diagnostics. v1.0 currently ships **6
real recipes** (coordinator listed 4 — plan-vs-reality mismatch; see
below): density heatmap, Moran's I by lag, nearest-neighbour distance,
pair correlation g(r), Ripley's L with CSR envelope, and Voronoi
territory map. Missing are the **Clark-Evans index**, **F function
empty-space**, **spatial covariogram**, **LISA cluster map**,
**bivariate PCF**, **Voronoi area distribution**, **co-occurrence
significance matrix**, **quadrat χ² test**, and **spatial permutation
null** reviewers expect.

> **Plan-vs-reality reconciliation (Path 2).** The coordinator
> (`docs/hydration_coordinator.md` line 16) records
> `spatial_statistics: 4 → 15`. Real v1.0 baseline is 6 (two
> seed-list names — `l_function_with_envelope` and
> `point_pattern_density_map` — already ship as `ripley_l_function`
> and `kernel_density_heatmap`). To land the 15-target in one session
> I drop those two duplicate seeds and propose **+9 new** to hit
> 6 + 9 = 15, matching s07's Path-2 pattern.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `kernel_density_heatmap` | `heatmap` | point-density KDE |
| 2 | `moran_i_by_lag` | `diagnostic_curve` | Moran's I vs neighbourhood radius |
| 3 | `nearest_neighbor_distance_distribution` | `diagnostic_curve` | NN distance histogram + CDF (i.e. G function) |
| 4 | `pair_correlation_function` | `diagnostic_curve` | g(r) |
| 5 | `ripley_l_function` | `diagnostic_curve` | L(r) − r with CSR envelope |
| 6 | `voronoi_territory_map` | `heatmap` | Voronoi tessellation |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Aggregation & scale diagnostics (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `clark_evans_aggregation_bar` | Across conditions, is the point pattern **clustered** (CE < 1), **random** (CE ≈ 1), or **dispersed** (CE > 1)? | `ripley_l_function` (scale-dependent); no summary index | Per-condition Clark-Evans index ± 95 % CI with CSR reference line at 1.0. Distinct grammar: single summary statistic per condition (ladder), not a scale-dependent curve. | `ladder` |
| N2 | `f_function_empty_space` | Is there **empty space** in the pattern — regions far from any observed point — more than CSR predicts? | `nearest_neighbor_distance_distribution` (G function, point-to-point); `ripley_l_function` (K-based, pairwise) | **F(r) vs CSR F(r) = 1 − exp(−λπr²)** with envelope. F probes empty space from **random test points**; G probes point-to-point NN. Different question. | `diagnostic_curve` |
| N3 | `spatial_covariogram` | At what spatial lag does the covariance of a continuous field decay to zero (correlation length)? | `moran_i_by_lag` (autocorrelation coefficient, categorical / binary) | C(h) covariogram for **continuous** marks with nugget/sill/range fit; different statistic (covariance, not Moran's I) and different mark type. | `diagnostic_curve` |

### Local & bivariate autocorrelation (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N4 | `lisa_cluster_map` | Where on the field are **local** hot-spot (HH), cold-spot (LL), and outlier (HL/LH) tiles? | `moran_i_by_lag` (global, scale-aware); `kernel_density_heatmap` (density, no significance) | **Local Indicators of Spatial Association** — per-point HH/HL/LH/LL category with significance shading. Different grammar (per-point classification). | `heatmap` |
| N5 | `bivariate_pair_correlation` | At what radii are two cell types **co-clustered** (g_12 > 1) vs **segregated** (g_12 < 1)? | `pair_correlation_function` (univariate g(r)) | **g_12(r)** with CSR envelope — pair correlation **between** two point types. Distinct axis semantics (type × type × r). | `diagnostic_curve` |

### Territory & composition (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N6 | `voronoi_area_distribution` | How are **per-cell territory areas** distributed, and does the distribution shift across conditions? | `voronoi_territory_map` (spatial map, no distribution) | Ridge stack of Voronoi cell-area distributions per condition; aggregate statistic (distribution) vs per-cell spatial map. | `ridge_by_group` |
| N7 | `co_occurrence_significance_matrix` | Which cell-type pairs significantly **co-occur** vs **avoid** each other across tiles? | `bivariate_pair_correlation` (continuous r-dependent); no matrix-level significance summary | **type × type** z-score matrix with star-significance overlay — pairwise summary, not r-dependent curve. | `matrix` |

### Statistical tests (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `quadrat_count_chisq` | Is the overall point pattern **non-uniform** at the chosen quadrat scale? | `kernel_density_heatmap` (continuous density, no test statistic) | Quadrat grid with per-cell count + χ² residual colouring + overall χ² p-value pill. Distinct grammar (discrete cells, not KDE). | `matrix` |
| N9 | `spatial_permutation_null_distribution` | Given an observed test statistic, how significant is it against random label-permutation nulls? | `ripley_l_function` (envelope is MC simulation, **not** label-permutation); no null-distribution histogram exists | Histogram of permutation null with observed statistic marked and empirical p shown. Different grammar (null distribution, not curve-with-envelope). | `ridge_by_group` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (summary aggregation index, empty-space F, continuous covariogram, LISA HH/LL tiles, bivariate PCF, area distribution, type × type co-occurrence, quadrat χ², permutation-null histogram).
3. **No grammar duplication** — `ladder` × 1, `diagnostic_curve` × 3 (F, covariogram, bivariate PCF) on **distinct question-axis pairs**, `heatmap` × 1 (LISA cluster map vs density KDE — categorical classification vs continuous density), `ridge_by_group` × 2 (Voronoi areas, null distribution) with different axis semantics, `matrix` × 2 (co-occurrence, quadrat) with different axis pairs.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic`.
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 9 → modality goes from **6 → 15** recipes. Total catalog goes from **281 → 290**. Tests projected: **1456 → ~1501** (5 per recipe × 9).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
