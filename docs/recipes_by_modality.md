# Recipes by modality

v1.0.0 stable: 20 modalities, 137 recipes.
v1.1 in progress: 210 recipes (s01 rhogtpase_dynamics +6, s02 fret_biosensors +8, s03 actin_microtubule_morphometry +18, s03b actin_microtubule_morphometry catch-up +11, s04 mixed_effects_models +7, s05 sensitivity_analysis +7, s06 redox_imaging +7, s07 intravital_imaging +9).

## v0.1.0-alpha (3 modalities, 18 recipes)

- **grant_and_conceptual** (6): executive summaries, Gantts, WP flows,
  hypothesis diagrams, team matrices, conceptual triptychs.
- **meta_and_diagnostic** (4): power curves, sample-size ladders,
  missing-data patterns, QC radars.
- **sensitivity_analysis** (8): Sobol / Morris / parameter scan / Pi-group
  collapse / interaction matrix / convergence / active subspace.

## v0.1.0-beta1 (4 modalities, 31 recipes)

- **mixed_effects_models** (9).
- **dose_response_pharmacology** (5).
- **biophysics_scaling** (5).
- **rhogtpase_dynamics** (12).

## v0.1.0-beta2 (4 modalities, 31 recipes)

- **gillespie_stochastic** (7).
- **redox_imaging** (8).
- **fret_biosensors** (10).
- **calcium_signaling** (6).

## v0.1.0-beta3 (4 modalities, 27 recipes)

- **omics_differential** (10): volcanos, MA plot, GSEA running-enrichment,
  ORA dotplot, UpSet set comparisons, differential rank ladder, pathway-flux
  bubble, effect-size vs significance, multi-contrast volcano grid,
  annotated cluster heatmap.
- **single_cell_embeddings** (7): UMAP categorical + continuous, pseudotime
  trajectory with arrow, expression dotplot by cluster, PCA biplot with
  loadings, 2D diffusion map, neighborhood composition stacked bars.
- **network_and_pathway** (5): regulatory hive, chord diagram, Sankey-like
  flux, module eigengene heatmap, centrality degree distribution.
- **diffusion_and_tracking** (5): MSD by condition with α fit, step-size
  distribution by condition, angle autocorrelation decay, confinement
  radius map, track persistence histogram.

## v1.0.0 — Session 5 (5 modalities, 30 recipes)

- **spatial_statistics** (6): Ripley's L, pair correlation, NN distances,
  Voronoi territories, KDE heatmap, Moran's I by lag.
- **clinical_cohort** (6): Kaplan-Meier by stratum, Cox forest, CONSORT
  flow, baseline characteristics, subgroup forest, outcome by quartile.
- **cryoem_and_structure** (6): FSC curve, angular distribution, local
  resolution, 2D class montage, Ramachandran, B-factor vs residue.
- **intravital_imaging** (6): cell-track field, two-photon depth
  projection, vessel-diameter kymograph, cell-shape descriptors by state,
  migration rose, time-to-homing survival.
- **actin_microtubule_morphometry** (6): filament orientation, branch-point
  density, persistence-length fit, protrusion length × velocity,
  cortical thickness by region, skeleton kymograph.

## v1.1.0-s07 — intravital_imaging hydration (+9 Path 2, in progress)

Real baseline was 6 (coordinator listed 8); Path 2 chosen to hit the
plan's 15-target in one session by adding the 7 seeds + 2 gap-closers:

- **depth_projected_microglia_field** — per-cell (x,y,z) scatter with
  depth colormap and size-coded markers.
- **process_event_timeline** — per-cell event raster across time.
- **territory_change_pre_post** — paired pre/post territory polygons
  with centroid arrow and expanded/shrank counts.
- **surveillance_efficiency_metric** — condition-level forest with
  CI, baseline reference and above/below colour coding.
- **cell_cell_contact_frequency_matrix** — pairwise lower-triangular
  contact heatmap with top-pair footer.
- **laser_injury_response_radial** — radial response curves over time
  with CI bands and peak-position callout.
- **multi_channel_intravital_overlay** — RGB blend with histogram
  sidebar.
- **msd_curve_by_state** — log-log MSD vs τ per state with α-fit.
- **velocity_distribution_by_state** — instantaneous-speed split
  violin per state.

## v1.1.0-s06 — redox_imaging hydration (+7, in progress)

Expands redox_imaging from 8 to 15 recipes:

- **roGFP2_ratio_vs_disulfide_titration** — biosensor calibration
  curve with sigmoid fit and Rmin/Rmax/midpoint/R² callout.
- **bimodality_kurtosis_vs_conditions** — grouped bars for BC / κ /
  dip with per-statistic thresholds and consensus star marker.
- **time_above_threshold_distribution** — per-condition duration
  CCDF with median dots and consolidated median footer.
- **paracrine_kernel_fit** — 1-D K(r) with SEM band, fitted kernel
  and λ / amp / R² corner callout.
- **multiplicative_vs_additive_noise_diagnostic** — Langevin ξ² vs Y
  with competing additive / multiplicative fits and ΔAIC verdict.
- **redox_state_switching_frequency_map** — inferno spatial
  switching-rate heatmap with rate-scaled cell centroids and
  mandatory scale bar.
- **ratio_autocorrelation_decay** — temporal ACF per state with
  exponential fits, 1/e reference and τ-ratio callout.

## v1.1.0-s05 — sensitivity_analysis hydration (+7, in progress)

Expands sensitivity_analysis from 8 to 15 recipes:

- **fast_sensitivity_spectrum** — FAST frequency-domain periodogram
  with per-parameter fundamentals + harmonics.
- **lhs_parameter_space_coverage** — LHS scatter matrix with marginal
  histograms and √CD² discrepancy callout.
- **tornado_diagram** — classic OAT ±Δ tornado with high/low halves
  sorted by magnitude.
- **sensitivity_by_output_quantity** — param × output sensitivity-index
  heatmap with dominant-driver margin markers.
- **sobol_bootstrap_convergence** — per-parameter S₁ line with
  shrinking bootstrap CI ribbon and rank-flip diagnostic.
- **interaction_network_sobol** — circular graph view of pairwise S₂
  with edge width/colour coded and node size from Sᵀ.
- **sensitivity_time_evolution** — time-resolved Sobol indices per
  parameter with CI bands and window-dominant-driver callouts.

## v1.1.0-s04 — mixed_effects_models hydration (+7, in progress)

Expands mixed_effects_models from 9 to 16 recipes:

- **sex_stratified_raincloud_with_coef_box** — raw-data raincloud per
  sex × genotype with inline mixed-model β + CI + p callout.
- **random_intercepts_vs_slopes_scatter** — joint (intercept, slope) per
  cluster with 95 % shrinkage ellipse, OLS fit and r annotation.
- **model_comparison_aic_bic_ladder** — Burnham-Anderson ΔAIC ladder
  with paired BIC dots and the Δ=2/4/7 evidence strip.
- **posterior_contrast_density** — stacked Δ-posteriors per contrast
  with HDI, split fill at zero, P(Δ>0).
- **partial_residuals_vs_predictor** — partial residuals per predictor
  with LOESS per group and β̂·x fitted overlay.
- **group_level_emmeans_with_pairwise** — response-scale emmeans per
  group with Bonferroni-adjusted pairwise significance brackets.
- **fixed_vs_random_effect_partition** — Nakagawa-Schielzeth marginal /
  conditional / residual R² stacked bars with per-term hatch strip.

## v1.1.0-s03b — actin_microtubule_morphometry catch-up (+11, in progress)

Catch-up for the 11 recipes the plan's idealised v1.0 spec assumed
existed (surfaced by Path 2 reconciliation in s03). Brings the
modality from 24 to 35 recipes (5 over the 30-roster target; user
approved):

- **Sub-family A** (+2): `process_length_distribution_by_sex`,
  `sex_stratified_cvvelocity`.
- **Sub-family B** (+3): `skeleton_complexity_radar`,
  `branching_topology_sunburst`, `persistence_length_by_segment`.
- **Sub-family C** (+3): `actin_microtubule_crosstalk_quiver`,
  `protrusion_retraction_kymograph`,
  `cytoskeleton_polarity_vectorfield`.
- **Sub-family D** (+1): `airyscan_segmentation_mosaic`.
- **Sub-family E** (+1): `shape_pca_morphospace`.
- **Sub-family F** (+1): `colocalization_coefficient_matrix`.

## v1.1.0-s03 — actin_microtubule_morphometry hydration (+18, in progress)

Expands actin_microtubule_morphometry from 6 to 24 recipes (Path 2),
organised into six functional sub-families:

- **Sub-family A — distributions** (+4): `branch_point_count_raincloud`,
  `process_end_count_violin`, `cell_body_area_distribution`,
  `sphericity_vs_elongation_scatter`.
- **Sub-family B — topology** (+2): `branch_angle_distribution`,
  `topology_ternary_simplex`.
- **Sub-family C — spatial / kinematic** (+2):
  `edge_velocity_spatial_correlation`, `mitochondrial_axis_alignment`.
- **Sub-family D — thumbnails / mosaics** (+3):
  `per_cell_thumbnail_grid_with_metrics`, `exemplar_extremes_panel`,
  `condition_average_cell_composite`.
- **Sub-family E — dim reduction** (+3): `shape_umap_by_condition`,
  `morphospace_trajectory_by_time`, `shape_descriptor_scatter_matrix`.
- **Sub-family F — colocalization / intensity** (+4):
  `actin_mt_ratio_spatial_map`, `intensity_radial_profile`,
  `tip_enrichment_vs_shaft_scatter`,
  `colocalization_vs_morphology_correlation`.

## v1.1.0-s02 — fret_biosensors hydration (+8, in progress)

Expands fret_biosensors from 10 to 18 recipes:

- **donor_acceptor_scatter_linearity** — sensor-linearity validation
  scatter with OLS fit, 95% CI, slope / R² callout.
- **fret_efficiency_vs_distance** — Förster-distance / physics
  calibration with fitted R₀.
- **paired_pre_post_stimulus** — per-cell pre/post connecting lines
  with Wilcoxon statistics.
- **biosensor_dose_response_matrix** — dose × time 2-D heatmap with
  iso-contours and peak-response marker.
- **kymograph_ratio_edge_to_center** — 1-D spatial × temporal
  kymograph along the cell radius.
- **ratio_map_with_segmentation_overlay** — ratio heatmap with cell
  outlines overlaid.
- **windowed_roi_ratio_trajectory** — per-window sub-cellular
  trajectories colour-coded by arc-length position.
- **fret_vs_scalar_activity_regression** — cross-method FRET-vs-
  orthogonal-scalar regression.

## v1.1.0-s01 — rhogtpase_dynamics hydration (+6, in progress)

Expands rhogtpase_dynamics from 12 to 18 recipes:

- **phase_portrait_with_trajectories** — streamplot + time-colored integrated
  trajectories from multiple ICs with stability-coded fixed points.
- **codim2_bifurcation_map** — two-parameter (µ, ν) plane with SN/Hopf/
  pitchfork curves and codim-2 points (cusp, BT).
- **potential_landscape_waddington_3d** — isometric 3-D Waddington surface
  with gradient-descent trajectories.
- **excitability_threshold_diagram** — FitzHugh-Nagumo with threshold curve
  and paired sub/super-threshold trajectories.
- **slow_manifold_projection** — geometric collapse of fast trajectories
  onto the slow manifold.
- **poincare_first_return_map** — 1-D discrete return map with cobweb
  iteration and slope-at-FP diagnostic.
