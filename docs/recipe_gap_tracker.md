# v1.1 Recipe Gap Tracker

Live progress of the 20-session v1.1 hydration. Update this table on
every PR merge. Governed by
[`docs/hydration_coordinator.md`](hydration_coordinator.md).

## Summary

| Metric | v1.0 | Current | v1.1 target |
|---|---|---|---|
| Modalities | 20 | 20 | 20 |
| Total recipes | 137 | 218 | ≥320 |
| Sessions complete | 0 | 8.5 | 20 |

## Per-session status

| Session | Modality | Status | PR | Merged tag | Recipes added | Aesthetic regressions | Notes |
|---|---|---|---|---|---|---|---|
| 01 | `rhogtpase_dynamics`        | merged  | — | `v1.1.0-s01` | 6 (12→18) | none | Waddington family retagged heatmap→conceptual; lw=2.4→2.2 to hold ratchet |
| 02 | `fret_biosensors`            | merged  | — | `v1.1.0-s02` | 8 (10→18) | none | Visual-QA polish: dose_matrix callout axes-fraction anchor; windowed_roi legend minimized |
| 03 | `actin_microtubule_morphometry` | merged  | — | `v1.1.0-s03` | 18 (6→24, Path 2) | none | 9+ catch-up recipes deferred to s03b; fontsize/lw snapped to ratchet; 3 panels polished |
| 03b | `actin_microtubule_morphometry` (catch-up) | merged  | — | `v1.1.0-s03b` | 11 (24→35) | none | User approved "land all 11" → 5 over 30-roster target (4 real-v1.0 bonus + persistence_length_by_segment); 2 panels polished (sunburst legend, polarity summary) |
| 04 | `mixed_effects_models`       | merged  | — | `v1.1.0-s04` | 7 (9→16) | none | Raw-data raincloud + (int, slope) scatter + AIC/BIC ladder + Δ-posteriors + partial residuals + emmeans-with-brackets + fixed/random/residual partition; 3 panels polished (raincloud n-labels, AIC legend, variance legend) |
| 05 | `sensitivity_analysis`       | merged  | — | `v1.1.0-s05` | 7 (8→15) | none | FAST spectrum + LHS coverage + OAT tornado + param×output matrix + bootstrap-CI convergence + interaction graph + time-resolved indices; 3 panels polished (tornado baseline pill, driver-markers as edge triangles, FAST top-drivers footer) |
| 06 | `redox_imaging`              | merged  | — | `v1.1.0-s06` | 7 (8→15) | none | roGFP2 calibration + three-stat bimodality ladder + duration CCDF + 1-D paracrine kernel + Langevin model comparison + switching-rate heatmap + per-state ACF; 2 panels polished (CCDF median footer, Langevin demo convention) |
| 07 | `intravital_imaging`         | merged  | — | `v1.1.0-s07` | 9 (6→15, Path 2) | none | Real baseline 6 (plan listed 8); +9 lands 15-target in one session; seeds (depth field, event timeline, territory pre/post, surveillance forest, contact matrix, laser injury radial, RGB overlay) + 2 gap-closers (MSD by state, velocity by state); 2 panels polished (midline line removed from territory, baseline label repositioned in surveillance) |
| 08 | `gillespie_stochastic`       | merged  | — | `v1.1.0-s08` | 8 (7→15) | none | Master-eq P(n) overlap + tau-leap method comparison + MFPT matrix + FIM matrix + burst-size PMF + extinction P_ext(θ) + trajectory ACF + stochastic-resonance SNR; 2 panels polished (tau-leap inset xlabel, extinction interpolation sign) |
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
