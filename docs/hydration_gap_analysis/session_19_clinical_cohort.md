# Session 19 — Gap Analysis: `clinical_cohort` (6 → 15, +9, Path 2)

**Branch:** `v1.1/session-19-clinical_cohort`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`clinical_cohort` is the forward-looking modality for ATHENA
downstream (clinical validation). v1.0 currently ships **6 real
recipes** (coordinator listed 3 — plan-vs-reality mismatch; see
below): baseline table viz, CONSORT flow, Cox forest, KM by
stratum, outcome by quartile, and subgroup forest. Missing are the
**ROC with cutoff**, **decision curve**, **calibration plot**,
**competing risks CIF**, **risk-score ladder**, **propensity-score
balance**, **NNT forest**, **adverse-event bar**, and
**time-varying HR** reviewers expect.

> **Plan-vs-reality reconciliation (Path 2).** The coordinator
> (`docs/hydration_coordinator.md`) records `clinical_cohort: 3 →
> 15`. Real v1.0 baseline is 6; three seed names
> (`consort_flow_diagram`, `baseline_characteristics_table_figure`,
> `subgroup_forest_clinical`) already ship as existing recipes, and
> `time_to_event_stratified_km` duplicates `kaplan_meier_by_stratum`.
> To land the 15-target in one session I drop those 4 duplicate
> seeds and propose **+9 new** to hit 6 + 9 = 15 — same Path-2
> pattern as s07 and s16.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `baseline_table_visualization` | `matrix` | Table-1 SMD visualisation |
| 2 | `consort_flow_diagram` | `flow` | CONSORT participant flow |
| 3 | `cox_forest_hazard_ratios` | `coef_forest` | Cox HR per covariate |
| 4 | `kaplan_meier_by_stratum` | `diagnostic_curve` | KM survival curves by stratum |
| 5 | `outcome_by_quartile` | `ladder` | outcome rate × exposure quartile |
| 6 | `subgroup_forest_plot` | `coef_forest` | treatment-effect × subgroup forest |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Discrimination & calibration (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `roc_with_cutoff_optimization` | At what cutoff does the biomarker maximise sensitivity + specificity (Youden), and what is the AUC? | None — no ROC recipe in v1.0 | ROC curve with Youden-index star + CI band + AUC callout. Different axis grammar (sensitivity vs 1-specificity). | `diagnostic_curve` |
| N2 | `calibration_plot_with_hl_test` | Does the predicted probability match the observed outcome rate across deciles (calibration)? | `outcome_by_quartile` (exposure quartile, observational); no calibration | Observed vs predicted deciles with reference y=x line, Hosmer-Lemeshow χ² p-value callout. Different question and grammar. | `scatter_collapse` |
| N3 | `decision_curve_analysis` | Across probability thresholds, does the model's net benefit exceed treat-all / treat-none strategies? | None | Threshold × net-benefit curve with model / treat-all / treat-none reference lines. Different axis pair. | `diagnostic_curve` |

### Survival & time-to-event (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N4 | `competing_risks_cumulative_incidence` | In the presence of competing risks, what are the per-cause cumulative-incidence functions? | `kaplan_meier_by_stratum` (single endpoint, KM 1-S) | **CIF per cause** with Gray's test p-value; different statistic (CIF vs 1-S). | `diagnostic_curve` |
| N5 | `hazard_ratio_over_time_smoothed` | Does the hazard ratio between arms change over follow-up time (proportional-hazards check)? | `cox_forest_hazard_ratios` (single-HR per covariate, static) | Smoothed HR(t) curve with 95 % band and flat-reference line at HR=1; different question (time-varying, PH diagnostic). | `diagnostic_curve` |

### Risk & benefit (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N6 | `risk_score_discrimination_ladder` | Across risk-score tertiles / deciles, does the event rate increase monotonically? | `outcome_by_quartile` (**exposure** quartile); different direction | Per-tertile event rate with reference trend line and monotonicity p; different question (risk-score discrimination, not exposure). | `ladder` |
| N7 | `number_needed_to_treat_forest` | Across subgroups / conditions, what is the NNT to prevent one event (with 95 % CI)? | `subgroup_forest_plot` (treatment-effect HR/OR, not NNT scale) | Per-subgroup NNT ± CI forest with reference line at infinity (no benefit); different outcome metric. | `coef_forest` |

### Causal balance & safety (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `propensity_score_balance_diagnostic` | After propensity-score matching / IPTW, are baseline covariates balanced (SMD < 0.1)? | `baseline_table_visualization` (**unadjusted** SMD) | Before / after paired forest with SMD=0.1 reference band; different axis (paired before/after) and analytic step. | `coef_forest` |
| N9 | `adverse_event_incidence_bar` | Per adverse-event category, how do arm incidences compare? | None | Per-AE horizontal bar of incidence rate per arm with RR annotation + any/serious counts; different content type. | `ladder` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (ROC cutoff, calibration, net benefit, competing risks CIF, PH-violation HR(t), risk-score tertile rate, NNT, PS balance, AE-rate-per-arm).
3. **No grammar duplication** — `diagnostic_curve` × 4 (ROC, DCA, CIF, HR-over-time) with distinct axis pairs; `scatter_collapse` × 1 (calibration); `ladder` × 2 (risk tertile vs AE bar — different axis types); `coef_forest` × 2 (NNT vs PS balance — distinct semantic).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic`.
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 9 → modality goes from **6 → 15** recipes. Total catalog goes from **310 → 319**. Tests projected: **1601 → ~1646** (5 per recipe × 9).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
