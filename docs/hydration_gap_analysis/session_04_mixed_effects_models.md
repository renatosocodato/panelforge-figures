# Session 04 — Gap Analysis: `mixed_effects_models` (9 → 16, +7)

**Branch:** `v1.1/session-04-mixed_effects_models`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`mixed_effects_models` is the most *cross-cutting* modality in the catalog: every Neuron / Nature / Science-style systems-biology paper with hierarchical data (animal → section → cell → protrusion) uses a mixed model, and reviewers reliably demand:

1. a **forest** of fixed-effect estimates,
2. a **raincloud / violin** of the raw data under each effect,
3. a **per-cluster** view (caterpillar + random slopes),
4. at least one **diagnostic** (residuals, PPC).

v1.0 already ships (4) of those (caterpillar, residual diag, PPC, random-slopes), plus the scaffold v4.3 sex × genotype forest, ICC decomposition, Bayesian term densities, marginal-effect ribbons, and an emmeans contrast grid — **9 recipes**.

The 7 catch-up recipes below close the grammar in four directions: (i) a raw-data raincloud tied to a coefficient, (ii) a per-cluster (intercept, slope) scatter, (iii) **model-selection** (AIC / BIC), (iv) **Bayesian contrast densities** (complement to the term-level densities), and the "emmeans-with-pairwise-brackets / partial-residuals / variance-partition" trio that reviewers specifically ask for.

## Current 9-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `bayes_posterior_density_by_term` | `ridge_by_group` | Bayesian term-level posteriors stacked |
| 2 | `emmeans_contrast_grid` | `coef_forest` | grid of pairwise emmeans **contrasts** (differences) |
| 3 | `icc_variance_decomposition` | `matrix` | ICC at each random level |
| 4 | `marginal_effects_ribbon` | `timecourse_hierarchical_ci` | fitted outcome vs continuous predictor, per group, with ribbon |
| 5 | `mixed_model_residual_diagnostic` | `diagnostic_curve` | QQ + residual-vs-fitted |
| 6 | `posterior_predictive_check` | `diagnostic_curve` | PPC overlay (observed vs replicated density) |
| 7 | `random_effects_caterpillar` | `coef_forest` | per-cluster intercept rank with CI |
| 8 | `random_slopes_per_cluster` | `diagnostic_curve` | per-cluster **slope** spaghetti / histogram |
| 9 | `sex_x_genotype_interaction_forest` | `coef_forest` | fixed-effect + interaction forest |

## Proposed 7 new recipes

All 7 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Split-violin / raw-data grammar (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R1 | `sex_stratified_raincloud_with_coef_box` | What does the raw outcome distribution look like under each sex × genotype stratum, with the fitted coefficient + CI overlaid in-panel? | `sex_x_genotype_interaction_forest` (forest of coefficients, **no raw data**); no existing raincloud in modality | Measurement: **raw data raincloud** (violin + box + jitter) per sex × genotype stratum, with an **inset coefficient summary box** (β, 95% CI, p). Provides the data-plus-fit view reviewers demand — the forest alone hides the raw spread. Inset coef box is a new convention for the modality. | `split_violin` |

### Per-cluster random-effects grammar (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R2 | `random_intercepts_vs_slopes_scatter` | Per cluster (animal, batch), how do the random intercept and random slope covary — do fast-baseline clusters also respond more steeply? | `random_effects_caterpillar` (intercepts only, **sorted 1-D**); `random_slopes_per_cluster` (slopes only, **marginal 1-D**) | Measurement: **joint (intercept, slope) per cluster** as a 2-D scatter with per-point ellipse shrunk to cluster-level CI and a marginal-density rug. Captures intercept-slope correlation (the `cor(int, slope)` term of a mixed model) that neither 1-D recipe can show. | `scatter_collapse` |

### Model selection (+1) — new grammar for this modality

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R3 | `model_comparison_aic_bic_ladder` | Among competing mixed-model specifications, which has the lowest AIC / BIC, and by how much? | No model-selection recipe currently exists in the modality. Nearest is the grant/conceptual `executive_summary_tile`, which is a different grammar altogether. | Measurement: **AIC and BIC** (paired) per model specification, with Δ-AIC shown as a horizontal bar from the best fit. Visual: ladder of model rows ordered by AIC, paired dots for AIC vs BIC, and a Δ-AIC = 2 / 4 / 7 reference strip. Fills an obvious gap — reviewers explicitly ask "why these random effects and not others?", and this is the recipe that answers. | `ladder` |

### Bayesian-contrast grammar (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R4 | `posterior_contrast_density` | What is the full posterior distribution of each *contrast* (Δ between groups), with 95 % HDI and probability-of-direction? | `bayes_posterior_density_by_term` (term-level posteriors — **absolute coefficients**, not differences); `emmeans_contrast_grid` (point + CI, **not full density**) | Measurement: **Δ-posteriors** (contrast densities), not term posteriors. Visual: stacked ridgeline of Δ-densities per contrast with 95 % HDI, P(Δ > 0), and 0-reference. Different unit of analysis (differences, not terms) and different visual depth (full density, not point+CI). | `ridge_by_group` |

### Diagnostic / interpretation grammar (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R5 | `partial_residuals_vs_predictor` | For a given continuous predictor, what is the predictor-specific partial-residual pattern, and does the fitted term capture it? | `mixed_model_residual_diagnostic` (QQ + residual-vs-**fitted**, not per-predictor); `marginal_effects_ribbon` (fitted curve, **not residuals**) | Measurement: **partial residuals** (e_ij + β̂·x_ij) vs a specific predictor, overlaid with the fitted partial-effect curve and per-group LOESS. Standard diagnostic for mis-specification of a continuous term; **different residual type** from the existing residual-vs-fitted diagnostic. | `diagnostic_curve` |
| R6 | `group_level_emmeans_with_pairwise` | What are the estimated marginal means per condition, **in the response scale**, with pairwise-significance brackets above the groups? | `emmeans_contrast_grid` (**differences**, matrix view); `sex_x_genotype_interaction_forest` (**coefficients**, not response-scale means) | Measurement: **emmeans on the response scale per group** (absolute levels), with pairwise brackets (Bonferroni / Tukey). Distinct from `emmeans_contrast_grid` which plots the **Δ between groups in a grid**; this shows the **absolute emmean per group with pairwise significance arcs** — the convention reviewers ask for in response figures. | `coef_forest` |

### Variance-partition grammar (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| R7 | `fixed_vs_random_effect_partition` | How is the total outcome variance split into **fixed-effect** vs **random-effect** vs **residual** variance? | `icc_variance_decomposition` (**random-level variance fractions**: level-2 / level-3 / level-4 — strictly among the *random* side); no existing fixed-vs-random partition | Measurement: **marginal R² vs conditional R² vs residual** (Nakagawa-Schielzeth partition) as a stacked bar per model, plus a fixed-term contribution breakdown inside the fixed stripe. Distinct from ICC, which partitions **within** the random side only; this partitions **fixed vs random vs residual**. | `matrix` |

## Distinctness summary

All 7 pass all three existing distinctness tests:

1. **No name collision** with the 9 existing recipes. (Verified against `src/panelforge_figures/recipes/mixed_effects_models/__init__.py`.)
2. **No scientific-question duplication** — each answers a question that no existing recipe answers (different aggregation level, different statistic type, or different visual grammar; see the "why distinct" column).
3. **No visual-grammar duplication** — each uses a different family-dispatch quality rule, or a clearly differentiated visual within the same family (e.g., `coef_forest` is already used 3× but for differences / ranks / fixed-effects; R6 uses it for absolute emmeans with pairwise brackets — the brackets are the new element).

## Invariants this session preserves

- [x] No changes to `core/` (only new files under `src/panelforge_figures/recipes/mixed_effects_models/` and doc updates).
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 7 recipes use existing `ModalityAesthetic` — no additions to the aesthetic object.
- [x] All 7 families dispatch to existing `quality_rules.py` functions (no new rule functions).
- [x] Style-drift ratchet: will reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 7 → modality goes from **9 → 16** recipes. Total catalog goes from **180 → 187** (target for v1.1 end-state: ≥ 320). Tests projected: **951 → ~1007** (8 per recipe).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
