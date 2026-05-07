# Spec — Statistical contract for recipes (the AUDIT layer)

**Status:** `proposed` (v2.0.0 candidate, highest-leverage elevation)
**Version label (target):** `[2.0.0-statistical_contract]`
**Owner stream:** v2.0.0 elevations (parallel-swarm spec W2)
**Branch:** `roadmap-v2-specs` (this spec) → implementation in dedicated PR series
**Anchor pattern:** `[1.5.0-beta-factorial_design_companion]` (PR #44–#48) — wave-gated, additive, zero-deps-by-default
**Scope:** 1 new dataclass module, 1 new audit module (~12–15 rules), 1 new field on `RecipeMetadata`, 1 new CLI verb, contract-tagging of the 56 Tier-1 recipes (cdc42 + disc1 packs), full backwards-compatibility for the remaining 392 untagged recipes.
**TL;DR.** Today, every recipe in the catalog declares only a *visualisation* contract: "I render a coef-forest given `rows: list[CoefRow]`." A user can hand `coef_forest` data with three samples per group, NaN-laden estimates, or six panels lacking any multiple-comparison correction, and the renderer will dutifully draw a figure that *lies*. This spec adds a **statistical contract** layer — a per-recipe declaration of the inferential preconditions the data must satisfy — together with a pre-render `figures audit` step that checks each precondition and either **refuses to render** (`StatisticalContractViolation`) or emits a warning that propagates to `RENDER_REPORT.md`. The render pipeline becomes `intake → score → bind → AUDIT (new) → render → report`. Tier-1 of 56 cdc42 + disc1 recipes ship with explicit contracts in this PR; the remaining 392 default to the all-permissive contract and continue to render unchanged.

## 1. Why now / problem statement

panelforge-figures has 448 recipes and zero statistical preconditions. The renderer is a *visualisation* tool that gets confused for a *peer reviewer* — and this is the single gap between the two. Three concrete failure modes are already in the wild:

- **Underpowered groups render confidently.** A `coef_forest` recipe consumes `rows: list[CoefRow]` where each row carries `(label, point, low, high, n)`. Today the recipe is happy with `n=3` per group; it draws three CIs of width ≫ effect, and the figure is meaningless. The reviewer catches this; the tool did not.
- **Non-Gaussian data through parametric primitives.** A `split_violin` over a heavy-tailed dataset (e.g. confinement velocity with a log-normal tail) is auto-paired with the recipe's per-half median + IQR overlay. The recipe is parametric in spirit; the data is not. The figure is technically correct but inferentially wrong.
- **Multi-panel pipelines without multiple-comparison correction.** A `figures generate --shortlist` pipeline emits 6 panels, each with its own p-value annotation, and zero of them carry a Bonferroni or Benjamini–Hochberg label. Seven independent tests at α=0.05 means at least one false positive in expectation; the figure suite implies seven independent confirmations.

Reviewer-detected statistical errors are the **leading cause** of submission-stage rejection in cell-biology and biophysics venues we target. A tool that catches even a fraction of these before the manuscript leaves the author's machine pays for the entire elevation in saved-revision time.

The fix is not a heroic statistical engine. It is a **declarative contract**: each recipe says, in writing, what data it considers itself capable of summarising honestly, and the audit layer checks the data against that declaration before any pixels are drawn.

## 2. Statistical contract schema

A new immutable dataclass lives at `src/panelforge_figures/core/statistical_contract.py` (~80 LOC) and is composed into `RecipeMetadata` as a single new optional field.

```python
from dataclasses import dataclass
from typing import Literal

DistributionAssumption = Literal[
    "any",
    "approximately_gaussian",
    "non_negative",
    "bounded_unit_interval",
    "count_non_negative_integer",
    "log_normal",
    "circular",
]

MultipleComparisonsPolicy = Literal[
    "none",
    "bonferroni",
    "fdr",
    "any_correction_required",
]

IndependenceStructure = Literal[
    "iid",
    "paired",
    "clustered_by_subject",
    "longitudinal",
    "any",
]


@dataclass(frozen=True)
class StatisticalContract:
    """Per-recipe inferential preconditions, checked by `figures audit`."""

    min_n_per_group: int | None = None
    distribution_assumption: DistributionAssumption = "any"
    multiple_comparisons: MultipleComparisonsPolicy = "none"
    independence: IndependenceStructure = "any"
    effect_size_in_units: str | None = None
    rendered_claim_template: str | None = None
    n_minimum_for_visualization: int | None = None
    refuses_when: tuple[str, ...] = ()  # named refusal-rules (see §4)
```

`RecipeMetadata` gains exactly one field:

```python
@dataclass(frozen=True)
class RecipeMetadata:
    # ... existing fields ...
    statistical_contract: StatisticalContract = StatisticalContract()  # default: all-permissive
```

The default is the empty contract — every existing recipe behaves *exactly* as it does today. Tagging is opt-in, per-recipe, by the recipe author.

## 3. Refusal-rules vocabulary

`refuses_when` is a tuple of *named rules*, not a free-form expression. The closed taxonomy makes audits diff-able, testable, and survives `__eq__`. The Tier-1 implementation ships **13 rules**; the schema is open for incremental additions in follow-up PRs but the taxonomy is enum-validated in YAML and at registry-import time.

| Rule name | Triggers when | Driving primitive | Default verdict |
|---|---|---|---|
| `underpowered` | `n_per_group < contract.min_n_per_group` | `_check_min_n` | refuse |
| `non_normal_with_parametric_test` | KS-test p < 0.01 against normal AND `distribution_assumption == "approximately_gaussian"` | `_check_normality` | warn |
| `uncorrected_multiple_comparisons` | shortlist size ≥ 5 AND `multiple_comparisons == "any_correction_required"` AND no `correction_label` flag in data manifest | `_check_mc_correction` | refuse |
| `missing_paired_structure` | `independence == "paired"` AND data lacks subject/replicate id columns | `_check_pairing_columns` | refuse |
| `singular_design` | covariate matrix rank-deficient (rank < ncols) | `_check_design_rank` | refuse |
| `negative_in_non_negative` | `distribution_assumption == "non_negative"` AND any value < 0 | `_check_non_negative` | refuse |
| `unit_interval_violation` | `distribution_assumption == "bounded_unit_interval"` AND any value < 0 or > 1 | `_check_unit_interval` | refuse |
| `non_integer_in_count` | `distribution_assumption == "count_non_negative_integer"` AND any non-integer | `_check_integer_counts` | refuse |
| `excessive_missingness` | per-group NaN fraction > 0.30 | `_check_missingness` | warn |
| `tied_zero_inflated` | > 40 % exact zeros AND `distribution_assumption == "approximately_gaussian"` | `_check_zero_inflation` | warn |
| `cluster_imbalance` | clustered design with ≥ 5× imbalance between cluster sizes | `_check_cluster_balance` | warn |
| `n_below_visualization_floor` | `n_per_group < n_minimum_for_visualization` (always) | `_check_min_n_for_viz` | refuse |
| `effect_size_units_undeclared` | `rendered_claim_template` references units AND `effect_size_in_units is None` | `_check_units_declared` | warn |

Verdict semantics:

- **`refuse`** — the audit raises `StatisticalContractViolation` *before* any rendering happens; the binding is dropped from the shortlist; the user sees a one-line message + a one-line suggestion (e.g. "collect more data" or "pick a recipe with `min_n_per_group=3`").
- **`warn`** — render proceeds, but `RENDER_REPORT.md` carries a `STATISTICAL WARNING` block describing the rule, the threshold, and the observed value.
- **`pass`** — silent.

## 4. Audit pipeline

A new module `src/panelforge_figures/manifest/statistical_audit.py` (~400 LOC) hosts one function per rule plus a top-level driver:

```python
def audit_binding(
    binding: RenderBinding,
    *,
    allow_warnings: bool = True,
    skip: bool = False,
) -> AuditReport: ...
```

The driver loads the per-field data file(s) (already resolved by `data_bridge`), materialises a per-rule context (e.g. groupby counts, KS-test statistic, design matrix), and calls each rule whose `if_applicable(contract)` returns `True`. Each rule returns one of:

```python
@dataclass(frozen=True)
class RuleResult:
    rule: str
    verdict: Literal["pass", "warn", "refuse"]
    observed: str         # human-readable observation
    threshold: str        # human-readable threshold
    suggestion: str | None
```

The driver aggregates `RuleResult`s into an `AuditReport`. If any verdict is `refuse`, the driver raises `StatisticalContractViolation` carrying the offending list.

### Pipeline placement

The render pipeline today is:

```
intake → score → bind → render → report
```

This spec inserts AUDIT between `bind` and `render`:

```
intake → score → bind → AUDIT → render → report
```

`render_loop.run_render_loop` calls `audit_binding(b)` for each bound recipe `b` *before* the contract is constructed and the renderer invoked. A refused binding becomes a `RenderOutcome(status="refused_audit", reason=...)` that flows into `RENDER_REPORT.md` exactly like a contract-validation failure today. A warned binding renders normally; the warning rides along on the outcome and surfaces in the report's "Statistical warnings" section.

## 5. Three worked examples

### Example A — REFUSE (underpowered)

User has `cells_per_condition.csv` with `n=3` per genotype × sex cell. They bind `mixed_effects_models.two_way_anova_summary_plot` (contract: `min_n_per_group=6`, `refuses_when=("underpowered",)`).

```
$ figures audit mixed_effects_models.two_way_anova_summary_plot cells_per_condition.csv
[REFUSE] mixed_effects_models.two_way_anova_summary_plot
  rule:        underpowered
  observed:    n_per_group min = 3 (cells: CKO_F = 3, CTL_F = 3, CKO_M = 3, CTL_M = 3)
  threshold:   min_n_per_group = 6
  suggestion:  collect more replicates, or pick a recipe with min_n_per_group ≤ 3
               (e.g. mixed_effects_models.sex_x_genotype_interaction_forest)

$ figures generate manifest.yaml
[ABORT] 1 / 12 recipes refused by statistical audit; rerun with `--skip-audit`
        to bypass (NOT recommended), or `figures audit-shortlist` for diagnostics.
```

### Example B — WARN (non-Gaussian + parametric)

User has `confinement_velocity.csv` with a heavy-tailed confinement velocity. They bind `actin_microtubule_morphometry.split_violin_with_paired_lines` (contract: `distribution_assumption="approximately_gaussian"`, NO `non_normal_with_parametric_test` in `refuses_when` — warn-only).

```
$ figures generate manifest.yaml
[OK] 12 / 12 recipes rendered; 1 statistical warning (see RENDER_REPORT.md)
```

`RENDER_REPORT.md` gains:

```markdown
## Statistical warnings

### actin_microtubule_morphometry.split_violin_with_paired_lines
- **rule:** non_normal_with_parametric_test
- **observed:** Kolmogorov–Smirnov D = 0.213, p = 1.7e-04 (heavy right tail)
- **threshold:** approximately_gaussian (KS p ≥ 0.01)
- **suggestion:** consider a non-parametric primitive (e.g.
  `actin_microtubule_morphometry.ridge_by_group`) or log-transform the
  input column before binding.
```

### Example C — PASS (well-conditioned)

User has 12 cells per group, balanced cluster sizes, no missingness, count data on integer scale. They bind `omics_differential.proteome_phosphoproteome_pathway_scatter` (contract: `min_n_per_group=8`, `distribution_assumption="any"`, `multiple_comparisons="fdr"`, `independence="iid"`). All rules pass; the audit is silent.

```
$ figures generate manifest.yaml
[OK] 12 / 12 recipes rendered; 0 statistical warnings.
```

## 6. Backwards compatibility

The existing 448 recipes have **no** `statistical_contract`. Strategy:

- Default contract = `StatisticalContract()` — every field at its all-permissive sentinel. Every rule short-circuits at `if_applicable` and returns `pass`.
- Migration is **incremental and recipe-author-driven**.
- **Tier 1** (this PR series, 56 recipes): the cdc42 + disc1 packs (25 + 31 = 56). These two packs anchor in-flight peer-review-cycle manuscripts and are the highest-value targets. Each Tier-1 recipe gains an explicit `statistical_contract` argument in its `RecipeMetadata(...)` call.
- **Tier 2** (deferred to follow-up PRs, ~392 recipes): the remaining catalog. Each future companion pack inherits the contract as a baseline part of the recipe author's checklist (added to `docs/adding_a_recipe.md`).

A migration of all 392 untagged recipes in one PR is explicitly **out of scope** — it would either gold-plate (uniform `min_n_per_group=6` is wrong for many primitives) or cause a fan-out of false-positive refusals at v2.0.0 release. Incremental wins.

## 7. CLI surface

Three additions, no removals:

- `figures audit <recipe> <data>` — standalone audit; no rendering. Returns exit 0 (pass), 1 (warn), 2 (refuse). Used by editor integrations and CI.
- `figures audit-shortlist <manifest>` — runs the audit across every bound recipe in a profile; prints a per-recipe verdict table. Used as a dry-run before `figures generate`.
- `figures generate --skip-audit` — escape hatch for development. Logs a banner: "AUDIT SKIPPED — DO NOT SHIP THIS RUN." Exit code carries an `audit_skipped` annotation in the rendered `RENDER_REPORT.md` summary.

The implementation lives in `cli.py` with three new `@main.command()` functions, mirroring the existing `validate` / `render` / `catalog` triplet.

## 8. Files to create / modify

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/core/statistical_contract.py` | **NEW** | `StatisticalContract` dataclass; the three `Literal` enums; `__all__` export. ~80 LOC. |
| `src/panelforge_figures/manifest/statistical_audit.py` | **NEW** | `audit_binding(...)` + 13 rule functions + `RuleResult` + `AuditReport` + `StatisticalContractViolation`. ~400 LOC, pure numpy / scipy.stats. |
| `src/panelforge_figures/core/contract.py` | edit | Add `statistical_contract: StatisticalContract = StatisticalContract()` to `RecipeMetadata`. |
| `src/panelforge_figures/core/__init__.py` | edit | Export `StatisticalContract`. |
| `src/panelforge_figures/manifest/__init__.py` | edit | Export `audit_binding`, `StatisticalContractViolation`. |
| `src/panelforge_figures/manifest/render_loop.py` | edit | Insert `audit_binding(b)` between bind and render; new `RenderOutcome` status `refused_audit`; new "Statistical warnings" section in `write_render_report`. |
| `src/panelforge_figures/cli.py` | edit | New `audit`, `audit-shortlist`, `--skip-audit` flags. |
| `src/panelforge_figures/recipes/{cdc42-pack-25}/...` | edit | 25 recipe modules add explicit contracts. |
| `src/panelforge_figures/recipes/{disc1-pack-31}/...` | edit | 31 recipe modules add explicit contracts. |
| `tests/test_statistical_contract.py` | **NEW** | `StatisticalContract` dataclass tests. |
| `tests/test_statistical_audit.py` | **NEW** | ~300 LOC; ≥10 tests across the 13 rules; integration tests. |
| `tests/fixtures/audit_data/` | **NEW** | One synthetic CSV per rule that exercises the trigger path: `n3_per_group.csv`, `heavy_tailed.csv`, `singular_design.csv`, `unpaired_when_paired.csv`, `negative_in_non_negative.csv`, etc. |
| `docs/adding_a_recipe.md` | edit | New "§ Statistical contract" section listing the 13 rules and the template. |
| `docs/spec_statistical_contract.md` | this file | Spec authoritative source. |

LOC summary: ~80 + ~400 + ~300 + 56 × ~6 line-edit = ~1100 LOC of net new code. The 56-recipe edit fan-out is mechanical (one `statistical_contract=...` argument per `RecipeMetadata(...)` call).

## 9. Test surface (≥10 tests)

`tests/test_statistical_audit.py` ships ten or more direct rule tests plus three integration tests:

| # | Test | Driving fixture | Asserts |
|---|---|---|---|
| 1 | `test_underpowered_refused_at_n3` | `n3_per_group.csv` | raises `StatisticalContractViolation`; rule = `underpowered` |
| 2 | `test_non_normal_warns` | `heavy_tailed.csv` | verdict = `warn`; rule = `non_normal_with_parametric_test` |
| 3 | `test_uncorrected_mc_in_5_panel_pipeline` | manifest with 5 bindings, no MC label | verdict = `refuse`; aggregated at shortlist level |
| 4 | `test_paired_structure_missing` | `unpaired.csv` against paired contract | verdict = `refuse`; rule = `missing_paired_structure` |
| 5 | `test_singular_design_detected` | `rank_deficient.csv` | verdict = `refuse`; rule = `singular_design` |
| 6 | `test_refuses_when_enforced` | contract with `refuses_when=("underpowered",)` + n=3 data | raises; **without** that rule in `refuses_when`, same data → warn |
| 7 | `test_default_permissive_passes` | recipe with no contract, any data | verdict = `pass`; report empty |
| 8 | `test_audit_shortlist_integration` | 12-recipe profile, mixed verdicts | report tabulates 8 pass / 3 warn / 1 refuse |
| 9 | `test_negative_in_non_negative_refuses` | `negative_velocity.csv` | refuses |
| 10 | `test_unit_interval_violation_refuses` | proportions with values 1.7 | refuses |
| 11 | `test_excessive_missingness_warns` | 35 % NaN fraction | warns; threshold 0.30 |
| 12 | `test_skip_audit_flag_bypasses` | `figures generate --skip-audit` | renders all; report carries `audit_skipped: True` |
| 13 | `test_render_report_carries_warnings` | one warn outcome | `RENDER_REPORT.md` contains "## Statistical warnings" with rule + observed + suggestion |

## 10. Risks + mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| **False positives** at borderline cases (KS p = 0.009 on a slightly-skewed sample of n=200) | medium | `--allow-warnings` flag (default true); warn-not-refuse default verdict for distribution / missingness rules; per-rule p-thresholds tunable in the contract (e.g. `ks_p_threshold=0.001`) — deferred to v2.1 |
| **Migration burden** for 448 recipes | high if attempted in one PR | Tier 2 explicitly deferred; default contract is permissive; recipe-author checklist updated incrementally |
| **Performance** — KS test on 10 000-row inputs × 60 panels × every render | low (KS is O(n log n)) | Audit runs once per binding, not per render call; rule results cached on `(file_id, recipe.full_name)` keys for the duration of a CLI invocation; KS uses `scipy.stats.kstest` (C-backed) |
| **Test brittleness** — non-deterministic KS on bootstrap fixtures | low | All fixtures are seeded; KS thresholds set at fixed p-values, not bootstrap percentiles |
| **CLI confusion** — users surprised by sudden refusals at v2.0.0 upgrade | low (Tier 1 only) | CHANGELOG carries a "BREAKING (Tier-1 only)" banner; the 392 untagged recipes unchanged; `--skip-audit` documented |
| **Rule taxonomy drift** — future PRs add ad-hoc rules | medium | YAML-validated enum list at registry-import time (mirrors the closed-taxonomy enum class pattern PR #57 already established); CI fails on unknown rule names |

## 11. Acceptance criteria — ship gate

The PR series ships when **all five** acceptance tests pass:

1. **3-cell-per-group input correctly refused.** `pytest tests/test_statistical_audit.py::test_underpowered_refused_at_n3` green; `figures audit` exits 2; the printed message names the offending cells and offers a `min_n_per_group ≤ 3` suggestion.
2. **Non-Gaussian + parametric correctly warned.** `pytest tests/test_statistical_audit.py::test_non_normal_warns` green; `RENDER_REPORT.md` contains a "Statistical warnings" section with the KS p-value and the suggestion.
3. **6-panel pipeline correctly flags missing MC correction.** `pytest tests/test_statistical_audit.py::test_uncorrected_mc_in_5_panel_pipeline` green; the audit-shortlist verdict for a 6-panel profile without `correction_label` is `refuse`.
4. **All 56 cdc42 + disc1 Tier-1 recipes have explicit contracts.** A new test `tests/test_tier1_contracts.py::test_all_tier1_have_explicit_contract` enumerates the 56 expected `full_name`s and asserts `recipe.metadata.statistical_contract != StatisticalContract()` (i.e. *something* was set explicitly).
5. **Existing 392 untagged recipes still render without breaking.** The full quality-gate suite (`tests/test_quality_gates.py`, `tests/test_render_loop_integration.py`) passes against a representative profile that exercises ≥ 100 untagged recipes; zero new refusals; zero new warnings.

CI must additionally show:

- `ruff check` clean,
- `mypy --strict` clean on the two new modules,
- a 1-step `figures audit-shortlist examples/example_factorial/manifest.yaml` smoke test that exits 0 on well-conditioned synthetic data and 2 on the included `n3_per_group.csv` fixture.

## 12. Out of scope

Explicitly deferred to follow-up specs / future v2.x elevations:

- **Bayesian-vs-frequentist distinction.** Whether a recipe's inferential idiom is Bayesian or frequentist is a recipe-level concern, not a data-precondition. A `posterior_density_by_term` plot does not need to validate a frequentist test's assumptions.
- **Power calculation.** The audit answers "is this data adequate for *this* recipe", not "what n would be adequate". Power calculators are auxiliary tooling and live in `core/power_utility.py` (TBD).
- **Effect-size-only audit when no statistical inference is rendered.** A pure descriptive `ridge_by_group` (no test, no CI) does not need a statistical contract; descriptive families default to `StatisticalContract()` and are unaffected.
- **Per-cell exclusion logging.** Recipes that already log exclusions (e.g. `hypothesis_exclusion_table`) continue to do so via their own contract; the audit layer does not duplicate that work.
- **Cross-recipe consistency rules** (e.g. "all panels in a profile must share an n threshold"). Profile-level rules live in a future `figures audit-profile` verb; this spec ships only per-binding rules and a single shortlist-level rule (`uncorrected_multiple_comparisons`).
- **Tier-2 contracts** for the 392 non-Tier-1 recipes. Each future companion pack adds contracts as part of its standard recipe-author checklist; tracker docs follow the existing per-pack tracker pattern (`docs/<pack>_pack_tracker.md`).

## 13. Wave plan (implementation only — outside this spec)

For posterity, the implementation will land in three sub-PRs on a `v2.0.0-statistical_contract` branch:

| Sub-PR | Scope | LOC | Wave-gate |
|---|---|---|---|
| W1 | Substrate: `StatisticalContract` dataclass + `audit_binding` + 13 rules + integration with `render_loop` + CLI verbs + 13 tests + fixtures | ~900 | merge after acceptance test 1–3 + 5 |
| W2 | Tier-1 cdc42 pack — 25 recipes get explicit contracts | ~150 | merge after acceptance test 4 (cdc42 subset) |
| W3 | Tier-1 disc1 pack — 31 recipes get explicit contracts; close pack with `v2.0.0-statistical_contract` tag | ~190 | merge after full acceptance gate |

Each sub-PR follows the existing pack-tracker discipline: `docs/statistical_contract_pack_tracker.md` carries the per-wave status table, branch names, and commit hashes; visual-QA fit-ups apply to any rule whose suggestion text changes; CHANGELOG entries follow the established format.

## 14. References

- Existing closed-enum pattern: PR #57 (`feat(t2-enum-validation): closed-taxonomy enum classes + YAML-parse-time typo detection`).
- Existing wave-gated pack pattern: `docs/factorial_design_companion_pack_tracker.md`, `docs/cytoskeletal_morphometry_companion_pack_tracker.md`.
- Existing render-loop architecture: `src/panelforge_figures/manifest/render_loop.py` §1–§3 (run_render_loop, RenderOutcome, EnvironmentalFailure).
- Existing recipe-metadata pattern: `src/panelforge_figures/core/contract.py` (`RecipeMetadata`, `register_recipe`).
- Statistical primitives consumed: `scipy.stats.kstest` (normality), `numpy.linalg.matrix_rank` (singular design), per-group `scipy.stats.bootstrap` for CI-aware suggestions (deferred to v2.1).

### Migration completed

Sprint 1A (Build-C) migrated **45 of 57** Tier-1 recipes (cdc42 + disc1 manuscript companion packs) to declare explicit `StatisticalContract` blocks. The remaining 12 recipes are conceptual / narrative / raw-image primitives that do not render an inferential claim and therefore retain the all-permissive default contract by design (see spec §6 — descriptive families default to `StatisticalContract()` and are unaffected). All 448 recipes still render unchanged via their `_demo()` paths; the full pytest suite remains green at 2616 / 2616.

The five contract templates used by this migration are:

- **effect-size** — `min_n_per_group=10`, `distribution_assumption="approximately_gaussian"`, `multiple_comparisons="any_correction_required"`, `independence="iid"`, `effect_size_in_units="standardized_d"`, `refuses_when=("underpowered",)`.
- **proportion** — `min_n_per_group=20`, `distribution_assumption="unit_interval"`, `independence="iid"`, `refuses_when=("underpowered", "unit_interval_violation")`.
- **count** — `min_n_per_group=10`, `distribution_assumption="non_negative_integer"`, `refuses_when=("non_integer_in_count", "negative_in_non_negative")`.
- **paired** — `min_n_per_group=10`, `independence="paired"`, `refuses_when=("missing_paired_structure",)`.
- **paired + TOST / equivalence** — paired effect-size with `rendered_claim_template="d = {d:.2f}, TOST p = {p_tost:.4f}"`.

#### Effect-size template (38 recipes)

- `actin_microtubule_morphometry.behavioral_fingerprint_trio_composite`
- `actin_microtubule_morphometry.colocalization_raincloud_per_metric`
- `actin_microtubule_morphometry.cortex_composite_zone_descriptors`
- `actin_microtubule_morphometry.edge_gradient_intensity_profile`
- `actin_microtubule_morphometry.overlap_juxtaposition_quantification`
- `actin_microtubule_morphometry.pca_silhouette_glyph_morphospace`
- `actin_microtubule_morphometry.protrusion_outline_with_cleveland_summary`
- `biophysics_scaling.censoring_mode_waterfall_cascade`
- `biophysics_scaling.confinement_energy_gauge_per_genotype`
- `biophysics_scaling.confinement_ratio_distribution_by_genotype`
- `biophysics_scaling.dissipation_quartile_pca_with_ellipses`
- `biophysics_scaling.dual_scale_significance_lollipop`
- `biophysics_scaling.molecular_resilience_index_bar`
- `biophysics_scaling.permanova_null_distribution`
- `biophysics_scaling.route_geometry_compact_screen`
- `biophysics_scaling.sensitivity_sweep_alpha_width_seed_compound`
- `biophysics_scaling.splay_taper_polarity_displacement_compound`
- `biophysics_scaling.split_mirror_measured_vs_simulated`
- `biophysics_scaling.z_span_vs_width_with_euler_threshold`
- `intravital_imaging.residence_time_kaplan_meier_with_ks_overlay`
- `intravital_imaging.state_entry_exit_with_switch_callout`
- `intravital_imaging.transition_matrix_diagonal_dominance_callout`
- `meta_and_diagnostic.bayes_factor_arrow_plot`
- `meta_and_diagnostic.competing_model_residual_panels`
- `meta_and_diagnostic.cross_contrast_correlation_matrix`
- `meta_and_diagnostic.multiverse_robustness_classification_bar`
- `meta_and_diagnostic.multiverse_specification_curve`
- `meta_and_diagnostic.pca_loadings_heatmap`
- `meta_and_diagnostic.random_forest_confusion_loocv`
- `mixed_effects_models.sex_stratified_roc_loocv`
- `mixed_effects_models.two_way_anova_summary_plot`
- `omics_differential.gge_branch_selectivity_permutation_bar`
- `omics_differential.module_concordance_signed_heatmap`
- `omics_differential.pathway_module_activity_with_sign_concordance`
- `omics_differential.pathway_space_bridge_summary_heatmap`
- `omics_differential.pathway_space_triangulation_heatmap`
- `omics_differential.proteome_phosphoproteome_pathway_scatter`
- `spatial_statistics.kinhom_inhomogeneous_isotropy`

#### Proportion template (2 recipes)

- `actin_microtubule_morphometry.zone_fraction_alluvial_sankey`
- `biophysics_scaling.quartile_stacked_bar_by_factor`

#### Count template (1 recipe)

- `actin_microtubule_morphometry.sholl_intersections_radial_histogram`

#### Paired template (3 recipes)

- `meta_and_diagnostic.proxy_alignment_in_vs_loocv_forest`
- `mixed_effects_models.mediation_decomposition_slope_chart`
- `mixed_effects_models.pre_post_slope_chart_by_module`

#### Paired + TOST / equivalence template (1 recipe)

- `biophysics_scaling.compartment_paired_delta_scatter`

#### Defaulted — narrative / conceptual / raw-image (12 recipes)

These recipes render visual-only or conceptual content (raw imaging, narrative cascades, schematic flow, audit tables) rather than inferential statistical claims, and therefore retain the all-permissive `StatisticalContract()` per spec §6.

- `actin_microtubule_morphometry.actin_mt_angle_rose_with_distance_inset`
- `actin_microtubule_morphometry.airyscan_to_zone_territory_triptych`
- `actin_microtubule_morphometry.mt_mesh_density_compartment_compare`
- `actin_microtubule_morphometry.pseudotime_thumbnail_strip`
- `actin_microtubule_morphometry.territory_contact_network_overlay`
- `biophysics_scaling.force_budget_schematic_with_data`
- `grant_and_conceptual.narrative_cascade_river_with_xrefs`
- `intravital_imaging.territory_zone_overlay_intravital`
- `meta_and_diagnostic.alternative_hypothesis_exclusion_table`
- `meta_and_diagnostic.model_parameterization_lineage_panel`
- `meta_and_diagnostic.panel_provenance_ledger_table`
- `meta_and_diagnostic.per_cell_audit_table_with_qa_flags`
