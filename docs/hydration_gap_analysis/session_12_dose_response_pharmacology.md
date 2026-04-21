# Session 12 — Gap Analysis: `dose_response_pharmacology` (5 → 15, +10)

**Branch:** `v1.1/session-12-dose_response_pharmacology`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`dose_response_pharmacology` powers the **ATHENA** pharmacology panels
and any sex-stratified drug-response work. v1.0 ships Hill fit with
CI, IC50 forest, Schild regression, isobologram and 2-D drug-combo
heatmap (5 recipes). Missing are the **sex-stratified dose response**,
**IC50-vs-Ki concordance**, **selectivity tornado**, **dose × time
matrix**, **synergy-score comparison** (Bliss vs Loewe), **normalised
EC50 forest**, **pharmacophore SAR heatmap**, **polypharmacology
radar**, **washout/recovery kinetics**, and **clustered SAR** panels
reviewers reliably request.

## Current 5-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `drug_combo_heatmap` | `heatmap` | dose₁ × dose₂ effect/synergy map |
| 2 | `hill_fit_with_ci` | `diagnostic_curve` | single Hill curve + CI |
| 3 | `ic50_forest_across_compounds` | `coef_forest` | compounds ranked by IC50 |
| 4 | `isobologram_combination` | `scatter_collapse` | iso-effect line + combo points |
| 5 | `schild_regression` | `scatter_collapse` | log(CR-1) vs log[B], pA2 |

## Proposed 10 new recipes

All 10 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Dose-response variants (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| D1 | `dose_response_sex_stratified` | For a sex-stratified dataset, do male and female Hill curves differ, and is the interaction significant? | `hill_fit_with_ci` (**single curve**, no sex stratification) | Two Hill curves (F, M) on the same axis with per-sex IC50 markers + sex×dose interaction p-value callout. Different unit of analysis (stratified by sex). | `diagnostic_curve` |
| D2 | `dose_response_time_matrix` | Over a concentration × time grid, when and at what concentration does the effect peak? | `drug_combo_heatmap` (**dose₁ × dose₂**, not dose × time); `hill_fit_with_ci` (single dose curve) | **Concentration × time** heatmap with peak-time isochrone overlay and a (peak conc, peak time) annotation. Different axis semantics. | `heatmap` |
| D3 | `response_rebound_kinetics` | After washout, how does the response recover — does it overshoot (rebound) before returning to baseline? | None — no time-course recovery panel exists | Response(t) post-wash with a dashed vertical "washout onset" reference, baseline, rebound-peak marker and recovery-τ fit. Distinct role (kinetic recovery). | `diagnostic_curve` |

### Potency / affinity correlation + selectivity (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| D4 | `ic50_vs_target_affinity_scatter` | Across compounds, how well does functional IC50 correlate with binding Ki? | `ic50_forest_across_compounds` (1-D IC50 ranking, **no Ki axis**) | **Ki vs IC50** log-log scatter with identity reference line, OLS fit, Pearson r and per-mechanism colour coding. Different grammar (correlation) vs ranking. | `scatter_collapse` |
| D5 | `selectivity_index_tornado` | For a lead compound, how selective is it across the target panel (fold-IC50 ratios), and which off-targets break selectivity? | `ic50_forest_across_compounds` (compound × IC50, **single target**) | **Fold-IC50 vs on-target** per off-target as a horizontal tornado sorted by magnitude, with cliff-marker for the 10-fold selectivity threshold. Different axis (off-targets, not compounds). | `ladder` |
| D6 | `dose_normalized_ec50_forest` | Across a compound series, how do EC50s compare when normalised to the most potent lead (x-fold)? | `ic50_forest_across_compounds` (**raw IC50 bars**, unnormalised) | **x-fold EC50 / EC50_lead** forest, log-x, with reference at 1× and category colouring by mechanism. Different statistic (fold-change, not absolute). | `coef_forest` |

### Combination + SAR grammar (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| D7 | `synergy_score_bliss_loewe` | For a panel of drug pairs, how do Bliss and Loewe synergy scores compare — do the two models agree on which pairs are synergistic? | `isobologram_combination` (**iso-effect line**, single pair); `drug_combo_heatmap` (**2-D effect map**, single pair) | **Scatter of Bliss vs Loewe** across N drug pairs with diagonal agreement line, synergy-threshold lines at S ≥ 0.1, and per-pair labels. Different unit (many pairs) and different comparison (two methods). | `scatter_collapse` |
| D8 | `pharmacophore_activity_heatmap` | For a pharmacophore × compound matrix, which structural features drive activity? | None — no SAR heatmap exists | **Feature × compound** activity heatmap with hierarchical clustering rows + active-feature row annotation. Distinct grammar. | `heatmap` |
| D9 | `compound_cluster_structure_activity` | Cluster compounds by their structural fingerprints, which cluster has the best mean activity? | `ic50_forest_across_compounds` (individual compounds, no clustering) | Compound **PCA / dendrogram + mean activity per cluster** in a split panel. Different aggregation (cluster level) and different visual (cluster + activity bar). | `conceptual` |

### Polypharmacology (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| D10 | `polypharmacology_radar` | For a compound, what is its activity profile across N targets (polypharmacology radar)? | `selectivity_index_tornado` (off-target **ratios**, 1-D ranking); `ic50_vs_target_affinity_scatter` (scatter) | **Polar radar** of per-target activity with one polygon per compound, overlaid on a shared target axis. Different visual grammar (polar multi-axis). | `radar` |

## Distinctness summary

All 10 pass the three distinctness tests:

1. **No name collision** with the 5 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different statistic, aggregation, axis, or grammar).
3. **No grammar duplication** — `diagnostic_curve` × 3 (Hill, sex-stratified Hill, rebound kinetics) with distinct roles; `heatmap` × 3 (combo, dose×time, SAR); `coef_forest` × 2 (IC50 ranking, fold-EC50); `scatter_collapse` × 4 (isobologram, Schild, IC50-vs-Ki, Bliss-vs-Loewe) all with distinct axis semantics.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 10 recipes use the existing `ModalityAesthetic` (`mechanism_class` palette).
- [x] All 10 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 10 → modality goes from **5 → 15** recipes. Total catalog goes from **241 → 251**. Tests projected: **1256 → ~1306** (5 per recipe × 10).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
