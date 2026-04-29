# CDC42 factorial companion pack tracker

**Version label:** `[1.5.0-beta-cdc42_factorial_companion]` (sub-tags `-w1` … `-w4`)
**Scope:** ~25 new recipes scattered across 6 existing modalities + 2 new `core/` shims, landed across 4 user-gated waves. Pack pattern inherited from `[1.4.0-beta-disc1_manuscript_companion]` (PRs #39–#43; tag `v1.4.0-beta-disc1_manuscript_companion`).
**Anchor manuscript:** `/Users/renatosocodato/Desktop/cdc42_fxm_manuscript/submission_collaboration_bundle` — Cdc42 conditional knockout (CKO) microglial-surveillance paper with **Female × Male × CTL/CKO 2 × 2 factorial** design ("fxm" = Female × Male).
**Plan file:** `~/.claude/plans/shimmying-mapping-hammock.md`

## Why this pack

The just-shipped disc1_manuscript_companion pack (31 recipes; v1.4.0-beta) closed the cytoskeleton + intravital + universal-QA gaps. Cross-referencing the cdc42_fxm manuscript's full figure inventory (47 main panels in F1–F6 + 28 supplementary panels in SF1–SF6 + 6 numbered tables + Supplementary Table R1) against the resulting **423-recipe catalog** identifies a remaining gap of:

- **15 genuinely-missing high-end primitives** — Bayes-factor arrow plots, multiverse robustness curves, multi-omic concordance, panel provenance ledgers, two-way ANOVA summaries, route-geometry compact screens, pathway-space triangulation, dissipation-quartile compositional bars.
- **10 near-match variants** — extensions of existing recipes for switching-frequency callouts, sign-concordance overlays, descriptive ellipses, sex × genotype factorial fingerprint composites.

**Total: ~25 new recipes**, suitable for a 4-wave companion pack. Catalog grows 423 → 448.

## Heavy-deps decision: zero new top-level deps

Inherits the Option D inline-shim discipline. Two small new `core/` shims (~100 LOC combined):

- **`core/bayes_factor_utility.py`** (~40 LOC) — BIC-derived approximation `bf_from_bic(bic_alt, bic_null) → BF₀₁` + decisive / strong / moderate / anecdotal threshold helpers (Wagenmakers 2007). Replaces a `BayesFactor` R-package equivalent.
- **`core/multiverse_specification_utility.py`** (~60 LOC) — `multiverse_audit(specs, results) → (effect_size_grid, robust_flag_vector)` for specification-curve sensitivity analyses (Steegen 2016). Pure-numpy.

No new top-level deps. No `BayesFactor` / `JASP` / `multiverse-r` / etc.

## Modality-boundary distribution: scatter across 6 existing modalities

Per governance §9, no new modalities. The 25 recipes scatter as:

| Modality | Δ (this pack) | Pre-pack | After w4 |
|---|---|---|---|
| `meta_and_diagnostic` | +5 | 21 | **26** |
| `omics_differential` | +6 | 16 | **22** |
| `mixed_effects_models` | +4 | 16 | **20** |
| `biophysics_scaling` | +4 | 47 | **51** |
| `actin_microtubule_morphometry` | +3 | 47 | **50** |
| `intravital_imaging` | +3 | 58 | **61** |
| **Total catalog** | **+25** | **423** | **448** |

## Summary

| Metric | Start | After W1 | After W2 | After W3 | After W4 |
|---|---|---|---|---|---|
| Pack recipes landed | 0 | 6 | 12 | 19 | **25 (final)** |
| Total catalog recipes | 423 | 429 | 435 | 442 | **448 (final)** |
| New `core/` shims | 0 | 2 | 2 | 2 | **2 (final)** |
| Modalities touched | 0 | 1 | 2 | 5 | **6 (final)** |

## Per-wave status

| Wave | Scope | Status | Branch | Merged tag | Notes |
|---|---|---|---|---|---|
| w1 | Universal robustness primitives + provenance (+6 in `meta_and_diagnostic`): Bayes-factor arrow plot, panel provenance ledger, cross-contrast correlation, multiverse classification, multiverse spec curve, proxy-alignment forest. Pioneers 2 new `core/` shims (`bayes_factor_utility`, `multiverse_specification_utility`). | **merged** | `beta-cdc42-companion-w1` | — (squash-merged PR #44; commit `c51965d`) | 3 commits, 2 visual-QA fit-ups (W1.2 fontsize 8.0 → 8.2 ratchet snap; W1.6 OVERFIT label moved right of in-sample marker), 5 sub-contracts added, 13 new utility tests, total tests 2218 → 2261; CI green |
| w2 | Multi-omic integration (+6 in `omics_differential`): proteome × phospho concordance, module concordance, pathway-space triangulation, pathway-space bridge, GGE permutation bar, sign-concordance heatmap. Pioneers `omics_differential/_shared.py`. | **review** | `beta-cdc42-companion-w2` | — (PR open) | 3 commits, 4 visual-QA fit-ups (W2.1 unused linregress vars; W2.4 + W2.5 lw=2.0 → 2.2; all 5 W2 titles fontsize 8.0 → 8.2; W2.5 callout opposite-side placement), 5 sub-contracts pioneered, total tests 2261 → 2291 |
| w3 | Factorial statistics + sex-stratified validation (+7): two-way ANOVA, sex-stratified ROC, mediation slope, pre/post slope by module, Sholl radial histogram, fingerprint trio composite, switch-callout extension. | pending | — | — | Depends on w2 |
| w4 | Energetic / thermodynamic + narrative integration (+6): quartile stacked bar, route-geometry screen, resilience index bar, dissipation-quartile PCA ellipses, transition-matrix DD callout, residence-time KM with KS overlay. Closes pack at 25/25. | pending | — | — | Depends on w3; closes pack |

Status legend:
- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed

## Wave 1 — universal robustness primitives + provenance (+6) [merged]

**Why first.** All 6 recipes are biology-agnostic primitives reusable across any future rigorous-design / multiverse / multi-omic manuscript. They form the substrate for the cdc42_fxm manuscript's reviewer-proof supplementary panels (SF2G multiverse, SF4B robustness classification, SF4D cross-contrast correlation) plus the methods-section panel-provenance ledger (Supp Table R1) and the F2J Bayes factor arrow plot. The proxy-alignment forest (F4D) belongs here too because it generalises across any multi-readout in-sample-vs-LOOCV audit.

### Recipe roster (Wave 1)

| ID | Recipe | Family | Required fields | Precedent to mirror |
|---|---|---|---|---|
| W1.1 | `bayes_factor_arrow_plot` | `coef_forest` | `rows: list[BayesFactorRow]` (label + bf_01 + threshold class) | new — uses `core/bayes_factor_utility` |
| W1.2 | `panel_provenance_ledger_table` | `matrix` | `rows: list[PanelProvenanceRow]` (panel_id + dataset_layer + support_class + n) | new — Supp Table R1 visual surrogate |
| W1.3 | `cross_contrast_correlation_matrix` | `matrix` | `correlation: list[list[float]]` + `contrast_labels: list[str]` | new — between-contrast correlation grid |
| W1.4 | `multiverse_robustness_classification_bar` | `matrix` | `specs: list[MultiverseSpec]` (specification + outcome class) | new — uses `core/multiverse_specification_utility` |
| W1.5 | `multiverse_specification_curve` | `scatter_collapse` | `specs: list[MultiverseSpec]` | new — specification curve display |
| W1.6 | `proxy_alignment_in_vs_loocv_forest` | `coef_forest` | `entries: list[ProxyAlignmentEntry]` (in_sample_R2 + loocv_R2 + proxy) | new — paired-R² forest |

### Family-rule satisfaction checklist

- **W1.1, W1.6** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by per-row arrow / dual marker + threshold reference (W1.1: BF=1; W1.6: zero R² reference).
- **W1.2, W1.3, W1.4** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by row-coloured `pcolormesh` (W1.2 + W1.3) or annotated cell patches (W1.4).
- **W1.5** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by per-spec scatter + sorted-effect-size envelope as the fit line.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/core/bayes_factor_utility.py` | **NEW** | `bf_from_bic(bic_alt, bic_null) → float` + threshold-classification helper (~40 LOC, pure numpy / scipy.stats). Replaces a `BayesFactor` R-package equivalent. |
| `src/panelforge_figures/core/multiverse_specification_utility.py` | **NEW** | `multiverse_audit(specs, results) → (effect_size_grid, robust_flag_vector)` (~60 LOC, pure numpy). Replaces a `multiverse-r` equivalent. |
| `src/panelforge_figures/core/__init__.py` | edit | Export both new utilities. |
| `tests/test_bayes_factor_utility.py` | **NEW** | 6 tests: BIC delta → BF round-trip, decisive threshold detection, edge cases (equal BIC → BF=1), input validation, deterministic pass-through, threshold-class boundary. |
| `tests/test_multiverse_specification_utility.py` | **NEW** | 6 tests: shape, sorted-effect ordering, ROBUST / FRAGILE / NON_SIG classification, deterministic-under-seed, empty-input handling, threshold-bound semantics. |
| `recipes/meta_and_diagnostic/_shared.py` | edit | Adds 5 sub-contracts: `BayesFactorRow`, `PanelProvenanceRow`, `CrossContrastEntry`, `MultiverseSpec`, `ProxyAlignmentEntry`. |
| 6 new recipe modules under `recipes/meta_and_diagnostic/` | **NEW** | One per recipe |
| `recipes/meta_and_diagnostic/__init__.py` | edit | Register 6 new recipes; modality 21 → 26 (+5 — but listed as 6 because W1 includes the proxy-alignment forest which lives in mixed_effects per the original modality-distribution table; final count: 5 new in meta + 1 in mixed_effects). **Decision:** keep all 6 in `meta_and_diagnostic` since proxy-alignment is biology-agnostic; revise per-modality counts at end of wave. |
| `tests/test_contracts.py` | edit | Bump `counts["meta_and_diagnostic"] == 21` → `27` (=21 + 6). |

### `_demo()` seed convention (Wave 1)

All Wave 1 demos use seeded RNG (`np.random.default_rng(80X)`) and biology-agnostic synthetic data so the recipes are reusable beyond the cdc42 pack:

- W1.1: 4 secondary descriptors with BFs spanning anecdotal (BF₀₁ ≈ 1) → strong (BF₀₁ ≈ 6); reference threshold at BF=3.
- W1.2: 12 panel rows with mixed support classes (`main_inference`, `support_layer`, `constraint_layer`, `discovery_layer`); colour-coded.
- W1.3: 5×5 between-contrast correlation; off-diagonal values ~0.2 (independent contrasts).
- W1.4: 12 specifications across method × parameter; 7 ROBUST, 3 FRAGILE, 2 NON_SIG.
- W1.5: 25 specifications sorted by effect size; horizontal line at zero, shaded ROPE band.
- W1.6: 6 proxies with paired in-sample and LOOCV R²; one shows negative-R² overfit pattern.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| W1.1 BF arrow visualisation — risk that arrows look like CI segments | Use distinct arrow head + tail markers; threshold reference line at BF=1 (anecdotal); colour-code by threshold class (decisive / strong / moderate / anecdotal). |
| W1.2 provenance ledger has many columns (panel_id, dataset_layer, n_mice, n_obs, support_class, manuscript_status) — risk of cell-text crowding | Cap demo at 12 rows; left-align text; colour-code support_class column only; abbreviate dataset_layer ('main', 'supp', 'methods'). |
| W1.5 specification curve — many specs (25+) make x-axis crowded | Sort by effect size; show every spec as a tick on the lower x-axis with ROPE shading; only label specs at extremes. |
| W1.6 paired R² forest — risk of confusion between in-sample and LOOCV markers | Distinct marker shape (filled circle vs hollow square); per-row connecting line; legend explicit. |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 2218 + Wave 1 recipe smoke / quality / contracts (~12 new) + 12 utility tests = ~2242.
2. `pytest tests/test_recipes_smoke.py -k meta_and_diagnostic` — 27 demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k meta_and_diagnostic` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet at 20/20.
5. `pytest tests/test_bayes_factor_utility.py` + `tests/test_multiverse_specification_utility.py` — green.
6. Gallery regenerate `meta_and_diagnostic/` — 27 PNGs.
7. Eyeball each new panel; estimate **3–5 visual-QA fit-ups**.

## Wave 2 — multi-omic integration (+6) [gap-analysis]

**Why next.** Wave 1 shipped the universal-robustness primitives.
Wave 2 lands the **F4 multi-omic integration cluster** (proteome
× phosphoproteome concordance, GEF/GAP/Effector module
concordance, GGE branch-selectivity permutation, pathway-space
triangulation/bridge, sign-concordance overlay) — the manuscript's
Figure 4 + Figure 5K-L narrative around how proteome and
phosphoproteome capture **independent** dimensions of sex biology.
**Pioneers `omics_differential/_shared.py`** with 5 nested
sub-contracts (no `_shared.py` exists for this modality yet).

### Recipe roster (Wave 2)

| ID | Recipe | Modality | Family | Required fields | Panel |
|---|---|---|---|---|---|
| W2.1 | `proteome_phosphoproteome_pathway_scatter` | omics_differential | `scatter_collapse` | `pairs: list[ProteomePhosphoConcordanceRow]` (pathway × proteome score × phospho score) | F4B |
| W2.2 | `module_concordance_signed_heatmap` | omics_differential | `matrix` | `cells: list[ModuleConcordanceCell]` (module × condition × signed score) | F4C |
| W2.3 | `pathway_space_triangulation_heatmap` | omics_differential | `matrix` | `layers: list[PathwaySupportLayer]` (theme × match-tier × support score) | F5K |
| W2.4 | `pathway_space_bridge_summary_heatmap` | omics_differential | `matrix` | `layers: list[PathwaySupportLayer]` summarised at theme level | F5L |
| W2.5 | `gge_branch_selectivity_permutation_bar` | omics_differential | `coef_forest` | `branches: list[GGEBranchRow]` + `null: PermutationNullBundle` | F4F |
| W2.6 | `pathway_module_activity_with_sign_concordance` | omics_differential | `matrix` | `cells: list[ModuleConcordanceCell]` (sex × genotype × module + sign-concordance overlay) | F4G |

### Family-rule satisfaction checklist

- **W2.1** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by per-pathway scatter + zero-correlation reference / OLS fit line through origin.
- **W2.2, W2.3, W2.4, W2.6** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by `pcolormesh` heatmap (W2.2 + W2.3 + W2.4) or annotated cell patches (W2.6).
- **W2.5** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by per-pathway markers (≥3 GGE-enriched + ≥3 non-GGE rows) + zero-effect reference line; permutation null draws as faint grey markers behind.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/recipes/omics_differential/_shared.py` | **NEW** | 5 nested Pydantic sub-contracts: `ProteomePhosphoConcordanceRow`, `ModuleConcordanceCell`, `PathwaySupportLayer`, `GGEBranchRow`, `PermutationNullBundle`. Pioneers `_shared.py` for this modality. |
| 6 new recipe modules under `recipes/omics_differential/` | **NEW** | One per recipe |
| `recipes/omics_differential/__init__.py` | edit | Register 6 new recipes; modality 16 → 22 |

No new top-level deps; no new `core/` shims (Bayes factor and multiverse utilities from W1 cover the statistical needs; permutation-null computation for W2.5 is inline numpy, ~20 LOC).

### `_demo()` seed convention (Wave 2)

All Wave 2 demos use seeded RNG (`np.random.default_rng(81X)`) and biology-agnostic synthetic data so the recipes are reusable beyond the cdc42 pack:

- W2.1: 430 pathways × proteome score × phospho score; near-zero Spearman ρ to mirror the manuscript's "independent dimensions" finding.
- W2.2: 12 modules × 2 conditions × signed score; 5/12 sign-concordant (~42%) per the manuscript.
- W2.3: 5 themes × 3 match-tiers (matched / analog / internal) × support level; cytoskeletal/Rho strongest joint support.
- W2.4: 5 themes × 3 layers (matched / surrogate / internal) summarised — bridge summary; CYTO theme strongest.
- W2.5: 30 pathways split into 12 GGE + 18 non-GGE; 60% GGE Male>Female phospho vs 30% non-GGE; permutation p<0.001.
- W2.6: 12 modules × {WT-CTL, WT-CKO, M-CTL, M-CKO} × signed score; sign-concordance overlay (✓/✗) per cell.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| W2.1 near-zero correlation makes the scatter look unstructured by design — risk that the reader doesn't recognise that's the point | Annotate "Spearman ρ = ..." callout; draw an explicit dashed zero-line plus the OLS fit; legend explicit about expected near-zero. |
| W2.2/W2.6 sign-concordance grids — risk that the sign overlay glyph clashes with the cell colour | Use ASCII '+'/'−' marks (Helvetica-safe) + bold black on light-coloured cells, white on saturated cells. |
| W2.3 / W2.4 multi-layer pathway support — three nested levels can crowd | Stack as horizontal panels with shared y-axis (theme); each layer occupies one column. |
| W2.5 permutation null — risk of confusion between observed bars and null distribution | Draw observed bars solid, null draws as faint grey jitter behind; explicit p-value annotation per bar. |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 2261 + Wave 2 recipe smoke / quality / contracts (~12 new) ≈ 2273.
2. `pytest tests/test_recipes_smoke.py -k omics_differential` — 22 demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k omics_differential` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet at 20/20.
5. Gallery regenerate `omics_differential/` — 22 PNGs.
6. Eyeball each new panel; estimate **3 visual-QA fit-ups** (heatmap-heavy wave; signed cmap discipline established by disc1 W2 cohort-balance recipe).

## Wave 3 — factorial statistics + sex-stratified validation (+7) [pending]

(Detail filled in when Wave 3 gap analysis is gated.)

## Wave 4 — energetic / thermodynamic + narrative integration (+6) [pending]

(Detail filled in when Wave 4 gap analysis is gated.)

## Pack-closeout deliverables (after Commit 3 of Wave 4)

After Wave 4 ships, run pack-closeout in a follow-up PR (same pattern as biophysics_scaling pack PR #32 + intravital_imaging pack PR #38 + disc1_manuscript_companion pack PR #43):

1. Bump tracker w4 row `review` → `merged`; mark Summary "After W4" column ✅.
2. CHANGELOG roll-up `[1.5.0-beta-cdc42_factorial_companion]` (full pack release notes summing 4 waves).
3. Tag `v1.5.0-beta-cdc42_factorial_companion`, push, GitHub release with per-wave delta table.
4. `docs/recipes_by_modality.md` headline badge: catalog 448 recipes; per-modality counts updated.

## Out of scope for this pack

- Tables T1–T6 (auto-generated tabular outputs).
- Sex-stratified Bayesian hierarchical models (out of scope; figures only).
- New modality (additive governance — all recipes go into existing modalities).
- Wet-bench protocol diagrams.
- Manuscript-LaTeX integration / copy-paste-into-`.tex` templates.
