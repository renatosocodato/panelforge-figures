# Changelog

All notable changes to `panelforge-figures` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows semantic versioning.

## [Unreleased]

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
