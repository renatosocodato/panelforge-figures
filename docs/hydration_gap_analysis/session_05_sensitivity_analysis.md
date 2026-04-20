# Session 05 — Gap Analysis: `sensitivity_analysis` (8 → 15, +7)

**Branch:** `v1.1/session-05-sensitivity_analysis`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`sensitivity_analysis` is the modality behind Manuscript 3 Box 1 and
every grant-grade "which parameter drives the prediction?" panel. v1.0
ships the **Sobol-dominant core** (S1 + ST, Morris μ*–σ, 2-D parameter
scan, Sobol-convergence diagnostic, Π-group collapse, Π-group rank
ladder, active-subspace eigenvalue drop, pairwise interaction matrix —
8 recipes) but is thin on the *other* major global-SA methods
reviewers request: FAST (frequency-domain), LHS coverage, tornado
(OAT), multi-output indices, bootstrap-CI convergence, the interaction
**graph** view, and time-resolved Sobol.

These seven catch-up recipes add those missing grammars without
duplicating the Sobol-core.

## Current 8-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `convergence_diagnostic_sobol` | `diagnostic_curve` | **point value** of S1/ST over growing N |
| 2 | `dimensionless_pi_group_collapse` | `scatter_collapse` | master-curve test against a Π-group |
| 3 | `fast_subspace_detection` | `sobol_bar` | active-subspace eigenvalue drop |
| 4 | `interaction_matrix_sobol` | `matrix` | pairwise Sᵢⱼ as a param × param **heatmap** |
| 5 | `morris_elementary_effects` | `sobol_bar` | Morris (μ*, σ) OAT screening scatter |
| 6 | `parameter_scan_2d_contour` | `contour` | output as a function of two params |
| 7 | `pi_group_rank_plot` | `ladder` | candidate Π-group formulations ranked by R²/AIC |
| 8 | `sobol_first_total_pair` | `sobol_bar` | Sobol S1 + ST per parameter (scalar output) |

## Proposed 7 new recipes

All 7 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Complement the Sobol-core with other GSA methods (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S1 | `fast_sensitivity_spectrum` | In the FAST (Fourier Amplitude Sensitivity Test) decomposition, what does the frequency spectrum of the output reveal about each parameter's contribution? | `sobol_first_total_pair` (variance-based indices, **no frequency domain**); `morris_elementary_effects` (OAT μ*/σ, no spectrum) | Measurement: **power spectrum** of the output under harmonic parameter forcing. Visual: periodogram with per-parameter fundamental + harmonics highlighted + a noise floor. FAST is a distinct GSA method (frequency-domain) from Sobol (variance-based) and Morris (OAT). | `diagnostic_curve` |
| S2 | `lhs_parameter_space_coverage` | Does the Latin-hypercube sample actually cover the joint parameter space, or are there gaps / clustering? | None — no sampling-design diagnostic currently exists in the modality. | Measurement: **LHS sample coverage** (joint and marginal), not a sensitivity index. Visual: small scatter matrix with marginal histograms + a per-pair discrepancy annotation. Answers a design-of-experiments question no other recipe touches. | `matrix` |
| S3 | `tornado_diagram` | For a one-at-a-time (OAT) sweep, how does the output change when each parameter is varied to its ±Δ bound, ranked by magnitude? | `sobol_first_total_pair` (**global, variance-based**); `morris_elementary_effects` (Morris trajectories, not OAT ±Δ) | Measurement: **OAT local sensitivity** (Δoutput for ±Δparam around a nominal). Visual: classic horizontal tornado bars sorted by width with a baseline line. OAT is a distinct (and still-reviewer-mandated) method from variance-based or Morris-trajectory screening. | `ladder` |

### New unit of analysis — multi-output and bootstrap-CI (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S4 | `sensitivity_by_output_quantity` | Across multiple output quantities (QoIs), how do the Sobol indices of each parameter redistribute? | `interaction_matrix_sobol` (**param × param** for a single output); `sobol_first_total_pair` (single output, S1/ST) | Measurement: **param × output** index matrix (rows = parameters, columns = output quantities). Distinct axis semantics from the pairwise interaction matrix. Supports panels like "S_T of each param for (peak, AUC, decay, …)". | `matrix` |
| S5 | `sobol_bootstrap_convergence` | As sample size grows, how does the bootstrap 95 % CI on each Sobol S1 shrink, and have the top-k rankings stabilised? | `convergence_diagnostic_sobol` (**point value** stability over N, no CI band) | Measurement: **bootstrap CI width** as a function of N, not the point value. Visual: per-parameter S1 point + a shrinking ribbon of bootstrap CI over N, with a rank-flip annotation. Different statistic (uncertainty width vs value stability). | `diagnostic_curve` |

### Alternative visual grammars and time-resolved (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| S6 | `interaction_network_sobol` | As a graph, which parameters form the strongest interaction clusters and which are hubs? | `interaction_matrix_sobol` (**heatmap** of the same Sᵢⱼ data) | Measurement: identical data, **different visual grammar**. Graph layout reveals clusters and hubs that a heatmap collapses. Reviewers commonly ask for both — the matrix for magnitude, the graph for topology. | `conceptual` |
| S7 | `sensitivity_time_evolution` | For a time-resolved output, how do the Sobol indices of each parameter evolve over the output time axis? | All existing recipes produce **scalar** indices for a single output. `parameter_scan_2d_contour` is over two parameters, not time. | Measurement: Sobol S1(t) or ST(t) as a **function of output time**, one curve per parameter. Different aggregation from all existing recipes, which collapse to a single scalar per parameter. | `timecourse_hierarchical_ci` |

## Distinctness summary

All 7 pass the three distinctness tests:

1. **No name collision** with the 8 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different GSA method: FAST / LHS-coverage / OAT-tornado; different unit of analysis: param × output, bootstrap CI, time-resolved; or different visual grammar: interaction *graph* vs *matrix*).
3. **No grammar duplication** — each uses a different family-dispatch rule, or a clearly differentiated visual within the same family (`matrix` is used 3× — for param × param, param × output, and LHS scatter matrix; each row/column carries distinct semantics).

## Invariants this session preserves

- [x] No changes to `core/` (only new files under `src/panelforge_figures/recipes/sensitivity_analysis/` and doc updates).
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 7 recipes use the existing `ModalityAesthetic` — no additions.
- [x] All 7 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 7 → modality goes from **8 → 15** recipes. Total catalog goes from **187 → 194**. Tests projected: **986 → ~1021** (5 per recipe × 7).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
