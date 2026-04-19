# Session s03b — Gap Analysis: `actin_microtubule_morphometry` catch-up (24 → 35, +11)

**Branch:** `v1.1/session-s03b-actin_microtubule_morphometry`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

Session 03 (Path 2) landed 18 new recipes on the real v1.0 baseline of 6, reaching 24. The plan's idealised v1.0 roster assumed 12 recipes existed that did not; 9+ of those were deferred to **s03b** to hit the 30-recipe target without renames or breaking changes in s03.

This session proposes **11 catch-up recipes**. Adding them to the current 24 would bring the modality to **35**, which is 5 over the 30-roster target.

**Source of the overshoot:** the plan's 30-roster assumed 12 v1.0 recipes; actual v1.0 had 6 recipes, of which **4 are not in the 30-roster** (`branch_point_density_map`, `cortical_thickness_by_region`, `skeleton_overlay_kymograph`, `protrusion_length_velocity_joint`). Plus the catch-up list includes `persistence_length_by_segment` which is close in spirit to the actual `persistence_length_fit`. Those 5 extras cause the 24 + 11 = 35.

**Decision required in the STOP block below:** add all 11 and land at 35, or prune 5 to hit 30 exactly.

## Current 24-recipe state

| Sub-family | Current (after s03) | Target in 30-roster | Gap |
|---|---|---|---|
| A — distributions | 5 | 6 | +1 (from catch-up: 2) → 6 or 7 |
| B — topology | 4 | 6 | +2 (from catch-up: 3) → 6 or 7 |
| C — spatial / kinematic | 4 | 5 | +1 (from catch-up: 3) → 5 or 7 |
| D — thumbnails / mosaics | 3 | 4 | +1 (from catch-up: 1) → 4 |
| E — dim reduction | 3 | 4 | +1 (from catch-up: 1) → 4 |
| F — coloc / intensity | 5 | 5 | 0 (catch-up: 1 would overshoot) → 5 or 6 |

## Proposed 11 catch-up recipes

All 11 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**.

### Sub-family A — distributions (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| A5 | `process_length_distribution_by_sex` | How does total per-cell process length distribute by sex × genotype? | `cell_body_area_distribution` (area, not length); `branch_point_count_raincloud` (count, not length) | Measurement: **total process length** per cell. Comparison: split by **sex × genotype** (distinct 2×2 stratification). Visual: split violin. | `split_violin` |
| A6 | `sex_stratified_cvvelocity` | How does the coefficient of variation of instantaneous velocity distribute by sex × genotype? | `protrusion_length_velocity_joint` (velocity-scatter, not CV distribution) | Measurement: **CV of velocity** (the Neuron-manuscript signature metric). Derived scalar, not raw velocity; CV is distinct from a scatter. Visual: split violin stratified by sex × genotype. | `split_violin` |

### Sub-family B — topology (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| B3 | `skeleton_complexity_radar` | How do 6-8 topology-complexity metrics compare per condition, viewed together? | `filament_orientation_histogram` (only angle distribution); `topology_ternary_simplex` (only 3-part fractions) | Measurement: **composite of 6-8 metrics** (n_branches, Horton-Strahler, tortuosity, path-length, …). Visual: per-condition polar radar with threshold ring. | `radar` |
| B4 | `branching_topology_sunburst` | How does the skeleton's branching hierarchy (depth 0/1/2/3) split by condition? | `branch_angle_distribution` (angle, not depth); `topology_ternary_simplex` (flat 3-part fractions, not hierarchical) | Measurement: **hierarchical branch-depth composition**. Visual: sunburst (nested-ring donut) stratified by condition. A distinct visual grammar. | `matrix` (dispatched to `assert_matrix_ok` which accepts imshow or ≥4 patches — sunburst wedges are patches, satisfying the rule) |
| B5 | `persistence_length_by_segment` | For each contour segment, what is its persistence length, shown as a distribution per condition with bootstrap CI? | `persistence_length_fit` (fits a single $L_p$ over the whole population) | Measurement: **per-segment $L_p$** (distribution), not a population fit. The v1.0 recipe gives ONE number per population; this gives a distribution across N segments with bootstrap CIs. Different aggregation level. | `coef_forest` |

**Overlap flag:** `persistence_length_by_segment` is close in spirit to the actual v1.0 `persistence_length_fit`. Both describe persistence length; one is a single fit, the other a per-segment distribution. Kept here as distinct if user wants both; dropped if user wants the 30-roster hit exactly. Candidate for **prune**.

### Sub-family C — spatial / kinematic (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| C3 | `actin_microtubule_crosstalk_quiver` | Where do actin orientations align with or cross microtubule density peaks? | `filament_orientation_histogram` (angle distribution, not spatial); `actin_mt_ratio_spatial_map` (ratio map, not directional) | Measurement: **actin direction vectors + MT density background**. Visual: quiver (arrow field) overlaid on pcolormesh of MT density. | `heatmap` |
| C4 | `protrusion_retraction_kymograph` | Along the cell edge over time, where are protrusions vs retractions (edge velocity signed)? | `skeleton_overlay_kymograph` (intensity kymograph, not edge-velocity) | Measurement: **signed edge velocity** (protrusion positive, retraction negative). Visual: RdBu_r-anchored kymograph along (arc-length, time). | `heatmap` |
| C5 | `cytoskeleton_polarity_vectorfield` | Across a segmented multi-cell field, where do cells point their cytoskeletal polarity vectors? | `mitochondrial_axis_alignment` (per-cell Δ-angle distribution, not spatial); `actin_microtubule_crosstalk_quiver` (intra-cell directions, not inter-cell polarity) | Measurement: **per-cell polarity vector** (centroid → polarity direction) plotted across the multi-cell field. Visual: 2-D field with a coloured arrow at each cell's centroid. | `heatmap` |

**Sub-family C after s03b would total 7** (5 in roster + 2 actual-v1.0 extras: `skeleton_overlay_kymograph`, `protrusion_length_velocity_joint`). If user wants 30 exact, candidates for **prune**: drop 2 of the 3 catch-ups here; keep `protrusion_retraction_kymograph` (highest scientific value for DISC1 / scaffold v4.3).

### Sub-family D — thumbnails / mosaics (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| D4 | `airyscan_segmentation_mosaic` | What do multi-cell Airyscan raw images look like side-by-side with their segmentations, with mandatory scale bars? | `per_cell_thumbnail_grid_with_metrics` (single-cell thumbnails); `exemplar_extremes_panel` (quantile exemplars) | Measurement: **raw + segmentation pair per cell**. Visual: 2-column (raw / mask) multi-row grid with per-cell scale bars. Distinct from per-cell single-thumbnail recipes. | `matrix` |

### Sub-family E — dim reduction (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| E4 | `shape_pca_morphospace` | In a linear PCA embedding of shape descriptors, how do condition groups cluster (with convex hulls rather than density contours)? | `shape_umap_by_condition` (non-linear UMAP + density contours) | Measurement: **linear PCA**, not UMAP. Visual: convex hulls over per-condition scatters, with PC1/PC2 loading annotations. Paired story with UMAP — interpretable linear axes vs non-linear clustering. | `scatter_collapse` |

### Sub-family F — coloc / intensity (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| F5 | `colocalization_coefficient_matrix` | Across conditions, what are the M1 / M2 / Pearson / Manders colocalization coefficients, in a condition-level heatmap? | `colocalization_vs_morphology_correlation` (per-cell correlation of coloc metrics with shape metrics, not condition-level) | Measurement: **condition × coefficient** heatmap (small N, condition-averaged). Distinct from the per-cell correlation matrix which plots Pearson r across metrics. Different unit of analysis. | `matrix` |

**Overlap flag:** `colocalization_coefficient_matrix` is thematically close to `colocalization_vs_morphology_correlation`. Both are heatmaps of coloc metrics; one is condition-averaged (rows = conditions, columns = metrics), the other is correlational (rows = coloc metrics, columns = shape metrics). Unit of analysis is different. Kept as distinct but candidate for **prune** if 30 target is strict.

## Two final decisions

### Count decision (required)

| Path | Count after s03b | Prune |
|---|---|---|
| **Land all 11** | **35** | none — accept 5-recipe bonus due to real-vs-planned v1.0 mismatch |
| **Prune to 30** | **30** | drop 5 of the 11: most defensible prunes are `persistence_length_by_segment` (B), `actin_microtubule_crosstalk_quiver` + `cytoskeleton_polarity_vectorfield` (C), `colocalization_coefficient_matrix` (F), plus one more from C or elsewhere |

### Implementation plan (Commit 2, pending approval)

Same pattern as s03: per-recipe Pydantic contracts, no `core/contract.py` changes, no `_aesthetic.py` changes (new visual grammars — sunburst, quiver, vector field, PCA biplot — live inline within recipes), style-drift ratchet will be preserved by sticking to existing `PF_FONT_SIZES` / `PF_LINE_WIDTHS`.

## Test impact

- **Land 11:** +33 tests (11 recipes × 3 layers). 896 → 929.
- **Prune to 6:** +18 tests. 896 → 914.

---

## STOP — awaiting user approval

> Please reply with one of:
>
> - **"approved, land all 11"** — I proceed with the full 11-recipe roster → **35 total**.
> - **"approved, prune to 30"** — I proceed with 6 recipes after dropping: `persistence_length_by_segment`, `actin_microtubule_crosstalk_quiver`, `cytoskeleton_polarity_vectorfield`, `colocalization_coefficient_matrix`, and one more of your choice → **30 total**.
> - **"approved with changes: …"** — list any specific edits, renames, or custom prune list.
> - **"rejected"** — I will revise the gap analysis and re-propose.
>
> No recipe code will be written until this approval step completes.
