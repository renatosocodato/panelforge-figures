# v1.1 Recipe Gap Tracker

Live progress of the 20-session v1.1 hydration. Update this table on
every PR merge. Governed by
[`docs/hydration_coordinator.md`](hydration_coordinator.md).

## Summary

| Metric | v1.0 | Current | v1.1 target |
|---|---|---|---|
| Modalities | 20 | 20 | 20 |
| Total recipes | 137 | 180 | ≥320 |
| Sessions complete | 0 | 3.5 | 20 |

## Per-session status

| Session | Modality | Status | PR | Merged tag | Recipes added | Aesthetic regressions | Notes |
|---|---|---|---|---|---|---|---|
| 01 | `rhogtpase_dynamics`        | merged  | — | `v1.1.0-s01` | 6 (12→18) | none | Waddington family retagged heatmap→conceptual; lw=2.4→2.2 to hold ratchet |
| 02 | `fret_biosensors`            | merged  | — | `v1.1.0-s02` | 8 (10→18) | none | Visual-QA polish: dose_matrix callout axes-fraction anchor; windowed_roi legend minimized |
| 03 | `actin_microtubule_morphometry` | merged  | — | `v1.1.0-s03` | 18 (6→24, Path 2) | none | 9+ catch-up recipes deferred to s03b; fontsize/lw snapped to ratchet; 3 panels polished |
| 03b | `actin_microtubule_morphometry` (catch-up) | merged  | — | `v1.1.0-s03b` | 11 (24→35) | none | User approved "land all 11" → 5 over 30-roster target (4 real-v1.0 bonus + persistence_length_by_segment); 2 panels polished (sunburst legend, polarity summary) |
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
