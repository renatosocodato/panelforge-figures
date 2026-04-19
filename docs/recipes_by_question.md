# Recipes by scientific question

Recipes from `recipes_by_modality.md`, grouped by the *claim* they help
you make. Useful for the bootstrap skill when a user says "I want a
figure that shows <X>" without naming a modality.

> **Note:** This question-grouped index was seeded at the 18-recipe
> milestone and has not kept pace with subsequent session additions.
> It will be fully regenerated from the catalog in a future batch. In
> the meantime the *by-modality* index is the authoritative catalog
> for the current 137 + 6 recipes.

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
