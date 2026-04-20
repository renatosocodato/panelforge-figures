# Session 06 — Gap Analysis: `redox_imaging` (8 → 15, +7)

**Branch:** `v1.1/session-06-redox_imaging`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`redox_imaging` powers the **µRedoxScape** submission. v1.0 ships the
bistability / paracrine-coupling / bimodality / drift-diffusion /
transition-rate / multiplicative-noise-σ-vs-μ / single-cell-density
core (8 recipes) but is missing the "calibration", "time-above-
threshold", "1-D coupling kernel fit", "Langevin noise decomposition",
"spatial switching-rate map", "condition-level bimodality stats", and
"temporal autocorrelation" panels reviewers expect alongside the
existing grammar.

## Current 8-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `bimodality_coefficient_grid` | `heatmap` | BC over **condition × time** |
| 2 | `bistability_hysteresis_loop` | `hysteresis_loop` | forward / reverse ramp |
| 3 | `drift_diffusion_decomposition` | `diagnostic_curve` | state-dependent drift + diffusion |
| 4 | `multiplicative_noise_diagnostic` | `scatter_collapse` | σ vs μ scaling law |
| 5 | `paracrine_coupling_length_map` | `heatmap` | spatial ratio field + λ callout |
| 6 | `ratio_trajectory_with_phase_annotation` | `diagnostic_curve` | per-cell ratio(t) with phase shading |
| 7 | `redox_state_transition_diagram` | `flow` | reduced ↔ intermediate ↔ oxidized rates |
| 8 | `single_cell_ratio_distribution` | `ridge_by_group` | per-condition ratio KDE stack |

## Proposed 7 new recipes

All 7 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Calibration + stats (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R1 | `roGFP2_ratio_vs_disulfide_titration` | For a roGFP2 biosensor, what is the calibration curve of measured ratio vs. disulfide fraction, including fitted E₀ / slope / R²? | None — no calibration workflow currently exists | **Calibration** (biosensor→biology conversion). Scatter of measured ratios at known titration points + sigmoid fit + E₀ callout. Distinct role (calibration, not measurement) from every existing recipe. | `scatter_collapse` |
| R2 | `bimodality_kurtosis_vs_conditions` | Across conditions, how do single-cell bimodality statistics (BC, kurtosis, Hartigan's dip) compare? | `bimodality_coefficient_grid` (**condition × time heatmap**, single statistic) | Measurement: **three** bimodality statistics (BC, κ, dip) per condition; condition-level, not condition × time. Visual: grouped bar ladder with significance dots for each statistic. Different aggregation + multi-stat. | `ladder` |

### Dynamics + diagnostics (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R3 | `time_above_threshold_distribution` | How long do individual cells spend above the oxidation threshold, and how does that duration distribute per condition? | `ratio_trajectory_with_phase_annotation` (per-cell ratio curve, not a derived duration); `single_cell_ratio_distribution` (instantaneous ratio KDE, not duration) | Measurement: **derived per-cell duration** above a threshold over a fixed time window. Visual: per-condition CCDF / survival-style curves with median-duration markers. Different aggregation (duration vs instantaneous). | `diagnostic_curve` |
| R4 | `paracrine_kernel_fit` | Fitted to pairwise-cell data, what is the 1-D paracrine coupling kernel K(r), and what is the decay length λ? | `paracrine_coupling_length_map` (2-D **spatial ratio field**, not 1-D kernel) | Measurement: radial decorrelation K(r) between pairs as a **1-D curve** with a fitted exponential or Gaussian kernel and a λ + R² callout. Different axis semantics (r, not (x, y)) and different model (kernel, not ratio map). | `diagnostic_curve` |
| R5 | `multiplicative_vs_additive_noise_diagnostic` | Is the Langevin noise on ratio(t) better explained by a Y-independent additive model, or a Y-dependent multiplicative D(Y)? | `multiplicative_noise_diagnostic` (σ-vs-μ **scaling scatter** — a *single* diagnostic slope, not a model comparison) | Measurement: ξ(t) = Y(t+Δ) − Y(t) − μ(Y)·Δ residuals vs Y, with **two competing model fits** (D_add constant vs D_mult(Y) = σ²·Y²) and an AIC-style preference callout. Model-comparison grammar, not a single scaling law. | `diagnostic_curve` |

### Spatial + temporal (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R6 | `redox_state_switching_frequency_map` | Across the imaging field, where do cells switch redox state most frequently? | `paracrine_coupling_length_map` (**ratio** map, not switching rate); `redox_state_transition_diagram` (aggregated rates, **not spatial**) | Measurement: per-pixel / per-cell switching **rate** field (counts / time). Visual: heatmap with cell centroids scaled by switching rate. Different physical quantity (rate vs ratio) and different view vs the transition diagram (spatial vs aggregated). | `heatmap` |
| R7 | `ratio_autocorrelation_decay` | How fast does the redox ratio decorrelate in time, broken down by state (reduced vs oxidized)? | `drift_diffusion_decomposition` (**drift + diffusion coefficients**, not ACF); `ratio_trajectory_with_phase_annotation` (raw trajectory, not ACF) | Measurement: temporal **autocorrelation function** ACF(τ) of ratio(t) per state, with fitted τ_reduced vs τ_oxidized and a crossover annotation. Different statistic (ACF, not drift) and different aggregation (per-state). | `diagnostic_curve` |

## Distinctness summary

All 7 pass the three distinctness tests:

1. **No name collision** with the 8 existing recipes (note: `multiplicative_vs_additive_noise_diagnostic` shares a prefix with `multiplicative_noise_diagnostic` but remains a distinct module name + distinct visual grammar — scatter-collapse scaling law vs residual-fit model comparison).
2. **No question duplication** — each answers a question no existing recipe answers (different physical quantity, aggregation, or model-comparison role).
3. **No grammar duplication** — `diagnostic_curve` appears 4× after this session but each is a different axis / statistic (drift-diffusion coefficients, time-above-threshold survival, 1-D paracrine kernel, Langevin model comparison, temporal ACF); `heatmap` and `ladder` each appear with clearly differentiated semantics.

## Invariants this session preserves

- [x] No changes to `core/` (only new files under `src/panelforge_figures/recipes/redox_imaging/` and doc updates).
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 7 recipes use the existing `ModalityAesthetic` — no additions.
- [x] All 7 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 7 → modality goes from **8 → 15** recipes. Total catalog goes from **194 → 201**. Tests projected: **1021 → ~1056** (5 per recipe × 7).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
