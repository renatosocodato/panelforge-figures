# Recipes by modality

v1.0.0 stable: 20 modalities, 137 recipes.
**v1.1.0 complete: 328 recipes across 20 modalities** (s01 rhogtpase_dynamics +6, s02 fret_biosensors +8, s03 actin_microtubule_morphometry +18, s03b actin_microtubule_morphometry catch-up +11, s04 mixed_effects_models +7, s05 sensitivity_analysis +7, s06 redox_imaging +7, s07 intravital_imaging +9, s08 gillespie_stochastic +8, s09 omics_differential +6, s10 calcium_signaling +9, s11 single_cell_embeddings +8, s12 dose_response_pharmacology +10, s13 network_and_pathway +10, s14 biophysics_scaling +10, s15 diffusion_and_tracking +10, s16 spatial_statistics +9 Path 2, s17 grant_and_conceptual +9, s18 meta_and_diagnostic +11, s19 clinical_cohort +9 Path 2, s20 cryoem_and_structure +9 Path 2).

**v1.2.0-beta-biophysics_scaling — Wave 3 landed: 348 recipes** (biophysics_scaling +20 cumulative across Waves 1–3). Pack total: 20/23 recipes; 3/4 waves. See `docs/biophysics_scaling_beta_pack_tracker.md`.

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

## v1.2.0-beta-biophysics_scaling — Wave 3 (territory / network / geometry + trajectory, +8)

Lands the territory / network / geometry physics block (C.3 / C.4 /
C.5 / C.6 / C.8 / C.9) plus the §5 trajectory layer (D.3 / D.4).
After Wave 3, §2 and §4 of the anchor manuscript are fully
panelable, and §5 has both its causal scaffold (Waves 2 + 3) and
its empirical reconstructions (D.3, D.4). biophysics_scaling
expands from 27 to 35 recipes; total catalog 340 → 348.

- **euler_critical_length_crossing_distribution** (`diagnostic_curve`)
  — per-group ECDF of supported lengths with L_crit reference.
- **confinement_free_energy_vs_width_curve**
  (`timecourse_hierarchical_ci`) — F_conf(w) per group with CI;
  divergence-width callout.
- **compartment_split_curvature_crosscorr**
  (`timecourse_hierarchical_ci`) — actin × MT CCF, side-by-side
  whole-cell / protrusion-internal sub-panels.
- **xz_microtubule_bowing_z_span** (`heatmap`) — per-group xz MIPs +
  paired z-span / bow-amplitude split violins.
- **width_alignment_buffered_unbuffered_interaction**
  (`timecourse_hierarchical_ci`) — α vs width with per-group LOESS,
  bootstrap CI, and buffered / unbuffered shading.
- **per_cell_colocalization_parallel_coordinates**
  (`scatter_collapse`) — three-spine parallel-coordinates with
  per-spine scatter rug and per-group median trace.
- **ordered_trajectory_checkpoint_divergence**
  (`timecourse_hierarchical_ci`) — per-group LOESS along an ordered
  axis with breakpoint reference and live-measurement caveat banner.
- **s_state_frontier_tip_raster** (`scatter_collapse`) — per-cell
  signed-position raster with frontier zero-line and S / non-S glyphs.

## v1.2.0-beta-biophysics_scaling — Wave 2 (scale-hierarchy + narrative anchors, +8)

Rounds out the scale-hierarchy grammar (A.2 / A.3 / A.4 / A.5) and
adds the §3 / §5 narrative anchors (C.1 / C.2 / D.1 / D.2). After
Wave 2, §1, §3, and the first half of §5 of the anchor manuscript
are fully panelable. biophysics_scaling expands from 19 to 27
recipes; total catalog 332 → 340.

- **compartment_paired_delta_scatter** (`scatter_collapse`) —
  whole-cell vs protrusion-internal d per feature; diagonal + null
  square.
- **feature_outcome_sankey_sig_vs_null** (`flow`) — three-column
  alluvial (total → scale → outcome) from matplotlib primitives only.
- **random_forest_importance_by_scale** (`coef_forest`) — top-N RF
  importance bars coloured by scale with CI whiskers.
- **scale_stratified_permanova_r2** (`coef_forest`) — per-scale R² ±
  CI with inline p-values and threshold reference.
- **persistence_length_lp_with_equivalence_bounds** (`split_violin`) —
  Lp 2×N split violin with TOST verdict per compartment.
- **psd_active_gel_overlay_with_motor_inset**
  (`timecourse_hierarchical_ci`) — log-log PSD with CI, ω^-2
  reference, active-gel / motor-band shading, motor-ratio inset.
- **geometric_mediation_path_diagram** (`conceptual`) — 3-node DAG
  with bootstrap-CI edge annotations and mediation verdict.
- **shared_manifold_scatter_with_residuals** (`scatter_collapse`) —
  central scatter + shared LOESS + marginal residual histograms + ANCOVA pill.

## v1.2.0-beta-biophysics_scaling — Wave 1 (substrate, +4)

Opens the `biophysics_scaling` beta expansion pack. Lands the shared
sub-contract module (`_shared.py` with 11 nested Pydantic sub-contracts),
a new `core/tost_bounds_utility.py`, and 4 substrate recipes that close
the module's scale-aware effect-size + equivalence + censoring +
validation-contract gap. biophysics_scaling expands from 15 to 19
recipes; total catalog 328 → 332.

- **hierarchical_effect_size_ladder** (`coef_forest`) — stratified
  effect-size forest over polymer / network / territory / geometry /
  whole-cell scales; two markers per feature (whole-cell vs
  protrusion-internal); outcome coded by TOST zone.
- **equivalence_forest_with_tost_bounds** (`coef_forest`) — feature
  forest with shaded TOST zone; three-colour outcome coding
  (significant / null-accepting / equivocal); optional per-feature N.
- **pre_registered_censoring_mode_grid** (`matrix`) — feature × mode
  traffic-light audit of direction × significance survival across
  pre-registered quality-gating modes.
- **forward_simulation_validation_contract** (`coef_forest`) — n-metric
  parameter-sufficiency audit; empirical medians normalized in
  simulated-CI units so metrics plot on a shared axis; +/- verdict
  glyph per (metric, group).

**Aesthetic change (isolated to this modality):**
`BiophysicsScalingAesthetic` subclasses `ModalityAesthetic` with an
`outcome_palette: dict[str, str]` field (default blue / green / grey).
Zero changes to `core/aesthetic_base.py` and no impact on other
modalities.

## v1.1.0-s20 — cryoem_and_structure hydration (+9 Path 2, FINAL)

Final session of the v1.1 hydration. Expands cryoem_and_structure
from 6 to 15 recipes:

- **b_factor_distribution_by_chain** — per-chain B-factor ridges.
- **conformational_ensemble_rmsf** — per-residue RMSF with SS tracks.
- **docking_pose_score_vs_rmsd** — funnel diagnostic with Spearman ρ.
- **contact_map_with_secondary_structure** — residue × residue
  contact imshow with SS tracks.
- **surface_electrostatics_colormap** — 2-D potential projection with
  ±1 kT/e contours.
- **interface_area_vs_affinity** — BSA × Kd log-log scatter.
- **domain_motion_decomposition** — normal-mode variance with
  cumulative-variance line.
- **hydrogen_bond_network_diagram** — radial H-bond network with
  occupancy-scaled lines.
- **motion_correction_shift_vector** — cumulative per-frame shift
  trajectory with drift metrics.

**After merge: `v1.1.0` final tag + closeout.**

## v1.1.0-s19 — clinical_cohort hydration (+9 Path 2, in progress)

Plan-vs-reality: coordinator listed v1.0=3, actual=6 (four seeds
already shipped). Path 2 lands +9 to hit 15-target. Expands
clinical_cohort from 6 to 15 recipes:

- **roc_with_cutoff_optimization** — ROC curve with Youden star,
  AUC bootstrap CI, sensitivity/specificity callout.
- **calibration_plot_with_hl_test** — decile observed vs predicted
  with y=x line and Hosmer-Lemeshow χ² p verdict.
- **decision_curve_analysis** — net-benefit vs threshold for model
  / treat-all / treat-none, with dominance-range callout.
- **competing_risks_cumulative_incidence** — per-cause CIF with
  Gray's test verdict.
- **hazard_ratio_over_time_smoothed** — HR(t) with 95 % band +
  Schoenfeld PH-violation verdict.
- **risk_score_discrimination_ladder** — event rate per risk-score
  tier with monotonicity + p-for-trend.
- **number_needed_to_treat_forest** — subgroup NNT ± CI with
  best/worst callouts.
- **propensity_score_balance_diagnostic** — before / after SMD
  paired forest with balance band.
- **adverse_event_incidence_bar** — per-AE arm-A vs arm-B bars with
  RR annotation and serious-event `!` markers.

## v1.1.0-s18 — meta_and_diagnostic hydration (+11, in progress)

Expands meta_and_diagnostic from 4 to 15 recipes:

- **prisma_flow_diagram** — PRISMA-2020 record-flow with main +
  excluded boxes and transitions.
- **effect_size_funnel_plot** — ES × SE funnel with 95 % cone and
  Egger's test verdict.
- **heterogeneity_forest** — per-study ES forest with pooled diamond
  and I² / τ² / Q in title.
- **sensitivity_leave_one_out** — LOO pooled-without-k forest with
  flagged-study callouts.
- **data_quality_heatmap** — per-sample × QC metric z-score heatmap
  with per-cell threshold-fail overlay.
- **missingness_upset** — intersection-dot UpSet view of
  co-missingness with per-set count bars.
- **outlier_detection_scatter** — 2-D Mahalanobis outlier detection
  with flagged X markers.
- **retention_vs_attrition_sankey** — cohort flow with per-stage
  retention bars and attrition tabs.
- **replication_retrospective_matrix** — study × attempt success
  grid with ES overlay.
- **reproducibility_correlogram** — replicate × replicate r heatmap
  with group-coded tick labels.
- **batch_effect_diagnostic_pca** — PC1 × PC2 per-batch ellipses with
  a batch-clustering-score verdict.

## v1.1.0-s17 — grant_and_conceptual hydration (+9, in progress)

Expands grant_and_conceptual from 6 to 15 recipes:

- **research_aims_pyramid** — hierarchical objective → aims →
  sub-questions card stack.
- **methods_pipeline_flow** — strictly linear input → steps → output
  with arrow connectors.
- **milestone_vs_risk_matrix** — 2×2 probability × impact with per-
  milestone tiles and risk-rated borders.
- **innovation_positioning_quadrant** — novelty × feasibility 2×2 with
  competitor scatter and starred our-proposal marker.
- **cost_by_work_package_bar** — per-WP stacked horizontal bars by
  cost category with grand-total callout.
- **ethics_and_impact_block** — two-column ETHICS / IMPACT panel with
  sub-section cards + bullets.
- **interdisciplinary_contribution_spider** — radar of discipline
  coverage with optional reference polygon.
- **team_network_graph** — institutional-sector radial consortium
  graph with collaboration edges.
- **deliverables_timeline** — per-WP lane with angled D-ID markers,
  status-coloured rings, year dividers.

## v1.1.0-s16 — spatial_statistics hydration (+9 Path 2, in progress)

Plan-vs-reality: coordinator listed v1.0=4, actual=6 (two seeds
already shipped). Path 2 lands +9 to hit 15-target. Expands
spatial_statistics from 6 to 15 recipes:

- **clark_evans_aggregation_bar** — per-condition CE index ± CI with
  CSR reference and clustered / random / dispersed colour coding.
- **f_function_empty_space** — F(r) vs analytical CSR reference +
  envelope, clustered / dispersed interpretation pill.
- **spatial_covariogram** — C(h) with exponential fit, nugget / sill /
  range annotations.
- **lisa_cluster_map** — per-point HH / HL / LH / LL classification
  with HH-minus-LL density overlay.
- **bivariate_pair_correlation** — g_12(r) with signed fill, peak +
  trough markers.
- **voronoi_area_distribution** — log-space ridge stack of per-
  condition area distributions.
- **co_occurrence_significance_matrix** — type × type z-score matrix
  with star-significance overlay and strongest-pair callouts.
- **quadrat_count_chisq** — Pearson residual heatmap with counts,
  χ² / df / p verdict.
- **spatial_permutation_null_distribution** — null + alternative
  ridges with observed statistic line and empirical p.

## v1.1.0-s15 — diffusion_and_tracking hydration (+10, in progress)

Expands diffusion_and_tracking from 5 to 15 recipes:

- **msd_anomalous_exponent_fit** — per-track α × D with representative
  MSD fit inset.
- **track_length_distribution** — per-condition CCDF of track duration
  with censoring marker.
- **jump_distance_van_hove** — P(|Δr|, Δt) stacked by lag, Gaussian
  reference, α₂ non-Gaussian parameter.
- **track_spaghetti_plot_colored_by_state** — per-segment LineCollection
  state colouring with start/end markers.
- **hmm_state_dwell_distribution** — per-state dwell ridges with
  exponential references and mean markers.
- **displacement_vs_state_residence** — state × residence-bin heatmap
  of median |Δr| with per-row trend summary.
- **diffusion_coefficient_heatmap_spatial** — D(x,y) pcolormesh with
  quartile contour overlay.
- **track_directionality_polar** — polar histogram with isotropic
  reference, mean direction and Rayleigh r.
- **ensemble_vs_time_averaged_msd** — EA-MSD line, TA-MSD cloud and
  EB(τ) ergodicity-breaking callout.
- **confinement_radius_vs_time** — per-track R_conf(t) mean ± 95 % CI
  per condition.

## v1.1.0-s14 — biophysics_scaling hydration (+10, in progress)

Expands biophysics_scaling from 5 to 15 recipes:

- **log_log_with_theory_line** — data vs theory-predicted slope with
  residuals-from-theory inset.
- **universality_class_comparison** — 2-3 candidate universality curves
  with per-class RMS residual bars.
- **fractal_dimension_scaling** — box-counting N(L) ~ L^D_f with local
  D_f(L) window inset.
- **stress_strain_regime_map** — σ-ε with elastic/plastic/failure bands,
  yield/ultimate markers, Young's-modulus inset.
- **knudsen_reynolds_regime_diagram** — Kn × Re regime grid with
  continuum/slip/transition/free-molecular bands.
- **energy_landscape_1d_cartoon** — schematic U(x) with wells, barriers,
  k_B T scale bar, transition arrows.
- **scaling_exponent_ci_forest** — per-study α ± CI forest with
  theoretical reference line.
- **characteristic_time_vs_control** — τ(p) critical divergence or
  Arrhenius fit.
- **pi_group_sensitivity_bar** — Buckingham Π-group variance
  contribution ranking.
- **crossover_scaling_diagnostic** — two-slope piecewise power law with
  crossover ξ + local-slope inset.

## v1.1.0-s13 — network_and_pathway hydration (+10, in progress)

Expands network_and_pathway from 5 to 15 recipes:

- **directed_network_force_layout** — directed graph with arrowed
  edges, degree-radial layout.
- **hub_gene_radial** — hub-centre + neighbours on a circle.
- **ppi_seed_expansion** — seed + first-neighbour two-shell layout.
- **pathway_crosstalk_matrix** — pathway × pathway crosstalk.
- **kegg_overlay_enrichment** — KEGG schematic with p-value coloring.
- **regulon_activity_heatmap** — TF × sample activity.
- **module_preservation_zsummary** — WGCNA Z-ladder with tiers.
- **centrality_vs_effect_scatter** — centrality vs effect OLS.
- **subnetwork_comparison_diff** — Δ-weight gain/loss graph.
- **pathway_flux_streamgraph** — normalised flux(t) stack.

## v1.1.0-s12 — dose_response_pharmacology hydration (+10, in progress)

Expands dose_response_pharmacology from 5 to 15 recipes:

- **dose_response_sex_stratified** — F/M Hill curves with interaction p.
- **dose_response_time_matrix** — conc × time effect heatmap.
- **response_rebound_kinetics** — washout recovery with rebound peak.
- **ic50_vs_target_affinity_scatter** — Ki vs IC50 log-log concordance.
- **selectivity_index_tornado** — off-target fold-IC50 tornado.
- **dose_normalized_ec50_forest** — x-fold EC50 vs lead.
- **synergy_score_bliss_loewe** — Bliss vs Loewe scatter with quadrants.
- **pharmacophore_activity_heatmap** — feature × compound SAR.
- **compound_cluster_structure_activity** — PCA + cluster activity.
- **polypharmacology_radar** — multi-compound target radar.

## v1.1.0-s11 — single_cell_embeddings hydration (+8, in progress)

Expands single_cell_embeddings from 7 to 15 recipes:

- **umap_density_contour_overlay** — per-condition density contours
  on shared UMAP with mean-shift arrows.
- **rare_population_highlighted_umap** — spotlight grammar: bulk
  greyed, rare pop with hull + median + %.
- **cluster_proportion_stacked_by_sample** — per-sample stacked
  bars with condition-group strip.
- **trajectory_branching_force_directed** — branching trajectory
  with Circle-patch branch points and endpoint labels.
- **per_cluster_marker_heatmap** — z-scored gene × cluster heatmap
  with origin-cluster strip.
- **pseudotime_gene_expression_trajectory** — gene(pseudotime)
  smoothed curves with CI bands and peak-order footer.
- **rnavelocity_arrow_field** — RNA-velocity quiver field with
  faint speed underlay.
- **receptor_ligand_signaling_dotplot** — (sender × receiver) ×
  LR-pair dotplot.

## v1.1.0-s10 — calcium_signaling hydration (+9, in progress)

Expands calcium_signaling from 6 to 15 recipes:

- **calcium_event_amplitude_distribution** — per-condition ΔF/F peak
  ridge plot.
- **calcium_event_onset_alignment** — PETH rate curves with CI band.
- **population_synchronization_timeline** — scalar sync(t) with
  threshold shading.
- **network_burst_detection_overlay** — raster+rate with shaded
  burst epochs.
- **calcium_wave_speed_map** — per-pixel wave-speed magma map.
- **single_cell_calcium_landscape** — per-cell (freq, amp) scatter
  with density + hulls.
- **calcium_and_fret_joint_plot** — Ca × FRET joint scatter with
  marginals.
- **oscillation_frequency_polar** — dominant-phase polar scatter
  with mean resultant R.
- **stimulus_triggered_calcium_heatmap** — cell × time ΔF/F matrix
  sorted by peak latency.

## v1.1.0-s09 — omics_differential hydration (+6, in progress)

Expands omics_differential from 10 to 16 recipes:

- **proteome_volcano_labeled_pathways** — pathway-group coloured
  volcano with centroid labels per pathway.
- **effect_size_replicate_concordance** — rep1 vs rep2 log2FC with
  identity line, OLS fit and 95% LoA band.
- **shrinkage_estimate_scatter** — raw vs shrunken log2FC with
  shrinkage-ratio colormap.
- **contrast_overlap_euler** — area-proportional Euler circles
  with region counts and Jaccard callout.
- **rank_product_meta_analysis** — top-N 1/RP bars with
  permutation-FDR stars and per-study rank strip.
- **pathway_module_activity_heatmap** — module × sample activity
  heatmap with module / sample group annotation strips.

## v1.1.0-s08 — gillespie_stochastic hydration (+8, in progress)

Expands gillespie_stochastic from 7 to 15 recipes:

- **master_equation_steady_state** — analytic P(n) vs sampled
  histogram with KL + TV distance.
- **tau_leaping_comparison** — exact SSA vs τ-leap with inset
  residual and RMSE / speedup callouts.
- **mean_first_passage_time_matrix** — pairwise MFPT heatmap with
  fastest-pair footer.
- **fisher_information_parameter_estimation** — K × K FIM with
  condition number and best / worst-identified directions.
- **burst_size_distribution** — burst-count PMF with geometric +
  negative-binomial fits.
- **extinction_probability_vs_parameter** — P_ext(θ) curves per
  initial state with tipping-point markers.
- **autocorrelation_of_trajectories** — per-state ACF with
  exponential fits and 1/e reference.
- **stochastic_resonance_signature** — SNR vs σ bell-curve with
  parabolic-fit peak.

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
