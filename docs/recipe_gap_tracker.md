# v1.1 Recipe Gap Tracker

Live progress of the 20-session v1.1 hydration. Update this table on
every PR merge. Governed by
[`docs/hydration_coordinator.md`](hydration_coordinator.md).

## Summary

| Metric | v1.0 | Current | v1.1 target |
|---|---|---|---|
| Modalities | 20 | 20 | 20 |
| Total recipes | 137 | 319 | ≥320 |
| Sessions complete | 0 | 19.5 | 20 |

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
| 09 | `omics_differential`         | merged  | — | `v1.1.0-s09` | 6 (10→16) | none | Pathway-labelled proteome volcano + replicate concordance + shrinkage diagnostic + Euler overlap + rank-product meta-analysis + module activity heatmap; 2 panels polished (rank-product strip moved right, module-heatmap annotation strips repositioned) |
| 10 | `calcium_signaling`          | merged  | — | `v1.1.0-s10` | 9 (6→15) | none | Amplitude ridge + PETH + sync timeline + burst overlay + wave-speed map + freq×amp landscape + Ca×FRET joint + oscillation polar + stim-triggered heatmap; 2 panels polished (burst-callout → title, polar radial-labels to 270°) |
| 11 | `single_cell_embeddings`     | merged  | — | `v1.1.0-s11` | 8 (7→15) | none | Condition-density UMAP overlay + rare-pop spotlight + per-sample composition stack + branching trajectory + marker heatmap + gene×pseudotime + RNA-velocity field + LR dotplot; 2 panels polished (per-sample tick labels, velocity legend) |
| 12 | `dose_response_pharmacology` | merged  | — | `v1.1.0-s12` | 10 (5→15) | none | Sex-stratified Hill + dose×time matrix + rebound kinetics + IC50-vs-Ki + selectivity tornado + fold-EC50 forest + Bliss-vs-Loewe + SAR heatmap + cluster-SAR two-panel + polypharmacology radar; 2 panels polished (forest legend, radar footer/legend) |
| 13 | `network_and_pathway`        | merged  | — | `v1.1.0-s13` | 10 (5→15) | none | Force layout + hub radial + PPI seed expansion + crosstalk matrix + KEGG overlay + regulon heatmap + module preservation + centrality-vs-effect + diff subnetwork + flux streamgraph; 1 panel polished (force layout -> degree-radial after spring collapse) |
| 14 | `biophysics_scaling`         | merged  | — | `v1.1.0-s14` | 10 (5→15) | none | Theory-line overlay + universality-class comparison + fractal D_f with local-window inset + σ-ε regime map + Kn × Re regime grid + 1-D energy-landscape cartoon + scaling-exponent CI forest + τ(p) critical/Arrhenius + Π-group sensitivity bar + crossover diagnostic; 3 panels polished (fractal legend upper-left, Kn-Re regime labels to bottom + legend below, crossover inset linear y) |
| 15 | `diffusion_and_tracking`     | merged  | — | `v1.1.0-s15` | 10 (5→15) | none | Per-track α fit + track-duration CCDF + van Hove self-correlation + state-coloured spaghetti + HMM dwell + residence-conditional Δr matrix + spatial D map + directionality polar + EA-vs-TA MSD ergodicity + R_conf time evolution; 1 panel polished (displacement × state-residence heatmap: removed right-edge Δ arrows, added compact trends footer) |
| 16 | `spatial_statistics`         | merged  | — | `v1.1.0-s16` | 9 (6→15, Path 2) | none | Real baseline 6 (plan listed 4); dropped 2 duplicate seeds (l_function_with_envelope ≡ ripley_l_function, point_pattern_density_map ≡ kernel_density_heatmap); +9 lands 15-target: Clark-Evans ladder + F function + spatial covariogram + LISA cluster map + bivariate PCF + Voronoi area ridges + co-occurrence z-matrix + quadrat χ² + permutation null ridges; 0 panels polished (clean first render) |
| 17 | `grant_and_conceptual`       | merged  | — | `v1.1.0-s17` | 9 (6→15) | none | Aims pyramid + linear methods pipeline + milestone-risk matrix + innovation-positioning quadrant + cost-by-WP stacked bars + ethics & impact block + interdisciplinary spider + consortium network + deliverables timeline; 4 panels polished (aims wrap widths, methods pipeline slot width, innovation-positioning legend removed, deliverables-timeline angled titles + in-marker IDs, cost legend below xlabel, team-network ID inside + names below) |
| 18 | `meta_and_diagnostic`        | merged  | — | `v1.1.0-s18` | 11 (4→15) | none | PRISMA flow + funnel plot + heterogeneity forest + LOO sensitivity + QC heatmap + missingness UpSet + outlier scatter + retention Sankey + replication matrix + correlogram + batch PCA; 7 panels polished (PRISMA reason layout, forest legend to upper-right + I²/τ²/Q in title, LOO summary in title, Sankey arrow-gap/bar-centre/tab layout, replication summary in title, correlogram tick-label colouring, PCA legend outside) |
| 19 | `clinical_cohort`            | merged  | — | `v1.1.0-s19` | 9 (6→15, Path 2) | none | Real baseline 6 (plan listed 3); 4 duplicate seeds dropped; +9 lands 15-target: ROC with Youden + HL calibration + decision curve + competing risks CIF + HR(t) PH check + risk-score ladder + NNT forest + PS balance + AE bars; 2 panels polished (NNT + PS-balance legends moved below axes) |
| 20 | `cryoem_and_structure`       | pending | — | — | — | — | — |

## Status legend

- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval of recipe table
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed
- **blocked** — halted by the stop rule (aesthetic regression surfaced in real use)
