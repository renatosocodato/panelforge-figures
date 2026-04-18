# Recipes by modality

Auto-describable via `figures catalog --by modality`. Below is the v0.1.0-alpha
snapshot (3 modalities, 18 recipes).

## `grant_and_conceptual` (6 recipes)

Executive summaries, Gantts, work-package flows, hypothesis diagrams,
team matrices, and conceptual triptychs for grant proposals.

| Recipe | Family | Answers |
|---|---|---|
| [executive_summary_tile](gallery/grant_and_conceptual/executive_summary_tile.png) | conceptual | At a glance, what is the headline impact and how is it structured? |
| [timeline_gantt_with_milestones](gallery/grant_and_conceptual/timeline_gantt_with_milestones.png) | gantt | When does each work package happen and when do its milestones land? |
| [work_package_flow](gallery/grant_and_conceptual/work_package_flow.png) | flow | How do the work packages depend on each other and what flows between them? |
| [hypothesis_diagram](gallery/grant_and_conceptual/hypothesis_diagram.png) | conceptual | What is the central hypothesis, and which observations support it vs. test it? |
| [team_expertise_matrix](gallery/grant_and_conceptual/team_expertise_matrix.png) | matrix | How is the team's expertise distributed across the required competencies? |
| [conceptual_triptych](gallery/grant_and_conceptual/conceptual_triptych.png) | conceptual | What's the narrative arc from the problem to the approach to the payoff? |

## `meta_and_diagnostic` (4 recipes)

Pre-analysis diagnostics — power curves, sample-size decision ladders,
missing-data patterns, multi-metric QC radars.

| Recipe | Family | Answers |
|---|---|---|
| [power_analysis_by_effect_size](gallery/meta_and_diagnostic/power_analysis_by_effect_size.png) | diagnostic_curve | How much statistical power does each planned sample size buy per effect size? |
| [sample_size_decision_ladder](gallery/meta_and_diagnostic/sample_size_decision_ladder.png) | ladder | For each candidate effect size tier, what sample size do we need vs. the budget? |
| [missing_data_pattern_matrix](gallery/meta_and_diagnostic/missing_data_pattern_matrix.png) | matrix | Which variables are co-missing, how often, and which rows are complete? |
| [qc_metric_radar](gallery/meta_and_diagnostic/qc_metric_radar.png) | radar | Which samples pass every QC metric, and which fail which axes? |

## `sensitivity_analysis` (8 recipes)

Global sensitivity (Sobol, Morris), parameter scans, dimensionless Pi-group
collapses, interaction matrices, and convergence diagnostics.

| Recipe | Family | Answers |
|---|---|---|
| [sobol_first_total_pair](gallery/sensitivity_analysis/sobol_first_total_pair.png) | sobol_bar | Which parameters carry most of the variance directly (S₁) and via interactions (Sₜ)? |
| [morris_elementary_effects](gallery/sensitivity_analysis/morris_elementary_effects.png) | sobol_bar | Which parameters matter directly (high μ*) vs. via interactions/nonlinearity (high σ)? |
| [parameter_scan_2d_contour](gallery/sensitivity_analysis/parameter_scan_2d_contour.png) | contour | How does the output depend on two parameters jointly, and where is a threshold crossed? |
| [dimensionless_pi_group_collapse](gallery/sensitivity_analysis/dimensionless_pi_group_collapse.png) | scatter_collapse | Do multiple experiments collapse onto one master curve under a dimensionless Π? |
| [pi_group_rank_plot](gallery/sensitivity_analysis/pi_group_rank_plot.png) | ladder | Among candidate Π formulations, which collapses the data best by R² and AIC? |
| [fast_subspace_detection](gallery/sensitivity_analysis/fast_subspace_detection.png) | sobol_bar | Is the output variance driven by a low-dimensional active subspace of parameters? |
| [convergence_diagnostic_sobol](gallery/sensitivity_analysis/convergence_diagnostic_sobol.png) | diagnostic_curve | Have the Sobol index estimates converged as we added more samples? |
| [interaction_matrix_sobol](gallery/sensitivity_analysis/interaction_matrix_sobol.png) | matrix | Which pairs of parameters interact strongly in driving the output? |

## Pending for v0.1.0 (17 modalities, 119 recipes)

See `CHANGELOG.md` roadmap for ordering. At `v0.1.0` the full 137-recipe
roster is the commitment.
