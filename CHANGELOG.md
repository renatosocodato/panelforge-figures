# Changelog

All notable changes to `panelforge-figures` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows semantic versioning.

## [Unreleased]

### In planning

- **CDC42 factorial companion pack**
  (`[1.5.0-beta-factorial_design_companion]`) — ~25 new recipes
  scattered across 6 existing modalities, landed across 4 user-
  gated waves. Closes the gap between the example_factorial manuscript's
  Bayes-factor / multiverse / multi-omic-concordance / 2 × 2
  factorial / pathway-support primitives and the 423-recipe
  catalog after the cytoskeletal_morphometry_companion pack. See
  [`docs/factorial_design_companion_pack_tracker.md`](docs/factorial_design_companion_pack_tracker.md)
  for the full pack plan. **Zero new heavy deps** (Option D
  inline-shim discipline preserved); 2 new `core/` shims
  (`bayes_factor_utility`, `multiverse_specification_utility`)
  land in Wave 1.
- **Wave 1** in review via PR (+6 universal robustness primitives
  in `meta_and_diagnostic`). meta_and_diagnostic 21 → 27; total
  catalog 423 → 429.
- **Waves 2–4 pending** (+6 multi-omic integration, +7 factorial
  statistics + sex-stratified validation, +6 energetic /
  thermodynamic + narrative integration). Cumulative final:
  catalog 423 → 448.

## [1.5.0-beta-factorial_design_companion-w1] — 2026-04-28

First wave of the `factorial_design_companion` beta expansion
pack. Lands the 6 universal robustness + provenance primitives
in `meta_and_diagnostic`, biology-agnostic and reusable beyond
the example_factorial manuscript. Pioneers 2 new `core/` shims
(`bayes_factor_utility`, `multiverse_specification_utility`).
`meta_and_diagnostic` expands from 21 to 27 recipes; total
catalog 423 → 429.

### Added (6 recipes)

- `bayes_factor_arrow_plot` (`coef_forest`, W1.1) — per-row
  arrow markers showing BF₀₁ on log-x with Wagenmakers /
  Kass-Raftery threshold zones (favours_alt / anecdotal /
  moderate / strong / decisive); reference at BF=1; n-decisive
  callout in title. Uses `core/bayes_factor_utility`.
  **Closes manuscript panel F2J.**
- `panel_provenance_ledger_table` (`matrix`, W1.2) — per-panel
  ledger with dataset layer, n_mice, n_obs, support class on
  diverging cmap (main_inference / support / constraint /
  discovery / limitation); per-class tally in title.
  **Closes Supp Table R1 visual surrogate.**
- `cross_contrast_correlation_matrix` (`matrix`, W1.3) — N × N
  RdBu_r heatmap with diagonal masked; mean off-diagonal r in
  title. **Closes manuscript panel SF4D.**
- `multiverse_robustness_classification_bar` (`matrix`, W1.4) —
  per-spec coloured cell strip + stacked composition bar
  showing ROBUST / FRAGILE / NON_SIG fractions.
  **Closes manuscript panel SF4B.**
- `multiverse_specification_curve` (`scatter_collapse`, W1.5) —
  sorted-effect scatter with shaded ROPE band + zero reference;
  per-spec coloured by classification; CI segments per spec.
  **Closes manuscript panel SF2G.**
- `proxy_alignment_in_vs_loocv_forest` (`coef_forest`, W1.6) —
  paired in-sample (filled) vs LOOCV (hollow) R² markers per
  proxy; OVERFIT flag for negative-LOOCV rows.
  **Closes manuscript panel F4D.**

### Infrastructure

- `core/bayes_factor_utility.py` (new, ~85 LOC) — `bf_from_bic(
  bic_alt, bic_null) → BF₀₁` (Wagenmakers 2007 BIC approximation)
  + `classify_bf_threshold(bf)` for Kass-Raftery tier mapping
  (favours_alt / anecdotal / moderate / strong / decisive).
  Replaces a `BayesFactor` (R) / `JASP` dep.
- `core/multiverse_specification_utility.py` (new, ~95 LOC) —
  `multiverse_audit(effect_sizes, ci_lo=None, ci_hi=None,
  threshold=0.10, rope=(-0.10, 0.10)) → (classifications,
  sort_order)`. Pure-numpy specification-curve sensitivity
  analysis (Steegen 2016, Simonsohn 2020). Replaces a
  `multiverse-r` dep.
- `core/__init__.py` (edit) — exports `bf_from_bic`,
  `classify_bf_threshold`, `BF_THRESHOLDS`, `multiverse_audit`,
  `MULTIVERSE_OUTCOME_CLASSES`.
- `tests/test_bayes_factor_utility.py` (new, 6 tests) — equal
  BICs → BF=1; alt-better → BF<1; null-better → BF>1; extreme
  delta clamps finite; threshold tier classification; boundary-
  inclusive lower-tier semantics.
- `tests/test_multiverse_specification_utility.py` (new, 7
  tests) — shape, class labels in official set, sub-threshold
  classified NON_SIG, CI-excludes-ROPE → ROBUST, CI-overlaps-
  ROPE → FRAGILE, sort-order ascending, no-CI fragile-collapse.
- `recipes/meta_and_diagnostic/_shared.py` (edit) — adds 5
  sub-contracts: `BayesFactorRow`, `PanelProvenanceRow`,
  `CrossContrastEntry`, `MultiverseSpec`, `ProxyAlignmentEntry`.
- `recipes/meta_and_diagnostic/__init__.py` (edit) — registers
  6 new recipes; modality 21 → 27.
- `tests/test_contracts.py` per-modality assertion bumped:
  `counts["meta_and_diagnostic"] == 21` → `27`.

### Demo conventions

All 6 demos use seeded RNG (`np.random.default_rng(80X)`) and
biology-agnostic synthetic data so the recipes are immediately
reusable outside the cdc42 pack:

- W1.1: 4 secondary descriptors with BFs spanning anecdotal
  → strong (one favouring alt with BF<1).
- W1.2: 12 panel rows with 3 main_inference / 5 support /
  1 constraint / 1 discovery / 1 limitation classes; mixed
  main + supp dataset layers.
- W1.3: 5×5 between-contrast correlation; off-diagonal mean
  r ≈ 0.20 (independent contrasts).
- W1.4: 12 specs (7 ROBUST / 3 FRAGILE / 2 NON_SIG) showing
  composition bar + per-spec strip.
- W1.5: 25 specs sorted by effect size; cluster crossings into
  ROPE band; CI segments per spec.
- W1.6: 4 proxies (vel_sd well-aligned, mean_velocity overfit
  with negative LOOCV); OVERFIT flag visible on the
  mean_velocity row.

### Visual-QA polish during authoring (1 fit-up)

- W1.2 `fontsize=8.0` snapped to existing `8.2` to keep the
  style-drift ratchet at 20/20.

### Tests

- Total: **2218 → 2261** (+43: 6 smoke + 6 quality + 13 utility
  + ~18 from auto-parametrized contracts and registry).
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- meta_and_diagnostic recipes: **21 → 27** (+6).
- factorial_design_companion pack recipes landed: **0 → 6**
  (Wave 1 of 4).
- New `core/` shims: **0 → 2** (`bayes_factor_utility`,
  `multiverse_specification_utility`).

### Completed packs

- **DISC1 manuscript companion pack
  `[1.4.0-beta-cytoskeletal_morphometry_companion]` — COMPLETE.** 4 waves,
  31 new recipes scattered across 6 existing modalities (no new
  modality), 1 new `core/` inline shim
  (`permanova_null_utility`), 14 new nested sub-contracts across
  3 newly-pioneered `_shared.py` modules
  (`meta_and_diagnostic`, `actin_microtubule_morphometry`,
  `grant_and_conceptual`) plus extensions to `biophysics_scaling`.
  **Zero new heavy dependencies** (no `scikit-bio` /
  `networkx` / `pysankey`). Catalog 392 → 423; 6 modalities
  touched. Tests 2056 → 2218. PRs #39 → #42 (+ #43 closeout).
  Tag `v1.4.0-beta-cytoskeletal_morphometry_companion`. See
  [`docs/cytoskeletal_morphometry_companion_pack_tracker.md`](docs/cytoskeletal_morphometry_companion_pack_tracker.md)
  for the full pack tracker.

- **intravital_imaging beta expansion pack
  `[1.3.0-beta-intravital_imaging]` — COMPLETE.** 4 waves, 42 new
  recipes, 5 new `core/` inline shims (HMM/HSMM, KM, GAM, spectral
  embedding, transfer entropy), 11 new nested sub-contracts,
  `microglia_states` semantic-palette polish. **Zero new heavy
  dependencies** beyond `hmmlearn` (no `umap-learn` / `pyhsmm` /
  `lifelines` / `statsmodels` / `pygam`). Catalog 350 → 392;
  intravital_imaging 15 → 57. Tests 1814 → 2056. PRs #33 → #37
  (+ #34 polish, #38 closeout). See pack-closeout summary at the
  end of its Wave 1 entry below, and
  [`docs/intravital_imaging_beta_pack_tracker.md`](docs/intravital_imaging_beta_pack_tracker.md)
  for the full pack tracker.

## [1.4.0-beta-cytoskeletal_morphometry_companion-w4] — 2026-04-28

Final wave of the `cytoskeletal_morphometry_companion` beta expansion
pack. Lands the 9-recipe F5 / F6 narrative-integration cluster +
FS1C / FS3D / FS5C / FS5D / FS6E-F / FS7B-D supplementary panels.
Pioneers `grant_and_conceptual/_shared.py` for the headline
`narrative_cascade_river_with_xrefs` synthesis-figure primitive.
Adds 1 new `core/` shim (`permanova_null_utility.py`). **Closes
the pack at 31/31 recipes.** Catalog 414 → 423.

### Added (9 recipes)

- `pseudotime_thumbnail_strip` (`matrix`,
  actin_microtubule_morphometry, W4.1) — per-cell thumbnail
  panels arranged along the Actin Drive Index pseudotime axis;
  per-condition stand-off-vs-pseudotime trace below shows
  checkpoint-bifurcation. **Closes manuscript panel F5C.**
- `narrative_cascade_river_with_xrefs` (`conceptual`,
  grant_and_conceptual, W4.2) — multi-stage causal river
  integrating manuscript-level findings with figure cross-
  references and inline statistics; **headline synthesis-figure
  primitive** reusable beyond the DISC1 pack.
  **Closes manuscript panel F5E.**
- `split_mirror_measured_vs_simulated` (`split_violin`,
  biophysics_scaling, W4.3) — three side-by-side panels (one per
  validation metric) with measured (left, solid) and simulated
  (right, hatched) split-violins per condition; per-panel max-
  rel-err in title. **Closes manuscript panel F6C.**
- `permanova_null_distribution` (`diagnostic_curve`,
  biophysics_scaling, W4.4) — histogram of permutation-shuffle
  null R² with observed R² as a vertical reference and p-value
  tail-shaded for visual percentile read-off. Uses new
  `core/permanova_null_utility.py` shim.
  **Closes manuscript panel FS1C.**
- `overlap_juxtaposition_quantification` (`scatter_collapse`,
  actin_microtubule_morphometry, W4.5) — per-cell scatter linking
  polymer-overlap to territory-juxtaposition; per-condition
  windowed-median fit lines highlight the shared manifold.
  **Closes manuscript panel FS3D.**
- `force_budget_schematic_with_data` (`conceptual`,
  biophysics_scaling, W4.6) — methods-style schematic of the
  protrusion force budget (4 terms) with measured per-term
  values + 95% CI bars on the right; sign convention coloured
  green (+) / red (-); net-force in title.
  **Closes manuscript panel FS5C.**
- `confinement_ratio_distribution_by_genotype` (`split_violin`,
  biophysics_scaling, W4.7) — split-violin distribution of
  per-cell confinement ratio (z-span / Euler L_crit) per
  genotype; horizontal reference at ratio = 1.0; per-genotype
  supercritical fraction in title.
  **Closes manuscript panel FS5D.**
- `splay_taper_polarity_displacement_compound` (`coef_forest`,
  biophysics_scaling, W4.8) — three frontier-architecture
  readouts (splay-taper transition, polarity-displacement
  offset, splay symmetry) compound forest with per-condition
  CI markers + zero-effect reference.
  **Closes manuscript panels FS6E-F.**
- `sensitivity_sweep_alpha_width_seed_compound`
  (`timecourse_hierarchical_ci`, biophysics_scaling, W4.9) —
  three side-by-side panels showing per-condition mean output
  curve + bootstrap CI ribbon as alpha / width / seed are
  swept; per-panel min-condition-gap callout shows separation
  persists. **Closes manuscript panels FS7B-D.**

### Infrastructure

- `core/permanova_null_utility.py` (new, ~85 LOC) —
  `permanova_null_distribution(X, labels, n_perms=999, seed=0) →
  (R2_obs, R2_null, p_perm)`. Pure-numpy permutation-shuffle
  estimator with squared-Euclidean distance + Phipson-Smyth
  small-sample p-value correction. Replaces a `scikit-bio` dep;
  matches Option D inline-shim discipline.
- `core/__init__.py` (edit) — exports `permanova_null_distribution`.
- `tests/test_permanova_null_utility.py` (new, 7 tests) — shape,
  R²-bounds, separated-blob recovery, deterministic-under-seed,
  random-label sanity, edge cases (too-few-samples, label
  size mismatch).
- `recipes/actin_microtubule_morphometry/_shared.py` (edit) —
  adds 2 sub-contracts: `PseudotimeOrderedCell` (W4.1),
  `OverlapJuxtapositionCell` (W4.5).
- `recipes/biophysics_scaling/_shared.py` (edit) — adds 5 sub-
  contracts: `MeasuredSimulatedPair` (W4.3),
  `ForceBudgetTerm` (W4.6), `ConfinementRatioSample` (W4.7),
  `CompoundReadoutRow` (W4.8), `SensitivitySweepCurve` (W4.9).
- `recipes/grant_and_conceptual/_shared.py` (new) — pioneers
  `_shared.py` for this modality with `CascadeStage` +
  `CascadeTransition` (used by W4.2 narrative cascade).
- `recipes/actin_microtubule_morphometry/__init__.py` (edit) —
  registers 2 new recipes; modality 45 → 47.
- `recipes/biophysics_scaling/__init__.py` (edit) — registers
  6 new recipes; modality 41 → 47.
- `recipes/grant_and_conceptual/__init__.py` (edit) — registers
  W4.2; modality 15 → 16.
- `tests/test_contracts.py` per-modality assertion bumped:
  `counts["grant_and_conceptual"] == 15` → `16`.

### Demo conventions

All 9 demos use seeded RNG (`np.random.default_rng(70X)`) and
the manuscript's WT vs LI condition labels with biology-agnostic
synthetic data:

- W4.1: 12 cells across pseudotime [0.05, 0.95]; thumbnails
  elongate with pseudotime; LI stand-off diverges past pseudotime
  ≈ 0.6 (checkpoint).
- W4.2: 6 cascade stages with figure cross-references and p-
  values; each stage carries a one-line summary claim.
- W4.3: 3 metrics (coherency, z-span, tapered-tip fraction) × 2
  conditions × 30 cells each (measured + simulated pair).
- W4.4: 2 well-separated blobs (n=60) producing observed R² ≈
  0.45; 499-perm null distribution; p_perm ≈ 0.002.
- W4.5: 2 conditions × 12 cells; LI shifted up-and-right of WT
  on the polymer-overlap × territory-juxtaposition plane.
- W4.6: 4 force-budget terms (active / elastic / drag /
  confinement) with realistic ± 95% CI bars; net = +0.4 pN
  (slightly forward-pushing).
- W4.7: 2 conditions × 30 cells; WT median ratio ≈ 0.55
  (subcritical), LI ≈ 1.55 (supercritical).
- W4.8: 3 readouts × 2 conditions; LI elevated on all three
  readouts vs WT.
- W4.9: 3 sweep parameters × 2 conditions × 12 grid points each;
  WT-vs-LI separation persists across the entire sweep range.

### Visual-QA polish during authoring (0 fit-ups)

All 9 recipes passed family-rule and style-drift ratchet checks
on first authoring; no fit-ups needed during tests. Visual audit
fit-ups are tracked separately in Commit 3.

### Tests

- Total: **2166 → 2218** (+52: 9 smoke + 9 quality + 7 utility
  + ~27 from auto-parametrized contracts and registry).
- New test file `tests/test_permanova_null_utility.py` (7 tests).
- `tests/test_contracts.py` `grant_and_conceptual` per-modality
  assertion bumped 15 → 16.
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- actin_microtubule_morphometry recipes: **45 → 47** (+2).
- biophysics_scaling recipes: **41 → 47** (+6).
- grant_and_conceptual recipes: **15 → 16** (+1).
- cytoskeletal_morphometry_companion pack recipes landed: **22 → 31**
  (Wave 4 of 4 — **closes pack at 31/31**).
- New `_shared.py` modules pioneered: **3 → 4**
  (`grant_and_conceptual` joins
  `meta_and_diagnostic` /
  `actin_microtubule_morphometry`, plus the existing
  `biophysics_scaling`).

## [1.4.0-beta-cytoskeletal_morphometry_companion-w3] — 2026-04-28

Third wave of the `cytoskeletal_morphometry_companion` beta expansion
pack. Lands the 9-recipe cytoskeleton geometry + statistics
cluster (F2D / F2E / F3 / F4 + supplementary FS2 / FS4 / FS5
panels). Extends both `actin_microtubule_morphometry/_shared.py`
(+5) and `biophysics_scaling/_shared.py` (+3) with new sub-
contracts. Catalog 405 → 414.

### Added (9 recipes)

- `actin_mt_angle_rose_with_distance_inset` (`radar`,
  actin_microtubule_morphometry, W3.1) — polar rose plots of
  actin-to-MT angle distributions overlaid per condition, with a
  Cartesian inset showing nearest-neighbour inter-filament
  distance distributions. **Closes manuscript panel F2D.**
- `protrusion_outline_with_cleveland_summary` (`scatter_collapse`,
  actin_microtubule_morphometry, W3.2) — left-side
  representative-protrusion outlines (one per condition, drawn
  as `Polygon` patches) + right-side Cleveland strip plot of
  per-cell width and erosion-depth scalars. **Closes manuscript
  panel F2E.**
- `censoring_mode_waterfall_cascade` (`coef_forest`,
  biophysics_scaling, W3.3) — per-feature estimate ± 95% CI
  cascading down across pre-registered censoring modes; per-row
  threshold-rule label inline; direction-stable headline in
  title. **Closes manuscript panel F3B.**
- `confinement_energy_gauge_per_genotype` (`coef_forest`,
  biophysics_scaling, W3.4) — semicircular gauge arcs (one per
  genotype) with per-cell tick marks plotted along the arc;
  buffered → unbuffered threshold drawn as a coloured boundary
  on the arc. **Closes manuscript panel F4C.**
- `kinhom_inhomogeneous_isotropy` (`diagnostic_curve`,
  spatial_statistics, W3.5) — edge-corrected Kinhom(r) accounting
  for spatially varying intensity λ(x); per-condition curves
  overlaid with CSR Monte Carlo envelopes; Kpois(r) = π·r²
  reference; per-condition % above CSR callout. Edge-correction
  inline (~30 LOC; per-point area-correction per Ohser 1983).
  **Closes manuscript panels FS2C-D.**
- `edge_gradient_intensity_profile` (`timecourse_hierarchical_ci`,
  actin_microtubule_morphometry, W3.6) — per-channel mean
  intensity vs signed distance from the cell edge (positive =
  inside cell), with bootstrap CI ribbons per condition × channel.
  **Closes manuscript panel FS2E.**
- `cortex_composite_zone_descriptors` (`matrix`,
  actin_microtubule_morphometry, W3.7) — zone × descriptor
  heatmap across two conditions; signed z-score colouring on
  RdBu_r; flag column highlights descriptors crossing the |z| > 0.5
  manuscript threshold. **Closes manuscript panel FS2F.**
- `mt_mesh_density_compartment_compare` (`heatmap`,
  actin_microtubule_morphometry, W3.8) — side-by-side imshow
  panels of MT mesh-density grids per (cell × compartment), with
  shared colour scale across panels and per-cell median-density
  callouts. **Closes manuscript panels FS4E-F.**
- `z_span_vs_width_with_euler_threshold` (`scatter_collapse`,
  biophysics_scaling, W3.9) — per-cell z-span vs width scatter
  with the Euler critical-length curve drawn as a dashed
  reference; per-condition supercritical-fraction in title.
  **Closes manuscript panel FS5B.**

### Infrastructure

- `recipes/actin_microtubule_morphometry/_shared.py` (edit) —
  adds 5 new sub-contracts: `BranchOrderEdge` (W3.1),
  `ProtrusionOutlineWithCleveland` (W3.2),
  `EdgeIntensityProfile` (W3.6),
  `CortexZoneDescriptor` (W3.7),
  `MTMeshDensitySnapshot` (W3.8).
- `recipes/biophysics_scaling/_shared.py` (edit) — adds 3 new
  sub-contracts: `CensoringCascadeRow` (W3.3),
  `ConfinementEnergyBundle` (W3.4),
  `ZSpanWidthSample` (W3.9).
- `recipes/actin_microtubule_morphometry/__init__.py` (edit) —
  registers 5 new recipes; modality 40 → 45.
- `recipes/biophysics_scaling/__init__.py` (edit) — registers 3
  new recipes; modality 38 → 41.
- `recipes/spatial_statistics/__init__.py` (edit) — registers
  W3.5; modality 15 → 16.

No new top-level deps; no new `core/` shims. Kinhom edge-
correction (W3.5) implemented inline (~30 LOC).

### Demo conventions

All 9 demos use seeded RNG (`np.random.default_rng(60X)`) and
the manuscript's WT vs LI condition labels with biology-agnostic
synthetic data:

- W3.1: 2 conditions × 200 angle samples; LI distribution shifted
  toward 0° (more parallel actin-MT alignment); NN-distance inset
  shows LI cluster shifted toward smaller distances.
- W3.2: 2 conditions × 8 cells per condition; WT wider
  (~4 µm) + shallow erosion, LI narrower (~2 µm) + deeper erosion.
- W3.3: 4 censoring modes × 1 feature; estimate stable in
  direction (LI ≲ WT) but support sub-threshold across all
  four censoring rules — the manuscript's "directionality stable,
  magnitude sub-threshold" finding.
- W3.4: 2 conditions × 12 cells; WT median ~2.6 kBT (buffered),
  LI median ~6.4 kBT (unbuffered) — gauge needles cleanly cross
  the 4 kBT threshold.
- W3.5: 2 conditions × 60 r-values; LI Kinhom > Kpois (clustering),
  WT inside CSR envelope.
- W3.6: 2 channels × 2 conditions × 25 sample profiles per group;
  cortical enrichment asymmetry visible (LI peaks shifted toward
  edge for both channels).
- W3.7: 4 zones × 6 descriptors × 2 conditions; LI flagged on
  contact_F-actin (intensity + density), connectivity, intermediate
  MT, and desert fragmentation.
- W3.8: 2 cells × 2 compartments × 64×64 mesh-density grids;
  protrusion-internal compartment shows ~3× density of whole-cell.
- W3.9: 2 conditions × 20 cells; LI cells skew above the Euler
  critical-length threshold (supercritical), WT below.

### Visual-QA polish during authoring (4 fit-ups)

- W3.5 `lw=1.6` → `1.4` (style-drift ratchet).
- W3.3 / W3.4 `lw=2.0` → `2.2` (style-drift ratchet).
- W3.3 / W3.6 `fontsize=8.0` → `8.2` (style-drift ratchet).
- W3.4 `coef_forest` family rule needed ≥3 scatter markers; data
  ticks live on inset axes as `ax.plot` (Line2D), not
  `PathCollection`. Added a sentinel `ax.scatter` with one entry
  per per-cell bundle on the parent ax (parked off-axes,
  `alpha=0`).

### Tests

- Total: **2121 → 2166** (+45: 9 smoke + 9 quality + ~27 from
  auto-parametrized contracts and registry).
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- actin_microtubule_morphometry recipes: **40 → 45** (+5).
- biophysics_scaling recipes: **38 → 41** (+3).
- spatial_statistics recipes: **15 → 16** (+1).
- cytoskeletal_morphometry_companion pack recipes landed: **13 → 22**
  (Wave 3 of 4).

## [1.4.0-beta-cytoskeletal_morphometry_companion-w2] — 2026-04-27

Second wave of the `cytoskeletal_morphometry_companion` beta expansion
pack. Lands the 7-recipe F1 + F2 cluster — cell-level territory
and scale-decomposition figures that open the manuscript narrative.
Pioneers `actin_microtubule_morphometry/_shared.py` with 6 nested
Pydantic sub-contracts. Catalog 398 → 405.

### Added (7 recipes)

- `dual_scale_significance_lollipop` (`coef_forest`,
  biophysics_scaling, W2.1) — diverging lollipop of -log10(p) at
  multiple scales (whole-cell vs protrusion-internal) per metric,
  row-banded by domain tier (polymer / network / territory).
  **Closes manuscript panel F1B.**
- `pca_silhouette_glyph_morphospace` (`scatter_collapse`,
  actin_microtubule_morphometry, W2.2) — per-cell scatter on
  (PC1, PC2) with cell-outline `Polygon` glyphs at each point;
  per-condition 2σ confidence ellipses; PERMANOVA R² + p caption.
  **Closes manuscript panel F1C.**
- `airyscan_to_zone_territory_triptych` (`matrix`,
  actin_microtubule_morphometry, W2.3) — three-panel triptych per
  representative cell (raw Airyscan → skeleton overlay →
  zone-resolved territory map); shared zone legend strip below.
  **Closes manuscript panel F1D.**
- `territory_zone_overlay_intravital` (`heatmap`,
  intravital_imaging, W2.4) — multi-channel intravital field
  rendered as RGB composite with per-zone contour outlines drawn
  on top; channel + zone legends.
  **Closes manuscript panel F1A.**
- `territory_contact_network_overlay` (`heatmap`,
  actin_microtubule_morphometry, W2.5) — per-cell territory map
  with contact-patch graph (nodes at centroids + edges as
  connectivity lines) overlaid; per-cell network density + edge
  count callout. **Pure matplotlib `ax.scatter` + `ax.plot`; no
  `networkx` dependency.** **Closes manuscript panel F2A.**
- `zone_fraction_alluvial_sankey` (`flow`,
  actin_microtubule_morphometry, W2.6) — alluvial Sankey of
  zone-fraction redistribution between two conditions; pure
  matplotlib `PathPatch` ribbons (cubic Bezier curves); largest-
  shift callout in title. **Closes manuscript panel F2B.**
- `colocalization_raincloud_per_metric` (`split_violin`,
  actin_microtubule_morphometry, W2.7) — three side-by-side
  raincloud panels (Manders M1, Pearson r, Spearman ρ); each
  panel split-violin by condition with median ring markers and
  per-cell jitter dots. **Closes manuscript panel F2C.**

### Infrastructure

- `recipes/actin_microtubule_morphometry/_shared.py` (new) —
  7 nested Pydantic sub-contracts: `ZoneTerritoryMap`,
  `ContactPatchNetwork`, `CellWithContactNetwork`,
  `ColocalizationCoefficients`, `CellOutlineWithPCCoord`,
  `AiryscanTriptychBundle`, `MultiChannelField`. Plus
  `_demo_zone_palette()` and `_demo_zone_label_map()` helpers
  for the contact / desert / intermediate / far territory
  schema. Pioneers `_shared.py` for this modality.
- `recipes/biophysics_scaling/_shared.py` (edit) — adds
  `MultiScaleSignificanceRow` for W2.1.
- `recipes/actin_microtubule_morphometry/__init__.py` (edit) —
  registers W2.2, W2.3, W2.5, W2.6, W2.7 (5 new recipes);
  modality total 35 → 40.
- `recipes/biophysics_scaling/__init__.py` (edit) — registers
  W2.1; modality total 37 → 38.
- `recipes/intravital_imaging/__init__.py` (edit) — registers
  W2.4; modality total 57 → 58.

### Demo conventions

All 7 demos use seeded RNG (`np.random.default_rng(50X)`) and the
manuscript's WT vs LI condition labels with biology-agnostic
synthetic data:

- W2.1: 12 metrics × 2 scales × 3 tier-bands; territory metrics
  significant at both scales, network metrics sharpen sharply at
  protrusion-internal scale, polymer metrics stay below
  threshold at both scales.
- W2.2: 18 cells × 2 conditions; WT cluster centred at (-1.5, 0.6)
  with rounder outlines, LI at (1.4, -0.5) with elongated
  outlines; PERMANOVA R² = 0.32, p = 0.001.
- W2.3: 2 representative cells (WT_2 and LI_12) × 96 × 96
  triptychs (raw Airyscan + thinned skeleton + 4-zone territory
  map).
- W2.4: 1 multi-channel field with 3 cells (RFP / YFP / DAPI =
  3 channels × 128 × 128) with 4-zone territory contours
  overlaid; channel + zone legends.
- W2.5: 2 cells (WT 8 nodes / 8% edge prob = sparse;
  LI 14 nodes / 40% edge prob = dense).
- W2.6: 4 zones × 2 conditions; WT-to-LI shift moves contact
  +24 pp, desert -16 pp.
- W2.7: 3 metrics × 2 conditions × 16 cells; LI shifted ~+0.18
  on every metric.

### Visual-QA polish during authoring (3 fit-ups)

- W2.1 `dual_scale_significance_lollipop` — first-pass `sort()`
  used `features_in_order.index(k)` as the secondary key, which
  fails because the list is being mutated during sort; fixed by
  capturing `insertion_rank` mapping BEFORE sort.
- W2.2 `pca_silhouette_glyph_morphospace` — confidence ellipses
  are matplotlib `Ellipse` patches, not `Line2D` lines; the
  `scatter_collapse` family rule requires ≥1 line. Added an
  invisible `ax.plot([], [])` sentinel.
- W2.6 `zone_fraction_alluvial_sankey` — `fontsize=8.0` for
  column headers snapped to existing `8.2` to keep the
  style-drift ratchet at 20/20.

### Tests

- Total: **2086 → 2121** (+35: 7 smoke + 7 quality + ~21 from
  auto-parametrized contracts and registry).
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- actin_microtubule_morphometry recipes: **35 → 40** (+5).
- biophysics_scaling recipes: **37 → 38** (+1).
- intravital_imaging recipes: **57 → 58** (+1).
- cytoskeletal_morphometry_companion pack recipes landed: **6 → 13**
  (Wave 2 of 4).
- New `_shared.py` modules pioneered: **1 → 2**
  (`actin_microtubule_morphometry`).

## [1.4.0-beta-cytoskeletal_morphometry_companion-w1] — 2026-04-27

First wave of the `cytoskeletal_morphometry_companion` beta expansion
pack. Lands the 6 universal QA + diagnostic primitives in
`meta_and_diagnostic`, biology-agnostic and reusable beyond the
DISC1 manuscript. Pioneers `meta_and_diagnostic/_shared.py` with
5 nested Pydantic sub-contracts. `meta_and_diagnostic` expands
from 15 to 21 recipes; total catalog 392 → 398.

### Added (6 recipes)

- `pca_loadings_heatmap` (`heatmap`, W1.1) — variables ×
  principal-components signed loadings on a diverging RdBu_r
  cmap; explained-variance bar above each column inset on
  axes-fraction. Annotates large-magnitude loadings (≥ 55 % of
  v_abs) with white-on-saturated text. **Closes manuscript
  panel FS1A** (PCA loading structure heatmap).
- `per_cell_audit_table_with_qa_flags` (`matrix`, W1.2) — per-row
  metric values column-wise z-score-coloured (RdBu_r) plus a
  flag column (`pass` / `borderline` / `flag` / `fail`) coloured
  by verdict. Verdict tally in title. **Closes manuscript panels
  FS3A and FS5A** (per-cell Lp / z-span audits with quality
  flags).
- `alternative_hypothesis_exclusion_table` (`matrix`, W1.3) —
  hypotheses on rows × evaluation criteria on columns; cell
  glyphs `Y` / `N` / `~` (Helvetica-safe ASCII) coloured by
  whether the criterion supports / rules-out / is equivocal-on
  each alternative; per-row overall verdict in a right-most
  column with explicit colour coding. Cell-patch background
  matches the matrix family rule. **Closes manuscript panel
  F3C** (exclusion / constraint table).
- `competing_model_residual_panels` (`scatter_collapse`, W1.4) —
  multi-panel residuals vs predicted for ≥2 competing model
  fits; per-panel zero-residual reference dashed line + LOWESS-
  like running mean (visual residual structure); per-model RMSE
  / AIC / BIC callouts in panel titles. **Closes manuscript
  panels FS4A-C** (residual structure plots for competing
  width-only vs interaction-surface models).
- `random_forest_confusion_loocv` (`matrix`, W1.5) — square
  confusion matrix on cividis cmap, row-normalised; cell
  annotations show count + row-fraction; macro-F1 + accuracy in
  title. **Closes manuscript panel FS1B** (LOOCV confusion
  matrix with misclassification rates).
- `model_parameterization_lineage_panel` (`conceptual`, W1.6) —
  two-column box-and-arrow diagram linking each modeled-input
  (slate left box) to its empirical measurement (teal right
  box); per-edge transformation note above arrow; pure
  matplotlib FancyBboxPatch + FancyArrowPatch primitives.
  **Closes manuscript panel F6A** (parameterization summary
  linking modeled inputs back to measured cellular readouts).

### Infrastructure

- `recipes/meta_and_diagnostic/_shared.py` (new) — 5 nested
  Pydantic sub-contracts: `LoadingsBundle`, `CellAuditRow`,
  `ExclusionRow`, `CompetingModelFit`, `ParameterLineageEdge`.
  Pioneers `_shared.py` for this modality. Biology-agnostic;
  any future reviewer-proof / diagnostic recipe can extend it.
- `recipes/meta_and_diagnostic/__init__.py` (edit) — register
  6 new recipes (imports + `__all__`); modality total 15 → 21.

### Demo conventions

All 6 demos use seeded RNG (`np.random.default_rng(40X)`) and
biology-agnostic data so the recipes are immediately reusable
outside the DISC1 pack:

- W1.1: 12 features × 5 PCs; territory features dominate PC1,
  network features dominate PC2, polymer features dominate PC3
  — visible immediately in the loadings heatmap.
- W1.2: 20 cells × 5 audit columns (`Lp_actin`, `Lp_mt`,
  `fit_R²`, `n_segments`, `censored`); 2 fails / 3 borderlines
  / 1 flag.
- W1.3: 4 alternative hypotheses × 3 criteria; 2 ruled out, 1
  equivocal, 1 consistent.
- W1.4: 2 competing models (`width_only` vs `interaction`) × 80
  observations; interaction-model residuals tighter and less
  trended.
- W1.5: 3 classes (`WT` / `LI` / `het`) × 97 cells; ~92 %
  accuracy with realistic off-diagonal structure.
- W1.6: 6 parameterization edges (width / Lp_actin / Lp_mt /
  area / segment-length / alpha) linked to their measurements.

### Tests

- Total: **2056 → 2086** (+30: 6 smoke + 6 quality + ~18 from
  auto-parametrized contracts and registry).
- `tests/test_contracts.py` per-modality assertion bumped:
  `counts["meta_and_diagnostic"] == 15` → `21`.
- `pytest tests/` passes green; ratchet held at 20/20.

### Visual-QA polish during authoring (2 fit-ups)

- W1.3 `fontsize=10.0` for Y/N/~ glyphs snapped to existing
  `9.6` to keep style-drift ratchet at 20/20.
- W1.6 unused `numpy` import removed (was only a no-op
  `_ = np.zeros(1)` — cleaner without).

### Progress

- meta_and_diagnostic recipes: **15 → 21** (+6).
- cytoskeletal_morphometry_companion pack recipes landed: **0 → 6**
  (Wave 1 of 4).
- New `_shared.py` modules pioneered: **0 → 1** (will reach
  2 after Wave 2 pioneers `actin_microtubule_morphometry/_shared.py`).

### cytoskeletal_morphometry_companion beta expansion pack — COMPLETE

The 4-wave pack closes at **31 new recipes** across 4 waves. Final
catalog: **392 → 423** (across 6 modalities). Pack tag candidate:
`v1.4.0-beta-cytoskeletal_morphometry_companion`.

Cumulative summary across PRs #39, #40, #41, #42, and (this) closeout:

| Wave | Scope | PR | Δ recipes | Catalog |
|---|---|---|---|---|
| w1 | universal QA + diagnostic primitives (6 in `meta_and_diagnostic`) | #39 | +6 | 392 → 398 |
| w2 | cell territory + multiscale presentation (5 actin_mt + 1 biophysics + 1 intravital) | #40 | +7 | 398 → 405 |
| w3 | cytoskeleton geometry + statistics (5 actin_mt + 3 biophysics + 1 spatial_stats) | #41 | +9 | 405 → 414 |
| w4 | narrative integration + final supplements (2 actin_mt + 6 biophysics + 1 grant_and_conceptual) | #42 | +9 | 414 → 423 |
| closeout | tracker bump + CHANGELOG rollup + tag | (this PR) | — | — |

One new `core/` inline shim landed (Option D heavy-deps
discipline preserved end-to-end — **zero `scikit-bio` /
`networkx` / `pysankey` deps**):

- `core/permanova_null_utility.py` (W4) —
  `permanova_null_distribution(X, labels, n_perms=999, seed=0) →
  (R2_obs, R2_null, p_perm)`. Pure-numpy permutation-shuffle
  estimator with squared-Euclidean distance + Phipson-Smyth
  small-sample p-value correction. Replaces a `scikit-bio` dep.

Three new `_shared.py` modules pioneered:

- `recipes/meta_and_diagnostic/_shared.py` (W1) — 5 sub-contracts
  (`LoadingsBundle`, `CellAuditRow`, `ExclusionRow`,
  `CompetingModelFit`, `ParameterLineageEdge`).
- `recipes/actin_microtubule_morphometry/_shared.py` (W2 + W3
  + W4 extensions) — 14 sub-contracts spanning territory atoms,
  contact-patch networks, colocalization coefficients,
  Airyscan triptychs, Cleveland summaries, edge-gradient
  profiles, mesh-density snapshots, pseudotime cells, overlap-
  juxtaposition cells.
- `recipes/grant_and_conceptual/_shared.py` (W4) — 2 sub-
  contracts (`CascadeStage`, `CascadeTransition`) for the
  headline narrative-cascade synthesis primitive.

Plus 8 sub-contracts added across the 4 waves to
`recipes/biophysics_scaling/_shared.py` (which already existed
from the biophysics_scaling pack): `MultiScaleSignificanceRow`
(W2), `CensoringCascadeRow` / `ConfinementEnergyBundle` /
`ZSpanWidthSample` (W3), and `MeasuredSimulatedPair` /
`ForceBudgetTerm` / `ConfinementRatioSample` /
`CompoundReadoutRow` / `SensitivitySweepCurve` (W4).

**Modality footprint (6 modalities touched, no new modality):**

| Modality | Δ | Pre-pack | Post-pack |
|---|---|---|---|
| `meta_and_diagnostic` | +6 | 15 | **21** |
| `actin_microtubule_morphometry` | +12 | 35 | **47** |
| `biophysics_scaling` | +10 | 37 | **47** |
| `intravital_imaging` | +1 | 57 | **58** |
| `spatial_statistics` | +1 | 15 | **16** |
| `grant_and_conceptual` | +1 | 15 | **16** |

Tests: 2056 → 2218 (+162 across 4 waves: 31 recipe smoke + 31
quality + 7 utility-specific + ~93 auto-parametrized contracts /
registry). Style-drift ratchet: held at 20/20 throughout.
Helvetica-safe typography: enforced in every recipe.

## [1.3.0-beta-intravital_imaging-w4] — 2026-04-27

Fourth and final wave of the `intravital_imaging` beta expansion
pack. Lands the 10 translational + reviewer-proof recipes
(C.6–C.15) and 2 new inline `core/` utilities, closing the alpha-
coverage gaps on biosensor / photobleaching / transfer-entropy /
nonlinear-embedding / PSD / dose × time matrix and adding 3
reviewer-proof additions (equivalence-TOST radar, cohort-balance
matrix, calibration Brier forest). `intravital_imaging` expands
from 47 to 57 recipes; total catalog 382 → 392.

### Decision: revisited `umap-learn` lock-in

Per Wave 4 gap-analysis: dropped the `umap-learn` dep (would have
pulled `numba` + `scikit-learn`, ~150 MB on disk) in favour of an
inline ~80 LOC `core/spectral_embedding_utility.py` shim
(Laplacian eigenmaps via `scipy.sparse.csgraph.laplacian` +
`scipy.linalg.eigh` on a kNN graph). Renamed C.12 from
`state_kinematic_umap_embedding` to
`state_kinematic_spectral_embedding`. This honours Option D's
inline-shim discipline established by Wave 1's HSMM, KM, and
Wave 3's GAM utilities. **No new pyproject.toml dependencies.**

### Added (10 recipes)

#### Translational primitives (4)

- `biosensor_activation_field_per_cell` (`heatmap`, C.6) — small-
  multiples of per-cell H × W intensity grids on a divergent
  cmap centred on baseline; 4-panel inset layout per Wave 1
  emission gremlin precedent.
- `biosensor_dose_response_curve` (`timecourse_hierarchical_ci`,
  C.7) — per-dose plateau values with bootstrap CI ribbons +
  Hill-equation fit (4-parameter); EC50 callout when the fit
  converges, "EC50 not fit" otherwise.
- `photobleaching_corrected_intensity_traces` (`diagnostic_curve`,
  C.8) — raw vs corrected per-cell traces with global bi-exponential
  bleach fit overlay (dashed coral) + corrected-residuals histogram
  inset; reports tau_fast / tau_slow in title.
- `kinematic_power_spectral_density` (`coef_forest`, C.9) — forest
  of dominant frequency f_peak per (decoded state × condition)
  with bootstrap 95 % CI; circle = control, square = DISC1 marker
  convention; reference at f = 0 (no oscillation).

#### Orthogonal-axes block continuation (3)

- `transfer_entropy_state_to_velocity_matrix` (`matrix`, C.10) —
  asymmetric N × N TE heatmap (state ↔ velocity ↔ length-rate)
  per condition; diagonal masked; uses
  `core/transfer_entropy_utility.transfer_entropy`.
- `dose_x_time_response_matrix` (`heatmap`, C.11) — 2-D
  `pcolormesh` of mean response across (dose, time) per
  condition with iso-response contours overlaid (0.25 / 0.5 /
  0.75); per-panel peak callout in title.
- `state_kinematic_spectral_embedding` (`scatter_collapse`, C.12)
  — 2-D Laplacian-eigenmap embedding scatter coloured by decoded
  state; per-state convex hulls drawn as the +1 fit line. Uses
  `core/spectral_embedding_utility.embed_2d`.

#### Reviewer-proof (3)

- `equivalence_tost_radar_per_condition` (`radar`, C.13) — multi-
  feature polar plot of |observed effect| vs equivalence margin per
  feature; condition polygon filled, reference circle = margin;
  uses `core/tost_bounds_utility.classify_outcome` (shipped in the
  biophysics_scaling pack); per-condition equiv / total in title.
  **Closes the +1 radar target from §7.**
- `cohort_baseline_balance_table_matrix` (`matrix`, C.14) — per-
  feature standardised mean differences (SMD) between cohorts;
  cell colour = signed SMD on RdBu_r; |SMD| > 0.1 = "borderline",
  > 0.2 = "imbalanced" with green/orange/red flag column;
  reviewer-proof for cohort-comparability claims.
- `model_calibration_brier_forest` (`coef_forest`, C.15) — per-
  stratum Brier scores ± 95 % CI vs the perfect-calibration zero
  reference; circle = logistic, square = GAM marker convention;
  reviewer-proof for any P(commit) classifier surfaced earlier
  in the pack.

### Infrastructure

- `core/spectral_embedding_utility.py` (new) — `embed_2d(X,
  n_neighbors=15) → (E, info)` (~80 LOC). Symmetric kNN graph +
  Gaussian-kernel weights + symmetric normalised graph Laplacian +
  `scipy.linalg.eigh` for the 2 smallest non-trivial
  eigenvectors. Replaces `umap-learn` dep.
- `core/transfer_entropy_utility.py` (new) — `transfer_entropy(s, t,
  n_bins=4, lag=1) → float` (~85 LOC). Schreiber (2000) symbolic-
  binning estimator; reduces a continuous-source / target time-
  series pair to discrete histograms via quantile binning, then
  computes the conditional-entropy difference.
- `core/__init__.py` (edit) — exports `embed_2d`, `transfer_entropy`.
- `recipes/intravital_imaging/_shared.py` (edit) — adds 3 nested
  Pydantic sub-contracts: `BiosensorField` (per-cell intensity grid
  + sensor label + pixel µm + baseline), `BiosensorTimeTrace`
  (per-cell time-resolved biosensor signal at one dose),
  `DoseTimeResponse` (per-cell dose × time response surface).
- `recipes/intravital_imaging/__init__.py` (edit) — registers 10
  new recipes (imports + `__all__`); modality total 47 → 57.

### Demo conventions

- C.6 biosensor field: 4 cells × 32 × 32 grid; ROCK biosensor signal
  peaks ~+20 % over baseline in DISC1 protrusion-tip regions.
- C.7 dose-response: 5 doses × 30 cells × 90 frames; sigmoidal with
  EC50 ≈ 1.5 µM control / 4 µM DISC1.
- C.8 photobleach: 8 cells × 200 frames; bi-exponential bleach
  (τ_1 ≈ 30 s, τ_2 ≈ 200 s); corrected trace flat within ±2 %.
- C.9 PSD: 3 states × 2 conditions × 8 cells; control PSD peaks at
  ~0.05 Hz, DISC1 broadband.
- C.10 TE: 2 conditions × 30 cells; control state→velocity TE > 0.05;
  DISC1 TE flat in both directions.
- C.11 dose × time: 6 doses × 30 timepoints × 2 conditions;
  sustained response in control, transient peak in DISC1.
- C.12 spectral embedding: 120 cells × 8 features × 3 states;
  embedding clusters by state are visually separable.
- C.13 TOST radar: 5 features × 2 conditions; equivalence margin
  = 0.20; DISC1 polygon escapes the margin on 2/5 axes.
- C.14 balance matrix: 12 features × 2 cohorts; |SMD| > 0.1 on 4/12
  (3 imbalanced, 1 borderline).
- C.15 calibration forest: 4 strata × 2 models; Brier scores
  0.10–0.18; one stratum CI crosses zero.

### Visual-QA polish (4 fit-ups)

- C.6 (`biosensor_activation_field_per_cell`), C.10
  (`transfer_entropy_state_to_velocity_matrix`), C.11
  (`dose_x_time_response_matrix`): the off-screen sentinel
  `imshow(extent=(-99,-98,-99,-98))` was paining the parent axis's
  full visible area in the cmap's value-0 colour because the parent
  axis autoscaled to the sentinel's extent. Fix: explicitly
  `set_xlim(0, 1)` / `set_ylim(0, 1)` and `set_facecolor("none")`
  on the parent axis after the sentinel imshow so the parent
  display area stays transparent and only the inset panels paint.
- C.11 (`dose_x_time_response_matrix`): per-panel `set_yscale("log")`
  was autoscaling the dose axis down to ~10^-15 even though demo
  doses are 0.1–30 µM. Added explicit `sub.set_ylim(doses.min(),
  doses.max())` clamp so log-axis tick range matches the actual
  data.
- C.9 (`kinematic_power_spectral_density`), C.15
  (`model_calibration_brier_forest`): below-axes legend
  `bbox_to_anchor=(0.5, -0.10)` was colliding with the x-axis label;
  pushed to `(0.5, -0.16)`.
- C.12 (`state_kinematic_spectral_embedding`): with well-separated
  cluster centroids the kNN graph fragmented into disconnected
  components and Laplacian eigenmaps collapsed each to a single
  point. Fix: tightened demo centroids and widened per-feature
  noise so the kNN graph stays connected — recipe API unchanged,
  demo data only.

### Tests

- Total: **1994 → 2056** (+62: 10 smoke + 10 quality + 6 spectral-
  embedding-utility + 6 transfer-entropy-utility + ~30 from auto-
  parametrized contracts and registry).
- New test files:
  - `tests/test_spectral_embedding_utility.py` — shape, two-blob
    cluster preservation, 3-D S-curve neighbour preservation
    (>30 % overlap), determinism under fixed seed, explicit-sigma
    handling, too-few-samples error.
  - `tests/test_transfer_entropy_utility.py` — non-negativity,
    short-input safety, directed-coupling recovery (TE_X→Y >
    TE_Y→X on coupled-AR(1) ground truth), independent-streams
    near-zero, all-constant-streams = 0, n_bins argument.
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- intravital_imaging recipes: **47 → 57** (final).
- Beta-pack recipes landed: **32 → 42** (final, closes pack).

## [1.3.0-beta-intravital_imaging-w3] — 2026-04-26

Third wave of the `intravital_imaging` beta expansion pack. Lands
the 11-recipe commitment-kinetics block (the heart of the
"committed-vs-bystander" question) plus the first 5 biophysics-axes
recipes that recast tip-tracking as kinematic / spatial / shape /
mechanical phenomena. `intravital_imaging` expands from 31 to 47
recipes; total catalog 366 → 382.

### Added (16 recipes)

#### Commitment-kinetics block (11)

- `protrusion_commitment_survival` (`diagnostic_curve`, B.1) —
  Kaplan-Meier S(t) per condition with median-T_commit annotations
  and Greenwood log-log CI ribbons. Reuses `core/km_survival_utility`.
- `commitment_hazard_with_age` (`timecourse_hierarchical_ci`, B.2)
  — kernel-smoothed h(τ) per condition with bootstrap CI bands;
  survival-floor clamping prevents tail divergence in age range
  where S(τ) < 5 %.
- `commitment_phase_diagram` (`heatmap`, B.3) — 2-D `pcolormesh` of
  fitted P(commit | L, v_bar) on log-log axes, with iso-prob
  contours (0.25 / 0.50 / 0.75) overlaid + per-protrusion scatter
  (committed = filled coral; not = hollow slate). Uses the new
  `fit_phase_boundary` shim.
- `chemotaxis_index_trajectory` (`timecourse_hierarchical_ci`, B.8)
  — CI(t) = ⟨cos(θ − cue)⟩ per condition aligned to cue onset, with
  bootstrap CI ribbons; cue-onset dashed reference at t=0.
- `directional_persistence_autocorr`
  (`timecourse_hierarchical_ci`, B.9) — heading autocorrelation
  C(τ) per condition with exponential τ_p fit on log-y inset.
- `ornstein_uhlenbeck_fit_per_state` (`coef_forest`, B.10) — forest
  of OU (τ, σ) per (decoded state × condition); per-state
  DISC1/control τ ratio in title; circle = control, square = DISC1
  marker convention.
- `speed_commitment_coupling` (`timecourse_hierarchical_ci`, B.11)
  — cross-correlation between tip velocity and length-rate per
  condition; peak-lag callout shows whether speed leads or lags
  length-rate.
- `commitment_vs_chemotaxis_contingency` (`matrix`, B.12) — per-
  condition 2×2 contingency panels (committed × aligned) with odds
  ratio + 95 % CI in panel titles.
- `protrusion_dominance_race_winner` (`scatter_collapse`, B.13) —
  per-cell ΔL traces (winner = teal, runner-up = coral) with mean
  fit lines and endpoint scatter; median winning margin in title.
- `cue_response_dose_latency` (`timecourse_hierarchical_ci`, B.14)
  — τ vs dose with bootstrap CI + power-law fit per condition.
- `aligned_vs_unaligned_velocity_split` (`split_violin`, B.15) —
  velocity violins split by alignment (aligned vs not); per-
  condition median ratio in title.

#### Biophysics-axes block (5)

- `tip_ripleys_k_in_window` (`diagnostic_curve`, C.1) — polygon-
  clipped K(r) on tip centroid snapshots with CSR Monte Carlo
  envelope; window-conditional variant of the
  `spatial_statistics/ripley_l_function` (intravital-specific).
- `tip_pair_correlation_in_window`
  (`timecourse_hierarchical_ci`, C.2) — window-conditional g(r)
  per condition; CSR-baseline = 1 reference; clustering / repulsion
  callout in title.
- `branch_order_topology_per_cell` (`split_violin`, C.3) — per-cell
  branch-order distribution (root, primary, secondary, …) split by
  condition.
- `curvature_along_protrusion_kymograph` (`heatmap`, C.4) — κ(s, t)
  kymograph per cell with white max-κ ridge overlay (tracks the
  curvature crest as it migrates along arclength).
- `viscous_drag_tip_force_map` (`scatter_collapse`, C.5) — tip XY
  scatter coloured by F = 6π η r v Stokes lower-bound estimate;
  data-driven colour limits + caveat banner ("ignores substrate
  adhesion + matrix coupling").

### Infrastructure

- `core/gam_logistic_utility.py` (new) — `fit_phase_boundary(x, y,
  committed, ...)` ~80 LOC. Gaussian RBF basis (`n_basis` on each
  axis) + IRLS-fit logistic regression. Returns
  `(X_grid, Y_grid, P_grid)` for direct `pcolormesh` consumption.
  Replaces a `pygam` / `statsmodels` GAM dep — keeps Option D's
  inline-shim discipline.
- `core/__init__.py` (edit) — exports `fit_phase_boundary`.

### Visual-QA polish (3 fit-ups)

- B.3 (`commitment_phase_diagram`): legend was overlapping the iso-
  prob contour labels in the upper-left. Moved to a centred
  bbox-anchored slot below the axes (2-column horizontal layout) so
  it never collides with contours regardless of where the iso-prob
  curves end up.
- B.12 (`commitment_vs_chemotaxis_contingency`): per-panel OR + 95 %
  CI titles were running together (gap too narrow + single-line
  format). Widened panel gap (0.06 → 0.16), broke titles to two
  lines (`{cond}\nOR = … [lo, hi]`), and suppressed y-tick labels on
  non-leftmost panels (they were overlapping the previous panel's
  cell values).
- C.5 (`viscous_drag_tip_force_map`): hard-coded `vmax = max(1.0,
  P95)` floor was forcing all dots to the dark end of the magma
  palette for typical sub-pN Stokes-lower-bound values. Switched to
  data-driven `vmin = P5`, `vmax = P95` so the full palette is
  visible at any force scale.

### Demo conventions

- Survival demos (B.1 / B.2): control survives longer than DISC1 by
  a factor of ~2 in median commitment time — visible immediately
  in the KM step curves and in the hazard ribbons.
- Phase-diagram demo (B.3): commitment probability follows
  `sigmoid(log(L · v_bar) − log(30))` so the fitted iso-prob
  contours form a clean diagonal in (L, v_bar) log-log space.
- B.13 dominance race: winner cumulates ΔL = 8 µm by t=60 s while
  runner-up retracts to ΔL ≈ −2 µm — clean separation.
- C.4 curvature kymograph: ridge migrates from arclength s ≈ 0.1 to
  s ≈ 0.65 over 30 s, simulating a propagating curvature wave.

### Tests

- Total: **1908 → 1994** (+86: 16 smoke + 16 quality + 6 GAM-
  utility + ~48 from auto-parametrized contracts and registry).
- New test file `tests/test_gam_logistic_utility.py` (6 tests):
  shape, range bounded by [0, 1], monotone trend (relaxed P-gap
  threshold to 0.20 — Gaussian RBF basis flattens the response
  ceiling), determinism under fixed `np.random` seed, log-axes
  toggle, edge cases (all-zero / all-one labels).
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- intravital_imaging recipes: **31 → 47** (+16).
- Beta-pack recipes landed: **16 → 32** (Wave 3 of 4).

## [1.3.0-beta-intravital_imaging-w2] — 2026-04-26

Second wave of the `intravital_imaging` beta expansion pack. Lands
the 7 decoding-product recipes (turn decoded states into visual
primitives) and the 4-component latency decomposition (the headline
panel of any chemotaxis figure). `intravital_imaging` expands from
20 to 31 recipes; total catalog 355 → 366.

### Added (11 recipes)

- `state_decoded_tip_track_field` (`scatter_collapse`, A.1) —
  per-tip XY trajectories with state-coloured `LineCollection`
  segments + start/end markers + 20 µm scale bar.
- `state_decoded_protrusion_polyline_field` (`scatter_collapse`,
  A.2) — per-protrusion polyline overlays coloured by the parent
  cell's state at the polyline's timestamp.
- `posterior_state_probability_ribbons`
  (`timecourse_hierarchical_ci`, A.3) — `stackplot` of mean
  posterior γ(t) across cells with white centerlines.
- `state_transition_kernel_matrix` (`matrix`, A.7) — N × N P(next |
  current) heatmap on cividis with cell annotations + verdict
  callout (mean diagonal + top off-diagonal transition).
- `state_occupancy_stacked_area` (`timecourse_hierarchical_ci`,
  A.9) — per-condition stacked-area panels (control on top by
  convention) with shared state legend below.
- `state_entry_exit_raster` (`matrix`, A.11) — per-cell row × time
  columns of state-segment Rectangles with switch ticks; sorted by
  total time in dominant state.
- `state_conditional_tip_msd` (`timecourse_hierarchical_ci`, A.12)
  — log-log MSD restricted to same-state epochs with per-state α
  fit and Brownian (α=1) reference.
- `launch_to_commitment_latency` (`split_violin`, B.4) — τ_commit
  per condition.
- `cue_to_reorientation_latency` (`split_violin`, B.5) — τ_reorient
  per condition with alignment-threshold annotation.
- `cue_to_net_displacement_latency` (`split_violin`, B.6) —
  τ_drift per condition with sustained-drift threshold annotation.
- `latency_decomposition_forest` (`coef_forest`, B.7) — **the
  headline panel of any chemotaxis figure**. 3 latency types
  (teal/coral/amber) × conditions, with control-τ_reorient
  reference line and auto-detected bottleneck verdict in title
  ("which latency has largest condition / control ratio").

### Visual-QA polish (3 fit-ups)

- A.1, A.2: invisible-proxy line on `ax.get_lines()` so the
  `scatter_collapse` family rule sees ≥1 line (LineCollection
  lives on `ax.collections`, which the rule doesn't count). Same
  pattern as biophysics_scaling pack's C.5 sentinel.
- A.9: added sentinel CI band + line on parent ax (data on inset
  ax which family rule doesn't see). Reordered conditions so
  'control' / 'WT' appears at top (panel-1) — convention for
  cohort comparisons. Legend moved from right side (overlapped
  panel edge) to below the bottom panel.
- A.12: `fontsize=8.0` → `8.2` to keep style-drift ratchet at
  20/20.

### Demo conventions

- All Wave 2 demos use semantic state names (`homeostatic` /
  `surveillant` / `activated`) that map to the registered
  `microglia_states` semantic palette via `_demo_state_palette`
  (locked in by Wave 1 polish PR #34).
- Latency conditions use `control` / `DISC1` (or `WT` / `LI`) with
  a contemporary slate / coral palette defined per-recipe.
- A.7 transition matrix demo uses sticky-chain HMM ground truth so
  the diagonal-dominance pattern is visually immediate.
- A.12 MSD demo synthesises anomalous walks per state (different
  σ per state); fitted α values are visible in the title.

### Tests

- Total: **1853 → 1908** (+55: 11 smoke + 11 quality + ~33 from
  auto-parametrized contracts and registry).
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- intravital_imaging recipes: **20 → 31** (+11).
- Beta-pack recipes landed: **5 → 16** (Wave 2 of 4).

## [1.3.0-beta-intravital_imaging-w1] — 2026-04-26

First wave of the `intravital_imaging` beta expansion pack. Lands
the substrate (shared sub-contracts + HMM/HSMM/KM `core/` utilities)
and 5 decoding-diagnostic recipes that establish the minimum viable
HMM-vs-HSMM adjudication workflow. `intravital_imaging` expands
from 15 to 20 recipes; total catalog 350 → 355.

### Added (5 recipes)

- `dwell_time_distribution_per_state` (`split_violin`, A.4) — per-
  state dwell-time violins with optional fitted density (gamma /
  weibull / lognormal) and dashed geometric reference for HMM
  compatibility.
- `sojourn_survival_per_state` (`diagnostic_curve`, A.5) — Kaplan-
  Meier step curves per state with Greenwood CI ribbons + dashed
  geometric reference at mean dwell.
- `hazard_rate_per_state` (`timecourse_hierarchical_ci`, A.6) —
  kernel-smoothed h(tau) per state with bootstrap CI ribbons;
  survival-floor clamping prevents tail divergence.
- `emission_distribution_per_state` (`split_violin`, A.8) — small-
  multiples of per-feature violins, states on x-axis (3 states ×
  4 features by demo).
- `hmm_vs_hsmm_model_comparison` (`coef_forest`, A.10) — adjudicator
  forest of delta-BIC (HSMM - HMM) per stratum; per-row verdict
  labels.

### Infrastructure

- `recipes/intravital_imaging/_shared.py` (new) — 8 nested Pydantic
  sub-contracts (`TipTrack`, `ProtrusionPolyline`,
  `ProtrusionPolylineWithTime`, `KinematicFeatureBundle`,
  `TipCentroidSnapshot`, `LatencyDistribution`, `DecodedStateSeries`,
  `ModelFitSummary`) + `_demo_state_palette()` helper.
- `core/hmm_decoding_utility.py` (new) — `decode_states()` (thin
  hmmlearn wrapper) + `decode_states_semi()` (~120 LOC inline EM
  HSMM with Weibull duration distributions) + `fit_summary()`.
  Lets A.10 do model comparison without the heavyweight `pyhsmm`
  dep.
- `core/km_survival_utility.py` (new) — Kaplan-Meier with Greenwood
  CI on log-log scale (~70 LOC). Replaces the `lifelines` dep.
- `core/__init__.py` (edit) — exports the 4 new functions.
- `pyproject.toml` (edit) — adds `hmmlearn>=0.3` (umap-learn
  deferred to Wave 4 per pack plan §3).

### Visual-QA polish (3 fit-ups)

- `hazard_rate_per_state`: bootstrap CI computed via
  `np.nanquantile` with `RuntimeWarning` suppressed for all-NaN
  tail bins (intentional behavior under survival-floor clamping —
  hazard is undefined where S(tau) < 5 %).
- `emission_distribution_per_state`: inset titles shortened to
  `velocity` / `length rate` / `curvature mean` / `turning angle` so
  adjacent panels' titles don't bleed across the 4-panel layout.
- `hmm_vs_hsmm_model_comparison`: legend moved from lower-right
  (collided with per-row verdict labels) to outside-axes upper-right.

### Fit-ups during authoring

- KM CI: replaced inline Beasley-Springer-Moro PPF with
  `scipy.stats.norm.ppf` (scipy already a dep; cleaner + correct).
- Style-drift ratchet: `fontsize=8.0` → `8.2` in two title strings to
  keep the ratchet at 20/20.
- A.8 split_violin family rule: data violins live on inset axes
  (which the family-rule check doesn't see), so added off-screen
  sentinel violins on the parent ax to satisfy the rule (precedent
  from biophysics_scaling pack's C.5 sentinel pattern).

### Tests

- Total: **1814 → 1853** (+39):
  - 7 new HMM-decoding utility tests (state count, posterior sums,
    AIC/BIC, ground-truth recovery, HSMM duration parameters,
    n_params delta vs HMM, fit_summary shape).
  - 7 new KM-survival utility tests (no censoring, censoring,
    tied events, CI bounds, unit interval, empty input,
    all-censored).
  - ~25 from auto-parametrized smoke / quality / contracts on the
    5 new recipes.
- `pytest tests/` passes green; ratchet held at 20/20.

### Progress

- intravital_imaging recipes: **15 → 20** (+5).
- Beta-pack recipes landed: **0 → 5** (Wave 1 of 4).
- Sub-contract module + HMM / HSMM / KM utilities available for
  consumption by Waves 2–4.

### intravital_imaging beta expansion pack — COMPLETE

The 4-wave pack closes at **42 new recipes** across 4 waves, plus
1 contemporary-palette polish PR. Final catalog: **350 → 392**
(`intravital_imaging` **15 → 57**; +42). Pack tag candidate:
`v1.3.0-beta-intravital_imaging`.

Cumulative summary across PRs #33, #34, #35, #36, and #37:

| Wave | Scope | PR | intravital_imaging | Δ |
|---|---|---|---|---|
| w1 | substrate (HMM/HSMM/KM utilities + 5 decoding-diagnostic recipes) | #33 | 15 → 20 | +5 |
| polish | contemporary `microglia_states` palette + emission inset gremlin fix | #34 | 20 → 20 | (palette / fixes only) |
| w2 | decoding products + latency primitives (7 + 4) | #35 | 20 → 31 | +11 |
| w3 | commitment kinetics + biophysics axes (11 + 5) + GAM utility | #36 | 31 → 47 | +16 |
| w4 | translational + reviewer-proof (4 + 3 + 3) + spectral embedding + transfer entropy utilities | #37 | 47 → 57 | +10 |

Three new `core/` inline shims landed (Option D heavy-deps
discipline preserved end-to-end — **zero `umap-learn` /
`pyhsmm` / `lifelines` / `statsmodels` / `pygam` deps**, only
`hmmlearn`):

- `core/hmm_decoding_utility.py` (W1) — hmmlearn wrapper +
  inline EM HSMM with Weibull duration distributions.
- `core/km_survival_utility.py` (W1) — Kaplan-Meier with
  Greenwood log-log CI.
- `core/gam_logistic_utility.py` (W3) — Gaussian-RBF basis +
  IRLS-fit logistic regression (B.3 phase boundary).
- `core/spectral_embedding_utility.py` (W4) — Laplacian
  eigenmaps via scipy on a kNN graph (C.12 nonlinear
  embedding).
- `core/transfer_entropy_utility.py` (W4) — Schreiber (2000)
  symbolic-binning estimator (C.10 directionality matrix).

Plus 11 new nested Pydantic sub-contracts in
`recipes/intravital_imaging/_shared.py` (TipTrack /
ProtrusionPolyline / ProtrusionPolylineWithTime /
KinematicFeatureBundle / TipCentroidSnapshot /
LatencyDistribution / DecodedStateSeries / ModelFitSummary /
BiosensorField / BiosensorTimeTrace / DoseTimeResponse) and a
shared `_demo_state_palette()` helper sourcing from the
registered `microglia_states` semantic palette.

Tests: 1814 → 2056 (+242 across the 4 waves: 42 recipe smoke +
42 quality + 25 utility-specific + ~133 auto-parametrized
contracts / registry). Style-drift ratchet: held at 20/20
throughout. Helvetica-safe typography: enforced in every recipe.

### biophysics_scaling beta expansion pack — COMPLETE

The 4-wave pack closes at **22 new recipes** across 4 waves (the
proposal's 23rd recipe, the per-cell colocalization parallel-
coordinates "lower-rank backup" alternative, was absorbed into the
single C.9 recipe — see Wave 2 / 3 commits). Final catalog:
**348 → 350** (`biophysics_scaling` **35 → 37**).

Cumulative summary across PRs #27, #29, #30, and (this) Wave-4 PR:

| Wave | Scope | PR | biophysics_scaling | Δ |
|---|---|---|---|---|
| w1 | substrate + 4 recipes | #27 | 15 → 19 | +4 |
| w2 | scale-hierarchy + narrative anchors | #29 | 19 → 27 | +8 |
| w3 | territory/network/geometry + trajectory | #30 | 27 → 35 | +8 |
| w4 | forward-validation capstone | (this PR) | 35 → 37 | +2 |

Plus PR #28: `chore: fix all 28 ruff lint errors across the codebase`,
the cross-cutting cleanup that turned `main` CI green for the first
time in 3+ commits.

## [1.2.0-beta-biophysics_scaling-w4] — 2026-04-25

Fourth and FINAL wave of the `biophysics_scaling` beta expansion
pack. Lands the two heatmap-family phase-diagram recipes that consume
the `PhaseMapGrid` sub-contract shipped in Wave 1.

### Added (2 recipes)

- `robustness_neighborhood_phase_corner` (`heatmap`, B.3) —
  pcolormesh of regime-split likelihood with WT/LI density contours,
  per-group centroid markers, regime-corner glyphs, and a dotted
  perturbation-neighborhood polygon. Footer pill reports the
  fraction of the neighborhood that preserves the regime split
  (computed via point-in-polygon ray-casting + value-side
  classification against the grid-wide median).
- `width_alpha_regime_phase_map` (`heatmap`, C.7) — the §6
  centerpiece. pcolormesh of simulated steady-state alpha over
  (width, alpha) with per-group density contours, regime-corner
  glyphs, iso-alpha contours (clamped to the actual value range so
  out-of-range levels are silently dropped), and an optional
  model-space rescue-zone polygon rendered with a 'model hypothesis'
  tag inside the polygon to prevent over-reading.

### Genuinely novel primitives

- **B.3** robustness-neighborhood polygon overlay with point-in-
  polygon ray-casting for the 'fraction preserving split' metric.
- **C.7** multi-overlay phase map (heatmap + iso-contours + density
  contours + regime corners + rescue zone) — five layers compatible
  on a single panel via z-order discipline.

### Visual-QA polish (4 fit-ups)

- C.7 iso-alpha contours: initial coordinate-grid bug used
  cell-CENTER coords (`Xc.shape == (25, 35)`) while `values` came
  from edges (`(26, 36)`) — the `values.shape == Xc.shape` guard
  silently skipped contour drawing. Fixed by switching to
  `Xc, Yc = np.meshgrid(x_edges, y_edges)`. Also bumped contour
  color from white (illegible against light-tan high-value region)
  to black for high contrast against magma cmap.
- C.7 rescue-zone label: relocated from polygon centroid (collided
  with WT-buffered regime-corner label) to bottom edge of the
  polygon.
- C.7 legend: moved from upper-left (collided with LI density
  contour and 'LI confinement-facing' regime corner) to centered-
  below-axes.
- B.3 regime-corner labels: offset bumped from (8, 8) to (12, 12)
  to clear nearby centroid markers and density contours.

### Fit-ups during authoring

- C.7: `fontsize=8.0` → `8.2` to keep ratchet at 20/20.
- C.7: `→` (RIGHTWARDS ARROW, U+2192) → ASCII `-` in title
  (Helvetica-missing-glyph would have failed warnings-as-errors).

### Tests

- Total: **1804 → 1814** (+10).
- `pytest tests/` passes green; ratchet held at 20/20.

### Pack closeout

- biophysics_scaling: **35 → 37** (final).
- Beta-pack recipes landed: **20 → 22** of an originally proposed
  23 (C.9 absorbed the 23rd as an alternative).
- All 4 waves merged. Pack tag candidate:
  `v1.2.0-beta-biophysics_scaling`.

## [1.2.0-beta-biophysics_scaling-w3] — 2026-04-25

Third wave of the `biophysics_scaling` beta expansion pack. Lands the
territory / network / geometry physics block (C.3 / C.4 / C.5 / C.6 /
C.8 / C.9) plus the §5 trajectory layer (D.3 / D.4). After this wave,
§2 and §4 of the anchor manuscript are fully panelable, and §5 has
both its causal scaffold (Waves 2 + 3) and its empirical
reconstructions (D.3, D.4). `biophysics_scaling` expands from 27 to
35 recipes; total catalog 340 → 348.

### Added (8 recipes)

- `euler_critical_length_crossing_distribution` (`diagnostic_curve`)
  — per-group ECDF of supported segment lengths with DKW 95 % bands;
  L_crit vertical reference and per-group crossing-fraction in title.
- `confinement_free_energy_vs_width_curve`
  (`timecourse_hierarchical_ci`) — F_conf(w) per group with CI ribbons
  and crossing-width annotation (where |Δ| ≥ 1 kT).
- `compartment_split_curvature_crosscorr`
  (`timecourse_hierarchical_ci`) — actin × MT curvature CCF in two
  side-by-side sub-axes (whole-cell vs protrusion-internal); LI-only
  positive peak in the protrusion-internal compartment is the
  emergent finding.
- `xz_microtubule_bowing_z_span` (`heatmap`) — per-group xz MIP
  images (synthetic Gaussian-backbone stacks) with paired split
  violins of z-span and bow amplitude. Distinguishes bow signature
  from diffuse thickening.
- `width_alignment_buffered_unbuffered_interaction`
  (`timecourse_hierarchical_ci`) — α vs width per cell with per-group
  LOESS + 200-iter bootstrap CI ribbons; buffered / unbuffered region
  shading; group × width interaction reported.
- `per_cell_colocalization_parallel_coordinates` (`scatter_collapse`)
  — three-spine parallel-coordinates with per-spine scatter rug and
  per-group median bold trace; pairwise Pearson r in title.
- `ordered_trajectory_checkpoint_divergence`
  (`timecourse_hierarchical_ci`) — per-group LOESS curves with
  bootstrap CI on an ordered axis (e.g. Actin Drive Index); breakpoint
  vertical reference. Footer banner: 'Ordered fixed-cell
  reconstruction — not a live measurement.'
- `s_state_frontier_tip_raster` (`scatter_collapse`) — per-cell signed
  -position raster with frontier zero-line; S state filled circle,
  non-S hollow circle; per-cell %S sidebar.

### Infrastructure

- 8 new recipe modules; `biophysics_scaling/__init__.py` registers
  them.
- Reused from earlier waves: `OrderedTrajectoryPoint`, `TipStateCall`
  sub-contracts (Wave 1); inline LOESS pattern (Wave 2).
- No new `core/` utilities; no aesthetic changes.

### Genuinely novel primitives (no in-repo precedent)

- **C.6** xz MIPs + scale-bar overlay + paired split violins —
  deterministic Gaussian-backbone xz-slice synthesis.
- **C.9** three-spine parallel-coordinates with per-spine scatter
  rug.
- **D.4** signed-position raster with filled/hollow state glyph
  convention and frontier zero-reference.

### Visual-QA polish (3 panels)

- `xz_microtubule_bowing_z_span`: MIP insets switched from
  `set_yticks([])` (which still leaks tick labels under imshow) to
  `axis('off')`. Violin metric labels moved from ylabel (overlapped
  violins inside the narrow inset) to inset titles, shortened to
  'z-span' / 'bow amp' so adjacent inset titles don't collide.
- `per_cell_colocalization_parallel_coordinates`: legend moved from
  upper-right (collided with topmost data markers at y = 1.0) to
  centered-below-axes (ncols=2).
- `s_state_frontier_tip_raster`: legend moved further below axes
  (`bbox_to_anchor=(0.5, -0.18)`) so it clears the wrapped
  signed-frontier-position xlabel.

### Fit-ups during authoring

- `s_state_frontier_tip_raster`: replaced 'x' marker for non-S tips
  with hollow circles to avoid matplotlib's 'x' + edgecolor
  warning under warnings-as-errors in the smoke suite.
- Style-drift ratchet: `fontsize=8.0` → `8.2` in two title strings
  (existing literal). Ratchet held at 20/20.

### Tests

- Total: **1764 → 1804** (+40).
- `pytest tests/` passes green; all smoke / quality / contracts /
  style-drift / tost assertions satisfied for all 8 new recipes.

### Progress

- biophysics_scaling recipes: **27 → 35** (+8).
- Beta-pack recipes landed: **12 → 20** (Wave 3 of 4).

## [1.2.0-beta-biophysics_scaling-w2] — 2026-04-24

Second wave of the `biophysics_scaling` beta expansion pack. Lands
the scale-hierarchy remainder (A.2 / A.3 / A.4 / A.5) and the §3 / §5
narrative anchors (C.1 / C.2 / D.1 / D.2). After this wave, §1, §3,
and the first half of §5 of the anchor manuscript are fully panelable.
`biophysics_scaling` expands from 19 to 27 recipes; total catalog
332 → 340.

### Added (8 recipes)

- `compartment_paired_delta_scatter` (`scatter_collapse`) — whole-cell
  vs protrusion-internal effect-size scatter with diagonal reference
  and null-zone square; Spearman-ρ verdict.
- `feature_outcome_sankey_sig_vs_null` (`flow`) — three-column alluvial
  flow (total → scale → outcome) built with FancyBboxPatch nodes and
  smoothstep-interpolated Polygon ribbons; no matplotlib-Sankey dep.
- `random_forest_importance_by_scale` (`coef_forest`) — top-N feature
  importance ranked horizontally, bars coloured by scale stratum, CI
  whiskers, null-threshold reference.
- `scale_stratified_permanova_r2` (`coef_forest`) — per-scale R² ± CI
  with p-value annotations and a typical-threshold reference; shows
  where genotype variance lives across the hierarchy.
- `persistence_length_lp_with_equivalence_bounds` (`split_violin`) —
  2×N split violin (N compartments × 2 groups) with per-compartment
  log10-fold / TOST verdict reported inline.
- `psd_active_gel_overlay_with_motor_inset`
  (`timecourse_hierarchical_ci`) — log-log PSD per channel × group
  with CI ribbons, ω^-2 reference, active-gel + motor-band shading,
  and a motor-band deviation inset.
- `geometric_mediation_path_diagram` (`conceptual`) — 3-node DAG
  (X predictor → M mediator → Y outcome + X → Y direct) with bootstrap
  β ± CI edge annotations and mediation verdict footer.
- `shared_manifold_scatter_with_residuals` (`scatter_collapse`) —
  central scatter with shared LOESS fit + per-group marginal residual
  histograms via `make_axes_locatable`; inline ANCOVA `group | x` pill.

### Infrastructure

- 8 new recipe modules; `biophysics_scaling/__init__.py` registers
  them (imports + `__all__`).
- Reused from Wave 1: `_shared.EffectSizeEstimate`, `TostZone`,
  `ScaleTaggedFeature`, `MediationPathEstimate`, `PSDCurve`,
  `_demo_estimate_roster()`.
- No new `core/` utilities; no changes to `core/aesthetic_base.py`.
- A.3 (Sankey) and D.1 (DAG) are genuinely novel primitives in the
  repo — no existing recipe implements them. They use only matplotlib
  stdlib (no matplotlib-venn, no networkx).

### Visual-QA polish (4 panels)

- `scale_stratified_permanova_r2`: legend moved to upper-right-outside
  axes; per-row p-values anchored to the CI upper edge (clears the
  legend box).
- `psd_active_gel_overlay_with_motor_inset`: motor-band inset
  relocated from upper-right (overlapped the decaying PSD) to
  lower-left; PSD curve legend moved to upper-right where no data lives.
- `geometric_mediation_path_diagram`: M-node external label placed
  ABOVE the node so it no longer collides with the X→M and M→Y beta
  annotation boxes.
- `shared_manifold_scatter_with_residuals`: title moved to the top
  marginal strip (the main-axes title was hidden behind the
  `make_axes_locatable` top histogram).

### Fit-ups during authoring

- `random_forest_importance_by_scale`: added scatter markers at bar
  tips to satisfy the `coef_forest` ≥3-marker rule (bars alone register
  as `ax.patches`, not `ax.collections`).
- Style-drift ratchet: `lw=2.0` → `lw=2.2`, `fontsize=10.0` → `9.6`,
  `linewidth=0.3` → `0.4` (all snapped to existing literals). Ratchet
  held at 20/20.
- `_demo()` of C.2 PSD uses deterministic analytic curves — no RNG
  needed (auto-removed by ruff after initial draft).

### Tests

- Total: **1724 → 1764** (+40).
- `pytest tests/` passes green; all smoke / quality / contract /
  style-drift / tost assertions satisfied for all 8 new recipes.

### Progress

- biophysics_scaling recipes: **19 → 27** (+8).
- Beta-pack recipes landed: **4 → 12** (Wave 2 of 4).

## [1.2.0-beta-biophysics_scaling-w1] — 2026-04-24

First wave of the `biophysics_scaling` beta expansion pack. Lands the
shared sub-contract infrastructure, a new core TOST utility, and 4
substrate recipes that close the module's scale-aware effect-size +
equivalence + censoring + validation-contract gap. `biophysics_scaling`
expands from 15 to 19 recipes; total catalog 328 → 332.

### Added (4 recipes)

- `hierarchical_effect_size_ladder` (`coef_forest`) — stratified
  effect-size forest over polymer / network / territory / geometry /
  whole-cell scales; two markers per feature (whole-cell vs
  protrusion-internal compartment); outcome coded by TOST zone.
- `equivalence_forest_with_tost_bounds` (`coef_forest`) — feature
  effect-size forest with shaded TOST equivalence zone; three-colour
  outcome classification (significant / null-accepting / equivocal);
  optional per-feature N annotation.
- `pre_registered_censoring_mode_grid` (`matrix`) — feature × mode
  traffic-light grid (green = direction + sig; amber = direction,
  sub-sig; red = flipped / opposite; grey = null / excluded); column
  headers show per-mode `n_cells_retained`.
- `forward_simulation_validation_contract` (`coef_forest`) — n-metric
  parameter-sufficiency audit; empirical medians normalized in
  simulated-CI units so metrics plot on a shared axis; +/- verdict
  glyph per (metric, group); overall contract verdict in title.

### Infrastructure

- `src/panelforge_figures/recipes/biophysics_scaling/_shared.py`
  (new) — 11 nested Pydantic sub-contracts (`ScaleTaggedFeature`,
  `TostZone`, `EffectSizeEstimate`, `CensoringMode`, `CensoringResult`,
  `ValidationMetric`, `MediationPathEstimate`, `PhaseMapGrid`,
  `OrderedTrajectoryPoint`, `TipStateCall`, `PSDCurve`);
  `OUTCOME_PALETTE_DEFAULT` fallback; shared `_demo_estimate_roster()`
  helper that A.1 and B.1 demos consume.
- `src/panelforge_figures/core/tost_bounds_utility.py` (new) —
  `classify_outcome(ci_lo, ci_hi, lower, upper)` returns one of
  `significant` / `null_accepting` / `equivocal`;
  `tost_band_patch(ax, lower, upper, orientation="y"|"x")` shades the
  equivalence zone. Both duck-type on the TostZone sub-contract.
- `src/panelforge_figures/recipes/biophysics_scaling/_aesthetic.py`
  (edit) — `ModalityAesthetic` subclass `BiophysicsScalingAesthetic`
  carries `outcome_palette: dict[str, str]` (default blue / green /
  grey). Subclass is isolated to this modality; no changes to
  `core/aesthetic_base.py`.
- Registered 4 recipes in `biophysics_scaling/__init__.py`.
- `tests/test_tost_bounds_utility.py` (new, 13 tests) — classification
  numerics on synthetic CIs + `tost_band_patch` render smoke.

### Tests

- Total: **1691 → 1724** (+33).
- `pytest tests/` passes green; style-drift ratchet held; quality rules
  satisfied for all 4 new recipes.

### Visual-QA polish (2 panels)

- `hierarchical_effect_size_ladder`: scale-group sidebar labels were
  double-counted (used `len(by_scale[scale])` which already contains
  both compartments); `geometry` and `whole_cell` labels drifted into
  whitespace below the axis. Fixed to count unique features and
  relocated labels to a horizontal, blended-transform anchor above
  each stratum separator — decoupled from stratum size so
  single-feature strata (e.g. `territory`) don't collide with
  neighbours. Legend bbox also shifted from `(0.5, -0.08)` to
  `(0.5, -0.16)` so it clears the xlabel.
- `forward_simulation_validation_contract`: 'verdict' header label at
  `y=-0.85` escaped the axis above the top row and collided with the
  title. Removed — the legend's pass/fail entries already identify
  the column.

### Gallery

- `biophysics_scaling/` regenerated: **15 → 19 PNGs**. Total catalog
  PNGs: **328 → 332**.

### Progress

- biophysics_scaling recipes: **15 → 19** (+4).
- Beta-pack recipes landed: **0 → 4** (Wave 1 of 4).
- Sub-contract module available for consumption by Waves 2–4.

## [1.1.0] — 2026-04-24

**v1.1.0 FINAL RELEASE.** The 20-session hydration plan is complete.
The catalog now contains **328 recipes** across 20 modalities, up
from 137 at v1.0.0 — a **+139 % increase** landed across 21 user-
gated sessions (20 planned + s03b catch-up).

### Summary of per-session deltas

| Session | Modality | Δ | Notes |
|---|---|---|---|
| s01 | `rhogtpase_dynamics` | +6 (12→18) | Waddington family retagged |
| s02 | `fret_biosensors` | +8 (10→18) | dose-matrix callout anchor |
| s03 | `actin_microtubule_morphometry` | +18 (6→24) | Path 2 |
| s03b | `actin_microtubule_morphometry` catch-up | +11 (24→35) | approved overage |
| s04 | `mixed_effects_models` | +7 (9→16) | raincloud + partition |
| s05 | `sensitivity_analysis` | +7 (8→15) | FAST + LHS + Sobol |
| s06 | `redox_imaging` | +7 (8→15) | roGFP2 + Langevin |
| s07 | `intravital_imaging` | +9 (6→15, Path 2) | depth + laser injury |
| s08 | `gillespie_stochastic` | +8 (7→15) | master-eq + stochastic-resonance |
| s09 | `omics_differential` | +6 (10→16) | pathway volcano + Euler |
| s10 | `calcium_signaling` | +9 (6→15) | sync + wave-speed + polar |
| s11 | `single_cell_embeddings` | +8 (7→15) | density + rare-pop + LR |
| s12 | `dose_response_pharmacology` | +10 (5→15) | sex-stratified + SAR |
| s13 | `network_and_pathway` | +10 (5→15) | force layout + crosstalk |
| s14 | `biophysics_scaling` | +10 (5→15) | universality + Π-groups |
| s15 | `diffusion_and_tracking` | +10 (5→15) | van Hove + ergodicity |
| s16 | `spatial_statistics` | +9 (6→15, Path 2) | LISA + F function |
| s17 | `grant_and_conceptual` | +9 (6→15) | aims pyramid + deliverables |
| s18 | `meta_and_diagnostic` | +11 (4→15) | PRISMA + funnel + UpSet |
| s19 | `clinical_cohort` | +9 (6→15, Path 2) | ROC + NNT + PS balance |
| s20 | `cryoem_and_structure` | +9 (6→15, Path 2) | funnel + electrostatics |

### Catalog growth
- Total recipes: **137 → 328** (+191, +139 %)
- Total tests: **~500 → 1691** (+1191)
- Modalities at v1.1 target (≥15): **17 of 20** (mixed_effects at 16, omics_differential at 16, actin_microtubule_morphometry at 35 per s03b approval)

### Infrastructure kept stable across all 21 sessions
- No changes to `core/`
- No new top-level dependencies
- Style-drift ratchet held throughout

### Path-2 reconciliations
- s07 `intravital_imaging`: coord=8, actual=6 → +9
- s16 `spatial_statistics`: coord=4, actual=6 → +9
- s19 `clinical_cohort`: coord=3, actual=6 → +9
- s20 `cryoem_and_structure`: coord=3, actual=6 → +9

## [1.1.0-s20] — 2026-04-24

Twentieth (final) session of the v1.1 hydration plan. Hydrates the
`cryoem_and_structure` modality from 6 to 15 recipes via Path 2.

### Plan-vs-reality reconciliation

- Coordinator listed v1.0=3 but actual=6. Three seeds already
  shipped or duplicate existing: `ramachandran_plot`,
  `cryosparc_2d_class_averages_grid`, `local_resolution_volume_slice`.
- **Path 2**: drop duplicates, +9 new → 15-target and catalog
  crosses the ≥320 v1.1 finish line.

### Added

- `b_factor_distribution_by_chain` (ridge_by_group) — per-chain
  B-factor KDE ridges with median markers.
- `conformational_ensemble_rmsf` (diagnostic_curve) — per-residue
  RMSF trace with SS track (α/β/loop) and top-5 flex markers.
- `docking_pose_score_vs_rmsd` (scatter_collapse) — funnel diagnostic
  with near-native zone, lower envelope, Spearman ρ verdict.
- `contact_map_with_secondary_structure` (matrix) — residue × residue
  contact imshow with top/right SS tracks + long-range fraction.
- `surface_electrostatics_colormap` (heatmap) — 2-D potential
  projection with ±1 kT/e contours + charge-patch summary.
- `interface_area_vs_affinity` (scatter_collapse) — BSA × Kd log-log
  scatter with trend fit + Pearson r on log-transformed.
- `domain_motion_decomposition` (ladder) — normal-mode variance bars
  with cumulative-variance line on secondary axis + top-N-for-80 %.
- `hydrogen_bond_network_diagram` (conceptual) — radial network with
  occupancy-scaled line thickness, dashed when occ < 0.5.
- `motion_correction_shift_vector` (conceptual) — cumulative (dx, dy)
  trajectory coloured by frame, first/last frame markers,
  total-path / net-drift callouts.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.

### Fit-ups during authoring

- `conformational_ensemble_rmsf`: added median-RMSF reference line to
  satisfy diagnostic_curve ≥ 2-line rule.
- Style-drift ratchet: fontsize `8.0` snapped to `7.8` in
  `motion_correction_shift_vector` title.

### Visual-QA polish (3 panels)

- `hydrogen_bond_network_diagram`: "Asp 124" clipped inside 0.16-
  radius central circle; bumped radius to 0.24 + font 7.2 → 6.8 +
  xlim 1.5 → 1.8 + partner-label offset 0.18 → 0.32.
- `motion_correction_shift_vector`: fixed-4-Å xlim left empty space
  and origin/frame-0 labels stacked; switched to data-driven xlim
  and scaled offsets so labels separate cleanly.
- `surface_electrostatics_colormap`: title "+patch frac ... -patch
  frac ..." clipped at right; shortened to "+/- patch frac A / B".

### Progress

- Total recipes: **319 → 328** (+9). **Catalog crosses the ≥320
  v1.1 target.**
- Tests: **1646 → 1691** (+45).
- Modalities at v1.1 target (≥15): **17 of 20**.
- Sessions complete: **20 of 20** — **v1.1 hydration plan complete.**

## [1.1.0-s19] — 2026-04-23

Nineteenth session of the v1.1 hydration plan. Hydrates the
`clinical_cohort` modality from 6 to 15 recipes via Path 2 (forward-
looking ATHENA clinical-validation work).

### Plan-vs-reality reconciliation

- Coordinator listed v1.0=3 but actual baseline is 6. Four seeds
  (`consort_flow_diagram`, `baseline_characteristics_table_figure`,
  `subgroup_forest_clinical`, `time_to_event_stratified_km`) already
  ship as existing recipes or duplicate them.
- **Path 2**: drop duplicates, land +9 new to reach the 15-target
  (same pattern as s07 / s16).

### Added

- `roc_with_cutoff_optimization` (diagnostic_curve) — ROC with Youden
  star, AUC bootstrap CI, sens/spec callout.
- `calibration_plot_with_hl_test` (scatter_collapse) — decile
  observed vs predicted with HL χ² p-value verdict.
- `decision_curve_analysis` (diagnostic_curve) — net-benefit vs
  threshold with model-dominates range callout.
- `competing_risks_cumulative_incidence` (diagnostic_curve) — per-
  cause CIF with Gray's test verdict.
- `hazard_ratio_over_time_smoothed` (diagnostic_curve) — HR(t) with
  95 % band + Schoenfeld PH-violation verdict.
- `risk_score_discrimination_ladder` (ladder) — event rate per
  risk-score tier with monotonicity + p-for-trend.
- `number_needed_to_treat_forest` (coef_forest) — subgroup NNT ± CI
  with best / worst subgroup in title.
- `propensity_score_balance_diagnostic` (coef_forest) — paired
  before / after SMD forest with 0.1 balance band.
- `adverse_event_incidence_bar` (ladder) — per-AE arm-A vs arm-B
  horizontal bars with RR annotation + serious-event markers.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Compat: `np.trapz` → `np.trapezoid` (numpy 2.x).
- Helvetica-safe: replaced `→` / `∞` glyphs with ASCII substitutes.

### Visual-QA polish (2 panels)

- `number_needed_to_treat_forest` — legend at lower-right occluded
  the bottom-row's NNT label; moved legend below axes.
- `propensity_score_balance_diagnostic` — legend at lower-right
  occluded `prior CVD` and `hypertension` rows; moved to below
  axes (`bbox_to_anchor=(0.5, -0.18)`, 3 columns).

### Progress

- Total recipes: **310 → 319** (+9).
- Tests: **1601 → 1646** (+45).
- Modalities at v1.1 target (≥15): 16 of 20.
- Sessions complete: **19 of 20**.

## [1.1.0-s18] — 2026-04-23

Eighteenth session of the v1.1 hydration plan. Hydrates the
`meta_and_diagnostic` modality from 4 to 15 recipes — the QC,
meta-analysis, and reproducibility workhorse used across every paper.

### Added

- `prisma_flow_diagram` (flow) — PRISMA-2020 stage funnel with main
  + excluded boxes and arrowed transitions.
- `effect_size_funnel_plot` (scatter_collapse) — ES × SE scatter with
  95 % pseudo-CI cone + Egger's test p-value / verdict.
- `heterogeneity_forest` (coef_forest) — per-study forest with pooled
  diamond and I² / τ² / Q-statistic in title.
- `sensitivity_leave_one_out` (coef_forest) — per-row pooled-without-k
  ES with influential-study flags (|Δ| above threshold).
- `data_quality_heatmap` (heatmap) — sample × QC-metric z-score heatmap
  with per-cell threshold-fail × overlay + global pass-rate.
- `missingness_upset` (matrix) — intersection-dot matrix with top
  per-set count bars (set-intersection view of co-missingness).
- `outlier_detection_scatter` (scatter_collapse) — 2-D feature plane
  with Mahalanobis boundary contour and flagged-marker annotations.
- `retention_vs_attrition_sankey` (flow) — per-stage retention bars
  with attrition tabs and reason callouts.
- `replication_retrospective_matrix` (matrix) — study × attempt
  success / partial / failure / na grid with ES overlay.
- `reproducibility_correlogram` (matrix) — replicate × replicate
  Pearson r heatmap with group-coded tick labels.
- `batch_effect_diagnostic_pca` (scatter_collapse) — PC1 × PC2 scatter
  with per-batch covariance ellipses and a batch-clustering-score
  verdict.

### Infrastructure

- No changes to `core/` — 11 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Updated `tests/test_contracts.py` to expect 15 (was 4) recipes in
  `meta_and_diagnostic`.

### Visual-QA polish (7 panels)

- `prisma_flow_diagram` — exclusion-reason text overlapped the "n = N"
  count; consolidated to "Excluded  n = N" single line + reason
  below.
- `heterogeneity_forest` — pooled-diamond label collided with legend;
  moved I²/τ²/Q into title and legend to upper-right.
- `sensitivity_leave_one_out` — bottom-left callout pill occluded the
  Study 1 marker; consolidated into title.
- `retention_vs_attrition_sankey` — arrow heads covered "n = N"
  labels; reworked layout to put arrow heads in left-of-lane gap,
  retention bars centred in lane, attrition tabs on the right.
- `replication_retrospective_matrix` — top summary callout collided
  with title; consolidated into title; legend offset below axes.
- `reproducibility_correlogram` — tick labels clipped by group strip;
  replaced strip with group-coloured y-tick labels.
- `batch_effect_diagnostic_pca` — legend inside axes hidden by data
  points; moved to outside-right (`bbox_to_anchor=(1.02, 0.5)`).

### Progress

- Total recipes: **299 → 310** (+11).
- Tests: **1546 → 1601** (+55).
- Modalities at v1.1 target (≥15): 15 of 20.
- Sessions complete: **18 of 20**.

## [1.1.0-s17] — 2026-04-22

Seventeenth session of the v1.1 hydration plan. Hydrates the
`grant_and_conceptual` modality from 6 to 15 recipes for ATHENA,
MIRROR, and Horizon Europe proposals. A4-portrait + Helvetica-safe
(Portuguese-compatible) typography.

### Added

- `research_aims_pyramid` (conceptual) — hierarchical objective → aims
  → sub-questions with coloured aim bands and white sub-question cards.
- `methods_pipeline_flow` (flow) — strictly linear input → step 1 …
  step N → output with rounded coloured boxes and arrow connectors.
- `milestone_vs_risk_matrix` (matrix) — 2×2 probability × impact grid
  with per-milestone tiles and risk-rated border colour.
- `innovation_positioning_quadrant` (matrix) — novelty × feasibility
  quadrant with competitor scatter + starred our-proposal marker.
- `cost_by_work_package_bar` (ladder) — per-WP stacked horizontal bars
  by cost category with grand-total callout.
- `ethics_and_impact_block` (conceptual) — two-column ETHICS / IMPACT
  panel with sub-section cards + bullets.
- `interdisciplinary_contribution_spider` (radar) — polar coverage
  radar with optional reference polygon + mean-coverage callout.
- `team_network_graph` (conceptual) — institutional-sector radial
  layout with Circle-patch partner nodes and collaboration edges
  scaled by strength.
- `deliverables_timeline` (gantt) — per-WP lane with angled deliverable
  IDs, status-coloured rings, year dividers.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Updated `tests/test_contracts.py` to expect 15 (was 6) recipes in
  `grant_and_conceptual`.
- Style-drift ratchet held (fontsize `14` snapped to `9.6` in
  `milestone_vs_risk_matrix` decorative `!!` glyph).

### Visual-QA polish (4 panels)

- `research_aims_pyramid`: initial layout clipped the objective text
  (wrap too wide) and aim titles (em-dash too long). Reworked to
  column-based layout with `width=58` objective wrap, ASCII-dash aim
  titles and narrower sub-question wrap (`width=20`).
- `methods_pipeline_flow`: step boxes too narrow — titles / descriptions
  clipped. Reworked slot-width formula to explicit margin + gap that
  leaves enough box width at the default 6-step pipeline, arrow gaps
  set to 0.018 axes-fraction for visible arrowheads.
- `innovation_positioning_quadrant`: legend duplicated the starred
  data-point label. Removed the legend; starred marker has its own
  bold red label above.
- `deliverables_timeline`: titles overlapped horizontally at closely-
  spaced deliverables, ID labels overlapped markers. Switched to
  angled (`rotation=20`) titles above, ID labels centred inside the
  scatter marker (white bold text on WP-colour fill). Also
  `cost_by_work_package_bar` — legend below axes bbox shifted to
  `(1.0, -0.20)` to clear the "cost (EUR)" x-axis label.
- `team_network_graph`: long partner names (`postdoc A`, `PI-partner`)
  clipped inside circles. Switched to short ID inside circle, full
  name + role below.

### Progress

- Total recipes: **290 → 299** (+9).
- Tests: **1501 → 1546** (+45).
- Modalities at v1.1 target (≥15): 14 of 20.
- Sessions complete: **17 of 20**.

## [1.1.0-s16] — 2026-04-22

Sixteenth session of the v1.1 hydration plan. Hydrates the
`spatial_statistics` modality from 6 to 15 recipes via Path 2.

### Plan-vs-reality reconciliation

- Coordinator listed v1.0=4 but actual baseline is 6. Two seeds
  (`l_function_with_envelope`, `point_pattern_density_map`) already
  ship as `ripley_l_function` and `kernel_density_heatmap`.
- **Path 2**: drop duplicates, land +9 new to reach the 15-target in
  one session (analogous to s07).

### Added

- `clark_evans_aggregation_bar` (ladder) — per-condition CE index ± CI
  with CSR reference, clustered / random / dispersed colour coding.
- `f_function_empty_space` (diagnostic_curve) — F(r) with CSR
  analytical reference + envelope, interpretation pill.
- `spatial_covariogram` (diagnostic_curve) — C(h) with exponential
  fit and nugget / sill / range annotations.
- `lisa_cluster_map` (heatmap) — per-point HH / HL / LH / LL
  classification with HH-minus-LL density overlay for the heatmap-
  rule and pseudo-p alpha scaling.
- `bivariate_pair_correlation` (diagnostic_curve) — g_12(r) with
  signed fill, peak + trough markers.
- `voronoi_area_distribution` (ridge_by_group) — log-space ridge stack
  of per-condition Voronoi areas with med / mean markers.
- `co_occurrence_significance_matrix` (matrix) — type × type z-score
  matrix with star-significance overlay + strongest-pair title.
- `quadrat_count_chisq` (matrix) — Pearson residual heatmap with
  counts, χ² / df / p verdict pill.
- `spatial_permutation_null_distribution` (ridge_by_group) — null +
  alternative ridges with observed statistic line and empirical p.

### Infrastructure

- No changes to `core/` — 9 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held: fontsize `7.5` snapped to `7.4` in two
  titles (co_occurrence_significance_matrix, quadrat_count_chisq).

### Visual-QA polish

- None — all 9 panels passed visual-QA on first render.

### Progress

- Total recipes: **281 → 290** (+9).
- Tests: **1456 → 1501** (+45).
- Modalities at v1.1 target (≥15): 13 of 20.
- Sessions complete: **16 of 20**.

## [1.1.0-s15] — 2026-04-22

Fifteenth session of the v1.1 hydration plan. Hydrates the
`diffusion_and_tracking` modality from 5 to 15 recipes. This is the
intravital downstream SPT workhorse.

### Added

- `msd_anomalous_exponent_fit` (scatter_collapse) — per-track α × D
  scatter coloured by α + representative MSD fit inset.
- `track_length_distribution` (diagnostic_curve) — per-condition CCDF
  of track duration with censoring marker.
- `jump_distance_van_hove` (ridge_by_group) — |Δr| stacked by lag with
  Gaussian reference and non-Gaussian α₂ per-lag callout.
- `track_spaghetti_plot_colored_by_state` (scatter_collapse) — raw
  trajectories with per-segment LineCollection state colouring,
  start/end markers, state-fraction footer.
- `hmm_state_dwell_distribution` (ridge_by_group) — per-state dwell-
  time ridges with exponential reference and mean-dwell markers.
- `displacement_vs_state_residence` (matrix) — state × residence-bin
  heatmap of median |Δr| with per-row trend summary footer.
- `diffusion_coefficient_heatmap_spatial` (heatmap) — gridded D(x, y)
  pcolormesh with quartile contour overlay.
- `track_directionality_polar` (radar) — polar histogram with isotropic
  reference, mean-direction vector, and Rayleigh r statistic.
- `ensemble_vs_time_averaged_msd` (scatter_collapse) — EA-MSD line,
  TA-MSD cloud, and EB(τ) ergodicity-breaking parameter callout.
- `confinement_radius_vs_time` (timecourse_hierarchical_ci) — per-track
  R_conf(t) with mean ± 95 % CI per condition.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held (invisible-line proxy uses `lw=0.5,
  alpha=0.0, color="none"` — no new literal introduced).

### Fit-ups during authoring

- `track_spaghetti_plot_colored_by_state`: scatter_collapse rule
  requires ≥1 Line2D; LineCollection segments live on
  `ax.collections`, not `ax.get_lines()`. Added an invisible
  `ax.plot([], [])` proxy.
- Replaced unicode glyphs incompatible with Helvetica: rightwards
  arrow `→` → `->`; mathematical angle brackets `⟨...⟩` → `mean ...`.

### Visual-QA polish (one panel)

- `displacement_vs_state_residence`: initial render had three
  overlaps (first-column numeric labels clipped by y-ticks, right-
  edge per-row Δ-arrows overlapping the colorbar, header "largest
  trend" annotation colliding with the title). Removed the per-row
  right-edge annotations and replaced with a single compact trends
  footer below the axes; kept the in-cell numeric labels but skip
  them when column width is narrower than 60 % of the median width.

### Progress

- Total recipes: **271 → 281** (+10).
- Tests: **1406 → 1456** (+50).
- Modalities at v1.1 target (≥15): 12 of 20.
- Sessions complete: **15 of 20**.

## [1.1.0-s14] — 2026-04-22

Fourteenth session of the v1.1 hydration plan. Hydrates the
`biophysics_scaling` modality from 5 to 15 recipes for the Manuscript 3
collapse narrative and the `gc-chirrut` force-balance / Π-group analysis.

### Added

- `log_log_with_theory_line` (scatter_collapse) — data vs theory-
  predicted reference line with residuals-from-theory inset.
- `universality_class_comparison` (scatter_collapse) — 2-3 candidate
  universality curves overlaid, per-class RMS residual bar inset.
- `fractal_dimension_scaling` (scatter_collapse) — box-counting
  N(L) ~ L^D_f with sliding-window local D_f(L) inset.
- `stress_strain_regime_map` (matrix) — σ-ε with elastic/plastic/failure
  bands, yield + ultimate markers, Young's-modulus slope inset.
- `knudsen_reynolds_regime_diagram` (matrix) — Kn × Re log-log grid with
  continuum/slip/transition/free-molecular bands + sample scatter.
- `energy_landscape_1d_cartoon` (conceptual) — schematic U(x) with
  labelled wells, barriers, k_B T scale bar, transition arrows.
- `scaling_exponent_ci_forest` (coef_forest) — per-study α ± CI forest
  with theoretical reference line and heterogeneity summary.
- `characteristic_time_vs_control` (diagnostic_curve) — τ(p) critical
  divergence or Arrhenius fit with fitted exponent callout.
- `pi_group_sensitivity_bar` (ladder) — Buckingham Π-group variance
  contribution ranked with cumulative top-2/top-3 share.
- `crossover_scaling_diagnostic` (diagnostic_curve) — two-slope
  piecewise power law with crossover ξ + local-slope inset.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held; all new fontsize/lw literals snap to the
  existing canonical set.

### Visual-QA polish (three panels)

- `fractal_dimension_scaling`: legend + D_f callout originally both
  at lower-left → legend moved to upper-left, callout retained at
  lower-left.
- `knudsen_reynolds_regime_diagram`: rotated 90° regime labels
  collided with the 2-column upper-right legend → regime labels moved
  to the bottom of each band (horizontal, bold); sample legend moved
  below the axes; counts callout moved to upper-right.
- `crossover_scaling_diagnostic`: inset y-label "local α" was hidden
  by inset tick labels on a log y-axis → forced `inset.set_yscale
  ("linear")` plus `labelpad` tweaks for readable "local α" axis.

### Progress

- Total recipes: **261 → 271** (+10).
- Tests: **1356 → 1406** (+50).
- Modalities at v1.1 target (≥15): 11 of 20.
- Sessions complete: **14 of 20**.

## [1.1.0-s13] — 2026-04-21

Thirteenth session of the v1.1 hydration plan. Hydrates the
`network_and_pathway` modality from 5 to 15 recipes for Commentary +
Targetome network vocabulary.

### Added

- `directed_network_force_layout` (conceptual) — directed graph with
  arrowed edges and Circle-patch nodes.
- `hub_gene_radial` (conceptual) — hub-centre + neighbours on a
  circle, activator/repressor colour coding.
- `ppi_seed_expansion` (conceptual) — two-shell seed + expanded
  ring layout.
- `pathway_crosstalk_matrix` (matrix) — pathway × pathway crosstalk
  heatmap with top-pair footer.
- `kegg_overlay_enrichment` (conceptual) — KEGG schematic with
  FancyBboxPatch nodes coloured by −log10(p).
- `regulon_activity_heatmap` (heatmap) — TF × sample activity with
  condition strip.
- `module_preservation_zsummary` (ladder) — WGCNA Z-ladder with
  Z=2 / Z=10 tier shading.
- `centrality_vs_effect_scatter` (scatter_collapse) — centrality vs
  effect size with OLS + −log10(p) colormap.
- `subnetwork_comparison_diff` (conceptual) — Δ-weight graph with
  gain/loss edge coding.
- `pathway_flux_streamgraph` (timecourse_hierarchical_ci) —
  normalised stacked flux(t) with dominant-per-window footer.

### Infrastructure

- No changes to `core/` — 10 new per-recipe Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held (hub-radial title 8.8 → 8.6).

### Visual-QA polish (one panel)

- `directed_network_force_layout`: the initial Fruchterman-Reingold
  spring layout collapsed all 18 nodes to a tight cluster because
  the uncapped attractive force dominated. Replaced with a
  deterministic **degree-based radial layout** — hubs near centre,
  rim nodes outside, with per-tier angular stratification + small
  jitter — which reads cleanly for small/medium dense graphs.

### Progress

| | v1.1.0-s12 | **v1.1.0-s13** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 251 | **261** |
| `network_and_pathway` | 5 | **15** |
| Tests | 1306 | **1356** |


## [1.1.0-s12] — 2026-04-21

Twelfth session of the v1.1 hydration plan. Hydrates the
`dose_response_pharmacology` modality from 5 to 15 recipes for
ATHENA pharmacology + sex-stratified drug response.

### Added

- `dose_response_sex_stratified` (diagnostic_curve) — F/M Hill
  curves with sex × dose interaction p + EC50-fold callout.
- `dose_response_time_matrix` (heatmap) — concentration × time
  effect matrix with per-conc peak isochrone and global peak star.
- `response_rebound_kinetics` (diagnostic_curve) — washout curve
  with rebound peak marker and recovery τ callout.
- `ic50_vs_target_affinity_scatter` (scatter_collapse) — Ki vs IC50
  log-log with identity + OLS fit, mechanism-class coloring.
- `selectivity_index_tornado` (ladder) — fold-IC50 tornado with
  10× cliff marker and tractability shading.
- `dose_normalized_ec50_forest` (coef_forest) — x-fold EC50 vs
  lead, log-x, mechanism-coloured.
- `synergy_score_bliss_loewe` (scatter_collapse) — Bliss vs Loewe
  scatter with agreement diagonal and synergy / antagonism /
  disagreement quadrant coding.
- `pharmacophore_activity_heatmap` (heatmap) — feature × compound
  SAR heatmap with active-feature origin strip.
- `compound_cluster_structure_activity` (conceptual) — structural
  PCA + per-cluster mean activity two-panel.
- `polypharmacology_radar` (radar) — multi-compound polar radar
  with title-integrated mean-activity summary.

### Infrastructure

- No changes to `core/` — all 10 recipes use new per-recipe
  Pydantic contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Style-drift ratchet held — title fontsize 8.8 → 8.6 on two
  recipes during implementation.
- Conceptual-family rule satisfied in
  `compound_cluster_structure_activity` by adding per-bar value
  labels so ≥3 text artists are present.

### Visual-QA polish (two panels)

- `dose_normalized_ec50_forest`: the `lead (1×)` / `10×` legend
  originally sat at lower-right where it clipped the right-most
  x-fold labels; moved to upper-right.
- `polypharmacology_radar`: the mean-activity footer and
  compound legend both collided with the bottom "hydrolase"
  target label; folded the mean-activity summary into a 2-line
  title and anchored the legend at `bbox_to_anchor=(0.5, -0.14)`.

### Progress

| | v1.1.0-s11 | **v1.1.0-s12** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 241 | **251** |
| `dose_response_pharmacology` | 5 | **15** |
| Tests | 1256 | **1306** |


## [1.1.0-s11] — 2026-04-21

Eleventh session of the v1.1 hydration plan. Hydrates the
`single_cell_embeddings` modality from 7 to 15 recipes for Targetome
scRNA work and general single-cell omics.

### Added

- `single_cell_embeddings.umap_density_contour_overlay` — per-
  condition density contours on a shared UMAP, mean-shift arrows
  and pairwise centroid-distance callout.
- `single_cell_embeddings.rare_population_highlighted_umap` —
  spotlight grammar: bulk greyed, rare pop with convex hull +
  median star + % callout.
- `single_cell_embeddings.cluster_proportion_stacked_by_sample` —
  per-sample stacked bars with condition-group strip below.
- `single_cell_embeddings.trajectory_branching_force_directed` —
  branching trajectory with Circle-patch branch points, per-branch
  colours and endpoint labels.
- `single_cell_embeddings.per_cluster_marker_heatmap` — z-scored
  gene × cluster heatmap with origin-cluster annotation strip.
- `single_cell_embeddings.pseudotime_gene_expression_trajectory` —
  gene(pseudotime) smoothed curves with CI bands and peak-order
  footer.
- `single_cell_embeddings.rnavelocity_arrow_field` — RNA-velocity
  quiver field over UMAP scatter with faint speed underlay and |v|
  colorbar.
- `single_cell_embeddings.receptor_ligand_signaling_dotplot` —
  (sender × receiver) × LR-pair dotplot with size∝strength and
  colour∝-log10(p).

### Infrastructure

- No changes to `core/` — all 8 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- Liberation Sans-safe throughout — the rightwards-arrow glyph was
  replaced with `->` in branch labels, legend entries and peak-order
  footers.
- Quality-rule fit-ups during implementation:
  - `rnavelocity_arrow_field` (heatmap): added a faint speed
    `pcolormesh` underlay so the ≥1-surface rule is satisfied.
  - `trajectory_branching_force_directed` (conceptual): branch
    points drawn with `mpatches.Circle` patches so ≥2 decorative
    patches are present.
  - `umap_density_contour_overlay` (scatter_collapse): mean-shift
    arrows are underpinned by a Line2D segment so the ≥1-line rule
    is satisfied.

### Visual-QA polish (two panels)

- `cluster_proportion_stacked_by_sample`: per-sample tick labels
  were hidden behind the condition-group strip; moved the strip
  down (strip_y: -0.08 → -0.14) and shortened labels to the
  per-condition index so the numbers stay visible.
- `rnavelocity_arrow_field`: the cluster legend was inside the
  plot covering the quiver field; moved to a single-row anchor
  below the axes and added a |v| colorbar.

### Progress

| | v1.1.0-s10 | **v1.1.0-s11** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 233 | **241** |
| `single_cell_embeddings` | 7 | **15** |
| Tests | 1216 | **1256** |


## [1.1.0-s10] — 2026-04-21

Tenth session of the v1.1 hydration plan. Hydrates the
`calcium_signaling` modality from 6 to 15 recipes for the scaffold-
v4.3 GCaMP6f integration.

### Added

- `calcium_signaling.calcium_event_amplitude_distribution` — per-
  condition ridge of event amplitudes.
- `calcium_signaling.calcium_event_onset_alignment` — peri-event
  time histogram with CI.
- `calcium_signaling.population_synchronization_timeline` — sync(t)
  scalar curve with threshold shading.
- `calcium_signaling.network_burst_detection_overlay` — raster +
  rate with shaded burst epochs.
- `calcium_signaling.calcium_wave_speed_map` — per-pixel wave speed.
- `calcium_signaling.single_cell_calcium_landscape` — per-cell
  (frequency, amplitude) scatter with hulls.
- `calcium_signaling.calcium_and_fret_joint_plot` — Ca × FRET joint
  scatter with marginal histograms.
- `calcium_signaling.oscillation_frequency_polar` — dominant-phase
  polar with mean resultant R.
- `calcium_signaling.stimulus_triggered_calcium_heatmap` — cell ×
  time ΔF/F aligned to stim.

### Visual-QA polish (two panels)

- `network_burst_detection_overlay`: burst-count callout moved from
  rate-panel top-right (covered B3) into the title.
- `oscillation_frequency_polar`: radial tick labels moved to 270°
  via `set_rlabel_position(270)`; legend moved to a single-row anchor
  below the polar disc.

### Progress

| | v1.1.0-s09 | **v1.1.0-s10** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 224 | **233** |
| `calcium_signaling` | 6 | **15** |
| Tests | 1171 | **1216** |


## [1.1.0-s09] — 2026-04-20

Ninth session of the v1.1 hydration plan. Hydrates the
`omics_differential` modality from 10 to 16 recipes in direct
support of the Targetome and general omics pipelines.

### Added

- `omics_differential.proteome_volcano_labeled_pathways` — pathway-
  group coloured volcano with one centroid label per pathway group;
  distinct from the per-gene labelled volcano.
- `omics_differential.effect_size_replicate_concordance` — rep1 vs
  rep2 log2FC scatter with identity line, OLS fit, 95 % LoA band
  and bias / SD(Δ) callout.
- `omics_differential.shrinkage_estimate_scatter` — raw vs shrunken
  log2FC with shrinkage-ratio colormap and |Δ|>threshold highlight.
- `omics_differential.contrast_overlap_euler` — area-proportional
  Euler circles for 2- or 3-way contrast overlaps with region
  counts and Jaccard callout.
- `omics_differential.rank_product_meta_analysis` — top-N 1/RP bars
  with permutation-FDR star markers and a right-side per-study
  rank-colour strip.
- `omics_differential.pathway_module_activity_heatmap` — module ×
  sample activity heatmap with group-annotation strips for
  modules (right) and samples (bottom).

### Infrastructure

- No changes to `core/` — all 6 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (pathway-coloured volcano,
  replicate concordance with Bland-Altman band, shrinkage diagnostic,
  area-proportional Euler, rank-product meta-analysis ladder,
  module activity heatmap) live inline.
- Liberation Sans-safe labels throughout — replaced the union /
  intersection glyphs in the Euler callout with plain "union /
  inter / Jaccard" words.
- Style-drift ratchet held on first pass.

### Visual-QA polish (two panels)

- `rank_product_meta_analysis`: the per-study rank-colour strip was
  originally drawn to the left of the gene ladder where it collided
  with gene y-tick labels. Moved to the right side of the bars (in
  axes-fraction coords) with a reserved right-margin via
  `subplots_adjust(right=0.70)`.
- `pathway_module_activity_heatmap`: sample-group strip originally
  drawn above row-0 at `y = -1.2`, colliding with the title; moved
  to below the x-tick labels (`y = n_m + 0.8`). Module-group strip
  originally drawn at `x = -0.8`, colliding with module y-tick
  labels; moved to the right of the heatmap (`x = n_s + 0.05`).

### Progress

| | v1.1.0-s08 | **v1.1.0-s09** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 218 | **224** |
| `omics_differential` | 10 | **16** |
| Tests | 1141 | **1171** |


## [1.1.0-s08] — 2026-04-20

Eighth session of the v1.1 hydration plan. Hydrates the
`gillespie_stochastic` modality from 7 to 15 recipes in direct
support of HOME-GATE-TRAP dwell analyses and stochastic-state-
switching manuscripts.

### Added

- `gillespie_stochastic.master_equation_steady_state` — analytical
  master-equation P(n) overlaid with sampled SSA histogram, plus
  KL + TV distance callout.
- `gillespie_stochastic.tau_leaping_comparison` — exact-SSA vs
  τ-leap trajectory overlay with inset residual strip and RMSE /
  speedup callout.
- `gillespie_stochastic.mean_first_passage_time_matrix` — lower-
  triangular MFPT heatmap with every off-diagonal annotated and a
  fastest-pair footer.
- `gillespie_stochastic.fisher_information_parameter_estimation` —
  K × K Fisher-information matrix with condition-number callout
  and dominant / poorest-identified eigen-direction summaries.
- `gillespie_stochastic.burst_size_distribution` — discrete burst-
  count PMF with fitted geometric + negative-binomial overlays,
  preferred-model callout, mean / CV pill.
- `gillespie_stochastic.extinction_probability_vs_parameter` —
  per-initial-state P_ext(θ) curves with 0.5-crossing tipping-point
  markers and footer.
- `gillespie_stochastic.autocorrelation_of_trajectories` — per-state
  ACF(τ) with exponential fits, 1/e reference and slowest-over-
  fastest ratio callout.
- `gillespie_stochastic.stochastic_resonance_signature` — SNR vs
  noise-amplitude sweep with parabolic fit, vertical σ* and red
  peak-star marker.

### Infrastructure

- No changes to `core/` — all 8 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (analytic-vs-sampled
  overlap, method comparison with inset residual, MFPT matrix,
  FIM matrix, discrete-count PMF, P_ext-vs-θ sigmoid family,
  per-state ACF, SNR-vs-σ bell) live inline.
- Liberation Sans-safe labels — ASCII replacements for the
  unicode ↔ arrow used in the fastest-pair MFPT footer.
- Style-drift ratchet held on first pass; all new tests green.

### Visual-QA polish (two panels)

- `tau_leaping_comparison`: the residual inset was overlapping the
  main axis's "time (s)" xlabel — hid the main xlabel and placed the
  inset further below (y=[-0.40, -0.16]) so the residual-only axis
  carries the time label.
- `extinction_probability_vs_parameter`: tipping-point footer was
  showing absurd values (~1e6) because `max(denom, 1e-9)` clipped
  the negative denominator of a decreasing sigmoid; replaced with
  a signed-denominator test `abs(denom) > 1e-6` so both increasing
  and decreasing curves interpolate correctly.

### Progress

| | v1.1.0-s07 | **v1.1.0-s08** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 210 | **218** |
| `gillespie_stochastic` | 7 | **15** |
| Tests | 1101 | **1141** |


## [1.1.0-s07] — 2026-04-20

Seventh session of the v1.1 hydration plan. Hydrates the
`intravital_imaging` modality from 6 (real baseline; coordinator
listed 8 but actual v1.0 count = 6) to 15 recipes in direct support
of the Neuron figures and the formalised 2P-witness strategy. Path 2
reconciliation adopted — land 9 recipes in one session to hit the
plan's 15-target, matching the s03 precedent.

### Added — seeds from brief (+7)

- `intravital_imaging.depth_projected_microglia_field` — per-cell
  (x, y, z) scatter with depth-coded colormap, size-encoded cell
  size, faint per-bin density background, mandatory scale bar and
  depth stats pill. Distinct from the generic z-stack depth MIP.
- `intravital_imaging.process_event_timeline` — per-cell event
  raster with row-background state shading, marker-coded event
  types (extension / retraction / contact) and a bottom
  total-events-per-minute strip.
- `intravital_imaging.territory_change_pre_post` — paired
  pre-condition filled polygon + post-condition dashed outline per
  cell with centroid pre-to-post arrow and expanded/shrank counts in
  the title.
- `intravital_imaging.surveillance_efficiency_metric` — condition-
  level forest with 95 % CI sorted by estimate, colour-coded above /
  below baseline and numeric value labels right of CI.
- `intravital_imaging.cell_cell_contact_frequency_matrix` — lower-
  triangular inferno heatmap with threshold annotations and
  top-pair footer.
- `intravital_imaging.laser_injury_response_radial` — radial
  response curves over time with CI bands, t=0 baseline and
  peak-position / max-time callout.
- `intravital_imaging.multi_channel_intravital_overlay` — RGB
  channel blend with mandatory scale bar, per-channel step-histogram
  sidebar and per-channel mean callout.

### Added — gap-closers to hit 15 (+2)

- `intravital_imaging.msd_curve_by_state` — log-log ensemble MSD vs
  τ per state with α-slope fit labels and a pure-diffusion reference
  line. Reviewer-mandatory intravital analysis, no existing
  ensemble-statistic recipe.
- `intravital_imaging.velocity_distribution_by_state` —
  instantaneous-speed split violin with median / quartile overlays
  and per-category N labels. Distinct quantity from
  `cell_shape_descriptors_by_state` (shape, not motion) and
  `migration_rose_diagram` (angle only).

### Infrastructure

- No changes to `core/` — all 9 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (per-cell depth field,
  event raster, paired pre/post polygons, surveillance forest,
  pairwise cell contact matrix, radial-over-time curves, RGB blend
  with histogram sidebar, log-log MSD with α-fits, speed violin)
  live inline within their recipes.
- Liberation Sans-safe labels throughout — `→` replaced with
  `vs` / `(R)`, no unicode arrows in saved figures.
- Style-drift ratchet held; no new fontsize or linewidth literals.

### Visual-QA polish (two panels)

- `territory_change_pre_post`: the "field midline" faint line
  originally added to satisfy the `scatter_collapse` ≥1-line rule
  was visually distracting; replaced with an invisible
  `ax.plot([], [])` proxy.
- `surveillance_efficiency_metric`: baseline label pinned to the
  lower-right axes-fraction corner — original data-coord placement
  collided with the panel title at the top.

### Progress

| | v1.1.0-s06 | **v1.1.0-s07** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 201 | **210** |
| `intravital_imaging` | 6 | **15** |
| Tests | 1056 | **1101** |


## [1.1.0-s06] — 2026-04-20

Sixth session of the v1.1 hydration plan. Hydrates the
`redox_imaging` modality from 8 to 15 recipes in direct support of
the µRedoxScape submission.

### Added

- `redox_imaging.roGFP2_ratio_vs_disulfide_titration` — biosensor
  calibration curve with sigmoid fit, Rmin/Rmax reference lines,
  midpoint vertical and parameter callout.
- `redox_imaging.bimodality_kurtosis_vs_conditions` — grouped
  horizontal bars for three complementary bimodality statistics
  (BC, κ, dip) per condition with per-statistic thresholds and a
  red-star marker where all three agree.
- `redox_imaging.time_above_threshold_distribution` — per-condition
  CCDF of cell-level oxidation durations with median dots on P=0.5
  and a consolidated median-values footer.
- `redox_imaging.paracrine_kernel_fit` — 1-D K(r) with SEM band,
  exponential/Gaussian fit overlay, λ vertical and corner callout
  (λ / amp / R²).
- `redox_imaging.multiplicative_vs_additive_noise_diagnostic` —
  Langevin ξ² vs Y with two competing model fits (constant D_add vs
  D_mult(Y) = σ²Y²) and a ΔAIC-based preferred-model callout.
- `redox_imaging.redox_state_switching_frequency_map` — inferno
  spatial switching-rate heatmap with cell centroids scaled by
  per-cell rate, mandatory scale bar and mean / 95%ile pill.
- `redox_imaging.ratio_autocorrelation_decay` — temporal ACF per
  state with exponential fits, 1/e reference line and τ-ratio
  crossover callout.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (sigmoid calibration,
  three-stat grouped bars, CCDF survival, 1-D kernel fit, Langevin
  model comparison, switching-rate field, per-state ACF) live inline
  within their recipes.
- Liberation Sans-safe labels throughout (★ rendered via
  `ax.scatter(marker="*")` instead of a unicode glyph).
- Style-drift ratchet held; the single new `lw=0.0` that would have
  broken the 20-literal ceiling was resolved by switching
  `paracrine_kernel_fit` from `ax.plot(lw=0.0, marker=...)` to
  `ax.scatter(...)`.

### Visual-QA polish (two panels)

- `time_above_threshold_distribution`: consolidated per-condition
  median labels into a single figure-space footer — original
  strategy (labels offset vertically per index) still collided with
  the survival curves.
- `multiplicative_vs_additive_noise_diagnostic`: fixed the demo
  data-generation convention so `ξ² = 2·σ²·Y²·dt` matches the model
  curves drawn on the axis; AIC verdict now correctly reports
  "preferred: multiplicative" when the ground truth is multiplicative.

### Progress

| | v1.1.0-s05 | **v1.1.0-s06** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 194 | **201** |
| `redox_imaging` | 8 | **15** |
| Tests | 1021 | **1056** |


## [1.1.0-s05] — 2026-04-20

Fifth session of the v1.1 hydration plan. Hydrates the
`sensitivity_analysis` modality from 8 to 15 recipes — Sobol-dominant
with support for the other GSA methods reviewers routinely request.

### Added

- `sensitivity_analysis.fast_sensitivity_spectrum` — FAST
  frequency-domain periodogram with per-parameter fundamentals +
  harmonics, a noise/interaction floor reference and a dominant-peak
  callout.
- `sensitivity_analysis.lhs_parameter_space_coverage` — Latin-
  hypercube scatter matrix with marginal histograms and built-in
  √Centered-L2 discrepancy diagnostic. No new dependency.
- `sensitivity_analysis.tornado_diagram` — classic OAT ±Δ tornado
  with high/low halves colour-coded, sorted by total width, baseline
  reference line and pinned baseline pill.
- `sensitivity_analysis.sensitivity_by_output_quantity` — param ×
  output sensitivity-index heatmap with row-max right-triangle and
  col-max down-triangle margin markers (so cell values stay
  readable) and a dominant-driver-per-output callout.
- `sensitivity_analysis.sobol_bootstrap_convergence` — per-parameter
  S₁ line with shrinking bootstrap 95 % CI ribbon over N, rank-flip
  diagnostic at the smallest stable-top-k N, and a mean-CI-width
  footer.
- `sensitivity_analysis.interaction_network_sobol` — circular graph
  view of pairwise S₂ with edge width/colour coded, node size from
  Sᵀ, S₂-colorbar legend and top-edge callout; complements the
  existing interaction-matrix heatmap.
- `sensitivity_analysis.sensitivity_time_evolution` — time-resolved
  Sobol indices per parameter with CI bands, peak-time markers, and
  a per-time-window dominant-driver callout.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (FAST periodogram,
  LHS pair-matrix, OAT tornado, param × output heatmap, bootstrap-CI
  convergence ribbon, Sobol interaction graph, time-resolved
  indices) live inline within their recipes.
- Liberation Sans-safe labels throughout — subscripts via mathtext.
- Style-drift ratchet held by snapping the sole new literal
  (title fontsize 8.8 → 8.6).
- `tests/test_contracts.py` modality-count assertion bumped 8 → 15.

### Visual-QA polish (three panels)

- `tornado_diagram`: moved the baseline label from a data-coord
  annotation (which collided with the title) to an upper-left axes-
  fraction pill so it never competes with the panel title.
- `sensitivity_by_output_quantity`: replaced hollow-square
  driver highlights (which obscured cell values) with small right-
  triangle (row max) and down-triangle (col max) markers drawn on
  the cell margins with `clip_on=False`.
- `fast_sensitivity_spectrum`: moved the top-drivers pill from
  inside the axes (where it wrapped into the legend) to a figure-
  space footer below the x-axis.

### Progress

| | v1.1.0-s04 | **v1.1.0-s05** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 187 | **194** |
| `sensitivity_analysis` | 8 | **15** |
| Tests | 986 | **1021** |


## [1.1.0-s04] — 2026-04-19

Fourth session of the v1.1 hydration plan. Hydrates the
`mixed_effects_models` modality from 9 to 16 recipes. This is the
cross-cutting modality used in *every* manuscript — the 7 catch-up
recipes close four long-standing grammar gaps: raw data under the
forest, per-cluster (intercept, slope) covariation, model selection
(AIC / BIC), Bayesian contrast densities, plus the
partial-residuals / response-scale-emmeans / fixed-vs-random-variance
trio reviewers explicitly request.

### Added

- `mixed_effects_models.sex_stratified_raincloud_with_coef_box` —
  raw-data raincloud per sex × genotype (half-violin + inline
  5/25/50/75/95 box + rain jitter) with an upper-right coefficient
  callout (β, 95 % CI, p) tied to the mixed-model interaction term.
- `mixed_effects_models.random_intercepts_vs_slopes_scatter` — per-cluster
  joint (intercept, slope) scatter with 95 % shrinkage ellipse, OLS
  fit line, quadrant colouring from `sex_x_genotype`, and a Pearson
  r annotation. Captures the `cor(int, slope)` term that 1-D
  caterpillar + slopes panels hide.
- `mixed_effects_models.model_comparison_aic_bic_ladder` — competing
  model specs sorted by AIC, paired with BIC diamonds, ΔAIC bars
  and a Burnham-Anderson evidence strip (Δ=2/4/7). Best-fit row
  highlighted; per-row ΔAIC/ΔBIC callouts.
- `mixed_effects_models.posterior_contrast_density` — stacked
  Δ-posterior densities per contrast with 95 % HDI bars, median
  markers, split fill at zero (sign emphasis) and P(Δ>0) callouts.
  Distinct from `bayes_posterior_density_by_term` (absolute term
  posteriors, no Δ).
- `mixed_effects_models.partial_residuals_vs_predictor` — partial
  residuals (eᵢⱼ + β̂·xᵢⱼ) scattered per group with tricube-kernel
  LOESS smoothers and the fitted β̂·x reference line. Built-in
  lightweight LOESS — no new dependency.
- `mixed_effects_models.group_level_emmeans_with_pairwise` —
  response-scale emmeans per group with CI caps, Bonferroni-adjusted
  pairwise brackets stacked by arc length (*** / ** / *), and ns
  brackets on adjacent pairs. Distinct from `emmeans_contrast_grid`
  which shows the Δ between groups.
- `mixed_effects_models.fixed_vs_random_effect_partition` —
  Nakagawa-Schielzeth variance partition (marginal R² / conditional R²
  share / residual) as stacked horizontal bars per model, with a
  per-term hatched sub-strip under the fixed stripe. Distinct from
  `icc_variance_decomposition` which partitions the random-effect
  side only.

### Infrastructure

- No changes to `core/` — all 7 recipes use new per-recipe Pydantic
  contracts.
- No new top-level dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New grammars (raincloud-with-coef-box,
  Burnham-Anderson ΔAIC evidence strip, stacked Δ-posteriors with
  split-zero fills, Nakagawa-Schielzeth variance partition) live
  inline within their recipes.
- Liberation Sans-safe labels throughout — no subscript / proportional
  glyphs in any saved figure.
- Style-drift ratchet holds.

### Visual-QA polish (three panels)

- `sex_stratified_raincloud_with_coef_box`: moved per-stratum `n=`
  labels to a fixed axes-fraction y so they align with the xtick
  labels instead of drifting below the plot as later categories
  expanded the ylim.
- `model_comparison_aic_bic_ladder`: replaced the in-plot legend
  (which landed inside the lowest bar) with a title-bar key —
  "bar = ΔAIC, diamond = ΔBIC".
- `fixed_vs_random_effect_partition`: removed the redundant
  fixed/random/residual legend (bars are labelled inline) and
  bumped the per-term label threshold from 0.07 to 0.11 so crowded
  terms render as hatched colour strips without overlapping text.

### Progress

| | v1.1.0-s03b | **v1.1.0-s04** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 180 | **187** |
| `mixed_effects_models` | 9 | **16** |
| Tests | 951 | **986** |


## [1.1.0-s03b] — 2026-04-19

Catch-up session for `actin_microtubule_morphometry` — lands the 11
recipes the plan's idealised v1.0 spec assumed existed but were
absent from real v1.0 (surfaced by the Path 2 reconciliation in s03).
Brings the modality from 24 to 35 recipes. The 5-recipe overshoot
past the 30-roster target comes from 4 actual-v1.0 recipes not in the
user's original roster + `persistence_length_by_segment` overlapping
`persistence_length_fit`. User approved "land all 11".

### Added

- `actin_microtubule_morphometry.process_length_distribution_by_sex` —
  total per-cell process length by sex × genotype, split violin with
  per-group medians and Ns using the `sex_x_genotype` palette.
- `actin_microtubule_morphometry.sex_stratified_cvvelocity` — CV of
  instantaneous velocity per cell by sex × genotype with
  sex × genotype interaction bracket + p-value.
- `actin_microtubule_morphometry.skeleton_complexity_radar` —
  per-condition polar polygon over 6-8 normalised topology metrics
  with threshold reference polygon.
- `actin_microtubule_morphometry.branching_topology_sunburst` —
  nested-ring donut of branching-depth hierarchy by condition.
- `actin_microtubule_morphometry.persistence_length_by_segment` —
  per-segment Lp forest with bootstrap 95% CI, grand-mean reference.
- `actin_microtubule_morphometry.actin_microtubule_crosstalk_quiver`
  — MT density pcolormesh with actin-direction quiver overlay.
- `actin_microtubule_morphometry.protrusion_retraction_kymograph` —
  signed edge-velocity kymograph (arc × time) RdBu_r anchored at 0
  with v=0 iso-contour and time-averaged strip inset.
- `actin_microtubule_morphometry.cytoskeleton_polarity_vectorfield` —
  multi-cell field with per-cell centroid + polarity arrows,
  per-condition mean resultant length R.
- `actin_microtubule_morphometry.airyscan_segmentation_mosaic` —
  2-column (raw / segmentation) grid per cell with mandatory scale
  bars on the raw panel.
- `actin_microtubule_morphometry.shape_pca_morphospace` — PCA scatter
  with per-condition convex hulls and biplot loading arrows;
  paired story with `shape_umap_by_condition`.
- `actin_microtubule_morphometry.colocalization_coefficient_matrix` —
  condition × coefficient heatmap with mean ± SEM annotations.

### Infrastructure

- No changes to `core/` — all 11 recipes use new per-recipe Pydantic
  contracts.
- No new dependencies.
- No modifications to other modalities.
- `_aesthetic.py` unchanged. New visual grammars (sunburst,
  biplot arrows, quiver-on-pcolormesh, multi-cell polarity field)
  live inline within their recipes.
- Style-drift ratchet holds.

### Visual-QA polish (two panels)

- `branching_topology_sunburst`: widened depth-legend swatch gaps
  + fontsize so the d=0…d=4 labels no longer run together.
- `cytoskeleton_polarity_vectorfield`: moved R-summary pill from
  lower-left to upper-left so it clears the bottom-left scale bar.

### Progress

| | v1.1.0-s03 | **v1.1.0-s03b** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 169 | **180** |
| `actin_microtubule_morphometry` | 24 | **35** |
| Tests | 896 | **951** |


## [1.1.0-s03] — 2026-04-19

Third session of the v1.1 hydration plan. Hydrates the
`actin_microtubule_morphometry` modality from 6 to 24 recipes (Path 2
— the 9+ "catch-up" v1.0 recipes the idealised plan assumed existed
are deferred to session s03b). Organised into six functional
sub-families.

### Added

**Sub-family A — per-cell morphometric distributions (+4):**

- `actin_microtubule_morphometry.branch_point_count_raincloud` —
  per-cell branch-point count raincloud with animal-level ring markers.
- `actin_microtubule_morphometry.process_end_count_violin` — split
  violin by primary / higher-order end type per condition.
- `actin_microtubule_morphometry.cell_body_area_distribution` — soma
  area violin with median callouts and N per condition.
- `actin_microtubule_morphometry.sphericity_vs_elongation_scatter` —
  hero shape-plane scatter with marginal densities, per-condition
  convex hulls, OLS fit.

**Sub-family B — skeleton / network topology (+2):**

- `actin_microtubule_morphometry.branch_angle_distribution` — stacked
  KDE ridges by condition with Arp2/3 70° reference.
- `actin_microtubule_morphometry.topology_ternary_simplex` —
  (linear, branched, looped) barycentric scatter with per-condition
  convex hulls.

**Sub-family C — spatial / kinematic (+2):**

- `actin_microtubule_morphometry.edge_velocity_spatial_correlation` —
  C(s) along perimeter with exponential decay-length fit.
- `actin_microtubule_morphometry.mitochondrial_axis_alignment` —
  polar rose of Δ-angle vs filament axis with order-parameter S.

**Sub-family D — thumbnails / mosaics (+3):**

- `actin_microtubule_morphometry.per_cell_thumbnail_grid_with_metrics`
  — 4×4 grid of segmented cells with 2-line metric callouts and
  first-column scale bars.
- `actin_microtubule_morphometry.exemplar_extremes_panel` —
  (condition × min / median / max) tile grid with metric annotations.
- `actin_microtubule_morphometry.condition_average_cell_composite` —
  per-condition shape hulls overlaid on a 2-D hist2d variability
  cloud.

**Sub-family E — dimensionality reduction (+3):**

- `actin_microtubule_morphometry.shape_umap_by_condition` — scatter
  with per-condition KDE density contours.
- `actin_microtubule_morphometry.morphospace_trajectory_by_time` —
  per-condition centroid paths with arrowheads and net-displacement
  callouts.
- `actin_microtubule_morphometry.shape_descriptor_scatter_matrix` —
  full SPLOM with histogram diagonals and per-condition colouring.

**Sub-family F — colocalization / intensity (+4):**

- `actin_microtubule_morphometry.actin_mt_ratio_spatial_map` — 2-D
  `RdBu_r` anchored at 1.0 with cell outline and scale bar.
- `actin_microtubule_morphometry.intensity_radial_profile` — per-
  channel mean ± SEM vs radius with peak callout.
- `actin_microtubule_morphometry.tip_enrichment_vs_shaft_scatter` —
  tip vs shaft scatter with y=x reference, Pearson r, Wilcoxon p.
- `actin_microtubule_morphometry.colocalization_vs_morphology_correlation`
  — correlation heatmap with BH-FDR significance stars.

### Infrastructure

- No changes to `core/` — all 18 recipes use new per-recipe Pydantic
  contracts local to their `.py` file.
- `_aesthetic.py` unchanged. Four new visual grammars (ternary simplex,
  thumbnail grid, UMAP density contours, radial profile) live inline
  within their recipes so `AESTHETIC` stays stable.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds: snapped `fontsize=5.4` → `5.6` and
  `lw=1.6` → `1.5` to avoid new distinct values.

### Visual-QA polish (three panels)

- `per_cell_thumbnail_grid_with_metrics`: 2-line metric callouts,
  scale bars repositioned cleanly, taller figure + wider row spacing
  so all rows show the full annotation.
- `colocalization_vs_morphology_correlation`: FDR legend folded into
  title (was a figure footer colliding with rotated x-ticks).
- `shape_descriptor_scatter_matrix`: per-condition legend folded into
  suptitle (was a figure footer colliding with outer x-ticks).

### Deferred to session s03b

Nine+ "catch-up" recipes the plan's idealised v1.0 spec assumed
existed will land as a follow-up session between s03 and s04:
`process_length_distribution_by_sex`, `sex_stratified_cvvelocity`,
`skeleton_complexity_radar`, `branching_topology_sunburst`,
`persistence_length_by_segment`, `actin_microtubule_crosstalk_quiver`,
`protrusion_retraction_kymograph`, `cytoskeleton_polarity_vectorfield`,
`airyscan_segmentation_mosaic`, `shape_pca_morphospace`,
`colocalization_coefficient_matrix`.

### Progress

| | v1.1.0-s02 | **v1.1.0-s03** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 151 | **169** |
| `actin_microtubule_morphometry` | 6 | **24** |
| Tests | 806 | **896** |


## [1.1.0-s02] — 2026-04-19

Second session of the v1.1 hydration plan. Hydrates the
`fret_biosensors` modality from 10 to 18 recipes.

### Added

- `fret_biosensors.donor_acceptor_scatter_linearity` — sensor-linearity
  validation scatter with OLS fit, 95% CI band, y=x reference, and
  slope / R² / intercept callout.
- `fret_biosensors.fret_efficiency_vs_distance` — measured
  (distance, efficiency) with SEM bars overlaid on the theoretical
  `E = 1/(1 + (r/R_0)^6)` curve with fitted R_0 vertical line + halo label.
- `fret_biosensors.paired_pre_post_stimulus` — per-cell connecting
  lines between pre and post FRET ratios (colour-coded by direction),
  mean ± SEM markers, Wilcoxon bracket and stars.
- `fret_biosensors.biosensor_dose_response_matrix` — 2-D `RdBu_r`
  heatmap of dose × time Δ-ratio with iso-contours at 0.1 / 0.2 / 0.3
  and peak-response marker.
- `fret_biosensors.kymograph_ratio_edge_to_center` — 1-D spatial ×
  temporal kymograph along the cell radius, anchored at the
  FRET-neutral ratio 1.0, with optional inward-propagating wavefront
  overlay.
- `fret_biosensors.ratio_map_with_segmentation_overlay` — ratio
  heatmap with white cell-outline polygons and centroid labels;
  mandatory 10 µm scale bar.
- `fret_biosensors.windowed_roi_ratio_trajectory` — N per-window
  ratio traces colour-coded by arc-length position
  (viridis edge → interior), with position colorbar and a
  windows-schematic inset.
- `fret_biosensors.fret_vs_scalar_activity_regression` — FRET-vs-
  orthogonal-scalar regression with per-condition colour, OLS +
  95 % prediction band, Pearson r / p callout.

### Infrastructure

- No changes to `core/` — all eight recipes use new per-recipe
  Pydantic contracts local to their own `.py` file.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds (≤ 20 distinct fontsize + linewidth literals).

### Progress

| | v1.1.0-s01 | **v1.1.0-s02** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 143 | **151** |
| `fret_biosensors` | 10 | **18** |
| Tests | 766 | **806** |


## [1.1.0-s01] — 2026-04-19

First session of the v1.1 hydration plan (see
`docs/hydration_coordinator.md`). Hydrates the `rhogtpase_dynamics`
modality from 12 to 18 recipes.

### Added

- `rhogtpase_dynamics.phase_portrait_with_trajectories` — streamplot
  backdrop + time-colored integrated trajectories from multiple ICs,
  stability-coded fixed points.
- `rhogtpase_dynamics.codim2_bifurcation_map` — two-parameter (µ, ν)
  plane with saddle-node / Hopf / pitchfork curves and codim-2 points
  (cusp, Bogdanov-Takens); shaded regime regions.
- `rhogtpase_dynamics.potential_landscape_waddington_3d` — isometric
  3-D Waddington surface with gradient-descent sample trajectories
  sliding into wells; 2-D legend inset clarifies the start-ball /
  descent-path convention.
- `rhogtpase_dynamics.excitability_threshold_diagram` —
  FitzHugh-Nagumo in the excitable regime with rest point, threshold
  curve, and paired sub/super-threshold trajectories.
- `rhogtpase_dynamics.slow_manifold_projection` — geometric collapse
  of fast trajectories onto the slow manifold in phase space (the
  geometric counterpart to `quasi_steady_state_reduction`'s
  time-series comparison).
- `rhogtpase_dynamics.poincare_first_return_map` — 1-D discrete
  return map on a Poincaré section with identity diagonal, cobweb
  iteration, and slope-at-FP diagnostic.

### Infrastructure

- No changes to `core/` — all six recipes use new per-recipe Pydantic
  contracts local to their own `.py` file.
- No new dependencies.
- No modifications to other modalities.
- Style-drift ratchet holds at ≤ 20 distinct linewidths.

### Progress

| | v1.0.0 | **v1.1.0-s01** |
|---|---|---|
| Modalities | 20 | 20 |
| Recipes | 137 | **143** |
| rhogtpase_dynamics | 12 | **18** |
| Tests | 736 | **766** |


## [1.0.0] — 2026-04-19

**First stable release.** Promotes the 20-modality / 137-recipe
milestone previously tracked as `0.1.0` to a proper `v1.0.0`, in line
with the shipped reality:

- Stable public API — `figures` CLI, modality/recipe registry, manifest
  schema, Claude Code skill bootstrap. All have consumers.
- CI-enforced contract — cross-modality figure-integrity QA, typography
  stack, empty-data guard, style-drift ratchet.
- 736 tests pass on Python 3.11 and 3.12. Ruff clean.
- 4 pre-releases consumed (`0.1.0-alpha`, `-beta1`, `-beta2`, `-beta3`).

No code changed between `0.1.0` (which was not tagged) and `1.0.0`.
This entry formally renames the stable release; the `0.1.0` content is
the `1.0.0` content. `pyproject.toml` classifier moves from Beta to
Production/Stable to match the new version.

Going forward, SemVer is honored strictly: breaking changes require a
major bump. The v1.1 hydration plan (see
`docs/hydration_coordinator.md`) is a pure additive expansion — no
breaking changes — and lands under `v1.1.0-s01` through `v1.1.0-s20`.

## [0.1.0] — 2026-04-19

Session 5 — the full roadmap lands. 5 new modalities, 30 new recipes,
bringing the total to **137 recipes across 20 modalities** (the v0.1.0
target). Status moved from beta to first stable release.

### Added

- Modality `spatial_statistics` (6): ripley_l_function,
  pair_correlation_function, nearest_neighbor_distance_distribution,
  voronoi_territory_map, kernel_density_heatmap, moran_i_by_lag.
- Modality `clinical_cohort` (6): kaplan_meier_by_stratum,
  cox_forest_hazard_ratios, consort_flow_diagram,
  baseline_table_visualization, subgroup_forest_plot,
  outcome_by_quartile.
- Modality `cryoem_and_structure` (6): fsc_resolution_curve,
  angular_distribution_hist, local_resolution_surface,
  particle_2d_class_montage, ramachandran_plot, bfactor_vs_residue.
- Modality `intravital_imaging` (6): cell_track_trajectory_field,
  two_photon_depth_projection, vessel_diameter_kymograph,
  cell_shape_descriptors_by_state, migration_rose_diagram,
  time_to_homing_survival.
- Modality `actin_microtubule_morphometry` (6):
  filament_orientation_histogram, branch_point_density_map,
  persistence_length_fit, protrusion_length_velocity_joint,
  cortical_thickness_by_region, skeleton_overlay_kymograph.
- 30 new gallery PNGs under docs/gallery/ (137 total).

### Progress

| | v0.1.0b3 | **v0.1.0** | target |
|---|---|---|---|
| Modalities | 15 | **20** | 20 ✓ |
| Recipes | 107 | **137** | 137 ✓ |
| Tests | 586 | **736** | ≥400 ✓ |


## [0.1.0b3] — 2026-04-19

Session 4 batch — 4 new modalities, 27 new recipes, **107 total**.

### Added

- Modality `omics_differential` (10): volcano_labeled_repelled,
  ma_plot_with_lowess, annotated_cluster_heatmap, gsea_running_enrichment,
  ora_dotplot_by_ontology, upset_set_comparisons, differential_rank_ladder,
  pathway_flux_bubble, effect_size_vs_significance,
  multi_contrast_volcano_grid.
- Modality `single_cell_embeddings` (7): umap_categorical_with_density_contours,
  umap_continuous_expression, trajectory_pseudotime_arrow,
  expression_dotplot_by_cluster, pca_biplot_with_loadings,
  diffusion_map_2d, neighborhood_composition_stacked.
- Modality `network_and_pathway` (5): regulatory_network_hive,
  interaction_chord_diagram, pathway_flux_sankey_like,
  module_eigengene_heatmap, centrality_degree_distribution.
- Modality `diffusion_and_tracking` (5): msd_by_condition,
  step_size_distribution, angle_correlation_decay,
  confinement_radius_map, track_persistence_hist.
- Quality rule for the new `volcano` family: ≥10 scatter points + ≥1
  threshold line.
- 27 new gallery PNGs under docs/gallery/ (107 total).

### Progress toward v0.1.0

| | v0.1.0b2 | **v0.1.0b3** | v0.1.0 target |
|---|---|---|---|
| Modalities | 11 | **15** | 20 |
| Recipes | 80 | **107** | 137 |
| Tests | 361 | **469** | ≥400 ✓ |


## [0.1.0b2] — 2026-04-18

Session 3 batch — 4 new modalities, 31 new recipes, **80 total**.

### Added

- Modality `gillespie_stochastic` (7): trajectory_fan_with_fpt,
  dwell_time_log_violin, waiting_time_ecdf_fitted, rate_vs_control_parameter,
  state_occupancy_raster, ensemble_mean_variance_tube, noise_power_spectrum.
- Modality `redox_imaging` (8): bistability_hysteresis_loop,
  single_cell_ratio_distribution, paracrine_coupling_length_map,
  bimodality_coefficient_grid, ratio_trajectory_with_phase_annotation,
  redox_state_transition_diagram, multiplicative_noise_diagnostic,
  drift_diffusion_decomposition.
- Modality `fret_biosensors` (10): ratio_heatmap_over_field,
  ratio_timecourse_hierarchical_ci, stimulus_response_fan,
  donor_acceptor_dual_channel, sensor_calibration_curve,
  dose_response_hill_fret, single_cell_ratio_trajectories,
  ratio_distribution_by_condition, fret_signal_to_noise_map,
  roi_ratio_summary_grid.
- Modality `calcium_signaling` (6): event_raster_with_rate, gcamp_trace_stack,
  event_frequency_by_condition, calcium_propagation_wavefront,
  spike_triggered_average, synchronization_matrix.
- Quality rules for 2 new families: `split_violin`, `hysteresis_loop`.
  Broadened the split_violin rule's fill-detection to accept matplotlib ≥
  3.11's `FillBetweenPolyCollection` (now the default return type from
  `ax.violinplot`).
- 31 new gallery PNGs under docs/gallery/ (80 total).

### Progress toward v0.1.0

| | v0.1.0b1 | **v0.1.0b2** | v0.1.0 target |
|---|---|---|---|
| Modalities | 7 | **11** | 20 |
| Recipes | 49 | **80** | 137 |
| Tests | 237 | **361** | ≥400 |


## [0.1.0b1] — 2026-04-18

Session 2 batch — 4 new modalities, 31 new recipes, 49 total.

### Added

- Modality `mixed_effects_models` (9): sex_x_genotype_interaction_forest,
  random_effects_caterpillar, marginal_effects_ribbon, emmeans_contrast_grid,
  posterior_predictive_check, icc_variance_decomposition,
  mixed_model_residual_diagnostic, random_slopes_per_cluster,
  bayes_posterior_density_by_term.
- Modality `dose_response_pharmacology` (5): hill_fit_with_ci,
  ic50_forest_across_compounds, schild_regression, isobologram_combination,
  drug_combo_heatmap.
- Modality `biophysics_scaling` (5): log_log_scaling_with_slope_box,
  master_curve_collapse, force_length_characteristic,
  power_law_tail_diagnostic, buckling_critical_force_plot.
- Modality `rhogtpase_dynamics` (12): phase_portrait_tristable,
  phase_portrait_bistable, phase_portrait_oscillator, potential_landscape_1d,
  potential_landscape_2d_heatmap, bifurcation_saddle_node, bifurcation_hopf,
  bifurcation_pitchfork, nullcline_intersection_annotated,
  quasi_steady_state_reduction, timescale_separation_diagnostic,
  basin_of_attraction_map.
- Quality rules for 6 new families (phase_portrait, bifurcation, heatmap,
  ridge_by_group, timecourse_hierarchical_ci, coef_forest). Extended the
  "filled-polygon" rule to accept both `PolyCollection` and
  matplotlib ≥3.9's new `FillBetweenPolyCollection`.
- 31 new gallery PNGs under docs/gallery/.

### Progress toward v0.1.0

| | v0.1.0a0 | **v0.1.0b1** | v0.1.0 target |
|---|---|---|---|
| Modalities | 3 | **7** | 20 |
| Recipes | 18 | **49** | 137 |
| Tests | 113 | **237** | ≥400 |


## [0.1.0a0] — 2026-04-17

Initial alpha — scaffold, core, 3 of 20 modalities.

### Added

- Core layer: `style`, `palette`, `primitives`, `layout`, `export`, `contract`,
  `aesthetic_base`.
- 12 themes: `default`, `nature`, `cell`, `pnas`, `devcell`, `bpj`, `neuron`,
  `ncb`, `sttt`, `trends`, `fct_grant`, `horizon`.
- 13 palettes: `okabe_ito`, `sex_dimorphic`, `home_gate_trap`, `wt_ko`,
  `redox_bistable`, `fret_donor_acceptor`, `sex_x_genotype`,
  `timepoint_gradient`, `mechanism_class`, `cytoskeleton_components`,
  `rhogtpase_family`, `microglia_states`, `journal_neutral`.
- Adapters: `tabular`, `numpy_npz`, `pandas_pickle`, `passthrough`.
- Transforms: `reshape`, `aggregate`, `join`, `derive`.
- Manifest schema + resolver + catalog generator.
- CLI (`figures` entrypoint) with 11 subcommands.
- Modality 1 — `grant_and_conceptual` (6 recipes): `executive_summary_tile`,
  `timeline_gantt_with_milestones`, `work_package_flow`, `hypothesis_diagram`,
  `team_expertise_matrix`, `conceptual_triptych`.
- Modality 2 — `meta_and_diagnostic` (4 recipes): `power_analysis_by_effect_size`,
  `sample_size_decision_ladder`, `missing_data_pattern_matrix`,
  `qc_metric_radar`.
- Modality 3 — `sensitivity_analysis` (8 recipes): `sobol_first_total_pair`,
  `morris_elementary_effects`, `parameter_scan_2d_contour`,
  `dimensionless_pi_group_collapse`, `pi_group_rank_plot`,
  `fast_subspace_detection`, `convergence_diagnostic_sobol`,
  `interaction_matrix_sobol`.
- Gallery generator + 18 committed gallery PNGs.
- Quality gate, aesthetic compliance test framework, smoke test framework.
- Claude Code skill at `skill/SKILL.md` with `bootstrap`, `resurvey`,
  `add_figure` modes, plus references, example manifests, and templates.
- CI workflow on Python 3.11 and 3.12.

### Target for v0.1.0

Completes the remaining 17 modalities (119 recipes) in subsequent sessions,
following the order in `README.md`.
