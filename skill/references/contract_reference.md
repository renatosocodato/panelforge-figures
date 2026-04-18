# Contract reference

Every recipe has a pydantic `RecipeContract` subclass (its input shape).
Browse `figures catalog --json | jq '.contracts'` for the list of
registered contract class names and `.modalities[].recipes[].contract`
for the per-recipe mapping.

## Canonical contracts in v0.1.0-alpha

| Modality | Recipe | Contract | Required fields |
|---|---|---|---|
| grant_and_conceptual | executive_summary_tile | ExecutiveSummaryInput | headline_value, headline_label, payoffs |
| grant_and_conceptual | timeline_gantt_with_milestones | GanttInput | tasks |
| grant_and_conceptual | work_package_flow | WorkPackageFlowInput | wps |
| grant_and_conceptual | hypothesis_diagram | HypothesisDiagramInput | claim |
| grant_and_conceptual | team_expertise_matrix | TeamExpertiseInput | members, competencies, matrix |
| grant_and_conceptual | conceptual_triptych | ConceptualTriptychInput | left, middle, right |
| meta_and_diagnostic | power_analysis_by_effect_size | PowerAnalysisInput | effect_sizes, n_range |
| meta_and_diagnostic | sample_size_decision_ladder | SampleSizeLadderInput | effect_sizes |
| meta_and_diagnostic | missing_data_pattern_matrix | MissingPatternInput | variable_names, patterns, pattern_counts |
| meta_and_diagnostic | qc_metric_radar | QCMetricRadarInput | metric_names, sample_values |
| sensitivity_analysis | sobol_first_total_pair | SobolIndicesInput | parameter_names, S1, ST |
| sensitivity_analysis | morris_elementary_effects | MorrisEEInput | parameter_names, mu_star, sigma |
| sensitivity_analysis | parameter_scan_2d_contour | ParameterScan2DInput | x_name, y_name, x_grid, y_grid, z |
| sensitivity_analysis | dimensionless_pi_group_collapse | PiGroupCollapseInput | experiments |
| sensitivity_analysis | pi_group_rank_plot | PiGroupRankInput | formulations, r2, aic |
| sensitivity_analysis | fast_subspace_detection | FastSubspaceInput | parameter_names, sensitivity_matrix |
| sensitivity_analysis | convergence_diagnostic_sobol | SobolConvergenceInput | n_samples, parameter_names, index_trajectories |
| sensitivity_analysis | interaction_matrix_sobol | InteractionMatrixInput | parameter_names, S2 |

## How to match a data source to a contract

1. Confirm `required_fields` (catalog) are all present in the data
   (possibly after transforms).
2. Pass the coerced dict/DataFrame to the recipe; the resolver will
   call `contract.model_validate(data)` when possible.
3. If validation fails, use `columns:` (rename) or add `transforms:` to
   massage the input before it reaches the contract.

When the data is truly foreign, write a local adapter that emits exactly
the contract's shape.
