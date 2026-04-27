# Recipes by scientific question

Recipes from `recipes_by_modality.md`, grouped by the *claim* they help
you make. Useful for the bootstrap skill when a user says "I want a
figure that shows <X>" without naming a modality.

> **Note:** This question-grouped index was seeded at the 18-recipe
> milestone and has not kept pace with subsequent session additions.
> It will be fully regenerated from the catalog in a future batch. In
> the meantime the *by-modality* index is the authoritative catalog
> for the current 137 + 6 recipes.

## Intravital-imaging beta-pack Wave 4 additions (v1.3.0-beta-intravital_imaging-w4)

- **Where on a cell does the biosensor signal peak above baseline, and does the spatial pattern differ between conditions?** → [`intravital_imaging.biosensor_activation_field_per_cell`](gallery/intravital_imaging/biosensor_activation_field_per_cell.png)
- **How does the biosensor plateau response scale with cue dose, and what is the EC50 per condition?** → [`intravital_imaging.biosensor_dose_response_curve`](gallery/intravital_imaging/biosensor_dose_response_curve.png)
- **After bi-exponential photobleach correction, are the biosensor traces flat over the recording duration?** → [`intravital_imaging.photobleaching_corrected_intensity_traces`](gallery/intravital_imaging/photobleaching_corrected_intensity_traces.png)
- **Per (decoded state, condition), what is the dominant frequency in tip-velocity power spectral density, and does it differ between conditions?** → [`intravital_imaging.kinematic_power_spectral_density`](gallery/intravital_imaging/kinematic_power_spectral_density.png)
- **Does the decoded state stream Granger-cause velocity (and length-rate), and does the directionality hold per condition?** → [`intravital_imaging.transfer_entropy_state_to_velocity_matrix`](gallery/intravital_imaging/transfer_entropy_state_to_velocity_matrix.png)
- **Across (dose, time after exposure), how does response evolve, and is the response sustained or transient?** → [`intravital_imaging.dose_x_time_response_matrix`](gallery/intravital_imaging/dose_x_time_response_matrix.png)
- **Do per-cell kinematic feature vectors cluster by decoded state when projected to 2-D via Laplacian eigenmaps?** → [`intravital_imaging.state_kinematic_spectral_embedding`](gallery/intravital_imaging/state_kinematic_spectral_embedding.png)
- **Per feature, does the condition pass the equivalence test (observed |effect| < margin), and on which axes does the condition escape equivalence?** → [`intravital_imaging.equivalence_tost_radar_per_condition`](gallery/intravital_imaging/equivalence_tost_radar_per_condition.png)
- **Are imaging cohorts balanced on baseline characteristics, and on which features does standardised mean difference (SMD) cross the 0.1 / 0.2 reviewer-proof thresholds?** → [`intravital_imaging.cohort_baseline_balance_table_matrix`](gallery/intravital_imaging/cohort_baseline_balance_table_matrix.png)
- **Per stratum and model, is the P(commit) classifier well calibrated (Brier score with 95 % CI; reliability slope near 1, intercept near 0)?** → [`intravital_imaging.model_calibration_brier_forest`](gallery/intravital_imaging/model_calibration_brier_forest.png)

## Intravital-imaging beta-pack Wave 3 additions (v1.3.0-beta-intravital_imaging-w3)

- **At time t after launch, what fraction of protrusions remain uncommitted, and how does the curve differ between conditions?** → [`intravital_imaging.protrusion_commitment_survival`](gallery/intravital_imaging/protrusion_commitment_survival.png)
- **Per condition, how does the commitment hazard h(τ) depend on age-in-state (τ since launch)?** → [`intravital_imaging.commitment_hazard_with_age`](gallery/intravital_imaging/commitment_hazard_with_age.png)
- **Where on (length L, mean velocity v_bar) phase space does protrusion commitment happen, and what is the fitted iso-prob boundary?** → [`intravital_imaging.commitment_phase_diagram`](gallery/intravital_imaging/commitment_phase_diagram.png)
- **After cue onset, how does the chemotaxis index CI(t) = ⟨cos(θ − cue)⟩ evolve per condition?** → [`intravital_imaging.chemotaxis_index_trajectory`](gallery/intravital_imaging/chemotaxis_index_trajectory.png)
- **What is the directional persistence time τ_p of cell heading, computed via heading autocorrelation C(τ)?** → [`intravital_imaging.directional_persistence_autocorr`](gallery/intravital_imaging/directional_persistence_autocorr.png)
- **Per (decoded state, condition) cell, what are the OU heading dynamics parameters (τ, σ)?** → [`intravital_imaging.ornstein_uhlenbeck_fit_per_state`](gallery/intravital_imaging/ornstein_uhlenbeck_fit_per_state.png)
- **Does protrusion length-rate lead or lag tip velocity, and does the relationship differ between conditions?** → [`intravital_imaging.speed_commitment_coupling`](gallery/intravital_imaging/speed_commitment_coupling.png)
- **Are committed protrusions cue-aligned, and does the association strength differ between conditions?** → [`intravital_imaging.commitment_vs_chemotaxis_contingency`](gallery/intravital_imaging/commitment_vs_chemotaxis_contingency.png)
- **When two protrusions emerge concurrently, what is the winner-vs-runner-up dynamic and the winning margin?** → [`intravital_imaging.protrusion_dominance_race_winner`](gallery/intravital_imaging/protrusion_dominance_race_winner.png)
- **How does the cue-response latency τ scale with cue dose, and does the dose-response differ between conditions?** → [`intravital_imaging.cue_response_dose_latency`](gallery/intravital_imaging/cue_response_dose_latency.png)
- **For protrusions whose heading aligns with the cue vs not, how do their tip velocity distributions differ?** → [`intravital_imaging.aligned_vs_unaligned_velocity_split`](gallery/intravital_imaging/aligned_vs_unaligned_velocity_split.png)
- **Within a cell ROI window, does the tip-centroid pattern cluster, repel, or follow CSR (Ripley K with edge correction)?** → [`intravital_imaging.tip_ripleys_k_in_window`](gallery/intravital_imaging/tip_ripleys_k_in_window.png)
- **Within a cell ROI window, what is the pair correlation g(r) of tip centroids vs the CSR baseline g(r) = 1?** → [`intravital_imaging.tip_pair_correlation_in_window`](gallery/intravital_imaging/tip_pair_correlation_in_window.png)
- **Per cell, how is branch-order distributed (root, primary, secondary, …), and does the topology differ between conditions?** → [`intravital_imaging.branch_order_topology_per_cell`](gallery/intravital_imaging/branch_order_topology_per_cell.png)
- **Along a protrusion, how does curvature κ(s, t) propagate over time (does the max-κ ridge migrate)?** → [`intravital_imaging.curvature_along_protrusion_kymograph`](gallery/intravital_imaging/curvature_along_protrusion_kymograph.png)
- **Where do tips push hardest, given an order-of-magnitude Stokes drag estimate F = 6π η r v?** → [`intravital_imaging.viscous_drag_tip_force_map`](gallery/intravital_imaging/viscous_drag_tip_force_map.png)

## Intravital-imaging beta-pack Wave 2 additions (v1.3.0-beta-intravital_imaging-w2)

- **Where do tips travel, and how do their decoded states map onto the spatial trajectory?** → [`intravital_imaging.state_decoded_tip_track_field`](gallery/intravital_imaging/state_decoded_tip_track_field.png)
- **How do protrusion shapes (polylines of arbitrary length) differ across decoded states?** → [`intravital_imaging.state_decoded_protrusion_polyline_field`](gallery/intravital_imaging/state_decoded_protrusion_polyline_field.png)
- **Across cells, how does the posterior probability γ(t) of each decoded state evolve over time?** → [`intravital_imaging.posterior_state_probability_ribbons`](gallery/intravital_imaging/posterior_state_probability_ribbons.png)
- **What are the per-step (or per-switch) transition probabilities between decoded latent states?** → [`intravital_imaging.state_transition_kernel_matrix`](gallery/intravital_imaging/state_transition_kernel_matrix.png)
- **Per condition, how does the cohort-level state-occupancy fraction evolve over time?** → [`intravital_imaging.state_occupancy_stacked_area`](gallery/intravital_imaging/state_occupancy_stacked_area.png)
- **Per cell, when do entries and exits between decoded states happen, and which cells dominate which state?** → [`intravital_imaging.state_entry_exit_raster`](gallery/intravital_imaging/state_entry_exit_raster.png)
- **Per decoded state, what is the tip MSD(τ) computed over same-state epochs, and what is the diffusion exponent α?** → [`intravital_imaging.state_conditional_tip_msd`](gallery/intravital_imaging/state_conditional_tip_msd.png)
- **How long does a freshly nucleated protrusion take to commit?** → [`intravital_imaging.launch_to_commitment_latency`](gallery/intravital_imaging/launch_to_commitment_latency.png)
- **How long after cue onset does a cell's heading first align with the cue direction?** → [`intravital_imaging.cue_to_reorientation_latency`](gallery/intravital_imaging/cue_to_reorientation_latency.png)
- **How long after cue onset does the cell's net projected displacement along the cue exceed a threshold?** → [`intravital_imaging.cue_to_net_displacement_latency`](gallery/intravital_imaging/cue_to_net_displacement_latency.png)
- **Across the three canonical latencies and conditions, which latency is the chemotaxis bottleneck?** → [`intravital_imaging.latency_decomposition_forest`](gallery/intravital_imaging/latency_decomposition_forest.png)

## Intravital-imaging beta-pack Wave 1 additions (v1.3.0-beta-intravital_imaging-w1)

- **Per decoded latent state, how are sojourn dwells distributed, and are they consistent with the HMM geometric assumption?** → [`intravital_imaging.dwell_time_distribution_per_state`](gallery/intravital_imaging/dwell_time_distribution_per_state.png)
- **Per decoded state, how does the sojourn survival S(tau) behave, and is it consistent with HMM (geometric / log-linear)?** → [`intravital_imaging.sojourn_survival_per_state`](gallery/intravital_imaging/sojourn_survival_per_state.png)
- **Per decoded state, does the switch-out hazard depend on age-in-state (ramp / peak = HSMM) or is it flat (HMM-compatible)?** → [`intravital_imaging.hazard_rate_per_state`](gallery/intravital_imaging/hazard_rate_per_state.png)
- **Per decoded state, what kinematic signature (velocity, length-rate, curvature, turning-angle, …) characterises the state?** → [`intravital_imaging.emission_distribution_per_state`](gallery/intravital_imaging/emission_distribution_per_state.png)
- **Across strata, does HSMM (semi-Markov, age-dependent dwell) beat HMM (Markov, geometric dwell) by AIC / BIC / CV log-lik?** → [`intravital_imaging.hmm_vs_hsmm_model_comparison`](gallery/intravital_imaging/hmm_vs_hsmm_model_comparison.png)

## Biophysics-scaling beta-pack Wave 4 additions (v1.2.0-beta-biophysics_scaling-w4)

- **Does the regime classification at this phase corner hold across a local perturbation neighborhood of simulation parameters?** → [`biophysics_scaling.robustness_neighborhood_phase_corner`](gallery/biophysics_scaling/robustness_neighborhood_phase_corner.png)
- **Across (width, alpha) parameter space, where do the genotypes live, where do regime boundaries sit, and where would a model-hypothesised rescue zone be?** → [`biophysics_scaling.width_alpha_regime_phase_map`](gallery/biophysics_scaling/width_alpha_regime_phase_map.png)

## Biophysics-scaling beta-pack Wave 3 additions (v1.2.0-beta-biophysics_scaling-w3)

- **Per genotype, what fraction of supported filament segments exceed the Euler buckling length L_crit?** → [`biophysics_scaling.euler_critical_length_crossing_distribution`](gallery/biophysics_scaling/euler_critical_length_crossing_distribution.png)
- **How does the per-group confinement free-energy cost F_conf(w) depend on protrusion width, and where do the curves diverge?** → [`biophysics_scaling.confinement_free_energy_vs_width_curve`](gallery/biophysics_scaling/confinement_free_energy_vs_width_curve.png)
- **Does the actin × MT curvature cross-correlation differ between compartments, and does an emergent peak appear in the protrusion-internal compartment?** → [`biophysics_scaling.compartment_split_curvature_crosscorr`](gallery/biophysics_scaling/compartment_split_curvature_crosscorr.png)
- **Are LI protrusion microtubules bowed (increased z-span with preserved local variance) or diffusely thickened?** → [`biophysics_scaling.xz_microtubule_bowing_z_span`](gallery/biophysics_scaling/xz_microtubule_bowing_z_span.png)
- **Does the protrusion alignment α scale with width differently per genotype, and where is the relationship buffered vs unbuffered?** → [`biophysics_scaling.width_alignment_buffered_unbuffered_interaction`](gallery/biophysics_scaling/width_alignment_buffered_unbuffered_interaction.png)
- **Across cells, do the three colocalization metrics (Manders M1, Pearson r, Spearman ρ) move together, and does the genotype shift the consensus level?** → [`biophysics_scaling.per_cell_colocalization_parallel_coordinates`](gallery/biophysics_scaling/per_cell_colocalization_parallel_coordinates.png)
- **Along the ordered fixed-cell trajectory, where do the per-group curves diverge (checkpoint location)?** → [`biophysics_scaling.ordered_trajectory_checkpoint_divergence`](gallery/biophysics_scaling/ordered_trajectory_checkpoint_divergence.png)
- **Along the signed actin-frontier axis, how do tip states (S vs non-S) distribute per cell?** → [`biophysics_scaling.s_state_frontier_tip_raster`](gallery/biophysics_scaling/s_state_frontier_tip_raster.png)

## Biophysics-scaling beta-pack Wave 2 additions (v1.2.0-beta-biophysics_scaling-w2)

- **Per feature, how does the whole-cell effect size compare to the protrusion-internal one?** → [`biophysics_scaling.compartment_paired_delta_scatter`](gallery/biophysics_scaling/compartment_paired_delta_scatter.png)
- **Where across the scale hierarchy do the significant / null-accepting / equivocal feature outcomes concentrate?** → [`biophysics_scaling.feature_outcome_sankey_sig_vs_null`](gallery/biophysics_scaling/feature_outcome_sankey_sig_vs_null.png)
- **Which features drive genotype classification (RF importance) and from which organizational scale do they come?** → [`biophysics_scaling.random_forest_importance_by_scale`](gallery/biophysics_scaling/random_forest_importance_by_scale.png)
- **Where across the organizational hierarchy does the genotype signal account for the most variance (PERMANOVA R²)?** → [`biophysics_scaling.scale_stratified_permanova_r2`](gallery/biophysics_scaling/scale_stratified_permanova_r2.png)
- **Across compartments, does polymer Lp lie inside the pre-registered equivalence zone or outside it?** → [`biophysics_scaling.persistence_length_lp_with_equivalence_bounds`](gallery/biophysics_scaling/persistence_length_lp_with_equivalence_bounds.png)
- **Does the active-gel PSD differ between groups, and does the motor band show a genotype-dependent deviation?** → [`biophysics_scaling.psd_active_gel_overlay_with_motor_inset`](gallery/biophysics_scaling/psd_active_gel_overlay_with_motor_inset.png)
- **Does the putative mediator absorb the direct effect of predictor on outcome (path diagram with bootstrap CIs)?** → [`biophysics_scaling.geometric_mediation_path_diagram`](gallery/biophysics_scaling/geometric_mediation_path_diagram.png)
- **Do two groups share the same (x, y) manifold after accounting for x, or does a residual group effect remain?** → [`biophysics_scaling.shared_manifold_scatter_with_residuals`](gallery/biophysics_scaling/shared_manifold_scatter_with_residuals.png)

## Biophysics-scaling beta-pack Wave 1 additions (v1.2.0-beta-biophysics_scaling-w1)

- **Across the polymer → network → territory → geometry → whole-cell hierarchy, how large are the per-feature effects and how do they split across compartments?** → [`biophysics_scaling.hierarchical_effect_size_ladder`](gallery/biophysics_scaling/hierarchical_effect_size_ladder.png)
- **Which features lie inside the pre-registered TOST equivalence zone (null-accepting), which sit outside it (significant), and which straddle a bound (equivocal)?** → [`biophysics_scaling.equivalence_forest_with_tost_bounds`](gallery/biophysics_scaling/equivalence_forest_with_tost_bounds.png)
- **Does each feature's conclusion survive all four pre-registered censoring modes (permissive, standard, quality-gated, strict)?** → [`biophysics_scaling.pre_registered_censoring_mode_grid`](gallery/biophysics_scaling/pre_registered_censoring_mode_grid.png)
- **Across n metrics × m groups, does each empirical median lie inside its forward-simulation CI (parameter-sufficiency contract)?** → [`biophysics_scaling.forward_simulation_validation_contract`](gallery/biophysics_scaling/forward_simulation_validation_contract.png)

## CryoEM-and-structure catch-up (v1.1.0-s20 additions)

- **How do B-factor distributions compare between chains?** → [`cryoem_and_structure.b_factor_distribution_by_chain`](gallery/cryoem_and_structure/b_factor_distribution_by_chain.png)
- **Which residues have the highest RMS fluctuation in the ensemble?** → [`cryoem_and_structure.conformational_ensemble_rmsf`](gallery/cryoem_and_structure/conformational_ensemble_rmsf.png)
- **Does the docking score form a funnel around the native pose?** → [`cryoem_and_structure.docking_pose_score_vs_rmsd`](gallery/cryoem_and_structure/docking_pose_score_vs_rmsd.png)
- **Which residue pairs form contacts, in context of secondary structure?** → [`cryoem_and_structure.contact_map_with_secondary_structure`](gallery/cryoem_and_structure/contact_map_with_secondary_structure.png)
- **Where are the positive / negative patches on the molecular surface?** → [`cryoem_and_structure.surface_electrostatics_colormap`](gallery/cryoem_and_structure/surface_electrostatics_colormap.png)
- **Does buried surface area correlate with binding affinity?** → [`cryoem_and_structure.interface_area_vs_affinity`](gallery/cryoem_and_structure/interface_area_vs_affinity.png)
- **Which normal modes capture most concerted-motion variance?** → [`cryoem_and_structure.domain_motion_decomposition`](gallery/cryoem_and_structure/domain_motion_decomposition.png)
- **Around a key residue, what is the H-bond network with occupancies?** → [`cryoem_and_structure.hydrogen_bond_network_diagram`](gallery/cryoem_and_structure/hydrogen_bond_network_diagram.png)
- **How large and correlated were the motion-correction shifts?** → [`cryoem_and_structure.motion_correction_shift_vector`](gallery/cryoem_and_structure/motion_correction_shift_vector.png)

## Clinical-cohort catch-up (v1.1.0-s19 additions)

- **At what cutoff is sens+spec maximal (Youden) and what is AUC?** → [`clinical_cohort.roc_with_cutoff_optimization`](gallery/clinical_cohort/roc_with_cutoff_optimization.png)
- **Is the model calibrated (Hosmer-Lemeshow)?** → [`clinical_cohort.calibration_plot_with_hl_test`](gallery/clinical_cohort/calibration_plot_with_hl_test.png)
- **Does the model's net benefit beat treat-all/treat-none?** → [`clinical_cohort.decision_curve_analysis`](gallery/clinical_cohort/decision_curve_analysis.png)
- **With competing risks, what are per-cause CIFs (Gray's test)?** → [`clinical_cohort.competing_risks_cumulative_incidence`](gallery/clinical_cohort/competing_risks_cumulative_incidence.png)
- **Does the hazard ratio change over follow-up (PH check)?** → [`clinical_cohort.hazard_ratio_over_time_smoothed`](gallery/clinical_cohort/hazard_ratio_over_time_smoothed.png)
- **Does the event rate rise monotonically across risk-score tiers?** → [`clinical_cohort.risk_score_discrimination_ladder`](gallery/clinical_cohort/risk_score_discrimination_ladder.png)
- **What is the NNT across subgroups (with CIs)?** → [`clinical_cohort.number_needed_to_treat_forest`](gallery/clinical_cohort/number_needed_to_treat_forest.png)
- **Did propensity-score matching achieve balance (|SMD|<0.1)?** → [`clinical_cohort.propensity_score_balance_diagnostic`](gallery/clinical_cohort/propensity_score_balance_diagnostic.png)
- **Per AE, how do arm incidences compare (with RR)?** → [`clinical_cohort.adverse_event_incidence_bar`](gallery/clinical_cohort/adverse_event_incidence_bar.png)

## Meta-and-diagnostic catch-up (v1.1.0-s18 additions)

- **How many records survive each stage of a systematic review?** → [`meta_and_diagnostic.prisma_flow_diagram`](gallery/meta_and_diagnostic/prisma_flow_diagram.png)
- **Is there publication-bias asymmetry in a meta-analysis funnel?** → [`meta_and_diagnostic.effect_size_funnel_plot`](gallery/meta_and_diagnostic/effect_size_funnel_plot.png)
- **What is the pooled ES and how heterogeneous (I², τ²) are studies?** → [`meta_and_diagnostic.heterogeneity_forest`](gallery/meta_and_diagnostic/heterogeneity_forest.png)
- **Does any single study drive the pooled meta-analysis effect (LOO)?** → [`meta_and_diagnostic.sensitivity_leave_one_out`](gallery/meta_and_diagnostic/sensitivity_leave_one_out.png)
- **Which sample × QC-metric cells fail a threshold?** → [`meta_and_diagnostic.data_quality_heatmap`](gallery/meta_and_diagnostic/data_quality_heatmap.png)
- **Which combinations of variables are co-missing (UpSet view)?** → [`meta_and_diagnostic.missingness_upset`](gallery/meta_and_diagnostic/missingness_upset.png)
- **Which 2-D samples are Mahalanobis outliers?** → [`meta_and_diagnostic.outlier_detection_scatter`](gallery/meta_and_diagnostic/outlier_detection_scatter.png)
- **How do participants flow through enrolment / attrition stages?** → [`meta_and_diagnostic.retention_vs_attrition_sankey`](gallery/meta_and_diagnostic/retention_vs_attrition_sankey.png)
- **Across study × replication attempt, which succeeded?** → [`meta_and_diagnostic.replication_retrospective_matrix`](gallery/meta_and_diagnostic/replication_retrospective_matrix.png)
- **How correlated are replicate runs, and do they form blocks?** → [`meta_and_diagnostic.reproducibility_correlogram`](gallery/meta_and_diagnostic/reproducibility_correlogram.png)
- **Do samples cluster by batch rather than condition?** → [`meta_and_diagnostic.batch_effect_diagnostic_pca`](gallery/meta_and_diagnostic/batch_effect_diagnostic_pca.png)

## Grant-and-conceptual catch-up (v1.1.0-s17 additions)

- **How do specific aims nest under an overarching objective?** → [`grant_and_conceptual.research_aims_pyramid`](gallery/grant_and_conceptual/research_aims_pyramid.png)
- **What are the sequential methods-pipeline steps?** → [`grant_and_conceptual.methods_pipeline_flow`](gallery/grant_and_conceptual/methods_pipeline_flow.png)
- **Which milestones are high-risk and high-impact?** → [`grant_and_conceptual.milestone_vs_risk_matrix`](gallery/grant_and_conceptual/milestone_vs_risk_matrix.png)
- **Where does our proposal sit on the novelty × feasibility plane?** → [`grant_and_conceptual.innovation_positioning_quadrant`](gallery/grant_and_conceptual/innovation_positioning_quadrant.png)
- **How is the budget distributed across WPs and cost categories?** → [`grant_and_conceptual.cost_by_work_package_bar`](gallery/grant_and_conceptual/cost_by_work_package_bar.png)
- **What are the ethics safeguards and societal-impact pathways?** → [`grant_and_conceptual.ethics_and_impact_block`](gallery/grant_and_conceptual/ethics_and_impact_block.png)
- **How interdisciplinary is the proposal across fields?** → [`grant_and_conceptual.interdisciplinary_contribution_spider`](gallery/grant_and_conceptual/interdisciplinary_contribution_spider.png)
- **How do consortium partners connect (institution, role)?** → [`grant_and_conceptual.team_network_graph`](gallery/grant_and_conceptual/team_network_graph.png)
- **When does each deliverable land and in which WP?** → [`grant_and_conceptual.deliverables_timeline`](gallery/grant_and_conceptual/deliverables_timeline.png)

## Spatial-statistics catch-up (v1.1.0-s16 additions)

- **Is the point pattern clustered, random, or dispersed (CE index)?** → [`spatial_statistics.clark_evans_aggregation_bar`](gallery/spatial_statistics/clark_evans_aggregation_bar.png)
- **Is there more empty space than CSR predicts?** → [`spatial_statistics.f_function_empty_space`](gallery/spatial_statistics/f_function_empty_space.png)
- **What is the correlation length of a continuous spatial field?** → [`spatial_statistics.spatial_covariogram`](gallery/spatial_statistics/spatial_covariogram.png)
- **Where are local HH / LL / HL / LH tiles (LISA)?** → [`spatial_statistics.lisa_cluster_map`](gallery/spatial_statistics/lisa_cluster_map.png)
- **At what radii are two cell types co-clustered vs segregated?** → [`spatial_statistics.bivariate_pair_correlation`](gallery/spatial_statistics/bivariate_pair_correlation.png)
- **How are per-cell territory areas distributed across conditions?** → [`spatial_statistics.voronoi_area_distribution`](gallery/spatial_statistics/voronoi_area_distribution.png)
- **Which cell-type pairs significantly co-occur vs avoid?** → [`spatial_statistics.co_occurrence_significance_matrix`](gallery/spatial_statistics/co_occurrence_significance_matrix.png)
- **Is the point pattern non-uniform at the chosen quadrat scale?** → [`spatial_statistics.quadrat_count_chisq`](gallery/spatial_statistics/quadrat_count_chisq.png)
- **How significant is the observed statistic against a permutation null?** → [`spatial_statistics.spatial_permutation_null_distribution`](gallery/spatial_statistics/spatial_permutation_null_distribution.png)

## Diffusion-and-tracking catch-up (v1.1.0-s15 additions)

- **How is the per-track anomalous-diffusion exponent α distributed?** → [`diffusion_and_tracking.msd_anomalous_exponent_fit`](gallery/diffusion_and_tracking/msd_anomalous_exponent_fit.png)
- **How long do tracks persist across conditions, with acquisition censoring?** → [`diffusion_and_tracking.track_length_distribution`](gallery/diffusion_and_tracking/track_length_distribution.png)
- **Is P(Δr, Δt) Gaussian, or non-Gaussian at which lag?** → [`diffusion_and_tracking.jump_distance_van_hove`](gallery/diffusion_and_tracking/jump_distance_van_hove.png)
- **Where in raw trajectories do tracks switch state?** → [`diffusion_and_tracking.track_spaghetti_plot_colored_by_state`](gallery/diffusion_and_tracking/track_spaghetti_plot_colored_by_state.png)
- **How long do tracks dwell in each HMM state?** → [`diffusion_and_tracking.hmm_state_dwell_distribution`](gallery/diffusion_and_tracking/hmm_state_dwell_distribution.png)
- **Given state residence time, how does next-step displacement shift?** → [`diffusion_and_tracking.displacement_vs_state_residence`](gallery/diffusion_and_tracking/displacement_vs_state_residence.png)
- **Where in the field of view is diffusion fast vs slow?** → [`diffusion_and_tracking.diffusion_coefficient_heatmap_spatial`](gallery/diffusion_and_tracking/diffusion_coefficient_heatmap_spatial.png)
- **Is motion isotropic, or is there a preferred direction?** → [`diffusion_and_tracking.track_directionality_polar`](gallery/diffusion_and_tracking/track_directionality_polar.png)
- **Is motion ergodic — do EA-MSD and TA-MSD agree?** → [`diffusion_and_tracking.ensemble_vs_time_averaged_msd`](gallery/diffusion_and_tracking/ensemble_vs_time_averaged_msd.png)
- **Does a track's confinement radius evolve over time?** → [`diffusion_and_tracking.confinement_radius_vs_time`](gallery/diffusion_and_tracking/confinement_radius_vs_time.png)

## Biophysics-scaling catch-up (v1.1.0-s14 additions)

- **Is data consistent with a theoretically predicted scaling exponent?** → [`biophysics_scaling.log_log_with_theory_line`](gallery/biophysics_scaling/log_log_with_theory_line.png)
- **Which universality class best matches the data?** → [`biophysics_scaling.universality_class_comparison`](gallery/biophysics_scaling/universality_class_comparison.png)
- **What is the box-counting fractal dimension D_f of a structure?** → [`biophysics_scaling.fractal_dimension_scaling`](gallery/biophysics_scaling/fractal_dimension_scaling.png)
- **Where does material transition from elastic to plastic to failure?** → [`biophysics_scaling.stress_strain_regime_map`](gallery/biophysics_scaling/stress_strain_regime_map.png)
- **Which flow regime does my system occupy in Kn × Re?** → [`biophysics_scaling.knudsen_reynolds_regime_diagram`](gallery/biophysics_scaling/knudsen_reynolds_regime_diagram.png)
- **How does a 1-D energy landscape U(x) explain state lifetimes?** → [`biophysics_scaling.energy_landscape_1d_cartoon`](gallery/biophysics_scaling/energy_landscape_1d_cartoon.png)
- **How does the fitted scaling exponent α vary across studies?** → [`biophysics_scaling.scaling_exponent_ci_forest`](gallery/biophysics_scaling/scaling_exponent_ci_forest.png)
- **How does the characteristic time τ diverge near a critical point?** → [`biophysics_scaling.characteristic_time_vs_control`](gallery/biophysics_scaling/characteristic_time_vs_control.png)
- **Which Buckingham Π-group contributes most to the response variance?** → [`biophysics_scaling.pi_group_sensitivity_bar`](gallery/biophysics_scaling/pi_group_sensitivity_bar.png)
- **Does the data cross over between two power-law regimes at a scale ξ?** → [`biophysics_scaling.crossover_scaling_diagnostic`](gallery/biophysics_scaling/crossover_scaling_diagnostic.png)

## Network-and-pathway catch-up (v1.1.0-s13 additions)

- **What does a directed regulatory network look like with hubs highlighted?** → [`network_and_pathway.directed_network_force_layout`](gallery/network_and_pathway/directed_network_force_layout.png)
- **What are the hub's immediate neighbours and their edge weights?** → [`network_and_pathway.hub_gene_radial`](gallery/network_and_pathway/hub_gene_radial.png)
- **What does a seed + first-neighbour expansion look like?** → [`network_and_pathway.ppi_seed_expansion`](gallery/network_and_pathway/ppi_seed_expansion.png)
- **How do pathways cross-talk with each other?** → [`network_and_pathway.pathway_crosstalk_matrix`](gallery/network_and_pathway/pathway_crosstalk_matrix.png)
- **Which nodes in a KEGG pathway are enriched?** → [`network_and_pathway.kegg_overlay_enrichment`](gallery/network_and_pathway/kegg_overlay_enrichment.png)
- **How does each TF-regulon's activity vary across samples?** → [`network_and_pathway.regulon_activity_heatmap`](gallery/network_and_pathway/regulon_activity_heatmap.png)
- **How preserved is each module (Zsummary)?** → [`network_and_pathway.module_preservation_zsummary`](gallery/network_and_pathway/module_preservation_zsummary.png)
- **Do central nodes have the largest effect sizes?** → [`network_and_pathway.centrality_vs_effect_scatter`](gallery/network_and_pathway/centrality_vs_effect_scatter.png)
- **Which edges gain / lose weight between conditions?** → [`network_and_pathway.subnetwork_comparison_diff`](gallery/network_and_pathway/subnetwork_comparison_diff.png)
- **How does pathway-activity flux redistribute over time?** → [`network_and_pathway.pathway_flux_streamgraph`](gallery/network_and_pathway/pathway_flux_streamgraph.png)

## Dose-response pharmacology catch-up (v1.1.0-s12 additions)

- **Do male and female Hill curves differ?** → [`dose_response_pharmacology.dose_response_sex_stratified`](gallery/dose_response_pharmacology/dose_response_sex_stratified.png)
- **Over conc × time, when / where does the effect peak?** → [`dose_response_pharmacology.dose_response_time_matrix`](gallery/dose_response_pharmacology/dose_response_time_matrix.png)
- **After washout, does the response overshoot?** → [`dose_response_pharmacology.response_rebound_kinetics`](gallery/dose_response_pharmacology/response_rebound_kinetics.png)
- **How well does functional IC50 correlate with binding Ki?** → [`dose_response_pharmacology.ic50_vs_target_affinity_scatter`](gallery/dose_response_pharmacology/ic50_vs_target_affinity_scatter.png)
- **How selective is the lead across the target panel?** → [`dose_response_pharmacology.selectivity_index_tornado`](gallery/dose_response_pharmacology/selectivity_index_tornado.png)
- **How do EC50s compare normalised to the most potent lead?** → [`dose_response_pharmacology.dose_normalized_ec50_forest`](gallery/dose_response_pharmacology/dose_normalized_ec50_forest.png)
- **Do Bliss and Loewe synergy scores agree?** → [`dose_response_pharmacology.synergy_score_bliss_loewe`](gallery/dose_response_pharmacology/synergy_score_bliss_loewe.png)
- **Which pharmacophore features drive activity?** → [`dose_response_pharmacology.pharmacophore_activity_heatmap`](gallery/dose_response_pharmacology/pharmacophore_activity_heatmap.png)
- **Which compound cluster has the best mean activity?** → [`dose_response_pharmacology.compound_cluster_structure_activity`](gallery/dose_response_pharmacology/compound_cluster_structure_activity.png)
- **What is a compound's polypharmacology profile across targets?** → [`dose_response_pharmacology.polypharmacology_radar`](gallery/dose_response_pharmacology/polypharmacology_radar.png)

## Single-cell embeddings catch-up (v1.1.0-s11 additions)

- **How do condition densities shift across a shared UMAP?** → [`single_cell_embeddings.umap_density_contour_overlay`](gallery/single_cell_embeddings/umap_density_contour_overlay.png)
- **Where does a rare population sit vs the bulk?** → [`single_cell_embeddings.rare_population_highlighted_umap`](gallery/single_cell_embeddings/rare_population_highlighted_umap.png)
- **Per sample, how do cluster proportions vary?** → [`single_cell_embeddings.cluster_proportion_stacked_by_sample`](gallery/single_cell_embeddings/cluster_proportion_stacked_by_sample.png)
- **Where are the branch points in a multi-branch trajectory?** → [`single_cell_embeddings.trajectory_branching_force_directed`](gallery/single_cell_embeddings/trajectory_branching_force_directed.png)
- **What's the z-scored expression pattern of top markers per cluster?** → [`single_cell_embeddings.per_cluster_marker_heatmap`](gallery/single_cell_embeddings/per_cluster_marker_heatmap.png)
- **How do marker genes evolve along pseudotime?** → [`single_cell_embeddings.pseudotime_gene_expression_trajectory`](gallery/single_cell_embeddings/pseudotime_gene_expression_trajectory.png)
- **What does the RNA-velocity field look like on UMAP?** → [`single_cell_embeddings.rnavelocity_arrow_field`](gallery/single_cell_embeddings/rnavelocity_arrow_field.png)
- **Which LR interactions are enriched across sender × receiver pairs?** → [`single_cell_embeddings.receptor_ligand_signaling_dotplot`](gallery/single_cell_embeddings/receptor_ligand_signaling_dotplot.png)

## Calcium-signaling catch-up (v1.1.0-s10 additions)

- **How are Ca²⁺ event amplitudes distributed per condition?** → [`calcium_signaling.calcium_event_amplitude_distribution`](gallery/calcium_signaling/calcium_event_amplitude_distribution.png)
- **What does the PETH around an event onset look like?** → [`calcium_signaling.calcium_event_onset_alignment`](gallery/calcium_signaling/calcium_event_onset_alignment.png)
- **How does population synchrony evolve over time?** → [`calcium_signaling.population_synchronization_timeline`](gallery/calcium_signaling/population_synchronization_timeline.png)
- **Where are network bursts in the recording?** → [`calcium_signaling.network_burst_detection_overlay`](gallery/calcium_signaling/network_burst_detection_overlay.png)
- **What is the local wave propagation speed?** → [`calcium_signaling.calcium_wave_speed_map`](gallery/calcium_signaling/calcium_wave_speed_map.png)
- **Per cell, how does frequency relate to amplitude?** → [`calcium_signaling.single_cell_calcium_landscape`](gallery/calcium_signaling/single_cell_calcium_landscape.png)
- **How do Ca²⁺ and FRET covary per cell?** → [`calcium_signaling.calcium_and_fret_joint_plot`](gallery/calcium_signaling/calcium_and_fret_joint_plot.png)
- **Where does the dominant oscillation phase fall on the unit circle?** → [`calcium_signaling.oscillation_frequency_polar`](gallery/calcium_signaling/oscillation_frequency_polar.png)
- **How do all cells' ΔF/F traces align around a stimulus?** → [`calcium_signaling.stimulus_triggered_calcium_heatmap`](gallery/calcium_signaling/stimulus_triggered_calcium_heatmap.png)

## Omics-differential catch-up (v1.1.0-s09 additions)

- **On a proteome volcano, which pathways dominate the hits?** → [`omics_differential.proteome_volcano_labeled_pathways`](gallery/omics_differential/proteome_volcano_labeled_pathways.png)
- **How well do replicate effect-size estimates agree per gene?** → [`omics_differential.effect_size_replicate_concordance`](gallery/omics_differential/effect_size_replicate_concordance.png)
- **How does empirical-Bayes shrinkage change effect sizes?** → [`omics_differential.shrinkage_estimate_scatter`](gallery/omics_differential/shrinkage_estimate_scatter.png)
- **How do 2-3 contrast hit-sets overlap (area-proportional)?** → [`omics_differential.contrast_overlap_euler`](gallery/omics_differential/contrast_overlap_euler.png)
- **Which genes are consistently top-ranked across studies?** → [`omics_differential.rank_product_meta_analysis`](gallery/omics_differential/rank_product_meta_analysis.png)
- **How do pathway-module activities compare across samples?** → [`omics_differential.pathway_module_activity_heatmap`](gallery/omics_differential/pathway_module_activity_heatmap.png)

## Gillespie-stochastic catch-up (v1.1.0-s08 additions)

- **Does the sampled steady-state match the master-equation P(n)?** → [`gillespie_stochastic.master_equation_steady_state`](gallery/gillespie_stochastic/master_equation_steady_state.png)
- **How close is τ-leaping to the exact SSA trajectory?** → [`gillespie_stochastic.tau_leaping_comparison`](gallery/gillespie_stochastic/tau_leaping_comparison.png)
- **What is the MFPT between every pair of states?** → [`gillespie_stochastic.mean_first_passage_time_matrix`](gallery/gillespie_stochastic/mean_first_passage_time_matrix.png)
- **Which parameters are identifiable (Fisher-information matrix)?** → [`gillespie_stochastic.fisher_information_parameter_estimation`](gallery/gillespie_stochastic/fisher_information_parameter_estimation.png)
- **What is the burst-size PMF, and is it geometric / negative-binomial?** → [`gillespie_stochastic.burst_size_distribution`](gallery/gillespie_stochastic/burst_size_distribution.png)
- **How does extinction probability vary with a control parameter?** → [`gillespie_stochastic.extinction_probability_vs_parameter`](gallery/gillespie_stochastic/extinction_probability_vs_parameter.png)
- **How fast do trajectories decorrelate per state?** → [`gillespie_stochastic.autocorrelation_of_trajectories`](gallery/gillespie_stochastic/autocorrelation_of_trajectories.png)
- **Does the SNR vs noise show a stochastic-resonance peak?** → [`gillespie_stochastic.stochastic_resonance_signature`](gallery/gillespie_stochastic/stochastic_resonance_signature.png)

## Intravital-imaging catch-up (v1.1.0-s07 additions)

- **Across a field, where are cells in (x, y) and at what depth z?** → [`intravital_imaging.depth_projected_microglia_field`](gallery/intravital_imaging/depth_projected_microglia_field.png)
- **When do discrete events occur per cell across the observation window?** → [`intravital_imaging.process_event_timeline`](gallery/intravital_imaging/process_event_timeline.png)
- **How does each cell's surveyed territory change pre to post?** → [`intravital_imaging.territory_change_pre_post`](gallery/intravital_imaging/territory_change_pre_post.png)
- **How does the surveillance-efficiency metric compare across conditions?** → [`intravital_imaging.surveillance_efficiency_metric`](gallery/intravital_imaging/surveillance_efficiency_metric.png)
- **How often does each pair of cells make contact?** → [`intravital_imaging.cell_cell_contact_frequency_matrix`](gallery/intravital_imaging/cell_cell_contact_frequency_matrix.png)
- **At distance r from an ablation, how does the response evolve over time?** → [`intravital_imaging.laser_injury_response_radial`](gallery/intravital_imaging/laser_injury_response_radial.png)
- **How do multiple intravital channels co-register across a field?** → [`intravital_imaging.multi_channel_intravital_overlay`](gallery/intravital_imaging/multi_channel_intravital_overlay.png)
- **What is the ensemble MSD per state, and is motion sub- / super-diffusive?** → [`intravital_imaging.msd_curve_by_state`](gallery/intravital_imaging/msd_curve_by_state.png)
- **How do instantaneous speeds distribute per morphological state?** → [`intravital_imaging.velocity_distribution_by_state`](gallery/intravital_imaging/velocity_distribution_by_state.png)

## Redox-imaging catch-up (v1.1.0-s06 additions)

- **What is the roGFP2 calibration curve and fitted midpoint / R²?** → [`redox_imaging.roGFP2_ratio_vs_disulfide_titration`](gallery/redox_imaging/roGFP2_ratio_vs_disulfide_titration.png)
- **How do BC / kurtosis / Hartigan's dip compare per condition?** → [`redox_imaging.bimodality_kurtosis_vs_conditions`](gallery/redox_imaging/bimodality_kurtosis_vs_conditions.png)
- **How long do cells spend above the oxidation threshold per condition?** → [`redox_imaging.time_above_threshold_distribution`](gallery/redox_imaging/time_above_threshold_distribution.png)
- **What is the 1-D paracrine coupling kernel K(r), and what is λ?** → [`redox_imaging.paracrine_kernel_fit`](gallery/redox_imaging/paracrine_kernel_fit.png)
- **Is the Langevin noise better modelled as additive or multiplicative?** → [`redox_imaging.multiplicative_vs_additive_noise_diagnostic`](gallery/redox_imaging/multiplicative_vs_additive_noise_diagnostic.png)
- **Where in the imaging field do cells switch redox state most often?** → [`redox_imaging.redox_state_switching_frequency_map`](gallery/redox_imaging/redox_state_switching_frequency_map.png)
- **How fast does the ratio decorrelate in time, per state?** → [`redox_imaging.ratio_autocorrelation_decay`](gallery/redox_imaging/ratio_autocorrelation_decay.png)

## Sensitivity-analysis catch-up (v1.1.0-s05 additions)

- **What does the FAST frequency spectrum reveal about each parameter?** → [`sensitivity_analysis.fast_sensitivity_spectrum`](gallery/sensitivity_analysis/fast_sensitivity_spectrum.png)
- **Does the LHS sample cover the joint parameter space?** → [`sensitivity_analysis.lhs_parameter_space_coverage`](gallery/sensitivity_analysis/lhs_parameter_space_coverage.png)
- **OAT: how does the output change under ±Δ per parameter?** → [`sensitivity_analysis.tornado_diagram`](gallery/sensitivity_analysis/tornado_diagram.png)
- **Across multiple output quantities, how do indices redistribute?** → [`sensitivity_analysis.sensitivity_by_output_quantity`](gallery/sensitivity_analysis/sensitivity_by_output_quantity.png)
- **How does the bootstrap 95 % CI on each S₁ shrink with N?** → [`sensitivity_analysis.sobol_bootstrap_convergence`](gallery/sensitivity_analysis/sobol_bootstrap_convergence.png)
- **As a graph, which parameters form the strongest interaction clusters?** → [`sensitivity_analysis.interaction_network_sobol`](gallery/sensitivity_analysis/interaction_network_sobol.png)
- **For a time-resolved output, how do Sobol indices evolve?** → [`sensitivity_analysis.sensitivity_time_evolution`](gallery/sensitivity_analysis/sensitivity_time_evolution.png)

## Mixed-effects model catch-up (v1.1.0-s04 additions)

- **What does the raw outcome look like under sex × genotype, with β + CI?** → [`mixed_effects_models.sex_stratified_raincloud_with_coef_box`](gallery/mixed_effects_models/sex_stratified_raincloud_with_coef_box.png)
- **Per cluster, how do random intercept and slope covary?** → [`mixed_effects_models.random_intercepts_vs_slopes_scatter`](gallery/mixed_effects_models/random_intercepts_vs_slopes_scatter.png)
- **Among competing mixed-model specifications, which has lowest AIC / BIC?** → [`mixed_effects_models.model_comparison_aic_bic_ladder`](gallery/mixed_effects_models/model_comparison_aic_bic_ladder.png)
- **What is the posterior distribution of each contrast (Δ) with HDI?** → [`mixed_effects_models.posterior_contrast_density`](gallery/mixed_effects_models/posterior_contrast_density.png)
- **For a given predictor, what is the partial-residual pattern?** → [`mixed_effects_models.partial_residuals_vs_predictor`](gallery/mixed_effects_models/partial_residuals_vs_predictor.png)
- **What are response-scale emmeans per group with pairwise brackets?** → [`mixed_effects_models.group_level_emmeans_with_pairwise`](gallery/mixed_effects_models/group_level_emmeans_with_pairwise.png)
- **How is variance split into fixed vs random vs residual?** → [`mixed_effects_models.fixed_vs_random_effect_partition`](gallery/mixed_effects_models/fixed_vs_random_effect_partition.png)

## Diagnostics / is the data usable?

- **How much power buys what effect size?** → [`meta_and_diagnostic.power_analysis_by_effect_size`](gallery/meta_and_diagnostic/power_analysis_by_effect_size.png)
- **What N is needed for each effect tier against a budget?** → [`meta_and_diagnostic.sample_size_decision_ladder`](gallery/meta_and_diagnostic/sample_size_decision_ladder.png)
- **Which variables are jointly missing?** → [`meta_and_diagnostic.missing_data_pattern_matrix`](gallery/meta_and_diagnostic/missing_data_pattern_matrix.png)
- **Which samples pass every QC axis?** → [`meta_and_diagnostic.qc_metric_radar`](gallery/meta_and_diagnostic/qc_metric_radar.png)

## Parameter sensitivity / model analysis

- **Which parameters drive the output, and how much via interactions?** → [`sensitivity_analysis.sobol_first_total_pair`](gallery/sensitivity_analysis/sobol_first_total_pair.png) · [`sensitivity_analysis.morris_elementary_effects`](gallery/sensitivity_analysis/morris_elementary_effects.png)
- **How does the output depend on two parameters jointly?** → [`sensitivity_analysis.parameter_scan_2d_contour`](gallery/sensitivity_analysis/parameter_scan_2d_contour.png)
- **Do my experiments collapse onto a dimensionless master curve?** → [`sensitivity_analysis.dimensionless_pi_group_collapse`](gallery/sensitivity_analysis/dimensionless_pi_group_collapse.png)
- **Which Π-formulation fits best?** → [`sensitivity_analysis.pi_group_rank_plot`](gallery/sensitivity_analysis/pi_group_rank_plot.png)
- **Is the system really low-dimensional (active subspace)?** → [`sensitivity_analysis.fast_subspace_detection`](gallery/sensitivity_analysis/fast_subspace_detection.png)
- **Have my Sobol estimates converged?** → [`sensitivity_analysis.convergence_diagnostic_sobol`](gallery/sensitivity_analysis/convergence_diagnostic_sobol.png)
- **Which parameter pairs interact most strongly?** → [`sensitivity_analysis.interaction_matrix_sobol`](gallery/sensitivity_analysis/interaction_matrix_sobol.png)

## Grant / strategic / conceptual figures

- **One-glance headline + structured payoff** → [`grant_and_conceptual.executive_summary_tile`](gallery/grant_and_conceptual/executive_summary_tile.png)
- **When do work packages and milestones land?** → [`grant_and_conceptual.timeline_gantt_with_milestones`](gallery/grant_and_conceptual/timeline_gantt_with_milestones.png)
- **How do work packages depend on each other?** → [`grant_and_conceptual.work_package_flow`](gallery/grant_and_conceptual/work_package_flow.png)
- **Hypothesis, evidence, predictions** → [`grant_and_conceptual.hypothesis_diagram`](gallery/grant_and_conceptual/hypothesis_diagram.png)
- **Team × competency coverage** → [`grant_and_conceptual.team_expertise_matrix`](gallery/grant_and_conceptual/team_expertise_matrix.png)
- **Problem → approach → payoff narrative** → [`grant_and_conceptual.conceptual_triptych`](gallery/grant_and_conceptual/conceptual_triptych.png)

## Cytoskeleton morphometry catch-up (v1.1.0-s03b additions)

- **How does total process length distribute by sex × genotype?** → [`actin_microtubule_morphometry.process_length_distribution_by_sex`](gallery/actin_microtubule_morphometry/process_length_distribution_by_sex.png)
- **Does CV of velocity show a sex × genotype interaction?** → [`actin_microtubule_morphometry.sex_stratified_cvvelocity`](gallery/actin_microtubule_morphometry/sex_stratified_cvvelocity.png)
- **How do 6-8 topology complexity metrics compare across conditions?** → [`actin_microtubule_morphometry.skeleton_complexity_radar`](gallery/actin_microtubule_morphometry/skeleton_complexity_radar.png)
- **How does the branching hierarchy (depth 0-4) split by condition?** → [`actin_microtubule_morphometry.branching_topology_sunburst`](gallery/actin_microtubule_morphometry/branching_topology_sunburst.png)
- **What is the distribution of per-segment persistence length with CI?** → [`actin_microtubule_morphometry.persistence_length_by_segment`](gallery/actin_microtubule_morphometry/persistence_length_by_segment.png)
- **Where do actin orientations align with MT density peaks?** → [`actin_microtubule_morphometry.actin_microtubule_crosstalk_quiver`](gallery/actin_microtubule_morphometry/actin_microtubule_crosstalk_quiver.png)
- **Where along the edge are protrusions vs retractions over time?** → [`actin_microtubule_morphometry.protrusion_retraction_kymograph`](gallery/actin_microtubule_morphometry/protrusion_retraction_kymograph.png)
- **Where do cells point their cytoskeletal polarity vectors in a field?** → [`actin_microtubule_morphometry.cytoskeleton_polarity_vectorfield`](gallery/actin_microtubule_morphometry/cytoskeleton_polarity_vectorfield.png)
- **What do Airyscan raw + segmentation pairs look like side-by-side?** → [`actin_microtubule_morphometry.airyscan_segmentation_mosaic`](gallery/actin_microtubule_morphometry/airyscan_segmentation_mosaic.png)
- **How do conditions cluster in linear PCA of shape descriptors?** → [`actin_microtubule_morphometry.shape_pca_morphospace`](gallery/actin_microtubule_morphometry/shape_pca_morphospace.png)
- **How do M1 / M2 / Pearson / Manders / ICQ coefficients compare by condition?** → [`actin_microtubule_morphometry.colocalization_coefficient_matrix`](gallery/actin_microtubule_morphometry/colocalization_coefficient_matrix.png)

## Cytoskeleton morphometry (v1.1.0-s03 additions)

- **How does per-cell branch count shift across conditions?** → [`actin_microtubule_morphometry.branch_point_count_raincloud`](gallery/actin_microtubule_morphometry/branch_point_count_raincloud.png)
- **How do primary vs higher-order terminal-tip counts distribute?** → [`actin_microtubule_morphometry.process_end_count_violin`](gallery/actin_microtubule_morphometry/process_end_count_violin.png)
- **How does soma area distribute per condition?** → [`actin_microtubule_morphometry.cell_body_area_distribution`](gallery/actin_microtubule_morphometry/cell_body_area_distribution.png)
- **Where do cells sit in the (sphericity, elongation) plane?** → [`actin_microtubule_morphometry.sphericity_vs_elongation_scatter`](gallery/actin_microtubule_morphometry/sphericity_vs_elongation_scatter.png)
- **What is the distribution of mother-daughter branch angles?** → [`actin_microtubule_morphometry.branch_angle_distribution`](gallery/actin_microtubule_morphometry/branch_angle_distribution.png)
- **What is the linear/branched/looped simplex partition per condition?** → [`actin_microtubule_morphometry.topology_ternary_simplex`](gallery/actin_microtubule_morphometry/topology_ternary_simplex.png)
- **How far along a perimeter does edge velocity stay correlated?** → [`actin_microtubule_morphometry.edge_velocity_spatial_correlation`](gallery/actin_microtubule_morphometry/edge_velocity_spatial_correlation.png)
- **Do mitochondria align with the cytoskeletal axis?** → [`actin_microtubule_morphometry.mitochondrial_axis_alignment`](gallery/actin_microtubule_morphometry/mitochondrial_axis_alignment.png)
- **What do individual cells look like alongside their metrics?** → [`actin_microtubule_morphometry.per_cell_thumbnail_grid_with_metrics`](gallery/actin_microtubule_morphometry/per_cell_thumbnail_grid_with_metrics.png)
- **What are the min / median / max exemplars per condition?** → [`actin_microtubule_morphometry.exemplar_extremes_panel`](gallery/actin_microtubule_morphometry/exemplar_extremes_panel.png)
- **What is the average cell shape per condition?** → [`actin_microtubule_morphometry.condition_average_cell_composite`](gallery/actin_microtubule_morphometry/condition_average_cell_composite.png)
- **How do conditions cluster in non-linear shape space?** → [`actin_microtubule_morphometry.shape_umap_by_condition`](gallery/actin_microtubule_morphometry/shape_umap_by_condition.png)
- **How do condition centroids move through shape space over time?** → [`actin_microtubule_morphometry.morphospace_trajectory_by_time`](gallery/actin_microtubule_morphometry/morphospace_trajectory_by_time.png)
- **How do 5-6 shape descriptors pairwise co-vary?** → [`actin_microtubule_morphometry.shape_descriptor_scatter_matrix`](gallery/actin_microtubule_morphometry/shape_descriptor_scatter_matrix.png)
- **What is the local actin-to-MT intensity ratio?** → [`actin_microtubule_morphometry.actin_mt_ratio_spatial_map`](gallery/actin_microtubule_morphometry/actin_mt_ratio_spatial_map.png)
- **How do channel intensities vary radially from centroid?** → [`actin_microtubule_morphometry.intensity_radial_profile`](gallery/actin_microtubule_morphometry/intensity_radial_profile.png)
- **Is a marker enriched at tips relative to shafts?** → [`actin_microtubule_morphometry.tip_enrichment_vs_shaft_scatter`](gallery/actin_microtubule_morphometry/tip_enrichment_vs_shaft_scatter.png)
- **Do colocalization metrics correlate with shape metrics (FDR-corrected)?** → [`actin_microtubule_morphometry.colocalization_vs_morphology_correlation`](gallery/actin_microtubule_morphometry/colocalization_vs_morphology_correlation.png)

## FRET biosensors (v1.1.0-s02 additions)

- **Does the donor/acceptor pair behave linearly?** → [`fret_biosensors.donor_acceptor_scatter_linearity`](gallery/fret_biosensors/donor_acceptor_scatter_linearity.png)
- **What is the fitted Förster radius R₀?** → [`fret_biosensors.fret_efficiency_vs_distance`](gallery/fret_biosensors/fret_efficiency_vs_distance.png)
- **Does each cell's ratio change pre-to-post stimulus?** → [`fret_biosensors.paired_pre_post_stimulus`](gallery/fret_biosensors/paired_pre_post_stimulus.png)
- **How does the ratio change jointly vs dose and time?** → [`fret_biosensors.biosensor_dose_response_matrix`](gallery/fret_biosensors/biosensor_dose_response_matrix.png)
- **How does the ratio propagate from cell edge to centre?** → [`fret_biosensors.kymograph_ratio_edge_to_center`](gallery/fret_biosensors/kymograph_ratio_edge_to_center.png)
- **Which cell contributes which ratio region in the field?** → [`fret_biosensors.ratio_map_with_segmentation_overlay`](gallery/fret_biosensors/ratio_map_with_segmentation_overlay.png)
- **How does the ratio evolve per sub-cellular window?** → [`fret_biosensors.windowed_roi_ratio_trajectory`](gallery/fret_biosensors/windowed_roi_ratio_trajectory.png)
- **Does FRET correlate with an orthogonal activity readout?** → [`fret_biosensors.fret_vs_scalar_activity_regression`](gallery/fret_biosensors/fret_vs_scalar_activity_regression.png)

## Dynamical systems / landscapes (v1.1.0-s01 additions)

- **How do sample trajectories relax onto the attractor landscape?** → [`rhogtpase_dynamics.phase_portrait_with_trajectories`](gallery/rhogtpase_dynamics/phase_portrait_with_trajectories.png)
- **Where are the saddle-node / Hopf / pitchfork curves in the two-parameter plane?** → [`rhogtpase_dynamics.codim2_bifurcation_map`](gallery/rhogtpase_dynamics/codim2_bifurcation_map.png)
- **What does the potential landscape look like as a 3-D Waddington surface?** → [`rhogtpase_dynamics.potential_landscape_waddington_3d`](gallery/rhogtpase_dynamics/potential_landscape_waddington_3d.png)
- **What distinguishes a sub-threshold from a super-threshold perturbation?** → [`rhogtpase_dynamics.excitability_threshold_diagram`](gallery/rhogtpase_dynamics/excitability_threshold_diagram.png)
- **How do fast trajectories collapse geometrically onto the slow manifold?** → [`rhogtpase_dynamics.slow_manifold_projection`](gallery/rhogtpase_dynamics/slow_manifold_projection.png)
- **What does the Poincaré first-return map reveal about periodic-orbit stability?** → [`rhogtpase_dynamics.poincare_first_return_map`](gallery/rhogtpase_dynamics/poincare_first_return_map.png)
