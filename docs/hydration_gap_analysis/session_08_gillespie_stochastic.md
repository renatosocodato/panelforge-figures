# Session 08 — Gap Analysis: `gillespie_stochastic` (7 → 15, +8)

**Branch:** `v1.1/session-08-gillespie_stochastic`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`gillespie_stochastic` powers the **HOME-GATE-TRAP** dwell analyses and
any stochastic-state-switching manuscript. v1.0 ships the trajectory
+ dwell-violin + waiting-time ECDF + rate-vs-parameter + state
occupancy raster + mean-variance tube + noise power spectrum core
(7 recipes). Missing are the **analytic ↔ sampled** comparisons
(master-equation, τ-leaping), **MFPT / extinction / Fisher-information
matrices**, **burst-size distributions**, **trajectory ACF** and
**stochastic-resonance SNR signatures** reviewers expect.

## Current 7-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `dwell_time_log_violin` | `split_violin` | log-scale dwell per state |
| 2 | `ensemble_mean_variance_tube` | `timecourse_hierarchical_ci` | mean + variance band over time |
| 3 | `noise_power_spectrum` | `diagnostic_curve` | PSD — white / Lorentzian / 1/f |
| 4 | `rate_vs_control_parameter` | `timecourse_hierarchical_ci` | per-transition rates vs param |
| 5 | `state_occupancy_raster` | `heatmap` | per-trial state × time raster |
| 6 | `trajectory_fan_with_fpt` | `timecourse_hierarchical_ci` | SSA trajectory fan with FPT stars |
| 7 | `waiting_time_ecdf_fitted` | `diagnostic_curve` | ECDF vs exponential / gamma fit |

## Proposed 8 new recipes

All 8 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Analytic ↔ sampled comparisons (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| G1 | `master_equation_steady_state` | Does the Gillespie steady-state sampled distribution P(n) match the analytical master-equation solution? | None — no analytic-vs-sampled distribution comparison currently exists | Measurement: **analytical P(n)** line + **sampled histogram** line + KL-divergence / total-variation callout. Different grammar (distribution overlap) from any existing recipe. | `diagnostic_curve` |
| G2 | `tau_leaping_comparison` | How close does a τ-leaping approximation stay to the exact SSA trajectory, and how does error accumulate over t? | `trajectory_fan_with_fpt` (trajectory fan, **no method comparison**) | Measurement: **two-method trace overlay** (exact vs τ-leap) with a residual-over-time secondary panel and a speedup-factor callout. Different grammar (method comparison) from trajectory fan. | `diagnostic_curve` |

### State-space matrices (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| G3 | `mean_first_passage_time_matrix` | Between every pair of states, what is the expected first-passage time MFPT(i, j)? | `trajectory_fan_with_fpt` (first-passage **time markers**, scalar); `state_occupancy_raster` (occupancy, not transitions) | Measurement: **N × N MFPT matrix** (off-diagonal), not a single FPT. Visual: heatmap with diagonal zero reference and top-pair callouts. Different aggregation (pairwise scalar vs per-trial event). | `matrix` |
| G4 | `fisher_information_parameter_estimation` | Which parameters can the data **distinguish**, and where is information lost (Fisher-information matrix)? | None — no parameter-information recipe in modality | Measurement: **K × K Fisher-information matrix** with condition-number callout and the most / least-identifiable eigen-directions. Different role (model identifiability) from every existing recipe. | `matrix` |

### Distributions (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| G5 | `burst_size_distribution` | For transcription-burst-style dynamics, what is the burst-size distribution, and is it geometric / negative-binomial? | `dwell_time_log_violin` (dwell, not **burst size**); `waiting_time_ecdf_fitted` (waiting time, not counts) | Measurement: **burst-count PMF** (discrete), not a dwell or waiting time. Visual: observed PMF bars + fitted geometric / negative-binomial line + mean-burst / CV callout. Different quantity (discrete count, not time). | `diagnostic_curve` |

### Parameter dependence (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| G6 | `extinction_probability_vs_parameter` | As a control parameter varies, what is the probability that the population goes extinct before some horizon? | `rate_vs_control_parameter` (**rates**, not extinction probability) | Measurement: **P_ext(θ)** curves per initial state / horizon, with the θ at which P_ext crosses 0.5 annotated. Different quantity (probability, not rate) from every existing recipe. | `diagnostic_curve` |

### Temporal + SNR (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| G7 | `autocorrelation_of_trajectories` | How fast do the sampled SSA trajectories decorrelate in time, and does the decay differ by state? | `noise_power_spectrum` (frequency-domain PSD, **not ACF**); `ensemble_mean_variance_tube` (mean + variance, no ACF) | Measurement: temporal **ACF(τ)** per state / condition with fitted decay constant τ_c and 1/e reference. Distinct statistic (time-domain ACF) from PSD. | `diagnostic_curve` |
| G8 | `stochastic_resonance_signature` | As the noise amplitude grows, does the signal-to-noise ratio show a non-monotonic peak (stochastic resonance)? | None — no SNR-vs-noise grammar currently exists | Measurement: **SNR(σ)** sampled over a noise-amplitude sweep with a Lorentzian / parabolic fit around the peak and the optimal σ* annotated. Canonical stochastic-resonance signature. | `scatter_collapse` |

## Distinctness summary

All 8 pass the three distinctness tests:

1. **No name collision** with the 7 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different physical quantity, aggregation, or role).
3. **No grammar duplication** — `diagnostic_curve` is used 5× after this session but each is a clearly distinct axis / statistic (PSD / ECDF / analytic vs sampled distribution / τ-leap method comparison / burst PMF / P_ext vs θ / ACF). `matrix` × 2 (MFPT transitions, FIM) with clearly distinct semantics.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 8 recipes use the existing `ModalityAesthetic` (`home_gate_trap` palette).
- [x] All 8 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 8 → modality goes from **7 → 15** recipes. Total catalog goes from **210 → 218**. Tests projected: **1101 → ~1141** (5 per recipe × 8).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
