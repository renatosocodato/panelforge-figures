# biophysics_scaling beta expansion pack tracker

**Version label:** `[1.2.0-beta-biophysics_scaling]` (sub-tags `-w1` … `-w4`)
**Scope:** 23 new recipes + shared sub-contract module + one new `core/`
utility, landed across 4 waves. **User-gated per wave**: stop after each
wave's gap-analysis for approval.
**Anchor manuscript:** DISC1-lissencephaly primary microglia biophysics
(23 cells, 258 features, 109 sig / 149 null-accepting, 4 censoring modes,
256 replicates, 3-metric validation contract).
**Plan file:** `~/.claude/plans/shimmying-mapping-hammock.md`

## Summary

| Metric | Start | After W1 | After W2 | After W3 | After W4 |
|---|---|---|---|---|---|
| biophysics_scaling recipes | 15 | 19 | 27 | 35 | 38 |
| Total catalog recipes | 328 | 332 | 340 | 348 | 351 |
| Beta-pack recipes landed | 0 | 4 | 12 | 20 | 23 |

## Per-wave status

| Wave | Scope | Status | Branch | Merged tag | Notes |
|---|---|---|---|---|---|
| w1 | Substrate (+4): A.1, B.1, B.2, D.5 + shared contracts + TOST utility | **merged** | `beta-biophysics-scaling-w1` | — (squash-merged PR #27; commit `4c3134a`) | 4 commits, admin-merged; 2 visual-QA fit-ups; pre-existing main lint failures cleaned up separately in PR #28 |
| w2 | Scale-hierarchy + narrative anchors (+8): A.2, A.3, A.4, A.5, C.1, C.2, D.1, D.2 | **review** | `beta-biophysics-scaling-w2` | — | 8 recipes + 4 visual-QA fit-ups landed; awaiting PR merge |
| w3 | Territory/network/geometry physics + trajectory (+8): C.3, C.4, C.5, C.6, C.8, C.9, D.3, D.4 | pending | — | — | Depends on w2 |
| w4 | Forward-validation capstone (+2): B.3, C.7 (+ robustness ring) | pending | — | — | Depends on w3; closes pack |

Status legend:
- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed

## Wave 1 — substrate (+4)

**Why first.** The shared contract module + `tost_bounds_utility` are
load-bearing for every downstream recipe. A.1 is the manuscript's central
argument in one panel. B.1 is the inferential rigor pattern reviewers
actively look for. B.2 is the pre-registered censoring audit. D.5 is the
generic parameter-sufficiency contract (reusable for every future
biophysics_scaling manuscript with a simulation layer). Together with the
substrate, these four are the proposal §11 "disproportionately high-value
subset."

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/recipes/biophysics_scaling/_shared.py` | **NEW** | 11 nested Pydantic sub-contracts: `ScaleTaggedFeature`, `TostZone`, `EffectSizeEstimate`, `CensoringMode`, `CensoringResult`, `ValidationMetric`, `MediationPathEstimate`, `PhaseMapGrid`, `OrderedTrajectoryPoint`, `TipStateCall`, `PSDCurve`. Also exports `OUTCOME_PALETTE_DEFAULT` dict for local fallback. |
| `src/panelforge_figures/core/tost_bounds_utility.py` | **NEW** | `classify_outcome(ci_lo, ci_hi, tost) -> Literal["significant","null_accepting","equivocal"]` + `tost_band_patch(ax, tost, orientation="y", **kw)` helper that draws the shaded equivalence band. |
| `src/panelforge_figures/core/__init__.py` | edit | Export `classify_outcome`, `tost_band_patch` for recipes to import via `from ...core import …`. |
| `src/panelforge_figures/recipes/biophysics_scaling/_aesthetic.py` | edit | Subclass `ModalityAesthetic` → `BiophysicsScalingAesthetic` with `outcome_palette: dict[str,str]` field. Default `{"significant": "#1565C0", "null_accepting": "#2E7D32", "equivocal": "#9E9E9E"}`. **Isolated to this modality**; zero changes to `core/aesthetic_base.py`. |
| `src/panelforge_figures/recipes/biophysics_scaling/__init__.py` | edit | Register 4 new recipe modules (imports + `__all__`). |
| `tests/test_tost_bounds_utility.py` | **NEW** | Classification numerics on synthetic CIs; shaded-band render smoke. |

### Recipe roster

| ID | Recipe | Family | Contract | Required fields | Precedent to mirror |
|---|---|---|---|---|---|
| A.1 | `hierarchical_effect_size_ladder` | `coef_forest` | `HierarchicalEffectSizeLadderInput` | `estimates: list[EffectSizeEstimate]`, `scale_order: list[str]` | `meta_and_diagnostic/heterogeneity_forest.py` |
| B.1 | `equivalence_forest_with_tost_bounds` | `coef_forest` | `EquivalenceForestInput` | `estimates: list[EffectSizeEstimate]` | same as A.1 + `docking_pose_score_vs_rmsd` (band shading) |
| B.2 | `pre_registered_censoring_mode_grid` | `matrix` | `CensoringModeGridInput` | `results: list[CensoringResult]`, `modes: list[CensoringMode]`, `features: list[str]` | `meta_and_diagnostic/data_quality_heatmap.py` + `gillespie_stochastic/state_occupancy_raster.py` (ListedColormap) |
| D.5 | `forward_simulation_validation_contract` | `coef_forest` | `ValidationContractInput` | `metrics: list[ValidationMetric]` | same as A.1 (horizontal strip of CI bands + markers) |

### Family-rule satisfaction checklist

- A.1, B.1, D.5 → `coef_forest` rule (≥3 estimate markers + ≥1 reference
  line) — satisfied by ≥3 forest rows + the TOST band midline / null
  reference at x=0 / per-metric reference band. Demos must seed ≥3 rows.
- B.2 → `matrix` rule (≥4 cell patches) — satisfied by the 2-D
  traffic-light grid (rows × modes). Demos must seed at least 2 features
  × 2 modes = 4 cells.

### `_demo()` seed convention

Per §9 of the plan, demos use manuscript-grounded defaults where
concrete numbers exist:
- A.1 demo: 10-feature roster across 5 scales × 2 compartments, with
  median-|d| across scales close to manuscript values (109 sig / 149
  null out of 258).
- B.1 demo: same 10-feature roster, TOST margins ±0.2 (typical d).
- B.2 demo: 8 features × 4 censoring modes (permissive, standard,
  quality_gated, strict) — matches the manuscript's 4 pre-registered
  modes.
- D.5 demo: 3 metrics (in-plane ordering, z-span analogue, tapered-tip
  fraction) × 2 groups (WT, LI), n_replicates=256 — matches
  manuscript's validation contract exactly.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| TOST-band utility has to support both x-band (forests) and y-band (paired scatters) | `tost_band_patch(..., orientation="y" | "x")` |
| `coef_forest` rule requires ≥1 reference line — D.5 natively has CI bands and markers but no single vertical line | Add a zero-verdict reference line in each metric sub-panel |
| Demos for A.1 / B.1 share the `EffectSizeEstimate` list — risk of code duplication | Factor the demo roster into a shared helper in `_shared.py`: `_demo_estimate_roster() -> list[EffectSizeEstimate]` |
| Ratchet (≤20 distinct fontsize / linewidth literals) | New recipes reuse existing literals (6.4, 6.6, 6.8, 7.0, 7.2, 7.4, 7.8, 8.2, 8.4; 0.5, 0.7, 0.8, 1.0, 1.1, 1.2). No new values. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1691 tests still pass + new tost utility
   tests.
2. `pytest tests/test_recipes_smoke.py -k biophysics_scaling` — 19
   demos render headlessly (15 existing + 4 new).
3. `pytest tests/test_recipes_quality.py -k biophysics_scaling` — each
   new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held.
5. `pytest tests/test_tost_bounds_utility.py` — new.
6. Gallery regenerate `biophysics_scaling/` — 19 PNGs.
7. Eyeball each new panel for collisions, clipped text, legend overflow
   (matches prior-session production-audit checklist).

## Wave 2 — scale-hierarchy + narrative anchors (+8)

**Why next.** Wave 1 shipped the substrate (shared contracts + TOST
utility). Wave 2 rounds out the scale-hierarchy grammar (A.2 / A.3 / A.4
/ A.5) and delivers the §3 / §5 narrative anchors (C.1 / C.2 / D.1 /
D.2). After Wave 2, §1, §3, and the first half of §5 of the anchor
manuscript are fully panelable.

### Recipe roster

| ID | Recipe | Family | Required fields | Precedent to mirror |
|---|---|---|---|---|
| A.2 | `compartment_paired_delta_scatter` | `scatter_collapse` | `estimates: list[EffectSizeEstimate]` (both compartments per feature) | `cryoem_and_structure/docking_pose_score_vs_rmsd.py` (diagonal + zone shading) |
| A.3 | `feature_outcome_sankey_sig_vs_null` | `flow` | `estimates: list[EffectSizeEstimate]` | `meta_and_diagnostic/retention_vs_attrition_sankey.py` |
| A.4 | `random_forest_importance_by_scale` | `coef_forest` | `importance_mean: list[float]`, `importance_ci: list[tuple[float,float]]`, `features: list[ScaleTaggedFeature]` | Wave 1 A.1 layout + `meta_and_diagnostic/heterogeneity_forest.py` |
| A.5 | `scale_stratified_permanova_r2` | `coef_forest` | `r2_by_scale: dict[str, float]`, `ci_by_scale: dict[str, tuple[float,float]]`, `p_by_scale: dict[str, float]` | same as A.4 |
| C.1 | `persistence_length_lp_with_equivalence_bounds` | `split_violin` | `lp_by_group_and_compartment: dict[tuple[str,str], list[float]]`, `tost: TostZone` | `actin_microtubule_morphometry/process_end_count_violin.py` |
| C.2 | `psd_active_gel_overlay_with_motor_inset` | `timecourse_hierarchical_ci` | `psds: list[PSDCurve]`, `active_gel_band_hz: tuple[float, float]` | `biophysics_scaling/log_log_with_theory_line.py` (inset pattern) |
| D.1 | `geometric_mediation_path_diagram` | `conceptual` | `path: MediationPathEstimate` | `grant_and_conceptual/methods_pipeline_flow.py` |
| D.2 | `shared_manifold_scatter_with_residuals` | `scatter_collapse` | `x_by_cell`, `y_by_cell`, `group_by_cell`, `x_label`, `y_label` | `meta_and_diagnostic/batch_effect_diagnostic_pca.py` + `mpl_toolkits.axes_grid1.make_axes_locatable` |

### Family-rule satisfaction checklist

- **A.2** (`scatter_collapse`): ≥1 scatter + ≥1 fit line — satisfied by
  the paired scatter + the `y = x` diagonal reference.
- **A.3** (`flow`): ≥2 rounded boxes + ≥1 annotation arrow — satisfied
  by the 3-tier Sankey (total → scale → outcome) implemented with
  `FancyBboxPatch` + `FancyArrowPatch` (no matplotlib-Sankey dep).
- **A.4, A.5** (`coef_forest`): ≥3 markers + ≥1 reference line —
  A.4 satisfied by top-N importance rows + null-importance reference;
  A.5 by per-scale R² rows + the "typical threshold" reference line.
- **C.1** (`split_violin`): ≥2 violin bodies + ≥1 median marker —
  satisfied by 2×N split violins (N compartments × 2 groups) with
  median tick markers.
- **C.2** (`timecourse_hierarchical_ci`): ≥1 filled CI band + ≥1 mean
  line — satisfied by per-group PSD mean + CI ribbon.
- **D.1** (`conceptual`): ≥3 texts + ≥2 patches — satisfied by 3 node
  labels (X, M, Y) + 3 path-β annotations + node circle patches.
  **Note**: this is the plan reconciliation (proposal called for
  `matrix`; `conceptual` is a cleaner fit for a node-and-edge DAG).
- **D.2** (`scatter_collapse`): ≥1 scatter + ≥1 fit line — satisfied
  by the central scatter + shared LOESS / GAM fit.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| 8 new recipe modules under `recipes/biophysics_scaling/` | **NEW** | One per recipe, contract + `_demo()` + `render()` |
| `recipes/biophysics_scaling/__init__.py` | edit | Register 8 new recipes (imports + `__all__`); bumps total to 27 |
| `recipes/biophysics_scaling/_shared.py` | edit | Extend `_demo_estimate_roster()` or add a second helper if needed for A.4 / A.5 demos (which need `ScaleTaggedFeature` + importance values, not `EffectSizeEstimate`). Add `_demo_lp_distribution()` for C.1 and `_demo_psd_curves()` for C.2 if they are non-trivial |
| Gallery PNGs (8 new) | **NEW** | One per recipe |

No new `core/` utilities expected. D.2 uses `_fit_eval()` (LOESS smoother
at `core/primitives.py:232`, already available). C.1 uses
`violin_with_ring_markers()` (already available).

### `_demo()` seed convention (Wave 2)

- **A.2**: reuse `_demo_estimate_roster()` from Wave 1. Scatter x =
  whole-cell d vs y = protrusion-internal d.
- **A.3**: reuse `_demo_estimate_roster()`. Sankey counts roll up
  scale × outcome.
- **A.4**: 20 top features, importance drawn from an exponential prior
  so the top-5 dominate. Features use `ScaleTaggedFeature` + 5-scale
  spread matching A.1.
- **A.5**: 5 scales, R² ranging 0.02 → 0.18, p-values from permutation.
- **C.1**: 2 compartments × 2 groups Lp distributions; log-normal with
  μ-shifts that straddle the TOST band.
- **C.2**: 2 channels × 2 groups PSDs; ω⁻² reference + sub-dominant
  motor-band bump around 3–8 Hz.
- **D.1**: X = genotype_LI, M = cell_area_um2, Y = standoff_um. Direct
  β ≈ 0 (CI crosses 0); indirect β ≈ 0.4 (CI excludes 0).
- **D.2**: 50-cell scatter of cell_area vs standoff, two groups, shared
  LOESS fit with overlapping residual histograms.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| A.3 Sankey: bar widths must encode counts accurately in pixel-space with rounded boxes | Model as alternating `FancyBboxPatch` + `Polygon` quadrilaterals (not matplotlib Sankey). Precedent in `retention_vs_attrition_sankey.py`. |
| D.1 mediation DAG: 3-node layout + 5 labeled edges + CI annotations crowd a small axes | Auto-layout with fixed positions for 3 nodes; put CI annotations on a second line under each β; keep label fontsize 6.4–6.8. |
| D.2 marginal residual histograms can overflow if residual range is large | Use `make_axes_locatable` to pin histogram heights; let matplotlib auto-adapt xlim. |
| C.2 log-log inset for motor-band deviation might collide with legend | Park inset in lower-left by convention; legend stays upper-right. |
| Ratchet (≤20 distinct fontsize / linewidth literals) | Reuse Wave 1 literals; no new values. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1724 tests still pass.
2. `pytest tests/test_recipes_smoke.py -k biophysics_scaling` — 27
   demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k biophysics_scaling` —
   each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held.
5. Gallery regenerate `biophysics_scaling/` — 27 PNGs.
6. Eyeball each new panel; apply visual-QA fit-ups before Commit 3.

## Out of scope for this pack

- Statistical-method choices (TOST margin selection, bootstrap variant,
  breakpoint algorithm, PERMANOVA permutation counts).
- Figure-composition / layout templates.
- Cross-modality recipes.
- Interactive / web variants.
- Forward-simulation engine itself (D.5 only consumes outputs).
- TOST pre-registration governance.
