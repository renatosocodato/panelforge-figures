# Session 03 — Gap Analysis: `actin_microtubule_morphometry` (6 → 24, +18)

**Branch:** `v1.1/session-03-actin_microtubule_morphometry`
**Status:** Awaiting user approval. No implementation until the table below is approved.

**Baseline reconciliation (Path 2):** The actual v1.0 code has 6 recipes (not the 12 the plan's idealised spec assumed). This session adds 18 new recipes on top of the real 6 → 24 total. The 9 "catch-up" recipes the plan assumed existed (`process_length_distribution_by_sex`, `sex_stratified_cvvelocity`, `skeleton_complexity_radar`, `actin_microtubule_crosstalk_quiver`, `airyscan_segmentation_mosaic`, `branching_topology_sunburst`, `shape_pca_morphospace`, `colocalization_coefficient_matrix`, `cytoskeleton_polarity_vectorfield`) are deferred to session **s03b** to hit the 30-recipe target. No renames; no breaking changes.

## Actual v1.0 coverage (6 recipes)

Slotted into the 6 sub-families you specified:

| # | Recipe | Sub-family | Question |
|---|---|---|---|
| 1 | `cortical_thickness_by_region` | A (distributions) | How does cortical actin thickness vary across anatomical regions of a cell? |
| 2 | `filament_orientation_histogram` | B (topology) | How are filament orientations distributed for actin vs microtubules? |
| 3 | `persistence_length_fit` | B (topology) | What is the persistence length $L_p$ from angular-correlation decay? |
| 4 | `skeleton_overlay_kymograph` | C (spatial / kinematic) | How does filament intensity vary along the cell edge over time? |
| 5 | `protrusion_length_velocity_joint` | C (spatial / kinematic) | Do protrusion length and velocity cluster into kinematic regimes? |
| 6 | `branch_point_density_map` | F (spatial / intensity) | Where within a cell do actin-network branch points concentrate? |

Coverage by sub-family: A=1, B=2, C=2, D=0, E=0, F=1. D (thumbnails) and E (dim reduction) are empty — session-03 populates them substantively.

## Proposed 18 new recipes

All 18 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**.

For each recipe the table notes the nearest v1.0 neighbour AND the nearest within-session neighbour — the strongest protection against overlap in a 24-recipe module.

### Sub-family A — Per-cell morphometric distributions (+4)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| A1 | `branch_point_count_raincloud` | How does the per-cell count of skeleton branch points shift across conditions, and how does it cluster by animal? | `branch_counts_by_condition: dict[str, list[float]]`, `animal_ids_by_condition` (opt), `title` | `branch_point_density_map` | `process_end_count_violin` | Measurement: **count per cell** (not spatial density, not terminal tips). Comparison: by condition with animal-level overlay. Visual: raincloud (half-violin + strip + box). | `split_violin` |
| A2 | `process_end_count_violin` | How does the per-cell number of terminal tips distribute across conditions, split by primary vs. higher-order ends? | `end_counts_by_condition`, `end_type` (primary / higher-order hue split), `title` | `cortical_thickness_by_region` | `branch_point_count_raincloud` | Measurement: **terminal-tip count**, with an internal categorical split (primary vs higher-order). Comparison: by condition. Visual: split violin with hue-coded halves. | `split_violin` |
| A3 | `cell_body_area_distribution` | How does soma area distribute per cell and per condition? | `soma_areas_by_condition: dict[str, list[float]]`, `title` | none (classical morphometric not in v1.0) | `branch_point_count_raincloud` | Measurement: **soma area** (the classical morphometric). Comparison: by condition. Visual: ridge/violin with median markers. | `split_violin` |
| A4 | `sphericity_vs_elongation_scatter` | Where do cells sit in the (sphericity, elongation) shape plane, and how do condition groups separate? | `sphericity: list[float]`, `elongation: list[float]`, `condition: list[str]` (opt), `title` | `protrusion_length_velocity_joint` | `shape_descriptor_scatter_matrix` | Measurement: **bivariate shape plane** (two specific metrics). Comparison: per-cell heterogeneity. Visual: hero single-pair scatter with marginal densities + per-condition convex hulls — distinct from the scatter matrix which shows *all* pairs at small scale. Your audit flagged this possible overlap; kept as hero because the (sphericity, elongation) plane is a named morphometric phase space with regression-worthy structure that the matrix cannot emphasise. | `scatter_collapse` |

### Sub-family B — Skeleton and network topology (+2)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| B1 | `branch_angle_distribution` | What is the distribution of angles between mother and daughter branches, by condition? | `angles_deg_by_condition: dict[str, list[float]]`, `reference_angle_deg` (e.g. 70° for Arp2/3) (opt), `title` | `filament_orientation_histogram` | `topology_ternary_simplex` | Measurement: **branch angle** (mother↔daughter), categorically distinct from filament orientation (global angle distribution). Visual: stacked KDE / ridge per condition with a reference-angle line. | `ridge_by_group` |
| B2 | `topology_ternary_simplex` | What fraction of the skeleton is linear vs branched vs looped, and how do conditions partition within that simplex? | `linear_fraction: list[float]`, `branched_fraction: list[float]`, `looped_fraction: list[float]`, `condition: list[str]`, `title` | `filament_orientation_histogram` | `branch_angle_distribution` | Measurement: **three-part compositional** (fractions summing to 1). Visual: ternary simplex scatter with per-condition convex hulls — a genuinely new visual grammar in the modality. | `scatter_collapse` |

### Sub-family C — Spatial and kinematic (+2)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| C1 | `edge_velocity_spatial_correlation` | Along a cell perimeter, over what arc-length distance does edge velocity stay correlated? | `arc_lag_um: list[float]`, `correlation: list[float]`, `correlation_ci_lo` (opt), `correlation_ci_hi` (opt), `decay_scale_um` (opt), `title` | `skeleton_overlay_kymograph` | `mitochondrial_axis_alignment` | Measurement: **spatial autocorrelation of edge velocity** along perimeter. Orthogonal to temporal kymograph. Visual: correlation-vs-lag curve with exponential-fit annotation. | `diagnostic_curve` |
| C2 | `mitochondrial_axis_alignment` | Do mitochondria orient their long axis along the cytoskeletal axis of the cell, and by how much? | `delta_angle_deg: list[float]`, `condition: list[str]` (opt), `title` | `filament_orientation_histogram` | `edge_velocity_spatial_correlation` | Measurement: **Δ-angle between organelle long-axis and filament axis**, a cross-structural alignment metric. Visual: polar density rose of Δ-angles with a reference 0° line. | `radar` |

### Sub-family D — Per-cell thumbnails and visual mosaics (+3)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| D1 | `per_cell_thumbnail_grid_with_metrics` | What do individual segmented cells look like, and how do their shape-descriptor values compare at a glance? | `cell_thumbnails: list[2D array]`, `cell_metric_labels: list[str]`, `cell_condition` (opt), `title` | none (D was empty in v1.0) | `exemplar_extremes_panel` | Measurement: **per-cell qualitative + quantitative** side-by-side. Visual: 4×4 tile grid with inline metric callout under each thumbnail, mandatory scale bar per row. The paper-default "show, don't just quantify" anchor. | `matrix` |
| D2 | `exemplar_extremes_panel` | For each condition, what do the min / median / max cells look like with respect to a target metric? | `exemplars: list[dict]` with `(condition, quantile_label, thumbnail, metric_value)`, `target_metric_label`, `title` | none | `per_cell_thumbnail_grid_with_metrics` | Measurement: **quantile exemplars** — a small, principled 3-per-condition sample tied to a named metric. Visual: rows of 3-tile strips (min, median, max) per condition with numeric annotations. | `matrix` |
| D3 | `condition_average_cell_composite` | What is the "average" cell shape for each condition, and how tight is the shape variability around that mean? | `condition_hulls: dict[str, dict[xs, ys]]`, `variability_cloud` (opt, per-condition point cloud), `title` | none | `sphericity_vs_elongation_scatter` | Measurement: **shape-hull mean + variance cloud** (not per-cell; aggregate). Visual: overlaid condition hulls with faint per-cell outline cloud behind each. Distinct from single-pair shape scatter — this operates in *cell-outline space*, not descriptor space. | `heatmap` (uses a density-backdrop cloud) |

### Sub-family E — Dimensionality reduction of shape space (+3)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| E1 | `shape_umap_by_condition` | In a non-linear 2-D embedding of shape-descriptor vectors, how do condition groups cluster or overlap? | `umap_x: list[float]`, `umap_y: list[float]`, `condition: list[str]`, `density_contours` (opt bool), `title` | none | `morphospace_trajectory_by_time` | Measurement: **non-linear embedding** (not linear PCA). Visual: scatter with per-condition density contours (KDE). The non-linear counterpart to the deferred `shape_pca_morphospace`. | `scatter_collapse` |
| E2 | `morphospace_trajectory_by_time` | How does each condition's centroid in shape space move over time? | `times: list[float]`, `trajectories_by_condition: dict[str, {x, y}]`, `embedding_method: str` ("pca" / "umap"), `title` | none | `shape_umap_by_condition` | Measurement: **trajectory through embedded space** (temporal), not static embedding. Visual: coloured centroid paths with arrowheads + start-/end-markers, overlaid on a faint backdrop of the per-cell cloud. | `scatter_collapse` |
| E3 | `shape_descriptor_scatter_matrix` | Pairwise, how do 5-6 classical shape descriptors co-vary, with marginal distributions on the diagonal? | `descriptors: dict[str, list[float]]` (5-6 named), `condition` (opt), `title` | none | `sphericity_vs_elongation_scatter` | Measurement: **all pairs at once** — a SPLOM / scatter-matrix view. Visual: square grid of scatter panels with KDEs on the diagonal and light per-condition colouring. Distinct from the single-pair hero; complementary. | `matrix` |

### Sub-family F — Colocalization, intensity, and component ratios (+4)

| # | name | answers_question | contract fields | nearest v1.0 | nearest within-session | why distinct | family |
|---|---|---|---|---|---|---|---|
| F1 | `actin_mt_ratio_spatial_map` | At each point within a cell, what is the local ratio of actin to microtubule intensity? | `ratio_image: list[list[float]]`, `pixel_size_um: float`, `cell_outline_polygon` (opt), `title` | `branch_point_density_map` | `intensity_radial_profile` | Measurement: **intensity ratio** (signed `RdBu_r` anchored at 1.0), not a density map or branch count. Visual: 2-D ratio heatmap with cell-outline overlay and mandatory scale bar. | `heatmap` |
| F2 | `intensity_radial_profile` | From the cell centroid outward, how does intensity vary radially for each channel? | `radius_um: list[float]`, `intensity_by_channel: dict[str, {mean, sem}]`, `title` | `cortical_thickness_by_region` | `actin_mt_ratio_spatial_map` | Measurement: **1-D radial profile** per channel. Visual: line-plot of mean ± SEM vs radius, one line per channel, with shaded SEM band. Different from the per-region violin (cortical thickness) and the 2-D ratio map. | `diagnostic_curve` |
| F3 | `tip_enrichment_vs_shaft_scatter` | For each cell, is a target marker enriched at tips vs. along the shaft? | `tip_intensity: list[float]`, `shaft_intensity: list[float]`, `condition: list[str]` (opt), `title` | `protrusion_length_velocity_joint` | `sphericity_vs_elongation_scatter` | Measurement: **tip vs shaft intensity per cell**. Visual: scatter with $y = x$ reference line, per-condition colour, regression fit. Tests a specific biological hypothesis (apical vs axial localisation). | `scatter_collapse` |
| F4 | `colocalization_vs_morphology_correlation` | Do colocalization metrics predict shape metrics at the per-cell level? | `coloc_metrics: dict[str, list[float]]`, `shape_metrics: dict[str, list[float]]`, `fdr_method` ("bh"), `title` | none | `shape_descriptor_scatter_matrix` | Measurement: **cross-metric correlation matrix** (M1/M2/Pearson × sphericity/elongation/branching). Visual: annotated correlation heatmap with FDR-corrected significance stars. Unique in the modality — answers the "does organization predict shape?" question directly. | `matrix` |

## Within-session overlap audit

Your original audit flagged three possible overlaps. Resolution for this session:

1. **`branch_angle_distribution` vs `branching_topology_sunburst`** — moot; the sunburst doesn't exist in actual v1.0 and is deferred to s03b. No overlap.
2. **`shape_umap_by_condition` vs `shape_pca_morphospace`** — moot; PCA recipe is deferred to s03b. `shape_umap_by_condition` lands alone this session.
3. **`sphericity_vs_elongation_scatter` vs `shape_descriptor_scatter_matrix`** — kept both; the first is a hero single-pair panel with marginal densities, the second is a SPLOM where each tile is small and low-contrast. The hero earns its place by the density + regression emphasis the matrix cannot match. Your own note allowed this justification.

## Aesthetic extensions

Four new visual grammars land this session that don't have primitives in the existing `_aesthetic.py`:

- **Ternary simplex** — will be drawn inline in `topology_ternary_simplex` using `ax.fill` for the triangle + barycentric-to-cartesian conversion.
- **Thumbnail grid convention** — inline in `per_cell_thumbnail_grid_with_metrics` and `exemplar_extremes_panel` via `fig.add_subplot` grids with mandatory scale bars per row.
- **UMAP density-contour style** — inline in `shape_umap_by_condition` using `scipy.stats.gaussian_kde` to draw per-condition contour levels.
- **Radial intensity profile** — inline in `intensity_radial_profile` using existing line-plot primitives plus `ax.fill_between` SEM bands.

None of these requires changes to the public `AESTHETIC` object — they're drawing choices within individual recipes. `_aesthetic.py` stays stable; the v1.0 recipes in this modality are unaffected.

## Contract additions

All 18 recipes use **new per-recipe Pydantic contracts** local to their own `.py` file. **No changes required to `core/contract.py`**.

## Test impact

- +54 tests (18 recipes × 3 layers: smoke + quality + cross-modality QA).
- Current: **806**. Projected: **860**.
- Aesthetic-compliance: +18 (one per new recipe).
- Style-drift ratchet must hold; implementation will reuse existing `PF_FONT_SIZES` / `PF_LINE_WIDTHS` values.

## Deferred to session s03b

Nine "catch-up" recipes the plan's idealised v1.0 spec assumed existed will land as a follow-up session **s03b** between s03 and s04:

- Sub-family A: `process_length_distribution_by_sex`, `sex_stratified_cvvelocity`
- Sub-family B: `skeleton_complexity_radar`, `branching_topology_sunburst`, `persistence_length_by_segment`
- Sub-family C: `actin_microtubule_crosstalk_quiver`, `protrusion_retraction_kymograph`, `cytoskeleton_polarity_vectorfield`
- Sub-family D: `airyscan_segmentation_mosaic`
- Sub-family E: `shape_pca_morphospace`
- Sub-family F: `colocalization_coefficient_matrix`

That's actually 11 — I expanded from 9 because `persistence_length_by_segment` and `branching_depth_sunburst_stratified` were in your 30-roster but overlap strongly with `persistence_length_fit` (actual v1.0) and absent `branching_topology_sunburst` — worth re-auditing in the s03b gap analysis rather than this one. s03b target: 24 → 35 (+11), or trim to hit 30 exactly; decision deferred.

## Final session-03 target

| Sub-family | v1.0 actual | +new s03 | total after s03 | target in 30-roster |
|---|---|---|---|---|
| A distributions | 1 | 4 | 5 | 6 |
| B topology | 2 | 2 | 4 | 6 |
| C spatial / kinematic | 2 | 2 | 4 | 5 |
| D thumbnails | 0 | 3 | 3 | 4 |
| E dim reduction | 0 | 3 | 3 | 4 |
| F intensity / coloc | 1 | 4 | 5 | 5 |
| **Total** | **6** | **18** | **24** | **30** |

---

## STOP — awaiting user approval

Please review the 18 proposed recipes above and reply with one of:

- **"approved"** — I will proceed to Commit 2 (implementation) with the exact roster above.
- **"approved with changes: …"** — list any edits (rename, swap, adjust scope) and I will proceed with the revised roster.
- **"rejected"** — I will revise the gap analysis and re-propose.

No recipe code will be written until this approval step completes.
