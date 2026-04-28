# DISC1 manuscript companion pack tracker

**Version label:** `[1.4.0-beta-cytoskeletal_morphometry_companion]` (sub-tags `-w1` … `-w4`)
**Scope:** ~31 new recipes scattered across 5 existing modalities + 1 new `core/` shim, landed across 4 user-gated waves. Pack pattern inherited from `[1.3.0-beta-intravital_imaging]` (PRs #33–#38; tag `v1.3.0-beta-intravital_imaging`).
**Anchor manuscript:** `<project_root>` — DISC1-linked microglial cytoskeletal confinement (in-vivo intravital + fixed-cell Airyscan + forward simulation).
**Plan file:** `~/.claude/plans/shimmying-mapping-hammock.md`

## Why this pack

The just-shipped `intravital_imaging` pack covered the manuscript's **decision-layer / commitment-kinetics / biosensor / reviewer-proof** needs (42 recipes). Cross-referencing the manuscript's full figure inventory (28 main panels in F1–F6 + 26 supplementary panels in FS1–FS7) against the resulting **392-recipe catalog** identifies a remaining gap of:

- **11 genuinely-missing high-end primitives** — universal QA tools (PCA loadings, per-cell audit tables, hypothesis-exclusion tables, model-residual panels) plus DISC1-specific narrative pieces (territory contact-network overlay, zone-fraction alluvial Sankey, narrative cascade river).
- **17 near-match variants** — existing recipes (e.g. `colocalization_coefficient_matrix`, `airyscan_segmentation_mosaic`) that need new variants because the manuscript's framing is different (raincloud not matrix; triptych not mosaic; etc.). Per the repo's additive governance, these become **new recipes** rather than in-place extensions of the existing ones.

**Total: ~31 new recipes**, suitable for a 4-wave companion pack. Catalog grows 392 → ~423.

## Heavy-deps decision: zero new top-level deps

Inherits the Option D inline-shim discipline established by `intravital_imaging`. No `networkx`, `scikit-bio`, or other new heavy deps:

- F2A `territory_contact_network_overlay` — pure matplotlib (just plot nodes at coords + edges as lines from an adjacency-list passed in the contract; no graph algorithms needed for layout).
- F2B `zone_fraction_alluvial_sankey` — reuse the `flow` family layout primitives already used by `pathway_flux_streamgraph`.
- FS1A `pca_loadings_heatmap` — pure numpy SVD + `pcolormesh`.
- FS1C `permanova_null_distribution` — single new `core/permanova_null_utility.py` shim (~40 LOC, pure numpy) that replaces a `scikit-bio` dep; modest footprint matching `core/km_survival_utility.py`.
- All other recipes: numpy / scipy / matplotlib only.

## Modality-boundary distribution: scatter across 5 existing modalities

Per governance §9, no new modalities. The 31 recipes scatter as:

| Modality | Δ (this pack) | Pre-pack | After w4 |
|---|---|---|---|
| `meta_and_diagnostic` | +6 | 15 | **21** |
| `actin_microtubule_morphometry` | +14 | 35 | **49** |
| `biophysics_scaling` | +10 | 37 | **47** |
| `spatial_statistics` | +1 | 15 | **16** |
| `grant_and_conceptual` | +1 | 15 | **16** |
| `intravital_imaging` | +1 (extension) | 57 | **58** |
| Total catalog | **+31** | 392 | **423** |

## Summary

| Metric | Start | After W1 | After W2 | After W3 | After W4 |
|---|---|---|---|---|---|
| Pack recipes landed | 0 | 6 | 13 | 22 | **31 (final)** |
| Total catalog recipes | 392 | 398 | 405 | 414 | **423 (final)** |
| New `_shared.py` modules | 0 | 1 | 2 | 2 | **2 (final)** |
| New `core/` shims | 0 | 0 | 0 | 1 | **1 (final)** |

## Per-wave status

| Wave | Scope | Status | Branch | Merged tag | Notes |
|---|---|---|---|---|---|
| w1 | Universal QA + diagnostic primitives (+6): PCA loadings, per-cell audit, hypothesis exclusion, residual panels, RF confusion, parameterization lineage. All in `meta_and_diagnostic`. Pioneers `meta_and_diagnostic/_shared.py`. | **merged** | `beta-disc1-companion-w1` | — (squash-merged PR #39; commit `2267ba0`) | 3 commits, 2 visual-QA fit-ups (W1.5 cividis off-diagonal text colour threshold inverted; W1.6 title-vs-headers overlap), 5 sub-contracts pioneered, total tests 2056 → 2086; CI green |
| w2 | Cell territory + multiscale presentation (+7): F1A territory-zone overlay, F1B dual-scale lollipop, F1C PCA-silhouette, F1D triptych, F2A contact-network overlay, F2B zone-fraction Sankey, F2C colocalization raincloud. Pioneers `actin_microtubule_morphometry/_shared.py`. | **merged** | `beta-disc1-companion-w2` | — (squash-merged PR #40; commit `f918dfb`) | 3 commits, 4 visual-QA fit-ups (W2.1 sort-mutation bug, W2.2 ellipse-not-line family rule, W2.6 fontsize ratchet snap, W2.6 box-label truncation widened columns), 7 sub-contracts pioneered, total tests 2086 → 2121; CI green |
| w3 | Cytoskeleton geometry + statistics (+9): F2D angle rose, F2E Cleveland, F3B censoring waterfall, F4C confinement gauge, FS2C-D Kinhom, FS2E edge-gradient, FS2F cortex composite, FS4E-F mesh-density, FS5B z-span vs width. | **review** | `beta-disc1-companion-w3` | — (PR open) | 3 commits, 5 visual-QA fit-ups (W3.5 lw=1.6→1.4, W3.3+W3.4 lw=2.0→2.2, W3.3+W3.6 fontsize=8.0→8.2, W3.4 sentinel scatter for coef_forest family rule, W3.1 NN inset + legend repositioning), 8 sub-contracts added, total tests 2121 → 2166 |
| w4 | Narrative integration + final supplements (+9): F5C pseudotime strip, F5E narrative cascade, F6C split-mirror, FS1C PERMANOVA null + new `core/permanova_null_utility.py`, FS3D overlap-juxtaposition, FS5C force-budget, FS5D confinement-ratio, FS6E-F splay-taper-polarity, FS7B-D sensitivity sweeps. Closes pack. | pending | — | — | Depends on w3; closes pack |

Status legend:
- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed

## Wave 1 — universal QA + diagnostic primitives (+6) [merged]

**Why first.** All 6 recipes are biology-agnostic primitives that any future pack reuses. They form the substrate for the DISC1 manuscript's reviewer-proof supplementary panels (FS1A loadings, FS3A/FS5A audit, FS4A-C residuals, FS1B confusion) plus the methods-section parameterization lineage (F6A) and the rigorous-design exclusion table (F3C). No biology-specific contracts; pure substrate.

### Recipe roster (Wave 1)

| ID | Recipe | Family | Required fields | Precedent to mirror |
|---|---|---|---|---|
| W1.1 | `pca_loadings_heatmap` | `heatmap` | `loadings: ndarray`, `feature_names: list[str]`, `component_labels: list[str]` | new — variables × PC `pcolormesh` on diverging cmap |
| W1.2 | `per_cell_audit_table_with_qa_flags` | `matrix` | `rows: list[CellAuditRow]` (per-cell metric + R² + flag status) | extends pattern from `cohort_baseline_balance_table_matrix` (intravital_imaging Wave 4) |
| W1.3 | `alternative_hypothesis_exclusion_table` | `matrix` | `hypotheses: list[ExclusionRow]` (alternative + criterion + verdict) | new — visual table with ✓/✗ marks; reuses `tost_bounds_utility.classify_outcome` framing |
| W1.4 | `competing_model_residual_panels` | `scatter_collapse` | `models: list[CompetingModelFit]` (predicted, observed, residuals per model) | new — multi-panel residual structure for ≥2 model fits |
| W1.5 | `random_forest_confusion_loocv` | `matrix` | `confusion_matrix: ndarray`, `class_labels: list[str]`, `cv_metadata` | new — LOOCV confusion matrix with misclassification rates |
| W1.6 | `model_parameterization_lineage_panel` | `conceptual` | `lineage: list[ParameterLineageEdge]` (modeled-input → measured-readout) | new — methods-section staple; pure matplotlib arrows + boxes |

### Family-rule satisfaction checklist

- **W1.1** (`heatmap` ≥1 imshow / pcolormesh) — satisfied by the loadings `pcolormesh`.
- **W1.2, W1.3, W1.5** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by per-row colour `pcolormesh` (W1.2 + W1.5) or annotated cell patches (W1.3).
- **W1.4** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by per-model residual scatter + zero-residual reference line.
- **W1.6** (`conceptual` — no strict family quality rule) — pure matplotlib annotation.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/recipes/meta_and_diagnostic/_shared.py` | **NEW** | 5 nested Pydantic sub-contracts: `CellAuditRow`, `ExclusionRow`, `CompetingModelFit`, `ParameterLineageEdge`, `LoadingsBundle`. Pioneers `_shared.py` for this modality. |
| 6 new recipe modules under `recipes/meta_and_diagnostic/` | **NEW** | One per recipe |
| `recipes/meta_and_diagnostic/__init__.py` | edit | Register 6 new recipes (imports + `__all__`); bumps total to 21 |
| `CHANGELOG.md` | edit | "In planning" pointer rolled to cytoskeletal_morphometry_companion |
| `docs/cytoskeletal_morphometry_companion_pack_tracker.md` | **NEW** | This file |

No new top-level deps; no changes to other modalities.

### `_demo()` seed convention (Wave 1)

All Wave 1 demos use seeded RNG and the registered `meta_and_diagnostic` palette (already in `_aesthetic.py`). Demo data is biology-agnostic so the recipes can be reused outside the DISC1 pack:

- W1.1: 12 features × 5 PCs; explained-variance bars under heatmap; mock features `feature_01..12`.
- W1.2: 24 cells × 6 audit columns (Lp_actin, Lp_mt, fit_R², n_segments, censoring_flag, qa_pass); 4 cells flagged.
- W1.3: 5 alternative hypotheses × 3 criteria; one hypothesis ruled out on all three, two equivocal.
- W1.4: 2 competing models (`width_only` vs `interaction`) × 80 observations; interaction model has tighter residuals.
- W1.5: 3-class confusion (WT / LI / mixed) with 5 % off-diagonal LOOCV misclassification.
- W1.6: 4 modeled inputs (width, alpha, segment_length, persistence_length) lineage-mapped to 4 measurements.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| W1.6 `conceptual` family has no strict quality rule, so it can be visually inconsistent across recipes | Use existing `methods_pipeline_flow` (grant_and_conceptual) as reference for box / arrow style. |
| W1.3 hypothesis-exclusion ✓/✗ glyphs need to be Helvetica-safe | Use ASCII `Y` / `N` or coloured circles instead of unicode checkmarks. |
| W1.2 per-cell audit can have many rows in real data | Default-paginate at 30 rows; demo uses 24. |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 2056 + Wave 1 recipe smoke / quality / contracts (~12 new) = ~2068.
2. `pytest tests/test_recipes_smoke.py -k meta_and_diagnostic` — 21 demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k meta_and_diagnostic` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet at 20/20.
5. Gallery regenerate `meta_and_diagnostic/` — 21 PNGs.
6. Eyeball each new panel; estimate **3 visual-QA fit-ups** (small wave; conventions already established).

## Wave 2 — cell territory + multiscale presentation (+7) [merged]

**Why next.** Wave 1 shipped the universal QA primitives. Wave 2
delivers the F1 + F2 cluster of cell-level territory and scale-
decomposition figures, which open the manuscript narrative.
**Pioneers `actin_microtubule_morphometry/_shared.py`** with 6
nested sub-contracts (territory maps, contact-patch networks,
colocalization coefficients, protrusion outlines, multi-scale
significance rows, Airyscan triptych bundles). After this wave,
two of the three modalities affected by the pack carry their own
`_shared.py` (the third — `biophysics_scaling` — already had one
from its earlier pack).

### Recipe roster (Wave 2)

| ID | Recipe | Modality | Family | Required fields | Panel |
|---|---|---|---|---|---|
| W2.1 | `dual_scale_significance_lollipop` | biophysics_scaling | `coef_forest` | `rows: list[MultiScaleSignificanceRow]` (feature × scale × −log₁₀(p) × tier-band) | F1B |
| W2.2 | `pca_silhouette_glyph_morphospace` | actin_microtubule_morphometry | `scatter_collapse` | `cells: list[CellOutlineWithPCCoord]` (cell_id, pc_coord, condition, outline_xy) + PERMANOVA stats | F1C |
| W2.3 | `airyscan_to_zone_territory_triptych` | actin_microtubule_morphometry | `matrix` | `bundles: list[AiryscanTriptychBundle]` (raw + skeleton overlay + zone-territory map per cell) | F1D |
| W2.4 | `territory_zone_overlay_intravital` | intravital_imaging | `heatmap` | `field: MultiChannelField` + `zone_map: ZoneTerritoryMap` | F1A |
| W2.5 | `territory_contact_network_overlay` | actin_microtubule_morphometry | `heatmap` | `cells: list[CellWithContactNetwork]` (territory map + contact-patch network + ROI polygon) | F2A |
| W2.6 | `zone_fraction_alluvial_sankey` | actin_microtubule_morphometry | `flow` | `medians_by_condition: dict[str, dict[zone, fraction]]` | F2B |
| W2.7 | `colocalization_raincloud_per_metric` | actin_microtubule_morphometry | `split_violin` | `coefficients: list[ColocalizationCoefficients]` per cell × condition | F2C |

### Family-rule satisfaction checklist

- **W2.1** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by per-feature lollipop markers (≥3 metrics × ≥2 scales = ≥6 markers) + dashed reference line at −log₁₀(0.05) significance threshold.
- **W2.2** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by per-cell PC scatter + per-condition confidence-ellipse outlines as the "fit lines"; cell-outline silhouettes are scatter-marker glyphs (custom paths via `matplotlib.path.Path`).
- **W2.3** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by 3 inset `imshow` panels per cell × ≥2 cells; sentinel imshow on parent ax for layout safety.
- **W2.4, W2.5** (`heatmap` ≥1 imshow / pcolormesh) — W2.4 satisfied by multi-channel composite `imshow` with zone outlines overlaid; W2.5 by territory-map `imshow` with network drawn as overlay (lines + scatter).
- **W2.6** (`flow` family) — Sankey-style ribbons drawn via filled `mpatches.PathPatch` between left and right composition columns; mirrors `pathway_flux_streamgraph` precedent.
- **W2.7** (`split_violin` ≥2 violin bodies + ≥1 median marker) — satisfied by per-metric split violins (control left half / DISC1 right half) × 3 metrics; median ring markers per side.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/recipes/actin_microtubule_morphometry/_shared.py` | **NEW** | 6 nested Pydantic sub-contracts: `ZoneTerritoryMap`, `ContactPatchNetwork`, `ColocalizationCoefficients`, `CellOutlineWithPCCoord`, `MultiScaleSignificanceRow`, `AiryscanTriptychBundle` (+ `CellWithContactNetwork` and `MultiChannelField` composites). Pioneers `_shared.py` for this modality. |
| `recipes/actin_microtubule_morphometry/__init__.py` | edit | Register 5 new recipes (W2.2, W2.3, W2.5, W2.6, W2.7); modality total 35 → 40 |
| `recipes/biophysics_scaling/__init__.py` | edit | Register 1 new recipe (W2.1); modality total 37 → 38. **Extends existing `_shared.py`** with `MultiScaleSignificanceRow` if not already present (verify in Phase 1; otherwise pioneer in this modality's _shared.py). Re-export so both modalities can use it. |
| `recipes/intravital_imaging/__init__.py` | edit | Register 1 new recipe (W2.4); modality total 57 → 58. Reuses existing `_shared.py`. |
| `tests/test_contracts.py` | edit | Bump per-modality assertions: `actin_microtubule_morphometry` 35 → 40; `biophysics_scaling` 37 → 38; `intravital_imaging` 57 → 58. |

No new top-level deps; no new `core/` shims (the heavy-deps decision §"Heavy-deps decision" remains zero new deps for Wave 2). The contact-network overlay (W2.5) draws nodes + edges as plain `ax.scatter` + `ax.plot` — no `networkx` dependency.

### `_demo()` seed convention (Wave 2)

All Wave 2 demos use seeded RNG (`np.random.default_rng(50X)`) and the registered modality palettes. Demos use the manuscript's WT vs LI condition labels but with biology-agnostic synthetic data so future packs can reuse the recipes:

- **W2.1**: 12 metrics × 2 scales (whole-cell, protrusion-internal) × 3 tier-bands (polymer / network / territory). Network metrics sharpen at protrusion-internal scale; polymer metrics stay below significance at both scales — visible row-band pattern.
- **W2.2**: 18 cells × 2 conditions; cell-outline silhouettes parameterised as ellipses with per-cell aspect-ratio noise; PERMANOVA R² = 0.32, p = 0.001 in caption.
- **W2.3**: 2 representative cells (WT_2 and LI_12 per manuscript), each with 3-panel triptych (256 × 256 raw + skeleton overlay + 4-zone territory map: contact / desert / intermediate / far).
- **W2.4**: 1 multi-channel field (RFP / YFP / DAPI = 3 channels × 256 × 256) with 4-zone territory overlay; cell ROIs labelled.
- **W2.5**: 2 cells (WT vs LI); WT shows fragmented sparse contact patches (many small components); LI shows denser, more-connected network.
- **W2.6**: 4 zones (contact / intermediate / desert / far) × 2 conditions; control distribution shifted toward desert + intermediate; LI shifted toward contact + intermediate.
- **W2.7**: 3 metrics (Manders M1, Pearson r, Spearman ρ) × 2 conditions × 16 cells; LI distributions shifted ~0.18 above control on every metric.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| W2.2 cell-outline silhouette glyphs require custom `Path` per scatter point — easy to introduce per-cell scaling artefacts | Use a normalised glyph size (in axes-fraction) so cells appear at consistent visual scale regardless of outline size; precedent in seaborn's `mpl.markers.MarkerStyle` |
| W2.3 triptych layout (3 panels × 2 cells = 6 inset axes) — risk of cropped axes per Wave 1 W1.6 / intravital W4 sentinel-pattern issues | Apply the established sentinel pattern (parent `imshow` with off-axis extent + `set_xlim/ylim(0, 1)` + `set_facecolor("none")`) so parent ax stays transparent |
| W2.4 multi-channel composite + zone overlay — risk of over-saturation when channels are blended | Use the existing `multi_channel_intravital_overlay` precedent for RGB blending; zone outlines as white contour lines on top |
| W2.5 contact-network drawing without networkx — manual node/edge plotting can crowd visually | Cap demo network at ≤30 nodes per cell; use `linewidth` proportional to `1 / sqrt(n_edges)` to avoid clutter |
| W2.6 Sankey ribbons — drawing filled `Path` patches requires careful Bezier coordinate math | Use `pathway_flux_streamgraph` as the precedent template (already validated in CI) |
| W2.1 lollipop layout — multiple metrics × multiple scales = potentially many y-rows | Group rows by tier-band with subtle background banding; `axhspan` for each tier with `alpha=0.06` |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. The 7 recipes need to be disciplined. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 2086 + Wave 2 recipe smoke / quality / contracts (~14 new) = ~2100.
2. `pytest tests/test_recipes_smoke.py -k 'actin_microtubule_morphometry or biophysics_scaling or intravital_imaging'` — all relevant demos render headlessly.
3. `pytest tests/test_recipes_quality.py` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet at 20/20.
5. Gallery regenerate per modality. Estimate **5 visual-QA fit-ups** (multi-modality wave with new layout patterns: triptych, Sankey ribbons, contact-network overlay).

## Wave 3 — cytoskeleton geometry + statistics (+9) [gap-analysis]

**Why next.** Waves 1 + 2 shipped the universal QA primitives and
the F1 + F2 cell-territory cluster. Wave 3 lands the **F2D + F2E
+ F3 + F4** cluster — the geometry-and-statistics block where
the manuscript moves from "where do cells differ" to "by how
much, with what sensitivity". Builds on Wave 1's audit primitives
and Wave 2's territory contracts. Extends both
`actin_microtubule_morphometry/_shared.py` (with `BranchOrderEdge`,
`EdgeIntensityProfile`, `CortexZoneDescriptor`,
`MTMeshDensitySnapshot`, `ProtrusionOutlineWithCleveland`) and
`biophysics_scaling/_shared.py` (with
`CensoringCascadeRow`, `ConfinementEnergyBundle`,
`ZSpanWidthSample`).

### Recipe roster (Wave 3)

| ID | Recipe | Modality | Family | Required fields | Panel |
|---|---|---|---|---|---|
| W3.1 | `actin_mt_angle_rose_with_distance_inset` | actin_microtubule_morphometry | `radar` | `actin_mt_angles_deg: list[float]` per condition + `nn_distances_um: list[float]` for inset | F2D |
| W3.2 | `protrusion_outline_with_cleveland_summary` | actin_microtubule_morphometry | `scatter_collapse` | `cells: list[ProtrusionOutlineWithCleveland]` (outline polyline + per-cell width / erosion-depth scalars) | F2E |
| W3.3 | `censoring_mode_waterfall_cascade` | biophysics_scaling | `coef_forest` | `rows: list[CensoringCascadeRow]` (censoring rule × threshold × estimate × CI) | F3B |
| W3.4 | `confinement_energy_gauge_per_genotype` | biophysics_scaling | `coef_forest` | `bundles: list[ConfinementEnergyBundle]` (per-cell free-energy + per-genotype gauge thresholds) | F4C |
| W3.5 | `kinhom_inhomogeneous_isotropy` | spatial_statistics | `diagnostic_curve` | `r_grid_um: list[float]`, `kinhom_curves: dict[condition, list[float]]`, `csr_envelope: dict[condition, (lo, hi)]` | FS2C-D |
| W3.6 | `edge_gradient_intensity_profile` | actin_microtubule_morphometry | `timecourse_hierarchical_ci` | `profiles: list[EdgeIntensityProfile]` (signed-distance-from-edge × intensity per channel × condition) | FS2E |
| W3.7 | `cortex_composite_zone_descriptors` | actin_microtubule_morphometry | `matrix` | `descriptors: list[CortexZoneDescriptor]` (4 zones × N descriptors × 2 conditions, with z-scored colour) | FS2F |
| W3.8 | `mt_mesh_density_compartment_compare` | actin_microtubule_morphometry | `heatmap` | `snapshots: list[MTMeshDensitySnapshot]` (whole-cell vs protrusion-internal mesh-density H × W) | FS4E-F |
| W3.9 | `z_span_vs_width_with_euler_threshold` | biophysics_scaling | `scatter_collapse` | `samples: list[ZSpanWidthSample]` (per-cell width + z-span + Euler L_crit + condition) | FS5B |

### Family-rule satisfaction checklist

- **W3.1** (`radar` ≥1 polar axis + ≥1 filled polygon) — satisfied by per-condition angle-distribution rose polygons (filled `ax.fill` on polar projection); NN distance inset rendered on a separate cartesian inset axis.
- **W3.2** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — Cleveland dot scatter for per-cell width / erosion + zero-reference vertical line; representative-protrusion outlines drawn as `Polygon` patches in a left-side inset.
- **W3.3, W3.4** (`coef_forest` ≥3 markers + ≥1 reference line) — W3.3 satisfied by per-row CI-segment markers across ≥4 censoring modes + significance-threshold reference line; W3.4 by per-cell gauge tick markers across ≥2 genotypes + buffered/unbuffered threshold reference.
- **W3.5** (`diagnostic_curve` ≥2 curves + ≥1 legend) — per-condition Kinhom(r) curve + CSR envelope ribbon + reference Kpois(r) = πr² overlay.
- **W3.6** (`timecourse_hierarchical_ci` ≥1 CI band + ≥1 mean line) — per-condition mean intensity profile + bootstrap CI ribbon along signed-distance-from-edge axis.
- **W3.7** (`matrix` ≥1 imshow OR ≥4 cell patches) — 4-zone × N-descriptor × 2-condition heatmap via `pcolormesh`; flag column for descriptors crossing the manuscript's z-score threshold.
- **W3.8** (`heatmap` ≥1 imshow / pcolormesh) — side-by-side compartment imshow panels (whole-cell vs protrusion-internal) per genotype with shared colour scale.
- **W3.9** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — z-span vs width per-cell scatter + Euler L_crit threshold curve drawn as `ax.plot`.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `recipes/actin_microtubule_morphometry/_shared.py` | edit | Add 5 new sub-contracts: `BranchOrderEdge` (W3.1 distance-inset), `ProtrusionOutlineWithCleveland` (W3.2), `EdgeIntensityProfile` (W3.6), `CortexZoneDescriptor` (W3.7), `MTMeshDensitySnapshot` (W3.8). |
| `recipes/biophysics_scaling/_shared.py` | edit | Add 3 new sub-contracts: `CensoringCascadeRow` (W3.3), `ConfinementEnergyBundle` (W3.4), `ZSpanWidthSample` (W3.9). |
| 5 new modules in `recipes/actin_microtubule_morphometry/` | **NEW** | W3.1, W3.2, W3.6, W3.7, W3.8 |
| 3 new modules in `recipes/biophysics_scaling/` | **NEW** | W3.3, W3.4, W3.9 |
| 1 new module in `recipes/spatial_statistics/` | **NEW** | W3.5 (the only spatial_statistics +1 in the pack) |
| `recipes/actin_microtubule_morphometry/__init__.py` | edit | Register 5 new recipes; modality 40 → 45 |
| `recipes/biophysics_scaling/__init__.py` | edit | Register 3 new recipes; modality 38 → 41 |
| `recipes/spatial_statistics/__init__.py` | edit | Register 1 new recipe; modality 15 → 16 |

No new `core/` shims required (Kinhom edge-correction is a per-pixel scaling factor implemented inline in W3.5; ~30 LOC). No new top-level deps.

### `_demo()` seed convention (Wave 3)

All Wave 3 demos use seeded RNG (`np.random.default_rng(60X)`) and the manuscript's WT vs LI condition labels with biology-agnostic synthetic data so future packs can reuse the recipes:

- **W3.1**: 2 conditions × 200 angle samples; LI distribution shifted toward 0° (more parallel actin-MT alignment); NN-distance inset shows LI cluster shifted left of WT (closer inter-filament packing).
- **W3.2**: 2 cells (WT_2 + LI_12 representative outlines) × 8 cells per condition (Cleveland values); width and erosion-depth distributions visibly shifted between conditions.
- **W3.3**: 4 censoring modes × 2 conditions × 12 representative cells; estimate stable in direction (LI ≲ WT) but support sub-threshold across all four censoring rules (the manuscript's "directionality stable, magnitude sub-threshold" finding).
- **W3.4**: 2 conditions × 12 cells; gauge tick markers; LI gauge crosses the buffered → unbuffered threshold while WT remains buffered.
- **W3.5**: 2 conditions × 60 r-values; LI Kinhom > Kpois (clustering); WT lies inside CSR envelope.
- **W3.6**: 2 channels (F-actin + MT) × 2 conditions × 50 sample profiles; cortical enrichment asymmetry visible (LI shifted toward edge for both channels).
- **W3.7**: 4 zones × 6 descriptors × 2 conditions; intensity / density / connectivity columns flagged in red where |z| > 0.5.
- **W3.8**: 2 cells × 2 compartments × 64 × 64 mesh-density grids; protrusion-internal compartment shows ~3× density of whole-cell.
- **W3.9**: 2 conditions × 30 cells; LI cells skew above the Euler critical-length threshold (supercritical), WT below.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| W3.1 NN-distance inset on a polar axis — risk that the inset's Cartesian axes look out of place | Park the inset on a sub-axes that overlays the polar plot's lower-right corner; use a small axes-fraction box (0.65, 0.04, 0.32, 0.22) so it reads as an inset |
| W3.2 Cleveland summary needs both cells (icons) + scalar dots — risk of crowding when many cells | Use the left third of the figure for icons, right two-thirds for the Cleveland strip; precedent from `latency_decomposition_forest` (intravital w2) |
| W3.3 waterfall display — visual risk that the per-row CI segments look like the existing `pre_registered_censoring_mode_grid` (matrix family) | Differentiator: lay out as horizontal forest with **cascading** vertical offset between censoring modes (each row offset down-and-right) so the waterfall shape is visible |
| W3.4 gauge plots — non-trivial polar / arc geometry | Use the existing precedent from `qc_metric_radar` (meta_and_diagnostic) for the polar arc; per-cell tick marks via `ax.scatter` on the arc |
| W3.5 inhomogeneous Kinhom edge correction — easy to introduce subtle bias | Use the per-point area-correction method (Ohser 1983); keep edge-correction logic ≤30 LOC inline; don't ship as a separate `core/` shim |
| W3.6 edge-gradient profile — sign convention for "distance from edge" can flip | Convention: positive = inside cell, negative = outside; document in contract docstring |
| W3.7 cortex composite — 4 zones × 6 descriptors = 24 cells, busy heatmap | Use the existing `data_quality_heatmap` (meta_and_diagnostic) precedent for layout; flag column for crossing thresholds |
| W3.8 compartment compare — risk of clipped axes per Wave 2 W2.3 sentinel-pattern issues | Apply the established sentinel pattern (parent `imshow` parked off-axes + `set_xlim/ylim(0,1)` + `set_facecolor("none")`) |
| W3.9 z-span vs width with Euler curve — risk that Euler theory curve dominates the scatter | Use a faint dashed line for Euler; bold scatter for data; per-cell coloured by genotype |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. The 9 recipes need to be disciplined. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 2121 + Wave 3 recipe smoke / quality / contracts (~18 new) = ~2139.
2. `pytest tests/test_recipes_smoke.py -k 'actin_microtubule_morphometry or biophysics_scaling or spatial_statistics'` — all relevant demos render headlessly.
3. `pytest tests/test_recipes_quality.py` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet at 20/20.
5. Gallery regenerate per modality. Estimate **5 visual-QA fit-ups** (multi-modality wave with non-trivial geometry: polar inset, gauge arcs, waterfall cascade, Euler curve overlay).

## Wave 4 — narrative integration + final supplements (+9) [pending]

F5 / F6 narrative-integration panels + FS5–FS7 final supplements. Closes the pack. Includes the headline `narrative_cascade_river` (synthesis-figure primitive) plus the new `core/permanova_null_utility.py` shim.

(Detail filled in when Wave 4 gap analysis is gated.)

## Pack-closeout deliverables (after Commit 3 of Wave 4)

After Wave 4 ships, run pack-closeout in a follow-up PR (same pattern as biophysics_scaling pack PR #32 + intravital_imaging pack PR #38):

1. Bump tracker w4 row `review` → `merged`; mark Summary "After W4" column ✅.
2. CHANGELOG roll-up `[1.4.0-beta-cytoskeletal_morphometry_companion]` (full pack release notes summing 4 waves).
3. Tag `v1.4.0-beta-cytoskeletal_morphometry_companion`, push, GitHub release with per-wave delta table.
4. `docs/recipes_by_modality.md` headline badge: catalog 423 recipes; per-modality counts updated.

## Out of scope for this pack

- New modality (additive governance — all recipes go into existing modalities).
- Cytosim / Monte-Carlo simulation engines (those live outside panelforge; only their visual outputs are in scope, and those map to existing biophysics_scaling forward-validation recipes).
- Interactive / live-imaging variants.
- Tables S1–S9 (auto-generated from data, not figure recipes).
- SI text boxes (prose, not figures).
- Manuscript-LaTeX integration.
- Sex- / genotype-stratified layout templates — figure-composition concern.
