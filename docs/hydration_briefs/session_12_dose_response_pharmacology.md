# Session 12 — `dose_response_pharmacology` (5 → 15, +10)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `dose_response_pharmacology`
- `SESSION_NUM`: `12`
- `V10_COUNT`: 5
- `V11_TARGET`: 15
- `PRIORITY_CONTEXT`: ATHENA pharmacology panels, sex-stratified drug
  responses.

## Seed list

- `dose_response_sex_stratified` — side-by-side Hill fits with interaction p-value
- `ic50_vs_target_affinity_scatter` — IC50 vs Ki concordance
- `selectivity_index_tornado` — selectivity across targets
- `dose_response_time_matrix` — concentration × time matrix
- `synergy_score_bliss_loewe` — Bliss vs Loewe synergy scores
- `dose_normalized_ec50_forest` — normalized EC50 across compound series
- `pharmacophore_activity_heatmap` — SAR matrix
- `polypharmacology_radar` — multi-target radar per compound
- `response_rebound_kinetics` — washout/recovery curve
- `compound_cluster_structure_activity` — clustered SAR

Follow the Part 2 template exactly. Do not modify any other modality.
