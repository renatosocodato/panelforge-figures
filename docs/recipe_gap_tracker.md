# v1.1 Recipe Gap Tracker

Live progress of the 20-session v1.1 hydration. Update this table on
every PR merge. Governed by
[`docs/hydration_coordinator.md`](hydration_coordinator.md).

## Summary

| Metric | v1.0 | Current | v1.1 target |
|---|---|---|---|
| Modalities | 20 | 20 | 20 |
| Total recipes | 137 | 137 | ≥320 |
| Sessions complete | 0 | 0 | 20 |

## Per-session status

| Session | Modality | Status | PR | Merged tag | Recipes added | Aesthetic regressions | Notes |
|---|---|---|---|---|---|---|---|
| 01 | `rhogtpase_dynamics`        | pending | — | — | — | — | — |
| 02 | `fret_biosensors`            | pending | — | — | — | — | — |
| 03 | `actin_microtubule_morphometry` | pending | — | — | — | — | — |
| 04 | `mixed_effects_models`       | pending | — | — | — | — | — |
| 05 | `sensitivity_analysis`       | pending | — | — | — | — | — |
| 06 | `redox_imaging`              | pending | — | — | — | — | — |
| 07 | `intravital_imaging`         | pending | — | — | — | — | — |
| 08 | `gillespie_stochastic`       | pending | — | — | — | — | — |
| 09 | `omics_differential`         | pending | — | — | — | — | — |
| 10 | `calcium_signaling`          | pending | — | — | — | — | — |
| 11 | `single_cell_embeddings`     | pending | — | — | — | — | — |
| 12 | `dose_response_pharmacology` | pending | — | — | — | — | — |
| 13 | `network_and_pathway`        | pending | — | — | — | — | — |
| 14 | `biophysics_scaling`         | pending | — | — | — | — | — |
| 15 | `diffusion_and_tracking`     | pending | — | — | — | — | — |
| 16 | `spatial_statistics`         | pending | — | — | — | — | — |
| 17 | `grant_and_conceptual`       | pending | — | — | — | — | — |
| 18 | `meta_and_diagnostic`        | pending | — | — | — | — | — |
| 19 | `clinical_cohort`            | pending | — | — | — | — | — |
| 20 | `cryoem_and_structure`       | pending | — | — | — | — | — |

## Status legend

- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval of recipe table
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed
- **blocked** — halted by the stop rule (aesthetic regression surfaced in real use)
