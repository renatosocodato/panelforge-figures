# Session 14 — Gap Analysis: `biophysics_scaling` (5 → 15, +10)

**Branch:** `v1.1/session-14-biophysics_scaling`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`biophysics_scaling` underwrites the **Manuscript 3 collapse** narrative
and the force-balance / Π-group analysis from `gc-chirrut`. v1.0 ships
the **slope-box log-log**, **master-curve collapse**, **power-law tail
diagnostic**, **Euler buckling** and **force-length characteristic** (5
recipes). Missing are the **theory-overlay log-log**, **universality-
class comparison**, **fractal dimension scaling**, **stress-strain
regime map**, **Kn × Re regime diagram**, **1-D energy landscape
cartoon**, **exponent CI forest**, **characteristic-time divergence**,
**Π-group sensitivity bar** and **crossover-scaling diagnostic**
reviewers expect.

> **Note on target count.** The coordinator table
> (`docs/hydration_coordinator.md`, line 14) records `biophysics_scaling:
> 5 → 15`. The prior session-13 close-out message quoted `5 → 12 (+7)`,
> which conflicts with the coordinator. This gap analysis follows the
> authoritative coordinator target of **+10 → 15**.

## Current 5-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `buckling_critical_force_plot` | `diagnostic_curve` | Euler buckling F ∝ L⁻² |
| 2 | `force_length_characteristic` | `diagnostic_curve` | contractile force vs length (active + passive) |
| 3 | `log_log_scaling_with_slope_box` | `scatter_collapse` | single power law with fitted slope |
| 4 | `master_curve_collapse` | `scatter_collapse` | multi-condition rescaling collapse |
| 5 | `power_law_tail_diagnostic` | `diagnostic_curve` | tail exponent of a distribution |

## Proposed 10 new recipes

All 10 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits. The two seed names that would duplicate existing recipes (`dimensional_collapse_multiconditions` ≡ `master_curve_collapse`; `length_tension_characteristic` ≡ `force_length_characteristic`) are **dropped** and replaced with `pi_group_sensitivity_bar` and `crossover_scaling_diagnostic` to maintain distinctness.

### Scaling & collapses (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `log_log_with_theory_line` | Is my data consistent with a **theoretically predicted** scaling exponent, and how big are the residuals? | `log_log_scaling_with_slope_box` (**fitted** slope, no prior) | **Theory-predicted** reference line overlaid on data, plus residuals-from-theory inset with per-point deviation; different question (consistency with theory vs "what is α?"). | `scatter_collapse` |
| N2 | `universality_class_comparison` | Which **universality class** (e.g. mean-field, Ising-2D, KPZ) best matches the data? | `master_curve_collapse` (rescales data to one unknown master); `log_log_with_theory_line` (single theory curve) | **Multiple theoretical universality curves** overlaid with per-curve residual bars; different answer (choose one of several classes vs confirm collapse). | `scatter_collapse` |
| N3 | `fractal_dimension_scaling` | What is the box-counting fractal dimension D_f of a structure across scales? | `log_log_scaling_with_slope_box` (generic α) | **N(L) ~ L^D_f** specifically with scale-window inset showing D_f(L) variation; semantic is a dimensional (D_f) not an empirical exponent; adds crossover-scale annotation. | `scatter_collapse` |

### Regime & state diagrams (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N4 | `stress_strain_regime_map` | Where does the material transition from elastic to plastic to failure? | None — no σ-ε regime recipe in v1.0 | **σ vs ε curve** with elastic / plastic / failure bands shaded, yield point + ultimate stress markers, Young's modulus inset. Axis grammar is stress × strain, not log-log scaling. | `matrix` |
| N5 | `knudsen_reynolds_regime_diagram` | Given my dimensionless numbers, which flow / transport regime does my system sit in? | None — no dimensionless-regime map | **Kn × Re log-log grid** with continuum / slip / transition / free-molecular regions shaded, sample points overlaid. Both axes dimensionless — distinct axis grammar. | `matrix` |
| N6 | `energy_landscape_1d_cartoon` | How does a 1-D energy landscape U(x) explain the state lifetimes and transitions? | None — no energy-landscape cartoon | Schematic **U(x)** curve with wells, barriers, k_B T scale, optional basin labels; conceptual (not data). | `conceptual` |

### Exponents & time scales (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N7 | `scaling_exponent_ci_forest` | Across studies / conditions, what is the distribution of the fitted exponent α and its uncertainty? | `log_log_scaling_with_slope_box` (single α); no exponent forest | **Per-study α ± CI** ladder with reference vertical line at theoretical value; different grammar (forest of exponents vs one scatter). | `coef_forest` |
| N8 | `characteristic_time_vs_control` | How does the characteristic time τ diverge or decay as a control parameter is varied? | `buckling_critical_force_plot` (static F vs L); no τ-vs-control recipe | **τ(p)** with critical-divergence or Arrhenius form, fitted exponent + residuals; variable semantics is time (not force) and the emphasis is near-critical divergence / activation energy. | `diagnostic_curve` |
| N9 | `pi_group_sensitivity_bar` | Which **Π-group** (Buckingham Π) contributes most to the response variable variance? | None — no Π-group decomposition recipe | **Horizontal Π-group bars** ranked by contribution with stacked error / source bands; supports `gc-chirrut`'s Manuscript 3 Π-group analysis. | `ladder` |

### Crossover regimes (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N10 | `crossover_scaling_diagnostic` | Does the data **cross over** from one power-law regime to another at a scale ξ? | `log_log_scaling_with_slope_box` (single regime); `master_curve_collapse` (single master) | **Two-slope piecewise-power** diagnostic with crossover scale ξ marked, local-slope d log y / d log x inset reveals the transition. Different answer (detect crossover, not confirm a single exponent). | `diagnostic_curve` |

## Distinctness summary

All 10 pass the three distinctness tests:

1. **No name collision** with the 5 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (theory overlay, universality selection, fractal D, regime map, dimensionless regime, energy cartoon, exponent forest, τ-vs-control, Π-groups, crossover).
3. **No grammar duplication** — `scatter_collapse` × 3 (theory line, universality, fractal) each with distinct overlays; `matrix` × 2 (σ-ε regime, Kn-Re regime) both with shaded regions but different axis pairs; `diagnostic_curve` × 2 (τ-vs-control, crossover) each with distinct inset semantics.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 10 recipes use the existing `ModalityAesthetic`.
- [x] All 10 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 10 → modality goes from **5 → 15** recipes. Total catalog goes from **261 → 271**. Tests projected: **1356 → ~1406** (5 per recipe × 10).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
