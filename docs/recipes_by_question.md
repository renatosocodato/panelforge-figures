# Recipes by scientific question

Recipes from `recipes_by_modality.md`, grouped by the *claim* they help
you make. Useful for the bootstrap skill when a user says "I want a
figure that shows <X>" without naming a modality.

> **Note:** This question-grouped index was seeded at the 18-recipe
> milestone and has not kept pace with subsequent session additions.
> It will be fully regenerated from the catalog in a future batch. In
> the meantime the *by-modality* index is the authoritative catalog
> for the current 137 + 6 recipes.

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
