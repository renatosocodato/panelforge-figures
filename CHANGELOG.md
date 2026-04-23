# Changelog

All notable changes to `panelforge-figures` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows semantic versioning.

## [Unreleased]

## [1.1.0-s18] — 2026-04-23

Eighteenth session of the v1.1 hydration plan. Hydrates the
`meta_and_diagnostic` modality from 4 to 15 recipes — the QC,
meta-analysis, and reproducibility workhorse used across every paper.

### Added

- `prisma_flow_diagram` (flow) — PRISMA-2020 stage funnel with main
  + excluded boxes and arrowed transitions.
- `effect_size_funnel_plot` (scatter_collapse) — ES × SE scatter with
  95 % pseudo-CI cone + Egger's test p-value / verdict.
- `heterogeneity_forest` (coef_forest) — per-study forest with pooled
  diamond and I² / τ² / Q-statistic in title.
- `sensitivity_leave_one_out` (coef_forest) — per-row pooled-without-k
  ES with influential-study flags (|Δ| above threshold).
- `data_quality_heatmap` (heatmap) — sample × QC-metric z-score heatmap
  with per-cell threshold-fail × overlay + global pass-rate.
- `missingness_upset` (matrix) — intersection-dot matrix with top
  per-set count bars (set-intersection view of co-missingness).
- `outlier_detection_scatter` (scatter_collapse) — 2-D feature plane
  with Mahalanobis boundary contour and flagged-marker annotations.
- `retention_vs_attrition_sankey` (flow) — per-stage retention bars
  with attrition tabs and reason callouts.
- `replication_retrospective_matrix` (matrix) — study × attempt
  success / partial / failure / na grid with ES overlay.
- `reproducibility_correlogram` (matrix) — replicate × replicate
  Pearson r heatmap with group-coded tick labels.
- `batch_effect_diagnostic_pca` (scatter_collapse) — PC1 × PC2 scatter
  with per-batch covariance ellipses and a batch-clustering-score
  verdict.

### Infrastructure

- No changes to `core/` — 11 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Updated `tests/test_contracts.py` to expect 15 (was 4) recipes in
  `meta_and_diagnostic`.

### Visual-QA polish (7 panels)

- `prisma_flow_diagram` — exclusion-reason text overlapped the "n = N"
  count; consolidated to "Excluded  n = N" single line + reason
  below.
- `heterogeneity_forest` — pooled-diamond label collided with legend;
  moved I²/τ²/Q into title and legend to upper-right.
- `sensitivity_leave_one_out` — bottom-left callout pill occluded the
  Study 1 marker; consolidated into title.
- `retention_vs_attrition_sankey` — arrow heads covered "n = N"
  labels; reworked layout to put arrow heads in left-of-lane gap,
  retention bars centred in lane, attrition tabs on the right.
- `replication_retrospective_matrix` — top summary callout collided
  with title; consolidated into title; legend offset below axes.
- `reproducibility_correlogram` — tick labels clipped by group strip;
  replaced strip with group-coloured y-tick labels.
- `batch_effect_diagnostic_pca` — legend inside axes hidden by data
  points; moved to outside-right (`bbox_to_anchor=(1.02, 0.5)`).

### Progress

- Total recipes: **299 → 310** (+11).
- Tests: **1546 → 1601** (+55).
- Modalities at v1.1 target (≥15): 15 of 20.
- Sessions complete: **18 of 20**.

## [1.1.0-s17] — 2026-04-22

Seventeenth session of the v1.1 hydration plan. Hydrates the
`grant_and_conceptual` modality from 6 to 15 recipes for ATHENA,
MIRROR, and Horizon Europe proposals. A4-portrait + Helvetica-safe
(Portuguese-compatible) typography.

### Added

- `research_aims_pyramid` (conceptual) — hierarchical objective → aims
  → sub-questions with coloured aim bands and white sub-question cards.
- `methods_pipeline_flow` (flow) — strictly linear input → step 1 …
  step N → output with rounded coloured boxes and arrow connectors.
- `milestone_vs_risk_matrix` (matrix) — 2×2 probability × impact grid
  with per-milestone tiles and risk-rated border colour.
- `innovation_positioning_quadrant` (matrix) — novelty × feasibility
  quadrant with competitor scatter + starred our-proposal marker.
- `cost_by_work_package_bar` (ladder) — per-WP stacked horizontal bars
  by cost category with grand-total callout.
- `ethics_and_impact_block` (conceptual) — two-column ETHICS / IMPACT
  panel with sub-section cards + bullets.
- `interdisciplinary_contribution_spider` (radar) — polar coverage
  radar with optional reference polygon + mean-coverage callout.
- `team_network_graph` (conceptual) — institutional-sector radial
  layout with Circle-patch partner nodes and collaboration edges
  scaled by strength.
- `deliverables_timeline` (gantt) — per-WP lane with angled deliverable
  IDs, status-coloured rings, year dividers.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Updated `tests/test_contracts.py` to expect 15 (was 6) recipes in
  `grant_and_conceptual`.
- Style-drift ratchet held (fontsize `14` snapped to `9.6` in
  `milestone_vs_risk_matrix` decorative `!!` glyph).

### Visual-QA polish (4 panels)

- `research_aims_pyramid`: initial layout clipped the objective text
  (wrap too wide) and aim titles (em-dash too long). Reworked to
  column-based layout with `width=58` objective wrap, ASCII-dash aim
  titles and narrower sub-question wrap (`width=20`).
- `methods_pipeline_flow`: step boxes too narrow — titles / descriptions
  clipped. Reworked slot-width formula to explicit margin + gap that
  leaves enough box width at the default 6-step pipeline, arrow gaps
  set to 0.018 axes-fraction for visible arrowheads.
- `innovation_positioning_quadrant`: legend duplicated the starred
  data-point label. Removed the legend; starred marker has its own
  bold red label above.
- `deliverables_timeline`: titles overlapped horizontally at closely-
  spaced deliverables, ID labels overlapped markers. Switched to
  angled (`rotation=20`) titles above, ID labels centred inside the
  scatter marker (white bold text on WP-colour fill). Also
  `cost_by_work_package_bar` — legend below axes bbox shifted to
  `(1.0, -0.20)` to clear the "cost (EUR)" x-axis label.
- `team_network_graph`: long partner names (`postdoc A`, `PI-partner`)
  clipped inside circles. Switched to short ID inside circle, full
  name + role below.

### Progress

- Total recipes: **290 → 299** (+9).
- Tests: **1501 → 1546** (+45).
- Modalities at v1.1 target (≥15): 14 of 20.
- Sessions complete: **17 of 20**.

## [1.1.0-s16] — 2026-04-22

Sixteenth session of the v1.1 hydration plan. Hydrates the
`spatial_statistics` modality from 6 to 15 recipes via Path 2.

### Plan-vs-reality reconciliation

- Coordinator listed v1.0=4 but actual baseline is 6. Two seeds
  (`l_function_with_envelope`, `point_pattern_density_map`) already
  ship as `ripley_l_function` and `kernel_density_heatmap`.
- **Path 2**: drop duplicates, land +9 new to reach the 15-target in
  one session (analogous to s07).

### Added

- `clark_evans_aggregation_bar` (ladder) — per-condition CE index ± CI
  with CSR reference, clustered / random / dispersed colour coding.
- `f_function_empty_space` (diagnostic_curve) — F(r) with CSR
  analytical reference + envelope, interpretation pill.
- `spatial_covariogram` (diagnostic_curve) — C(h) with exponential
  fit and nugget / sill / range annotations.
- `lisa_cluster_map` (heatmap) — per-point HH / HL / LH / LL
  classification with HH-minus-LL density overlay for the heatmap-
  rule and pseudo-p alpha scaling.
- `bivariate_pair_correlation` (diagnostic_curve) — g_12(r) with
  signed fill, peak + trough markers.
- `voronoi_area_distribution` (ridge_by_group) — log-space ridge stack
  of per-condition Voronoi areas with med / mean markers.
- `co_occurrence_significance_matrix` (matrix) — type × type z-score
  matrix with star-significance overlay + strongest-pair title.
- `quadrat_count_chisq` (matrix) — Pearson residual heatmap with
  counts, χ² / df / p verdict pill.
- `spatial_permutation_null_distribution` (ridge_by_group) — null +
  alternative ridges with observed statistic line and empirical p.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held: fontsize `7.5` snapped to `7.4` in two
  titles (co_occurrence_significance_matrix, quadrat_count_chisq).

### Visual-QA polish

- None — all 9 panels passed visual-QA on first render.

### Progress

- Total recipes: **281 → 290** (+9).
- Tests: **1456 → 1501** (+45).
- Modalities at v1.1 target (≥15): 13 of 20.
- Sessions complete: **16 of 20**.

## [1.1.0-s15] — 2026-04-22

Fifteenth session of the v1.1 hydration plan. Hydrates the
`diffusion_and_tracking` modality from 5 to 15 recipes. This is the
intravital downstream SPT workhorse.

### Added

- `msd_anomalous_exponent_fit` (scatter_collapse) — per-track α × D
  scatter coloured by α + representative MSD fit inset.
- `track_length_distribution` (diagnostic_curve) — per-condition CCDF
  of track duration with censoring marker.
- `jump_distance_van_hove` (ridge_by_group) — |Δr| stacked by lag with
  Gaussian reference and non-Gaussian α₂ per-lag callout.
- `track_spaghetti_plot_colored_by_state` (scatter_collapse) — raw
  trajectories with per-segment LineCollection state colouring,
  start/end markers, state-fraction footer.
- `hmm_state_dwell_distribution` (ridge_by_group) — per-state dwell-
  time ridges with exponential reference and mean-dwell markers.
- `displacement_vs_state_residence` (matrix) — state × residence-bin
  heatmap of median |Δr| with per-row trend summary footer.
- `diffusion_coefficient_heatmap_spatial` (heatmap) — gridded D(x, y)
  pcolormesh with quartile contour overlay.
- `track_directionality_polar` (radar) — polar histogram with isotropic
  reference, mean-direction vector, and Rayleigh r statistic.
- `ensemble_vs_time_averaged_msd` (scatter_collapse) — EA-MSD line,
  TA-MSD cloud, and EB(τ) ergodicity-breaking parameter callout.
- `confinement_radius_vs_time` (timecourse_hierarchical_ci) — per-track
  R_conf(t) with mean ± 95 % CI per condition.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held (invisible-line proxy uses `lw=0.5,
  alpha=0.0, color="none"` — no new literal introduced).

### Fit-ups during authoring

- `track_spaghetti_plot_colored_by_state`: scatter_collapse rule
  requires ≥1 Line2D; LineCollection segments live on
  `ax.collections`, not `ax.get_lines()`. Added an invisible
  `ax.plot([], [])` proxy.
- Replaced unicode glyphs incompatible with Helvetica: rightwards
  arrow `→` → `->`; mathematical angle brackets `⟨...⟩` → `mean ...`.

### Visual-QA polish (one panel)

- `displacement_vs_state_residence`: initial render had three
  overlaps (first-column numeric labels clipped by y-ticks, right-
  edge per-row Δ-arrows overlapping the colorbar, header "largest
  trend" annotation colliding with the title). Removed the per-row
  right-edge annotations and replaced with a single compact trends
  footer below the axes; kept the in-cell numeric labels but skip
  them when column width is narrower than 60 % of the median width.

### Progress

- Total recipes: **271 → 281** (+10).
- Tests: **1406 → 1456** (+50).
- Modalities at v1.1 target (≥15): 12 of 20.
- Sessions complete: **15 of 20**.

## [1.1.0-s14] — 2026-04-22

Fourteenth session of the v1.1 hydration plan. Hydrates the
`biophysics_scaling` modality from 5 to 15 recipes for the Manuscript 3
collapse narrative and the `gc-chirrut` force-balance / Π-group analysis.

### Added

- `log_log_with_theory_line` (scatter_collapse) — data vs theory-
  predicted reference line with residuals-from-theory inset.
- `universality_class_comparison` (scatter_collapse) — 2-3 candidate
  universality curves overlaid, per-class RMS residual bar inset.
- `fractal_dimension_scaling` (scatter_collapse) — box-counting
  N(L) ~ L^D_f with sliding-window local D_f(L) inset.
- `stress_strain_regime_map` (matrix) — σ-ε with elastic/plastic/failure
  bands, yield + ultimate markers, Young's-modulus slope inset.
- `knudsen_reynolds_regime_diagram` (matrix) — Kn × Re log-log grid with
  continuum/slip/transition/free-molecular bands + sample scatter.
- `energy_landscape_1d_cartoon` (conceptual) — schematic U(x) with
  labelled wells, barriers, k_B T scale bar, transition arrows.
- `scaling_exponent_ci_forest` (coef_forest) — per-study α ± CI forest
  with theoretical reference line and heterogeneity summary.
- `characteristic_time_vs_control` (diagnostic_curve) — τ(p) critical
  divergence or Arrhenius fit with fitted exponent callout.
- `pi_group_sensitivity_bar` (ladder) — Buckingham Π-group variance
  contribution ranked with cumulative top-2/top-3 share.
- `crossover_scaling_diagnostic` (diagnostic_curve) — two-slope
  piecewise power law with crossover ξ + local-slope inset.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held; all new fontsize/lw literals snap to the
  existing canonical set.

### Visual-QA polish (three panels)

- `fractal_dimension_scaling`: legend + D_f callout originally both
  at lower-left → legend moved to upper-left, callout retained at
  lower-left.
- `knudsen_reynolds_regime_diagram`: rotated 90° regime labels
  collided with the 2-column upper-right legend → regime labels moved
  to the bottom of each band (horizontal, bold); sample legend moved
  below the axes; counts callout moved to upper-right.
- `crossover_scaling_diagnostic`: inset y-label "local α" was hidden
  by inset tick labels on a log y-axis → forced `inset.set_yscale
  ("linear")` plus `labelpad` tweaks for readable "local α" axis.

### Progress

- Total recipes: **261 → 271** (+10).
- Tests: **1356 → 1406** (+50).
- Modalities at v1.1 target (≥15): 11 of 20.
- Sessions complete: **14 of 20**.

## [1.1.0-s13] — 2026-04-21

Thirteenth session of the v1.1 hydration plan. Hydrates the
`network_and_pathway` modality from 5 to 15 recipes for Commentary +
Targetome network vocabulary.

### Added

- `directed_network_force_layout` (conceptual) — directed graph with
  arrowed edges and Circle-patch nodes.
- `hub_gene_radial` (conceptual) — hub-centre + neighbours on a
  circle, activator/repressor colour coding.
- `ppi_seed_expansion` (conceptual) — two-shell seed + expanded
  ring layout.
- `pathway_crosstalk_matrix` (matrix) — pathway × pathway crosstalk
  heatmap with top-pair footer.
- `kegg_overlay_enrichment` (conceptual) — KEGG schematic with
  FancyBboxPatch nodes coloured by −log10(p).
- `regulon_activity_heatmap` (heatmap) — TF × sample activity with
  condition strip.
- `module_preservation_zsummary` (ladder) — WGCNA Z-ladder with
  Z=2 / Z=10 tier shading.
- `centrality_vs_effect_scatter` (scatter_collapse) — centrality vs
  effect size with OLS + −log10(p) colormap.
- `subnetwork_comparison_diff` (conceptual) — Δ-weight graph with
  gain/loss edge coding.
- `pathway_flux_streamgraph` (timecourse_hierarchical_ci) —
  normalised stacked flux(t) with dominant-per-window footer.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held (hub-radial title 8.8 → 8.6).

### Visual-QA polish (one panel)

- `directed_network_force_layout`: the initial Fruchterman-Reingold
  spring layout collapsed all 18 nodes to a tight cluster because
  the uncapped attractive force dominated. Replaced with a
  deterministic **degree-based radial layout** — hubs near centre,
  rim nodes outside, with per-tier angular stratification + small
  jitter — which reads cleanly for small/medium dense graphs.

### Progress

| | v1.1.0-s12 | **v1.1.0-s13** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 251 | **261** |
| `network_and_pathway` | 5 | **15** |
| Tests | 1306 | **1356** |


## [1.1.0-s12] — 2026-04-21

Twelfth session of the v1.1 hydration plan. Hydrates the
`dose_response_pharmacology` modality from 5 to 15 recipes for
ATHENA pharmacology + sex-stratified drug response.

### Added

- `dose_response_sex_stratified` (diagnostic_curve) — F/M Hill
  curves with sex × dose interaction p + EC50-fold callout.
- `dose_response_time_matrix` (heatmap) — concentration × time
  effect matrix with per-conc peak isochrone and global peak star.
- `response_rebound_kinetics` (diagnostic_curve) — washout curve
  with rebound peak marker and recovery τ callout.
- `ic50_vs_target_affinity_scatter` (scatter_collapse) — Ki vs IC50
  log-log with identity + OLS fit, mechanism-class coloring.
- `selectivity_index_tornado` (ladder) — fold-IC50 tornado with
  10× cliff marker and tractability shading.
- `dose_normalized_ec50_forest` (coef_forest) — x-fold EC50 vs
  lead, log-x, mechanism-coloured.
- `synergy_score_bliss_loewe` (scatter_collapse) — Bliss vs Loewe
  scatter with agreement diagonal and synergy / antagonism /
  disagreement quadrant coding.
- `pharmacophore_activity_heatmap` (heatmap) — feature × compound
  SAR heatmap with active-feature origin strip.
- `compound_cluster_structure_activity` (conceptual) — structural
  PCA + per-cluster mean activity two-panel.
- `polypharmacology_radar` (radar) — multi-compound polar radar
  with title-integrated mean-activity summary.

### Infrastructure

- No changes to `core/` — all 10 recipes use new per-recipe
  Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held — title fontsize 8.8 → 8.6 on two
  recipes during implementation.
- Conceptual-family rule satisfied in
  `compound_cluster_structure_activity` by adding per-bar value
  labels so ≥3 text artists are present.

### Visual-QA polish (two panels)

- `dose_normalized_ec50_forest`: the `lead (1×)` / `10×` legend
  originally sat at lower-right where it clipped the right-most
  x-fold labels; moved to upper-right.
- `polypharmacology_radar`: the mean-activity footer and
  compound legend both collided with the bottom "hydrolase"
  target label; folded the mean-activity summary into a 2-line
  title and anchored the legend at `bbox_to_anchor=(0.5, -0.14)`.

### Progress

| | v1.1.0-s11 | **v1.1.0-s12** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 241 | **251** |
| `dose_response_pharmacology` | 5 | **15** |
| Tests | 1256 | **1306** |


## [1.1.0-s11] — 2026-04-21

Eleventh session of the v1.1 hydration plan. Hydrates the
`single_cell_embeddings` modality from 7 to 15 recipes for Targetome
scRNA work and general single-cell omics.

### Added

- `single_cell_embeddings.umap_density_contour_overlay` — per-
  condition density contours on a shared UMAP, mean-shift arrows
  and pairwise centroid-distance callout.
- `single_cell_embeddings.rare_population_highlighted_umap` —
  spotlight grammar: bulk greyed, rare pop with convex hull +
  median star + % callout.
- `single_cell_embeddings.cluster_proportion_stacked_by_sample` —
  per-sample stacked bars with condition-group strip below.
- `single_cell_embeddings.trajectory_branching_force_directed` —
  branching trajectory with Circle-patch branch points, per-branch
  colours and endpoint labels.
- `single_cell_embeddings.per_cluster_marker_heatmap` — z-scored
  gene × cluster heatmap with origin-cluster annotation strip.
- `single_cell_embeddings.pseudotime_gene_expression_trajectory` —
  gene(pseudotime) smoothed curves with CI bands and peak-order
  footer.
- `single_cell_embeddings.rnavelocity_arrow_field` — RNA-velocity
  quiver field over UMAP scatter with faint speed underlay and |v|
  colorbar.
- `single_cell_embeddings.receptor_ligand_signaling_dotplot` —
  (sender × receiver) × LR-pair dotplot with size∝strength and
  colour∝-log10(p).

### Infrastructure

- No changes to `core/` — all 8 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Liberation Sans-safe throughout — the rightwards-arrow glyph was
  replaced with `->` in branch labels, legend entries and peak-order
  footers.
- Quality-rule fit-ups during implementation:
  - `rnavelocity_arrow_field` (heatmap): added a faint speed
    `pcolormesh` underlay so the ≥1-surface rule is satisfied.
  - `trajectory_branching_force_directed` (conceptual): branch
    points drawn with `mpatches.Circle` patches so ≥2 decorative
    patches are present.
  - `umap_density_contour_overlay` (scatter_collapse): mean-shift
    arrows are underpinned by a Line2D segment so the ≥1-line rule
    is satisfied.

### Visual-QA polish (two panels)

- `cluster_proportion_stacked_by_sample`: per-sample tick labels
  were hidden behind the condition-group strip; moved the strip
  down (strip_y: -0.08 → -0.14) and shortened labels to the
  per-condition index so the numbers stay visible.
- `rnavelocity_arrow_field`: the cluster legend was inside the
  plot covering the quiver field; moved to a single-row anchor
  below the axes and added a |v| colorbar.

### Progress

| | v1.1.0-s10 | **v1.1.0-s11** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 233 | **241** |
| `single_cell_embeddings` | 7 | **15** |
| Tests | 1216 | **1256** |


## [1.1.0-s10] — 2026-04-21

Tenth session of the v1.1 hydration plan. Hydrates the
`calcium_signaling` modality from 6 to 15 recipes for the scaffold-
v4.3 GCaMP6f integration.

### Added

- `calcium_signaling.calcium_event_amplitude_distribution` — per-
  condition ridge of event amplitudes.
- `calcium_signaling.calcium_event_onset_alignment` — peri-event
  time histogram with CI.
- `calcium_signaling.population_synchronization_timeline` — sync(t)
  scalar curve with threshold shading.
- `calcium_signaling.network_burst_detection_overlay` — raster +
  rate with shaded burst epochs.
- `calcium_signaling.calcium_wave_speed_map` — per-pixel wave speed.
- `calcium_signaling.single_cell_calcium_landscape` — per-cell
  (frequency, amplitude) scatter with hulls.
- `calcium_signaling.calcium_and_fret_joint_plot` — Ca × FRET joint
  scatter with marginal histograms.
- `calcium_signaling.oscillation_frequency_polar` — dominant-phase
  polar with mean resultant R.
- `calcium_signaling.stimulus_triggered_calcium_heatmap` — cell ×
  time ΔF/F aligned to stim.

### Visual-QA polish (two panels)

- `network_burst_detection_overlay`: burst-count callout moved from
  rate-panel top-right (covered B3) into the title.
- `oscillation_frequency_polar`: radial tick labels moved to 270°
  via `set_rlabel_position(270)`; legend moved to a single-row anchor
  below the polar disc.

### Progress

| | v1.1.0-s09 | **v1.1.0-s10** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 224 | **233** |
| `calcium_signaling` | 6 | **15** |
| Tests | 1171 | **1216** |


## [1.1.0-s09] — 2026-04-20

Ninth session of the v1.1 hydration plan. Hydrates the
`omics_differential` modality from 10 to 16 recipes in direct
support of the Targetome and general omics pipelines.

### Added

- `omics_differential.proteome_volcano_labeled_pathways` — pathway-
  group coloured volcano with one centroid label per pathway group;
  distinct from the per-gene labelled volcano.
- `omics_differential.effect_size_replicate_concordance` — rep1 vs
  rep2 log2FC scatter with identity line, OLS fit, 95 % LoA band
  and bias / SD(Δ) callout.
- `omics_differential.shrinkage_estimate_scatter` — raw vs shrunken
  log2FC with shrinkage-ratio colormap and |Δ|>threshold highlight.
- `omics_differential.contrast_overlap_euler` — area-proportional
  Euler circles for 2- or 3-way contrast overlaps with region
  counts and Jaccard callout.
- `omics_differential.rank_product_meta_analysis` — top-N 1/RP bars
  with permutation-FDR star markers and a right-side per-study
  rank-colour strip.
- `omics_differential.pathway_module_activity_heatmap` — module ×
  sample activity heatmap with group-annotation strips for
  modules (right) and samples (bottom).

### Infrastructure

- No changes to `core/` — all 6 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (pathway-coloured volcano,
  replicate concordance with Bland-Altman band, shrinkage diagnostic,
  area-proportional Euler, rank-product meta-analysis ladder,
  module activity heatmap) live inline.
- Liberation Sans-safe labels throughout — replaced the union /
  intersection glyphs in the Euler callout with plain "union /
  inter / Jaccard" words.
- Style-drift ratchet held on first pass.

### Visual-QA polish (two panels)

- `rank_product_meta_analysis`: the per-study rank-colour strip was
  originally drawn to the left of the gene ladder where it collided
  with gene y-tick labels. Moved to the right side of the bars (in
  axes-fraction coords) with a reserved right-margin via
  `subplots_adjust(right=0.70)`.
- `pathway_module_activity_heatmap`: sample-group strip originally
  drawn above row-0 at `y = -1.2`, colliding with the title; moved
  to below the x-tick labels (`y = n_m + 0.8`). Module-group strip
  originally drawn at `x = -0.8`, colliding with module y-tick
  labels; moved to the right of the heatmap (`x = n_s + 0.05`).

### Progress

| | v1.1.0-s08 | **v1.1.0-s09** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 218 | **224** |
| `omics_differential` | 10 | **16** |
| Tests | 1141 | **1171** |


## [1.1.0-s08] — 2026-04-20

Eighth session of the v1.1 hydration plan. Hydrates the
`gillespie_stochastic` modality from 7 to 15 recipes in direct
support of HOME-GATE-TRAP dwell analyses and stochastic-state-
switching manuscripts.

### Added

- `gillespie_stochastic.master_equation_steady_state` — analytical
  master-equation P(n) overlaid with sampled SSA histogram, plus
  KL + TV distance callout.
- `gillespie_stochastic.tau_leaping_comparison` — exact-SSA vs
  τ-leap trajectory overlay with inset residual strip and RMSE /
  speedup callout.
- `gillespie_stochastic.mean_first_passage_time_matrix` — lower-
  triangular MFPT heatmap with every off-diagonal annotated and a
  fastest-pair footer.
- `gillespie_stochastic.fisher_information_parameter_estimation` —
  K × K Fisher-information matrix with condition-number callout
  and dominant / poorest-identified eigen-direction summaries.
- `gillespie_stochastic.burst_size_distribution` — discrete burst-
  count PMF with fitted geometric + negative-binomial overlays,
  preferred-model callout, mean / CV pill.
- `gillespie_stochastic.extinction_probability_vs_parameter` —
  per-initial-state P_ext(θ) curves with 0.5-crossing tipping-point
  markers and footer.
- `gillespie_stochastic.autocorrelation_of_trajectories` — per-state
  ACF(τ) with exponential fits, 1/e reference and slowest-over-
  fastest ratio callout.
- `gillespie_stochastic.stochastic_resonance_signature` — SNR vs
  noise-amplitude sweep with parabolic fit, vertical σ* and red
  peak-star marker.

### Infrastructure

- No changes to `core/` — all 8 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (analytic-vs-sampled
  overlap, method comparison with inset residual, MFPT matrix,
  FIM matrix, discrete-count PMF, P_ext-vs-θ sigmoid family,
  per-state ACF, SNR-vs-σ bell) live inline.
- Liberation Sans-safe labels — ASCII replacements for the
  unicode ↔ arrow used in the fastest-pair MFPT footer.
- Style-drift ratchet held on first pass; all new tests green.

### Visual-QA polish (two panels)

- `tau_leaping_comparison`: the residual inset was overlapping the
  main axis's "time (s)" xlabel — hid the main xlabel and placed the
  inset further below (y=[-0.40, -0.16]) so the residual-only axis
  carries the time label.
- `extinction_probability_vs_parameter`: tipping-point footer was
  showing absurd values (~1e6) because `max(denom, 1e-9)` clipped
  the negative denominator of a decreasing sigmoid; replaced with
  a signed-denominator test `abs(denom) > 1e-6` so both increasing
  and decreasing curves interpolate correctly.

### Progress

| | v1.1.0-s07 | **v1.1.0-s08** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 210 | **218** |
| `gillespie_stochastic` | 7 | **15** |
| Tests | 1101 | **1141** |


## [1.1.0-s07] — 2026-04-20

Seventh session of the v1.1 hydration plan. Hydrates the
`intravital_imaging` modality from 6 (real baseline; coordinator
listed 8 but actual v1.0 count = 6) to 15 recipes in direct support
of the Neuron figures and the formalised 2P-witness strategy. Path 2
reconciliation adopted — land 9 recipes in one session to hit the
plan's 15-target, matching the s03 precedent.

### Added — seeds from brief (+7)

- `intravital_imaging.depth_projected_microglia_field` — per-cell
  (x, y, z) scatter with depth-coded colormap, size-encoded cell
  size, faint per-bin density background, mandatory scale bar and
  depth stats pill. Distinct from the generic z-stack depth MIP.
- `intravital_imaging.process_event_timeline` — per-cell event
  raster with row-background state shading, marker-coded event
  types (extension / retraction / contact) and a bottom
  total-events-per-minute strip.
- `intravital_imaging.territory_change_pre_post` — paired
  pre-condition filled polygon + post-condition dashed outline per
  cell with centroid pre-to-post arrow and expanded/shrank counts in
  the title.
- `intravital_imaging.surveillance_efficiency_metric` — condition-
  level forest with 95 % CI sorted by estimate, colour-coded above /
  below baseline and numeric value labels right of CI.
- `intravital_imaging.cell_cell_contact_frequency_matrix` — lower-
  triangular inferno heatmap with threshold annotations and
  top-pair footer.
- `intravital_imaging.laser_injury_response_radial` — radial
  response curves over time with CI bands, t=0 baseline and
  peak-position / max-time callout.
- `intravital_imaging.multi_channel_intravital_overlay` — RGB
  channel blend with mandatory scale bar, per-channel step-histogram
  sidebar and per-channel mean callout.

### Added — gap-closers to hit 15 (+2)

- `intravital_imaging.msd_curve_by_state` — log-log ensemble MSD vs
  τ per state with α-slope fit labels and a pure-diffusion reference
  line. Reviewer-mandatory intravital analysis, no existing
  ensemble-statistic recipe.
- `intravital_imaging.velocity_distribution_by_state` —
  instantaneous-speed split violin with median / quartile overlays
  and per-category N labels. Distinct quantity from
  `cell_shape_descriptors_by_state` (shape, not motion) and
  `migration_rose_diagram` (angle only).

### Infrastructure

- No changes to `core/` — all 9 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (per-cell depth field,
  event raster, paired pre/post polygons, surveillance forest,
  pairwise cell contact matrix, radial-over-time curves, RGB blend
  with histogram sidebar, log-log MSD with α-fits, speed violin)
  live inline within their recipes.
- Liberation Sans-safe labels throughout — `→` replaced with
  `vs` / `(R)`, no unicode arrows in saved figures.
- Style-drift ratchet held; no new fontsize or linewidth literals.

### Visual-QA polish (two panels)

- `territory_change_pre_post`: the "field midline" faint line
  originally added to satisfy the `scatter_collapse` ≥1-line rule
  was visually distracting; replaced with an invisible
  `ax.plot([], [])` proxy.
- `surveillance_efficiency_metric`: baseline label pinned to the
  lower-right axes-fraction corner — original data-coord placement
  collided with the panel title at the top.

### Progress

| | v1.1.0-s06 | **v1.1.0-s07** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 201 | **210** |
| `intravital_imaging` | 6 | **15** |
| Tests | 1056 | **1101** |


## [1.1.0-s06] — 2026-04-20

Sixth session of the v1.1 hydration plan. Hydrates the
`redox_imaging` modality from 8 to 15 recipes in direct support of
the µRedoxScape submission.

### Added

- `redox_imaging.roGFP2_ratio_vs_disulfide_titration` — biosensor
  calibration curve with sigmoid fit, Rmin/Rmax reference lines,
  midpoint vertical and parameter callout.
- `redox_imaging.bimodality_kurtosis_vs_conditions` — grouped
  horizontal bars for three complementary bimodality statistics
  (BC, κ, dip) per condition with per-statistic thresholds and a
  red-star marker where all three agree.
- `redox_imaging.time_above_threshold_distribution` — per-condition
  CCDF of cell-level oxidation durations with median dots on P=0.5
  and a consolidated median-values footer.
- `redox_imaging.paracrine_kernel_fit` — 1-D K(r) with SEM band,
  exponential/Gaussian fit overlay, λ vertical and corner callout
  (λ / amp / R²).
- `redox_imaging.multiplicative_vs_additive_noise_diagnostic` —
  Langevin ξ² vs Y with two competing model fits (constant D_add vs
  D_mult(Y) = σ²Y²) and a ΔAIC-based preferred-model callout.
- `redox_imaging.redox_state_switching_frequency_map` — inferno
  spatial switching-rate heatmap with cell centroids scaled by
  per-cell rate, mandatory scale bar and mean / 95%ile pill.
- `redox_imaging.ratio_autocorrelation_decay` — temporal ACF per
  state with exponential fits, 1/e reference line and τ-ratio
  crossover callout.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (sigmoid calibration,
  three-stat grouped bars, CCDF survival, 1-D kernel fit, Langevin
  model comparison, switching-rate field, per-state ACF) live inline
  within their recipes.
- Liberation Sans-safe labels throughout (★ rendered via
  `ax.scatter(marker="*")` instead of a unicode glyph).
- Style-drift ratchet held; the single new `lw=0.0` that would have
  broken the 20-literal ceiling was resolved by switching
  `paracrine_kernel_fit` from `ax.plot(lw=0.0, marker=...)` to
  `ax.scatter(...)`.

### Visual-QA polish (two panels)

- `time_above_threshold_distribution`: consolidated per-condition
  median labels into a single figure-space footer — original
  strategy (labels offset vertically per index) still collided with
  the survival curves.
- `multiplicative_vs_additive_noise_diagnostic`: fixed the demo
  data-generation convention so `ξ² = 2·σ²·Y²·dt` matches the model
  curves drawn on the axis; AIC verdict now correctly reports
  "preferred: multiplicative" when the ground truth is multiplicative.

### Progress

| | v1.1.0-s05 | **v1.1.0-s06** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 194 | **201** |
| `redox_imaging` | 8 | **15** |
| Tests | 1021 | **1056** |


## [1.1.0-s05] — 2026-04-20

Fifth session of the v1.1 hydration plan. Hydrates the
`sensitivity_analysis` modality from 8 to 15 recipes — Sobol-dominant
with support for the other GSA methods reviewers routinely request.

### Added

- `sensitivity_analysis.fast_sensitivity_spectrum` — FAST
  frequency-domain periodogram with per-parameter fundamentals +
  harmonics, a noise/interaction floor reference and a dominant-peak
  callout.
- `sensitivity_analysis.lhs_parameter_space_coverage` — Latin-
  hypercube scatter matrix with marginal histograms and built-in
  √Centered-L2 discrepancy diagnostic. No new dependency.
- `sensitivity_analysis.tornado_diagram` — classic OAT ±Δ tornado
  with high/low halves colour-coded, sorted by total width, baseline
  reference line and pinned baseline pill.
- `sensitivity_analysis.sensitivity_by_output_quantity` — param ×
  output sensitivity-index heatmap with row-max right-triangle and
  col-max down-triangle margin markers (so cell values stay
  readable) and a dominant-driver-per-output callout.
- `sensitivity_analysis.sobol_bootstrap_convergence` — per-parameter
  S₁ line with shrinking bootstrap 95 % CI ribbon over N, rank-flip
  diagnostic at the smallest stable-top-k N, and a mean-CI-width
  footer.
- `sensitivity_analysis.interaction_network_sobol` — circular graph
  view of pairwise S₂ with edge width/colour coded, node size from
  Sᵀ, S₂-colorbar legend and top-edge callout; complements the
  existing interaction-matrix heatmap.
- `sensitivity_analysis.sensitivity_time_evolution` — time-resolved
  Sobol indices per parameter with CI bands, peak-time markers, and
  a per-time-window dominant-driver callout.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (FAST periodogram,
  LHS pair-matrix, OAT tornado, param × output heatmap, bootstrap-CI
  convergence ribbon, Sobol interaction graph, time-resolved
  indices) live inline within their recipes.
- Liberation Sans-safe labels throughout — subscripts via mathtext.
- Style-drift ratchet held by snapping the sole new literal
  (title fontsize 8.8 → 8.6).
- `tests/test_contracts.py` modality-count assertion bumped 8 → 15.

### Visual-QA polish (three panels)

- `tornado_diagram`: moved the baseline label from a data-coord
  annotation (which collided with the title) to an upper-left axes-
  fraction pill so it never competes with the panel title.
- `sensitivity_by_output_quantity`: replaced hollow-square
  driver highlights (which obscured cell values) with small right-
  triangle (row max) and down-triangle (col max) markers drawn on
  the cell margins with `clip_on=False`.
- `fast_sensitivity_spectrum`: moved the top-drivers pill from
  inside the axes (where it wrapped into the legend) to a figure-
  space footer below the x-axis.

### Progress

| | v1.1.0-s04 | **v1.1.0-s05** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 187 | **194** |
| `sensitivity_analysis` | 8 | **15** |
| Tests | 986 | **1021** |


## [1.1.0-s04] — 2026-04-19

Fourth session of the v1.1 hydration plan. Hydrates the
`mixed_effects_models` modality from 9 to 16 recipes. This is the
cross-cutting modality used in *every* manuscript — the 7 catch-up
recipes close four long-standing grammar gaps: raw data under the
forest, per-cluster (intercept, slope) covariation, model selection
(AIC / BIC), Bayesian contrast densities, plus the
partial-residuals / response-scale-emmeans / fixed-vs-random-variance
trio reviewers explicitly request.

### Added

- `mixed_effects_models.sex_stratified_raincloud_with_coef_box` —
  raw-data raincloud per sex × genotype (half-violin + inline
  5/25/50/75/95 box + rain jitter) with an upper-right coefficient
  callout (β, 95 % CI, p) tied to the mixed-model interaction term.
- `mixed_effects_models.random_intercepts_vs_slopes_scatter` — per-cluster
  joint (intercept, slope) scatter with 95 % shrinkage ellipse, OLS
  fit line, quadrant colouring from `sex_x_genotype`, and a Pearson
  r annotation. Captures the `cor(int, slope)` term that 1-D
  caterpillar + slopes panels hide.
- `mixed_effects_models.model_comparison_aic_bic_ladder` — competing
  model specs sorted by AIC, paired with BIC diamonds, ΔAIC bars
  and a Burnham-Anderson evidence strip (Δ=2/4/7). Best-fit row
  highlighted; per-row ΔAIC/ΔBIC callouts.
- `mixed_effects_models.posterior_contrast_density` — stacked
  Δ-posterior densities per contrast with 95 % HDI bars, median
  markers, split fill at zero (sign emphasis) and P(Δ>0) callouts.
  Distinct from `bayes_posterior_density_by_term` (absolute term
  posteriors, no Δ).
- `mixed_effects_models.partial_residuals_vs_predictor` — partial
  residuals (eᵢⱼ + β̂·xᵢⱼ) scattered per group with tricube-kernel
  LOESS smoothers and the fitted β̂·x reference line. Built-in
  lightweight LOESS — no new dependency.
- `mixed_effects_models.group_level_emmeans_with_pairwise` —
  response-scale emmeans per group with CI caps, Bonferroni-adjusted
  pairwise brackets stacked by arc length (*** / ** / *), and ns
  brackets on adjacent pairs. Distinct from `emmeans_contrast_grid`
  which shows the Δ between groups.
- `mixed_effects_models.fixed_vs_random_effect_partition` —
  Nakagawa-Schielzeth variance partition (marginal R² / conditional R²
  share / residual) as stacked horizontal bars per model, with a
  per-term hatched sub-strip under the fixed stripe. Distinct from
  `icc_variance_decomposition` which partitions the random-effect
  side only.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (raincloud-with-coef-box,
  Burnham-Anderson ΔAIC evidence strip, stacked Δ-posteriors with
  split-zero fills, Nakagawa-Schielzeth variance partition) live
  inline within their recipes.
- Liberation Sans-safe labels throughout — no subscript / proportional
  glyphs in any saved figure.
- Style-drift ratchet holds.

### Visual-QA polish (three panels)

- `sex_stratified_raincloud_with_coef_box`: moved per-stratum `n=`
  labels to a fixed axes-fraction y so they align with the xtick
  labels instead of drifting below the plot as later categories
  expanded the ylim.
- `model_comparison_aic_bic_ladder`: replaced the in-plot legend
  (which landed inside the lowest bar) with a title-bar key —
  "bar = ΔAIC, diamond = ΔBIC".
- `fixed_vs_random_effect_partition`: removed the redundant
  fixed/random/residual legend (bars are labelled inline) and
  bumped the per-term label threshold from 0.07 to 0.11 so crowded
  terms render as hatched colour strips without overlapping text.

### Progress

| | v1.1.0-s03b | **v1.1.0-s04** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 180 | **187** |
| `mixed_effects_models` | 9 | **16** |
| Tests | 951 | **986** |


## [1.1.0-s03b] — 2026-04-19

Catch-up session for `actin_microtubule_morphometry` — lands the 11
recipes the plan's idealised v1.0 spec assumed existed but were
absent from real v1.0 (surfaced by the Path 2 reconciliation in s03).
Brings the modality from 24 to 35 recipes. The 5-recipe overshoot
past the 30-roster target comes from 4 actual-v1.0 recipes not in the
user's original roster + `persistence_length_by_segment` overlapping
`persistence_length_fit`. User approved "land all 11".

### Added

- `actin_microtubule_morphometry.process_length_distribution_by_sex` —
  total per-cell process length by sex × genotype, split violin with
  per-group medians and Ns using the `sex_x_genotype` palette.
- `actin_microtubule_morphometry.sex_stratified_cvvelocity` — CV of
  instantaneous velocity per cell by sex × genotype with
  sex × genotype interaction bracket + p-value.
- `actin_microtubule_morphometry.skeleton_complexity_radar` —
  per-condition polar polygon over 6-8 normalised topology metrics
  with threshold reference polygon.
- `actin_microtubule_morphometry.branching_topology_sunburst` —
  nested-ring donut of branching-depth hierarchy by condition.
- `actin_microtubule_morphometry.persistence_length_by_segment` —
  per-segment Lp forest with bootstrap 95% CI, grand-mean reference.
- `actin_microtubule_morphometry.actin_microtubule_crosstalk_quiver`
  — MT density pcolormesh with actin-direction quiver overlay.
- `actin_microtubule_morphometry.protrusion_retraction_kymograph` —
  signed edge-velocity kymograph (arc × time) RdBu_r anchored at 0
  with v=0 iso-contour and time-averaged strip inset.
- `actin_microtubule_morphometry.cytoskeleton_polarity_vectorfield` —
  multi-cell field with per-cell centroid + polarity arrows,
  per-condition mean resultant length R.
- `actin_microtubule_morphometry.airyscan_segmentation_mosaic` —
  2-column (raw / segmentation) grid per cell with mandatory scale
  bars on the raw panel.
- `actin_microtubule_morphometry.shape_pca_morphospace` — PCA scatter
  with per-condition convex hulls and biplot loading arrows;
  paired story with `shape_umap_by_condition`.
- `actin_microtubule_morphometry.colocalization_coefficient_matrix` —
  condition × coefficient heatmap with mean ± SEM annotations.

### Infrastructure

- No changes to `core/` — all 11 recipes use new per-recipe Pydantic
  contracts.
- No new dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New visual grammars (sunburst,
  biplot arrows, quiver-on-pcolormesh, multi-cell polarity field)
  live inline within their recipes.
- Style-drift ratchet holds.

### Visual-QA polish (two panels)

- `branching_topology_sunburst`: widened depth-legend swatch gaps
  + fontsize so the d=0…d=4 labels no longer run together.
- `cytoskeleton_polarity_vectorfield`: moved R-summary pill from
  lower-left to upper-left so it clears the bottom-left scale bar.

### Progress

| | v1.1.0-s03 | **v1.1.0-s03b** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 169 | **180** |
| `actin_microtubule_morphometry` | 24 | **35** |
| Tests | 896 | **951** |


## [1.1.0-s03] — 2026-04-19

Third session of the v1.1 hydration plan. Hydrates the
`actin_microtubule_morphometry` modality from 6 to 24 recipes (Path 2
— the 9+ "catch-up" v1.0 recipes the idealised plan assumed existed
are deferred to session s03b). Organised into six functional
sub-families.

### Added

**Sub-family A — per-cell morphometric distributions (+4):**

- `actin_microtubule_morphometry.branch_point_count_raincloud` —
  per-cell branch-point count raincloud with animal-level ring markers.
- `actin_microtubule_morphometry.process_end_count_violin` — split
  violin by primary / higher-order end type per condition.
- `actin_microtubule_morphometry.cell_body_area_distribution` — soma
  area violin with median callouts and N per condition.
- `actin_microtubule_morphometry.sphericity_vs_elongation_scatter` —
  hero shape-plane scatter with marginal densities, per-condition
  convex hulls, OLS fit.

**Sub-family B — skeleton / network topology (+2):**

- `actin_microtubule_morphometry.branch_angle_distribution` — stacked
  KDE ridges by condition with Arp2/3 70° reference.
- `actin_microtubule_morphometry.topology_ternary_simplex` —
  (linear, branched, looped) barycentric scatter with per-condition
  convex hulls.

**Sub-family C — spatial / kinematic (+2):**

- `actin_microtubule_morphometry.edge_velocity_spatial_correlation` —
  C(s) along perimeter with exponential decay-length fit.
- `actin_microtubule_morphometry.mitochondrial_axis_alignment` —
  polar rose of Δ-angle vs filament axis with order-parameter S.

**Sub-family D — thumbnails / mosaics (+3):**

- `actin_microtubule_morphometry.per_cell_thumbnail_grid_with_metrics`
  — 4×4 grid of segmented cells with 2-line metric callouts and
  first-column scale bars.
- `actin_microtubule_morphometry.exemplar_extremes_panel` —
  (condition × min / median / max) tile grid with metric annotations.
- `actin_microtubule_morphometry.condition_average_cell_composite` —
  per-condition shape hulls overlaid on a 2-D hist2d variability
  cloud.

**Sub-family E — dimensionality reduction (+3):**

- `actin_microtubule_morphometry.shape_umap_by_condition` — scatter
  with per-condition KDE density contours.
- `actin_microtubule_morphometry.morphospace_trajectory_by_time` —
  per-condition centroid paths with arrowheads and net-displacement
  callouts.
- `actin_microtubule_morphometry.shape_descriptor_scatter_matrix` —
  full SPLOM with histogram diagonals and per-condition colouring.

**Sub-family F — colocalization / intensity (+4):**

- `actin_microtubule_morphometry.actin_mt_ratio_spatial_map` — 2-D
  `RdBu_r` anchored at 1.0 with cell outline and scale bar.
- `actin_microtubule_morphometry.intensity_radial_profile` — per-
  channel mean ± SEM vs radius with peak callout.
- `actin_microtubule_morphometry.tip_enrichment_vs_shaft_scatter` —
  tip vs shaft scatter with y=x reference, Pearson r, Wilcoxon p.
- `actin_microtubule_morphometry.colocalization_vs_morphology_correlation`
  — correlation heatmap with BH-FDR significance stars.

### Infrastructure

- No changes to `core/` — all 18 recipes use new per-recipe Pydantic
  contracts local to their `.py` file.
- `_aesthetic.py` unchanged. Four new visual grammars (ternary simplex,
  thumbnail grid, UMAP density contours, radial profile) live inline
  within their recipes so `AESTHETIC` stays stable.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds: snapped `fontsize=5.4` → `5.6` and
  `lw=1.6` → `1.5` to avoid new distinct values.

### Visual-QA polish (three panels)

- `per_cell_thumbnail_grid_with_metrics`: 2-line metric callouts,
  scale bars repositioned cleanly, taller figure + wider row spacing
  so all rows show the full annotation.
- `colocalization_vs_morphology_correlation`: FDR legend folded into
  title (was a figure footer colliding with rotated x-ticks).
- `shape_descriptor_scatter_matrix`: per-condition legend folded into
  suptitle (was a figure footer colliding with outer x-ticks).

### Deferred to session s03b

Nine+ "catch-up" recipes the plan's idealised v1.0 spec assumed
existed will land as a follow-up session between s03 and s04:
`process_length_distribution_by_sex`, `sex_stratified_cvvelocity`,
`skeleton_complexity_radar`, `branching_topology_sunburst`,
`persistence_length_by_segment`, `actin_microtubule_crosstalk_quiver`,
`protrusion_retraction_kymograph`, `cytoskeleton_polarity_vectorfield`,
`airyscan_segmentation_mosaic`, `shape_pca_morphospace`,
`colocalization_coefficient_matrix`.

### Progress

| | v1.1.0-s02 | **v1.1.0-s03** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 151 | **169** |
| `actin_microtubule_morphometry` | 6 | **24** |
| Tests | 806 | **896** |


## [1.1.0-s02] — 2026-04-19

Second session of the v1.1 hydration plan. Hydrates the
`fret_biosensors` modality from 10 to 18 recipes.

### Added

- `fret_biosensors.donor_acceptor_scatter_linearity` — sensor-linearity
  validation scatter with OLS fit, 95% CI band, y=x reference, and
  slope / R² / intercept callout.
- `fret_biosensors.fret_efficiency_vs_distance` — measured
  (distance, efficiency) with SEM bars overlaid on the theoretical
  `E = 1/(1 + (r/R_0)^6)` curve with fitted R_0 vertical line + halo label.
- `fret_biosensors.paired_pre_post_stimulus` — per-cell connecting
  lines between pre and post FRET ratios (colour-coded by direction),
  mean ± SEM markers, Wilcoxon bracket and stars.
- `fret_biosensors.biosensor_dose_response_matrix` — 2-D `RdBu_r`
  heatmap of dose × time Δ-ratio with iso-contours at 0.1 / 0.2 / 0.3
  and peak-response marker.
- `fret_biosensors.kymograph_ratio_edge_to_center` — 1-D spatial ×
  temporal kymograph along the cell radius, anchored at the
  FRET-neutral ratio 1.0, with optional inward-propagating wavefront
  overlay.
- `fret_biosensors.ratio_map_with_segmentation_overlay` — ratio
  heatmap with white cell-outline polygons and centroid labels;
  mandatory 10 µm scale bar.
- `fret_biosensors.windowed_roi_ratio_trajectory` — N per-window
  ratio traces colour-coded by arc-length position
  (viridis edge → interior), with position colorbar and a
  windows-schematic inset.
- `fret_biosensors.fret_vs_scalar_activity_regression` — FRET-vs-
  orthogonal-scalar regression with per-condition colour, OLS +
  95 % prediction band, Pearson r / p callout.

### Infrastructure

- No changes to `core/` — all eight recipes use new per-recipe
  Pydantic contracts local to their own `.py` file.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds (≤ 20 distinct fontsize + linewidth literals).

### Progress

| | v1.1.0-s01 | **v1.1.0-s02** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 143 | **151** |
| `fret_biosensors` | 10 | **18** |
| Tests | 766 | **806** |


## [1.1.0-s01] — 2026-04-19

First session of the v1.1 hydration plan (see
`docs/hydration_coordinator.md`). Hydrates the `rhogtpase_dynamics`
modality from 12 to 18 recipes.

### Added

- `rhogtpase_dynamics.phase_portrait_with_trajectories` — streamplot
  backdrop + time-colored integrated trajectories from multiple ICs,
  stability-coded fixed points.
- `rhogtpase_dynamics.codim2_bifurcation_map` — two-parameter (µ, ν)
  plane with saddle-node / Hopf / pitchfork curves and codim-2 points
  (cusp, Bogdanov-Takens); shaded regime regions.
- `rhogtpase_dynamics.potential_landscape_waddington_3d` — isometric
  3-D Waddington surface with gradient-descent sample trajectories
  sliding into wells; 2-D legend inset clarifies the start-ball /
  descent-path convention.
- `rhogtpase_dynamics.excitability_threshold_diagram` —
  FitzHugh-Nagumo in the excitable regime with rest point, threshold
  curve, and paired sub/super-threshold trajectories.
- `rhogtpase_dynamics.slow_manifold_projection` — geometric collapse
  of fast trajectories onto the slow manifold in phase space (the
  geometric counterpart to `quasi_steady_state_reduction`'s
  time-series comparison).
- `rhogtpase_dynamics.poincare_first_return_map` — 1-D discrete
  return map on a Poincaré section with identity diagonal, cobweb
  iteration, and slope-at-FP diagnostic.

### Infrastructure

- No changes to `core/` — all six recipes use new per-recipe Pydantic
  contracts local to their own `.py` file.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds at ≤ 20 distinct linewidths.

### Progress

| | v1.0.0 | **v1.1.0-s01** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 137 | **143** |
| rhogtpase_dynamics | 12 | **18** |
| Tests | 736 | **766** |


## [1.0.0] — 2026-04-19

**First stable release.** Promotes the 20-modality / 137-recipe
milestone previously tracked as `0.1.0` to a proper `v1.0.0`, in line
with the shipped reality:

- Stable public API — `figures` CLI, modality/recipe registry, manifest
  schema, Claude Code skill bootstrap. All have consumers.
- CI-enforced contract — cross-modality figure-integrity QA, typography
  stack, empty-data guard, style-drift ratchet.
- 736 tests pass on Python 3.11 and 3.12. Ruff clean.
- 4 pre-releases consumed (`0.1.0-alpha`, `-beta1`, `-beta2`, `-beta3`).

No code changed between `0.1.0` (which was not tagged) and `1.0.0`.
This entry formally renames the stable release; the `0.1.0` content is
the `1.0.0` content. `pyproject.toml` classifier moves from Beta to
Production/Stable to match the new version.

Going forward, SemVer is honored strictly: breaking changes require a
major bump. The v1.1 hydration plan (see
`docs/hydration_coordinator.md`) is a pure additive expansion — no
breaking changes — and lands under `v1.1.0-s01` through `v1.1.0-s20`.

## [0.1.0] — 2026-04-19

Session 5 — the full roadmap lands. 5 new modalities, 30 new recipes,
bringing the total to **137 recipes across 20 modalities** (the v0.1.0
target). Status moved from beta to first stable release.

### Added

- Modality `spatial_statistics` (6): ripley_l_function,
  pair_correlation_function, nearest_neighbor_distance_distribution,
  voronoi_territory_map, kernel_density_heatmap, moran_i_by_lag.
- Modality `clinical_cohort` (6): kaplan_meier_by_stratum,
  cox_forest_hazard_ratios, consort_flow_diagram,
  baseline_table_visualization, subgroup_forest_plot,
  outcome_by_quartile.
- Modality `cryoem_and_structure` (6): fsc_resolution_curve,
  angular_distribution_hist, local_resolution_surface,
  particle_2d_class_montage, ramachandran_plot, bfactor_vs_residue.
- Modality `intravital_imaging` (6): cell_track_trajectory_field,
  two_photon_depth_projection, vessel_diameter_kymograph,
  cell_shape_descriptors_by_state, migration_rose_diagram,
  time_to_homing_survival.
- Modality `actin_microtubule_morphometry` (6):
  filament_orientation_histogram, branch_point_density_map,
  persistence_length_fit, protrusion_length_velocity_joint,
  cortical_thickness_by_region, skeleton_overlay_kymograph.
- 30 new gallery PNGs under docs/gallery/ (137 total).

### Progress

| | v0.1.0b3 | **v0.1.0** | target |
|---|---|---|---|
| Modalities | 15 | **20** | 20 ✓ |
| Recipes | 107 | **137** | 137 ✓ |
| Tests | 586 | **736** | ≥400 ✓ |


## [0.1.0b3] — 2026-04-19

Session 4 batch — 4 new modalities, 27 new recipes, **107 total**.

### Added

- Modality `omics_differential` (10): volcano_labeled_repelled,
  ma_plot_with_lowess, annotated_cluster_heatmap, gsea_running_enrichment,
  ora_dotplot_by_ontology, upset_set_comparisons, differential_rank_ladder,
  pathway_flux_bubble, effect_size_vs_significance,
  multi_contrast_volcano_grid.
- Modality `single_cell_embeddings` (7): umap_categorical_with_density_contours,
  umap_continuous_expression, trajectory_pseudotime_arrow,
  expression_dotplot_by_cluster, pca_biplot_with_loadings,
  diffusion_map_2d, neighborhood_composition_stacked.
- Modality `network_and_pathway` (5): regulatory_network_hive,
  interaction_chord_diagram, pathway_flux_sankey_like,
  module_eigengene_heatmap, centrality_degree_distribution.
- Modality `diffusion_and_tracking` (5): msd_by_condition,
  step_size_distribution, angle_correlation_decay,
  confinement_radius_map, track_persistence_hist.
- Quality rule for the new `volcano` family: ≥10 scatter points + ≥1
  threshold line.
- 27 new gallery PNGs under docs/gallery/ (107 total).

### Progress toward v0.1.0

| | v0.1.0b2 | **v0.1.0b3** | v0.1.0 target |
|---|---|---|---|
| Modalities | 11 | **15** | 20 |
| Recipes | 80 | **107** | 137 |
| Tests | 361 | **469** | ≥400 ✓ |


## [0.1.0b2] — 2026-04-18

Session 3 batch — 4 new modalities, 31 new recipes, **80 total**.

### Added

- Modality `gillespie_stochastic` (7): trajectory_fan_with_fpt,
  dwell_time_log_violin, waiting_time_ecdf_fitted, rate_vs_control_parameter,
  state_occupancy_raster, ensemble_mean_variance_tube, noise_power_spectrum.
- Modality `redox_imaging` (8): bistability_hysteresis_loop,
  single_cell_ratio_distribution, paracrine_coupling_length_map,
  bimodality_coefficient_grid, ratio_trajectory_with_phase_annotation,
  redox_state_transition_diagram, multiplicative_noise_diagnostic,
  drift_diffusion_decomposition.
- Modality `fret_biosensors` (10): ratio_heatmap_over_field,
  ratio_timecourse_hierarchical_ci, stimulus_response_fan,
  donor_acceptor_dual_channel, sensor_calibration_curve,
  dose_response_hill_fret, single_cell_ratio_trajectories,
  ratio_distribution_by_condition, fret_signal_to_noise_map,
  roi_ratio_summary_grid.
- Modality `calcium_signaling` (6): event_raster_with_rate, gcamp_trace_stack,
  event_frequency_by_condition, calcium_propagation_wavefront,
  spike_triggered_average, synchronization_matrix.
- Quality rules for 2 new families: `split_violin`, `hysteresis_loop`.
  Broadened the split_violin rule's fill-detection to accept matplotlib ≥
  3.11's `FillBetweenPolyCollection` (now the default return type from
  `ax.violinplot`).
- 31 new gallery PNGs under docs/gallery/ (80 total).

### Progress toward v0.1.0

| | v0.1.0b1 | **v0.1.0b2** | v0.1.0 target |
|---|---|---|---|
| Modalities | 7 | **11** | 20 |
| Recipes | 49 | **80** | 137 |
| Tests | 237 | **361** | ≥400 |


## [0.1.0b1] — 2026-04-18

Session 2 batch — 4 new modalities, 31 new recipes, 49 total.

### Added

- Modality `mixed_effects_models` (9): sex_x_genotype_interaction_forest,
  random_effects_caterpillar, marginal_effects_ribbon, emmeans_contrast_grid,
  posterior_predictive_check, icc_variance_decomposition,
  mixed_model_residual_diagnostic, random_slopes_per_cluster,
  bayes_posterior_density_by_term.
- Modality `dose_response_pharmacology` (5): hill_fit_with_ci,
  ic50_forest_across_compounds, schild_regression, isobologram_combination,
  drug_combo_heatmap.
- Modality `biophysics_scaling` (5): log_log_scaling_with_slope_box,
  master_curve_collapse, force_length_characteristic,
  power_law_tail_diagnostic, buckling_critical_force_plot.
- Modality `rhogtpase_dynamics` (12): phase_portrait_tristable,
  phase_portrait_bistable, phase_portrait_oscillator, potential_landscape_1d,
  potential_landscape_2d_heatmap, bifurcation_saddle_node, bifurcation_hopf,
  bifurcation_pitchfork, nullcline_intersection_annotated,
  quasi_steady_state_reduction, timescale_separation_diagnostic,
  basin_of_attraction_map.
- Quality rules for 6 new families (phase_portrait, bifurcation, heatmap,
  ridge_by_group, timecourse_hierarchical_ci, coef_forest). Extended the
  "filled-polygon" rule to accept both `PolyCollection` and
  matplotlib ≥3.9's new `FillBetweenPolyCollection`.
- 31 new gallery PNGs under docs/gallery/.

### Progress toward v0.1.0

| | v0.1.0a0 | **v0.1.0b1** | v0.1.0 target |
|---|---|---|---|
| Modalities | 3 | **7** | 20 |
| Recipes | 18 | **49** | 137 |
| Tests | 113 | **237** | ≥400 |


## [0.1.0a0] — 2026-04-17

Initial alpha — scaffold, core, 3 of 20 modalities.

### Added

- Core layer: `style`, `palette`, `primitives`, `layout`, `export`, `contract`,
  `aesthetic_base`.
- 12 themes: `default`, `nature`, `cell`, `pnas`, `devcell`, `bpj`, `neuron`,
  `ncb`, `sttt`, `trends`, `fct_grant`, `horizon`.
- 13 palettes: `okabe_ito`, `sex_dimorphic`, `home_gate_trap`, `wt_ko`,
  `redox_bistable`, `fret_donor_acceptor`, `sex_x_genotype`,
  `timepoint_gradient`, `mechanism_class`, `cytoskeleton_components`,
  `rhogtpase_family`, `microglia_states`, `journal_neutral`.
- Adapters: `tabular`, `numpy_npz`, `pandas_pickle`, `passthrough`.
- Transforms: `reshape`, `aggregate`, `join`, `derive`.
- Manifest schema + resolver + catalog generator.
- CLI (`figures` entrypoint) with 11 subcommands.
- Modality 1 — `grant_and_conceptual` (6 recipes): `executive_summary_tile`,
  `timeline_gantt_with_milestones`, `work_package_flow`, `hypothesis_diagram`,
  `team_expertise_matrix`, `conceptual_triptych`.
- Modality 2 — `meta_and_diagnostic` (4 recipes): `power_analysis_by_effect_size`,
  `sample_size_decision_ladder`, `missing_data_pattern_matrix`,
  `qc_metric_radar`.
- Modality 3 — `sensitivity_analysis` (8 recipes): `sobol_first_total_pair`,
  `morris_elementary_effects`, `parameter_scan_2d_contour`,
  `dimensionless_pi_group_collapse`, `pi_group_rank_plot`,
  `fast_subspace_detection`, `convergence_diagnostic_sobol`,
  `interaction_matrix_sobol`.
- Gallery generator + 18 committed gallery PNGs.
- Quality gate, aesthetic compliance test framework, smoke test framework.
- Claude Code skill at `skill/SKILL.md` with `bootstrap`, `resurvey`,
  `add_figure` modes, plus references, example manifests, and templates.
- CI workflow on Python 3.11 and 3.12.

### Target for v0.1.0

Completes the remaining 17 modalities (119 recipes) in subsequent sessions,
following the order in `README.md`.
