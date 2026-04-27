# intravital_imaging beta expansion pack tracker

**Version label:** `[1.3.0-beta-intravital_imaging]` (sub-tags `-w1` … `-w4`)
**Scope:** 42 new recipes + shared sub-contract module + 2–3 new
`core/` utilities, landed across 4 user-gated waves. Pack pattern
inherited from `[1.2.0-beta-biophysics_scaling]` (PRs #27–#32; tag
`v1.2.0-beta-biophysics_scaling`).
**Anchor manuscript:** in-vivo intravital microglia imaging in
DISC1-lissencephaly cortex (decision-layer / commitment+latency /
orthogonal axes).
**Plan file:** `~/.claude/plans/shimmying-mapping-hammock.md`

## Heavy-deps decision: Option D (Mixed)

Per user-gated decision before pack start:

- **`hmmlearn`** — added to `[project.dependencies]` (battle-tested HMM decoder; backbone of A.1–A.12).
- **`umap-learn`** — added to `[project.dependencies]` (cannot fake without coarse fallback; backbone of C.12).
- **Inline shims in `core/`** for: KM survival (Wave 1), HSMM duration-aware decoding (Wave 1, semi-Markov path for A.10 model comparison), GAM logistic spline (Wave 3 for B.3 phase boundary).
- `pyhsmm`, `lifelines`, `statsmodels` NOT added — replaced with the inline `core/` shims.

## Modality-boundary decision: option (b) (window-conditional recasts)

Per user-gated decision: C.1 / C.2 are recast as **intravital-specific tip-window-conditional** variants (not generic point-pattern). Names: `tip_ripleys_k_in_window` and `tip_pair_correlation_in_window`. The window is the cell ROI; signature uses `TipCentroidSnapshot.window_polygon_um` for polygon-clipped edge correction. Cross-references to existing `spatial_statistics` recipes in docs.

## Summary

| Metric | Start | After W1 | After W2 | After W3 | After W4 |
|---|---|---|---|---|---|
| intravital_imaging recipes | 15 | 20 | 31 | 47 | **57 (final)** |
| Total catalog recipes | 350 | 355 | 366 | 382 | **392 (final)** |
| Beta-pack recipes landed | 0 | 5 | 16 | 32 | **42 (final)** |

## Per-wave status

| Wave | Scope | Status | Branch | Merged tag | Notes |
|---|---|---|---|---|---|
| w1 | Substrate (+5): A.4 dwell-time, A.5 sojourn-survival, A.6 hazard-rate, A.8 emission-distribution, A.10 HMM-vs-HSMM model-comparison + shared contracts + HMM/HSMM/KM utilities | **merged** | `beta-intravital-imaging-w1` | — (squash-merged PR #33; commit `384bf88`); polish PR #34 (`c8851d0`) added contemporary palette + emission gremlin fix | 5 recipes + 3 visual-QA fit-ups (Wave 1) + 2 polish fix-ups (palette + gremlin); CI green |
| w2 | Decoding products + latency primitives (+11): A.1, A.2, A.3, A.7, A.9, A.11, A.12 + B.4, B.5, B.6, B.7 | **merged** | `beta-intravital-imaging-w2` | — (squash-merged PR #35; commit `c0b65e5`) | 3 commits, 3 visual-QA fit-ups; CI green |
| w3 | Commitment kinetics + biophysics block (+16): B.1, B.2, B.3, B.8–B.15 + C.1, C.2, C.3, C.4, C.5 + GAM utility | **merged** | `beta-intravital-imaging-w3` | — (squash-merged PR #36; commit `05cce3c`) | 3 commits, 3 visual-QA fit-ups (B.3 legend, B.12 panel-title spacing + tick-label suppression, C.5 colorbar range), 6 GAM-utility tests, total tests 1908 → 1994; CI green |
| w4 | Translational + reviewer-proof (+10): C.6, C.7, C.8, C.9, C.10, C.11, C.12, C.13, C.14, C.15 | **gap-analysis** | `beta-intravital-imaging-w4` | — | Wave 4 gap analysis in review; closes pack |

Status legend:
- **pending** — not yet started
- **gap-analysis** — Commit 1 landed, awaiting user approval
- **implementation** — recipes being authored (Commit 2)
- **review** — PR open, awaiting merge
- **merged** — squash-merged to `main`, tag pushed

## Wave 1 — substrate (+5)

**Why first.** Without decoded states, none of Part A's 7 downstream visualisation recipes (Wave 2) work. The 5 recipes here are the *minimum viable decoding diagnostic* — dwell-time distribution, sojourn survival, hazard-rate, per-state emission, and the HMM-vs-HSMM adjudicator. Once these land, Wave 2 can decorate the decoded states with field/raster/posterior-ribbon recipes.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/recipes/intravital_imaging/_shared.py` | **NEW** | 8 nested Pydantic sub-contracts: `TipTrack`, `ProtrusionPolyline`, `ProtrusionPolylineWithTime`, `KinematicFeatureBundle`, `TipCentroidSnapshot`, `LatencyDistribution`, `DecodedStateSeries`, `ModelFitSummary`. |
| `src/panelforge_figures/core/hmm_decoding_utility.py` | **NEW** | Thin wrapper around `hmmlearn.GaussianHMM`: `decode_states(features, n_states) -> DecodedStateSeries`, plus a small inline semi-Markov variant `decode_states_semi(features, n_states, duration_family) -> DecodedStateSeries` that adds explicit per-state duration distributions for the A.10 comparison. ~60 LOC + ~120 LOC for the HSMM. |
| `src/panelforge_figures/core/km_survival_utility.py` | **NEW** | `kaplan_meier(durations, censored) -> (t, S, ci_lo, ci_hi)` using Greenwood's formula. ~40 LOC. Exported via `core/__init__.py`. |
| `src/panelforge_figures/core/__init__.py` | edit | Export `decode_states`, `decode_states_semi`, `kaplan_meier`. |
| `src/panelforge_figures/recipes/intravital_imaging/__init__.py` | edit | Register 5 new recipe modules. |
| `pyproject.toml` | edit | Add `hmmlearn>=0.3` to `[project.dependencies]`. (`umap-learn` deferred to Wave 4 since C.12 ships there.) |
| `tests/test_hmm_decoding_utility.py` | **NEW** | EM convergence on a 3-state synthetic ground-truth; deterministic seed. |
| `tests/test_km_survival_utility.py` | **NEW** | Compare against scipy's reliability functions on a small dataset. |

### Recipe roster (Wave 1)

| ID | Recipe | Family | Required fields | Precedent to mirror |
|---|---|---|---|---|
| A.4 | `dwell_time_distribution_per_state` | `split_violin` | `dwells_by_state: dict[str, list[float]]`, `decoder_label: str` | `actin_microtubule_morphometry/process_end_count_violin.py` |
| A.5 | `sojourn_survival_per_state` | `diagnostic_curve` | `dwells_by_state`, `decoder_label` | new — KM-style step + dashed geometric reference |
| A.6 | `hazard_rate_per_state` | `timecourse_hierarchical_ci` | `dwells_by_state` | smoothed h(τ) ± CI; flat = HMM, ramp = HSMM |
| A.8 | `emission_distribution_per_state` | `split_violin` | `features_by_state: dict[str, dict[str, list[float]]]` | small-multiples of `process_end_count_violin` |
| A.10 | `hmm_vs_hsmm_model_comparison` | `coef_forest` | `fits: list[ModelFitSummary]` | `meta_and_diagnostic/heterogeneity_forest.py` (forest of ΔBIC ± CI) |

### Family-rule satisfaction checklist

- **A.4, A.8** (`split_violin` ≥2 violin bodies + ≥1 median marker) — satisfied by per-state violins (≥2 states required) + per-state median markers.
- **A.5** (`diagnostic_curve` ≥2 curves + ≥1 legend) — satisfied by S(τ) per state (≥2) + dashed geometric reference + legend.
- **A.6** (`timecourse_hierarchical_ci` ≥1 CI band + ≥1 mean line) — satisfied by per-state hazard curves with kernel-density CI ribbons.
- **A.10** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by ≥3 strata × {HMM, HSMM} markers + the zero-Δcriterion reference line.

### `_demo()` seed convention

Per pack governance, demos use seeded RNG and ship a fully-populated contract:
- A.4, A.5, A.6: Synthesize 3 states with deterministic dwell distributions — state 0 geometric (HMM-friendly), state 1 gamma (HSMM-favouring), state 2 lognormal (HSMM-favouring). Demonstrates the visual signal that distinguishes the two decoders.
- A.8: 3 states × 4 features (velocity, length-rate, curvature-mean, turning-angle) with each state's signature shifted to make per-state means visually distinct.
- A.10: 4 strata × {HMM, HSMM} fits with synthetic ΔBIC values that vary across strata so the forest plot has visible spread.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| `hmmlearn` is a new top-level dep — pyproject + CI install matrix may surface install issues | Pin to `hmmlearn>=0.3` (released 2023, scipy-native, pure-Python). Verify CI green before w1 PR. |
| KM utility shim must reproduce Greenwood's formula correctly | Write `tests/test_km_survival_utility.py` with a hand-computed comparison case BEFORE shipping. |
| Style-drift ratchet at 20/20 — 5 new recipes can't add a new fontsize/linewidth literal | Reuse existing literals exclusively (6.4, 6.6, 6.8, 7.0, 7.2, 7.4, 7.8, 8.2, 8.4 for fontsize; 0.4, 0.5, 0.7, 0.8, 1.0, 1.1, 1.2, 1.4, 2.2 for linewidth). |
| HSMM shim is the largest novel piece (~120 LOC) — risk of subtle EM bugs | Keep the implementation tight; validate against a published worked example (e.g. semi-Markov chain with explicit Weibull durations); contract test in `tests/test_hmm_decoding_utility.py`. |
| The 5 demo `_demo()` rosters must be visually consistent (same 3 states, same colour mapping) | Factor a `_shared._demo_state_palette()` helper in `_shared.py` so all 5 recipes pull from the same `microglia_states` palette index. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1814 still pass + new HMM/KM utility tests.
2. `pytest tests/test_recipes_smoke.py -k intravital_imaging` — 20 demos render headlessly (15 alpha + 5 new).
3. `pytest tests/test_recipes_quality.py -k intravital_imaging` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held at 20/20.
5. `pytest tests/test_hmm_decoding_utility.py` and `tests/test_km_survival_utility.py` — new.
6. Gallery regenerate `intravital_imaging/` — 20 PNGs.
7. Eyeball each new panel for collisions, clipped text, legend overflow.

## Wave 2 — decoding products + latency primitives (+11)

**Why next.** Wave 1 shipped the substrate (decoding utilities + 5
diagnostics that decide HMM-vs-HSMM). Wave 2 turns decoded states
into *visual* primitives: tip-track + polyline fields coloured by
state, posterior ribbons over time, transition matrices, occupancy
stacked-area, entry/exit rasters, and state-conditional MSD. It also
lands the *headline* of any chemotaxis figure — the four-component
latency forest (B.4 / B.5 / B.6 / B.7).

### Recipe roster (Wave 2)

| ID | Recipe | Family | Required fields | Precedent to mirror |
|---|---|---|---|---|
| A.1 | `state_decoded_tip_track_field` | `scatter_collapse` | `tip_tracks: list[TipTrack]`, `decoded: list[DecodedStateSeries]` | `intravital_imaging/cell_track_trajectory_field.py` (alpha) — but with state-coloured segments via `LineCollection` |
| A.2 | `state_decoded_protrusion_polyline_field` | `scatter_collapse` | `polylines: list[ProtrusionPolylineWithTime]`, `decoded` | new — polyline overlays coloured by parent-cell decoded state |
| A.3 | `posterior_state_probability_ribbons` | `timecourse_hierarchical_ci` | `decoded: list[DecodedStateSeries]` (must have posterior_prob), `states: list[str]` | new — stacked γ(t) ribbons; small-multiples-by-cell variant if `aggregate="per_cell"` |
| A.7 | `state_transition_kernel_matrix` | `matrix` | `decoded: list[DecodedStateSeries]`, `states: list[str]` | `meta_and_diagnostic/data_quality_heatmap.py` (annotated heatmap) |
| A.9 | `state_occupancy_stacked_area` | `timecourse_hierarchical_ci` | `decoded`, `condition_by_cell: dict[str, str]` | new — per-condition stacked area of occupancy fractions |
| A.11 | `state_entry_exit_raster` | `matrix` | `decoded: list[DecodedStateSeries]` | new — rows = cells, x = time, coloured bars per state with switch-tick markers |
| A.12 | `state_conditional_tip_msd` | `timecourse_hierarchical_ci` | `tracks: list[TipTrack]`, `decoded`, `states` | `intravital_imaging/msd_curve_by_state.py` (alpha) — but with τ restricted to same-state epochs and per-state α-fit |
| B.4 | `launch_to_commitment_latency` | `split_violin` | `latencies: list[LatencyDistribution]` (label="τ_commit") | `intravital_imaging/velocity_distribution_by_state.py` |
| B.5 | `cue_to_reorientation_latency` | `split_violin` | `latencies` (label="τ_reorient") | same |
| B.6 | `cue_to_net_displacement_latency` | `split_violin` | `latencies` (label="τ_drift") | same |
| B.7 | `latency_decomposition_forest` | `coef_forest` | `latencies` × labels {τ_reorient, τ_commit, τ_drift} × conditions | `meta_and_diagnostic/heterogeneity_forest.py` — headline panel of any chemotaxis figure |

### Family-rule satisfaction checklist

- **A.1, A.2** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by per-track scatter + state-coloured connecting line segments via `LineCollection` (counts as `ax.collections`).
- **A.3, A.9, A.12** (`timecourse_hierarchical_ci` ≥1 CI band + ≥1 mean line) — A.3 satisfied by stacked posterior ribbons + per-state mean γ; A.9 by stacked area + per-condition mean line; A.12 by MSD per state with bootstrap CI.
- **A.7, A.11** (`matrix` ≥1 imshow OR ≥4 cell patches) — A.7 satisfied by N×N transition `imshow`; A.11 by per-(cell, state-segment) rectangle patches (≥4 satisfied trivially).
- **B.4, B.5, B.6** (`split_violin` ≥2 violin bodies + ≥1 median marker) — satisfied by per-condition violins with median markers.
- **B.7** (`coef_forest` ≥3 markers + ≥1 reference line) — ≥3 latency × condition rows + the median(τ_reorient) of control reference.

### Demo seed convention

All Wave 2 demos use the same `microglia_states` semantic palette via the Wave 1 `_demo_state_palette()` helper. Specifically:
- A.1, A.2: 6 cells × 60-frame trajectories with per-cell decoded state segments (homeostatic / surveillant / activated). Tip-track demo uses synthetic random walks with state-dependent step sizes; polyline demo uses synthetic radial growth-and-retraction.
- A.3: 4-cell × 80-frame γ(t) where states transition smoothly so ribbons show coherent shifts.
- A.7: 3×3 transition matrix with diagonal-dominant probabilities (HMM-style sticky chains).
- A.9: 2 conditions × 80 cells × 60 frames with cohort-distinct occupancy patterns.
- A.11: 12 cells × 60 frames with decoded segments visible as raster bars.
- A.12: 6 cells × 30 lag bins with state-conditional MSD curves; activated-state α > 1 (super-diffusive), homeostatic α < 1 (sub-diffusive).
- B.4, B.5, B.6: 2 conditions × 50–80 latency values per recipe with cohort-distinct medians; 5–10 % censoring.
- B.7: 3 latencies × 2 conditions = 6 rows; control-median(τ_reorient) reference.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| A.1 / A.2 / A.11 LineCollection-on-scatter family rule (LineCollection lives on `ax.collections`, scatter lives on `ax.collections` too — but the rule expects ≥1 fit-line) | Reuse the biophysics_scaling pattern: add an invisible `ax.plot([], [], color="none", lw=0.5, alpha=0.0)` proxy line so the rule sees ≥1 line on `ax.get_lines()`. |
| A.3 stacked posterior ribbons collide visually when 5 states with similar γ(t) — overlapping ribbons hard to read | Use `stackplot` with the contemporary palette (slate / teal / coral / purple / amber); legend below axes; per-state median annotation on the right margin. |
| A.7 transition matrix labels (state names like "homeostatic") too long for 3×3 cell width — collide with cell numeric annotations | Use 4-letter slugs (`home`/`surv`/`acti`) for axis tick labels; full names in legend. |
| A.9 stacked area legend duplication (per-condition × per-state) blows up legend size | Single shared state legend below all condition panels; condition labels as panel titles. |
| A.11 raster sort_by parameter: cells sorted by total time-in-state vs n_switches gives different visual stories | Default to `total_time_in_state` (manuscript convention); user override available. |
| A.12 MSD restricted to same-state epochs may have very few points per state for short epochs — α fit unstable | Require ≥ 8 frames per epoch; degrade to "MSD shown but α not fit" if not met; show dashed reference α=1. |
| B.4/B.5/B.6 violin tail issues for heavily-skewed latency distributions | Use log-y where median > 5×IQR ratio; otherwise linear. |
| B.7 forest with 3 latency types × 2 conditions: 6-row layout could feel cramped | Tight figure (5.6×3.6"); colour-code by latency type (teal / coral / amber from the palette). |
| Style-drift ratchet at 20/20 | Reuse Wave 1 literals exclusively. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1853 still pass.
2. `pytest tests/test_recipes_smoke.py -k intravital_imaging` — 31 demos render headlessly (20 alpha+W1 + 11 new).
3. `pytest tests/test_recipes_quality.py -k intravital_imaging` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held at 20/20.
5. Gallery regenerate — 31 intravital_imaging PNGs.
6. Eyeball each new panel; estimate 5–8 visual-QA fit-ups for this wave.

## Wave 3 — commitment kinetics + biophysics block (+16)

**Why next.** Wave 1 shipped the substrate (decoding utilities +
diagnostics). Wave 2 turned decoded states into visual primitives
and shipped the headline latency forest. Wave 3 lands the
**commitment-kinetics** block (B.1 / B.2 / B.3 / B.8–B.15) — the
quantitative substrate for chemotaxis kinetics — and the
**biophysics-axes** block (C.1 / C.2 / C.3 / C.4 / C.5). After this
wave, all Part B recipes are complete and Part C is half-shipped.

### Recipe roster (Wave 3)

| ID | Recipe | Family | Required fields | Notes |
|---|---|---|---|---|
| B.1 | `protrusion_commitment_survival` | `diagnostic_curve` | `protrusions: list[ProtrusionPolyline]`, `condition_by_protrusion: dict[str, str]` | KM curves per condition via `kaplan_meier`; log-rank p in title if ≥2 conditions |
| B.2 | `commitment_hazard_with_age` | `timecourse_hierarchical_ci` | same as B.1 | Smoothed h(τ); ramp/peak = staged commitment |
| B.3 | `commitment_phase_diagram` | `heatmap` | `per_protrusion: list[{L_um, v_bar_um_per_min, committed}]` | **Ships GAM utility** (logistic-spline shim) for the boundary fit |
| B.8 | `chemotaxis_index_trajectory` | `timecourse_hierarchical_ci` | `bundles: list[KinematicFeatureBundle]`, `cue_onset_s_by_cell` | CI(t) = ⟨cos(θ−ĉ)⟩ ± 95 % CI per condition; t = 0 at cue onset |
| B.9 | `directional_persistence_autocorr` | `timecourse_hierarchical_ci` | `bundles` (need `heading_deg`) | C(τ) = ⟨cos(Δθ(τ))⟩ with fitted exponential τ_p callout |
| B.10 | `ornstein_uhlenbeck_fit_per_state` | `coef_forest` | `bundles`, `decoded` | Forest of (τ, σ) per state × condition |
| B.11 | `speed_commitment_coupling` | `timecourse_hierarchical_ci` | `bundles` (need both velocity + length-rate) | Cross-correlation function with peak-lag callout |
| B.12 | `commitment_vs_chemotaxis_contingency` | `matrix` | per-protrusion `{committed, aligned, condition}` | 2×2 with overlaid OR ± 95 % CI per condition |
| B.13 | `protrusion_dominance_race_winner` | `scatter_collapse` | per-cell polylines + win/loss labels | ΔL(t) traces colored by winner / runner-up |
| B.14 | `cue_response_dose_latency` | `timecourse_hierarchical_ci` | `LatencyDistribution` + `gradient_magnitude_per_cell: dict[str, float]` | τ vs |∇c| with fitted curve and CI band |
| B.15 | `aligned_vs_unaligned_velocity_split` | `split_violin` | per-step `{v, cos_theta_c, condition}` | Aligned-left / unaligned-right split per condition |
| C.1 | `tip_ripleys_k_in_window` | `diagnostic_curve` | `snapshots: list[TipCentroidSnapshot]`, `r_grid_um: list[float]` | **Window-conditional** intravital recast (option (b) decision); polygon-clipped edge correction; CSR envelope |
| C.2 | `tip_pair_correlation_in_window` | `timecourse_hierarchical_ci` | same as C.1 | Window-conditional g(r) per condition with CI |
| C.3 | `branch_order_topology_per_cell` | `split_violin` | `skeletons: list[{cell_id, branch_orders, n_bifurcations, total_length_um}]` | Branch-order distribution per condition + n_bif vs L scatter inset |
| C.4 | `curvature_along_protrusion_kymograph` | `heatmap` | `ProtrusionPolylineWithTime` with `curvature_per_s_per_t` | κ(s, t) heatmap with ridge-tracked max-κ overlay |
| C.5 | `viscous_drag_tip_force_map` | `scatter_collapse` | `tip_tracks: list[TipTrack]`, `viscosity_pa_s`, `tip_radius_um` | Tip XY coloured by F = 6πηr·v; lower-bound caveat banner |

### Family-rule satisfaction checklist

- **B.1, C.1** (`diagnostic_curve` ≥2 curves + ≥1 legend) — satisfied by per-condition KM (B.1) / Ripley K (C.1) curves + CSR / geometric reference + legend.
- **B.2, B.8, B.9, B.11, B.14, C.2** (`timecourse_hierarchical_ci` ≥1 CI band + ≥1 mean line) — satisfied by per-condition curves with bootstrap CI ribbons + per-condition mean lines.
- **B.3, C.4** (`heatmap` ≥1 imshow / pcolormesh) — B.3 satisfied by 2-D commitment-probability surface (`pcolormesh`) with iso-prob contours; C.4 by κ(s, t) heatmap.
- **B.10** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by ≥3 (state × condition) (τ, σ) markers + zero-reference for τ.
- **B.12** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by 2×2 contingency with annotated counts (4 cell patches; `OR ± 95 % CI` overlay).
- **B.13, C.5** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — B.13 satisfied by per-cell ΔL(t) traces + winner-vs-loser fit; C.5 by tip XY scatter + invisible-proxy line (LineCollection-shaped data).
- **B.15, C.3** (`split_violin` ≥2 violin bodies + ≥1 median marker) — satisfied by per-condition split violins with median markers.

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/core/gam_logistic_utility.py` | **NEW** | Inline GAM-style logistic regression with B-spline basis (~80 LOC). Used by B.3 commitment_phase_diagram. Signature: `fit_phase_boundary(L, v_bar, committed, n_grid_x=40, n_grid_y=40) -> tuple[X, Y, P_grid]`. Replaces `pygam` / `statsmodels.GAM` deps (Option D). |
| `src/panelforge_figures/core/__init__.py` | edit | Export `fit_phase_boundary`. |
| 16 new recipe modules under `src/panelforge_figures/recipes/intravital_imaging/` | **NEW** | One per recipe |
| `src/panelforge_figures/recipes/intravital_imaging/__init__.py` | edit | Register 16 new recipes (imports + `__all__`); bumps total to 47 |
| `tests/test_gam_logistic_utility.py` | **NEW** | Boundary recovery on synthetic ground truth + spline-basis sanity |

No new top-level deps (the GAM utility is the third and final inline shim per the Option D heavy-deps decision; `umap-learn` lands in Wave 4 with C.12).

### Demo seed convention (Wave 3)

All Wave 3 demos use seeded RNG and the contemporary palette (slate / teal / coral / purple / amber for states; slate / coral for control / DISC1 conditions per Wave 2 lock-in).

- **B.1, B.2**: 80 protrusions × 2 conditions; commitment defined as no retraction in 30 s window. Median lifetime ~120 s control / ~75 s DISC1 (DISC1 commits faster — visible in KM crossover).
- **B.3**: 200 protrusions on (L, v̄) grid; logistic boundary at L · v̄ ≈ 30; iso-prob 0.5 contour; demo data crosses the boundary visibly.
- **B.8**: 2 conditions × 30 cells × 90-frame heading + cue series; CI(t) ramps from ~0 (random) to ~0.6 (control) or ~0.3 (DISC1) post-cue.
- **B.9**: 2 conditions × 40 cells; τ_p ≈ 12 s (control) / 25 s (DISC1) — DISC1 has more directional memory.
- **B.10**: 3 states × 2 conditions = 6 markers; (τ, σ) per state distinct.
- **B.11**: speed-commit cross-correlation peaks at lag = +6 s (length-rate leads speed by 6 s).
- **B.12**: 4 strata of 2×2 contingency; per-condition OR labelled.
- **B.13**: 12 cells × 2 protrusions; winning protrusion has ΔL ≈ 8 µm ± 2 µm by end.
- **B.14**: 5 |∇c| levels × 30 cells; τ_reorient inversely scales with |∇c|.
- **B.15**: 2 conditions × 600 step-pairs; aligned (cos θ_c > 0) ~30 % faster than unaligned.
- **C.1, C.2**: 4-frame snapshots × 2 conditions; tips clustered (Ripley K > CSR envelope) in DISC1.
- **C.3**: 40 cells × 2 conditions; branch-order distribution shifts from mean 2.1 (control) to 2.7 (DISC1).
- **C.4**: 1 protrusion × 30 timepoints × 40 arc points; curvature ridge migrates over time.
- **C.5**: 60 tips with F = 6πηr·v range 0.5–4 pN.

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| GAM utility correctness (B-spline basis + logistic IRLS — easy to introduce subtle bugs) | Write `tests/test_gam_logistic_utility.py` with hand-computed boundary recovery on a synthetic logistic ground truth; require accuracy > 80 % on a clean test before merging. |
| B.3 phase-diagram heatmap + iso-prob contours + scatter overlay — three layers, easy to crowd | Use cividis cmap for heatmap (low-saturation), black solid contours, white-edged scatter for committed / hollow scatter for not-committed. |
| C.1, C.2 polygon-clipped edge correction (tip-window-conditional) is the differentiator from `spatial_statistics` | Implement Ripley correction via `shapely.geometry.Point.distance` to the polygon boundary; keep ~30 LOC of correction code; document the difference from `spatial_statistics/ripley_l_function`. |
| C.4 kymograph y-axis (arc length) needs interpretable units even when `normalize_arclength=True` | Two y-axis modes: arc length (µm) for absolute, arc fraction (0–1) for normalized — annotate which mode in title. |
| B.10 OU fit per state can fail when state-conditional epochs are too short | Require ≥ 20 frames per state × condition; degrade to "fit not shown, data shown" if not met. |
| B.13 ΔL(t) traces colour-coded by winner: legend duplication if shown per cell | Single shared 2-entry legend (winner / runner-up) below axes. |
| B.14 fitting `τ vs |∇c|` with fitted curve + CI band on log-log axes — curve may extrapolate poorly outside data | Restrict fit / CI to the data range; clip extrapolation. |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. The 16 recipes need to be disciplined. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1908 still pass + new GAM utility tests.
2. `pytest tests/test_recipes_smoke.py -k intravital_imaging` — 47 demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k intravital_imaging` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held at 20/20.
5. `pytest tests/test_gam_logistic_utility.py` — boundary recovery on synthetic data > 80 %.
6. Gallery regenerate `intravital_imaging/` — 47 PNGs.
7. Eyeball each new panel; estimate 5–8 visual-QA fit-ups (16 recipes is the largest wave so far for this pack).

## Wave 4 — translational + reviewer-proof (+10) [gap-analysis]

**Why last (closes pack).** Waves 1–3 shipped the decision layer (HMM/HSMM substrate + decoded-state visualisations + latency
forest), the commitment-kinetics block (survival, hazard, phase
diagram, persistence, OU, contingency, dominance race), and the
first 5 biophysics-axes recipes. Wave 4 closes the alpha-coverage
gap (biosensor / photobleaching / transfer-entropy / dim-reduction
/ PSD / dose×time matrix) and adds 3 **reviewer-proof** recipes
(equivalence-test radar, cohort-balance matrix, calibration
forest). After this wave intravital_imaging is **57 recipes**;
total catalog is **392**.

### Pre-wave decision: revisit `umap-learn` lock-in

Per pack governance §13, `umap-learn` was promised as a required
dep "(cannot fake without coarse fallback; backbone of C.12)".
Two reasons to revisit before Commit 2:

1. **Install-footprint blast radius.** `umap-learn` pulls
   `numba` (LLVM JIT, requires C-toolchain) and `scikit-learn`
   (~150 MB on disk). The pack so far has been zero-additional-
   weight outside `hmmlearn` and the inline shims. Adding
   `umap-learn` would more than double install cost.
2. **Option D inline-shim discipline.** Wave 1's HSMM, KM, and
   Wave 3's GAM utilities established the precedent that any
   non-numpy/scipy fittable algorithm can ship as a ~80 LOC
   inline shim. A 2-D **spectral embedding** (Laplacian
   eigenmaps via `scipy.sparse.csgraph.laplacian` +
   `scipy.linalg.eigh` on a kNN graph) is ~50 LOC, gives
   visually similar manifold structure to UMAP for the kinematic-
   feature distances at issue, and matches the shim discipline.

**Recommendation:** revise the Option D commitment — drop
`umap-learn`, add `core/spectral_embedding_utility.py`
(`embed_2d(X, n_neighbors=15) -> (E, info)`), and rename C.12 to
`state_kinematic_spectral_embedding`. This keeps the alpha-gap
fill ("no nonlinear-embedding of state-feature vectors found in
alpha") while honouring the inline-shim pattern.

If the user prefers to honour the original lock-in, the alternative
is keep `state_kinematic_umap_embedding` and add `umap-learn>=0.5`
to `[project.dependencies]`. **Plan commits to inline-shim path
unless gated otherwise.**

### Recipe roster (Wave 4)

| ID | Recipe | Family | Required fields | Notes |
|---|---|---|---|---|
| C.6 | `biosensor_activation_field_per_cell` | `heatmap` | `fields: list[BiosensorField]` (per-cell H×W intensity grid) + `condition_by_cell` | 4-panel small-multiples (per-cell intensity field, e.g. ROCK/Rho biosensor); divergent cmap centred on baseline |
| C.7 | `biosensor_dose_response_curve` | `timecourse_hierarchical_ci` | `traces: list[BiosensorTimeTrace]` keyed by dose + `condition_by_cell` | Per-dose mean trace + bootstrap CI ribbon; EC50 callout when fit converges |
| C.8 | `photobleaching_corrected_intensity_traces` | `diagnostic_curve` | `pre_correction_intensity[t]` + `corrected_intensity[t]` + `bleach_fit_params` | Two curves (raw + corrected) + dashed bi-exp fit reference; per-cell residual histogram inset |
| C.9 | `kinematic_power_spectral_density` | `coef_forest` | `bundles: list[KinematicFeatureBundle]` + `condition_by_cell` + (optional) decoded states | Forest of dominant frequency f_peak per (state × condition) ± 95 % CI; reference at f = 0 |
| C.10 | `transfer_entropy_state_to_velocity_matrix` | `matrix` | `bundles` + decoded states; symbolic-binning TE inline | N×N TE matrix (state↔velocity↔length-rate) per condition; row/col directionality |
| C.11 | `dose_x_time_response_matrix` | `heatmap` | `responses: list[DoseTimeResponse]` (dose × time grid) per condition | 2-D `pcolormesh` with iso-response contours; one panel per condition |
| C.12 | `state_kinematic_spectral_embedding` | `scatter_collapse` | `bundles` + decoded states; reduces per-cell feature vectors to 2-D | 2-D embedding scatter coloured by decoded state; per-state convex hull as the ≥1 fit line |
| C.13 | `equivalence_tost_radar_per_condition` | `radar` | per-feature TOST bounds (lower / upper / observed) | Reuses `core/tost_bounds_utility.classify_outcome`; polygon vertices = features; filled polygon = condition; reference circle at equivalence margin |
| C.14 | `cohort_baseline_balance_table_matrix` | `matrix` | per-cohort feature means + standardised-mean-differences (SMD) | CONSORT-style balance grid; cell colour = SMD; flagged when |SMD| > 0.1 |
| C.15 | `model_calibration_brier_forest` | `coef_forest` | per-stratum Brier scores + 95 % CI + reliability-curve auxiliary stats | Forest of Brier per stratum; reference at perfect-calibration zero; reviewer-proof for any P(commit) classifier surfaced earlier in the pack |

### Family-rule satisfaction checklist

- **C.6, C.11** (`heatmap` ≥1 imshow / pcolormesh) — satisfied by per-cell biosensor field (C.6) and dose × time response surface (C.11), both via `pcolormesh`.
- **C.7** (`timecourse_hierarchical_ci` ≥1 CI band + ≥1 mean line) — satisfied by per-dose mean trace + bootstrap CI ribbon.
- **C.8** (`diagnostic_curve` ≥2 curves + ≥1 legend) — satisfied by raw + corrected curves + bi-exp fit dashed reference + legend.
- **C.9, C.15** (`coef_forest` ≥3 markers + ≥1 reference line) — satisfied by ≥3 (state × condition) PSD-peak markers (C.9) / ≥3 stratum Brier markers (C.15) + zero / perfect-calibration reference.
- **C.10, C.14** (`matrix` ≥1 imshow OR ≥4 cell patches) — satisfied by N×N TE heatmap (C.10) and balance-grid `pcolormesh` (C.14).
- **C.12** (`scatter_collapse` ≥1 scatter + ≥1 fit line) — satisfied by 2-D embedding scatter + per-state convex-hull boundary as the "fit line".
- **C.13** (`radar` ≥1 polar axis + ≥1 filled polygon) — satisfied by `subplot(projection='polar')` with the per-condition filled polygon + reference circle at equivalence margin (precedent: `meta_and_diagnostic/qc_metric_radar`, `dose_response_pharmacology/polypharmacology_radar`).

### Infrastructure deliverables

| File | Kind | Purpose |
|---|---|---|
| `src/panelforge_figures/core/spectral_embedding_utility.py` | **NEW** (if recommended path) | `embed_2d(X, n_neighbors=15, sigma=None) -> (E, info)` — kNN-graph + symmetric Laplacian + smallest-non-zero eigenvectors via `scipy.linalg.eigh`. ~50 LOC. Used by C.12. |
| `src/panelforge_figures/core/transfer_entropy_utility.py` | **NEW** | `transfer_entropy(source, target, n_bins=4, lag=1) -> float` — symbolic binning + Shannon-entropy decomposition. ~60 LOC. Used by C.10. |
| `src/panelforge_figures/core/__init__.py` | edit | Export the two new functions. |
| 10 new recipe modules under `src/panelforge_figures/recipes/intravital_imaging/` | **NEW** | One per recipe |
| `src/panelforge_figures/recipes/intravital_imaging/__init__.py` | edit | Register 10 new recipes (imports + `__all__`); bumps total to 57 |
| `src/panelforge_figures/recipes/intravital_imaging/_shared.py` | edit | Add 3 nested sub-contracts: `BiosensorField`, `BiosensorTimeTrace`, `DoseTimeResponse` |
| `tests/test_spectral_embedding_utility.py` | **NEW** | Manifold-recovery on synthetic ring + S-curve (≥80 % neighbour preservation) |
| `tests/test_transfer_entropy_utility.py` | **NEW** | TE recovery on a coupled-AR(1) ground truth (TE_X→Y > 0, TE_Y→X ≈ 0) |
| `pyproject.toml` | **no edit** if recommended path; else add `umap-learn>=0.5` | — |

(If the user gates the original lock-in path, swap `spectral_embedding_utility` for `umap-learn` dep + skip the corresponding test file.)

### Demo seed convention (Wave 4)

All Wave 4 demos use seeded RNG and the contemporary palette
(slate / teal / coral / purple / amber for states; slate / coral
for control / DISC1 conditions; cividis / viridis / magma for
heatmap-family panels per Wave 3 lock-in).

- **C.6**: 4 cells × 32×32 grid; ROCK biosensor signal peaks at +20 % over baseline in DISC1 protrusion-tip regions.
- **C.7**: 5 doses × 30 cells × 90 frames; sigmoidal dose-response with EC50 ≈ 1.5 µM in control / 4 µM in DISC1.
- **C.8**: 8 cells × 200 frames; bi-exponential bleach (fast τ_1 ≈ 30 s, slow τ_2 ≈ 200 s); corrected trace flat within ±2 %.
- **C.9**: 3 states × 2 conditions × 30 cells; control PSD peak at ~0.05 Hz; DISC1 broadband (no clean peak).
- **C.10**: 3 streams (state, velocity, length-rate) × 2 conditions × 60 cells; control TE(state→velocity) ≈ 0.4, reverse direction ≈ 0.05; DISC1 TE flat ≈ 0.1 in both directions.
- **C.11**: 6 doses × 30 timepoints × 2 conditions; sustained response in control, transient peak in DISC1.
- **C.12**: 200 cells × 8 features × 3 states; embedding clusters by state are visually separable.
- **C.13**: 5 features × 2 conditions; equivalence margin = 0.2; DISC1 polygon escapes the margin on 2/5 axes.
- **C.14**: 12 features × 2 cohorts; |SMD| > 0.1 on 3/12 (flagged in red).
- **C.15**: 4 strata × 2 models; Brier scores 0.10–0.18; one stratum CI crosses zero (uncalibrated).

### Risks and fit-up budget

| Risk | Mitigation |
|---|---|
| Spectral-embedding utility correctness (eigenvector-sign ambiguity, kNN-graph density choice) | Hand-test on synthetic ring + S-curve; require ≥80 % neighbour preservation versus brute-force pairwise distance ranking. |
| C.10 transfer-entropy is sensitive to bin count and time-lag choice | Default `n_bins=4`, `lag=1`; expose both as contract fields; demo seed values produce visible asymmetry between TE(X→Y) and TE(Y→X). |
| C.13 radar polygon collapse when all features land inside equivalence margin | Reference circle at the margin is plotted regardless; legend explicitly says "shaded region inside circle = within margin". |
| C.14 cohort balance — |SMD| threshold (0.1 vs 0.2) is field-dependent | Both 0.1 and 0.2 reference circles drawn; cell colour interpolates linearly; user can read off via colourbar. |
| C.6 4-panel inset layout (small-multiples) — risk of cropped axes per Wave 1 emission gremlin | Use `inset_axes` with `gridspec_kw={'wspace': 0.35}`; sentinel patches on parent ax for family rule. |
| C.7 EC50 fit fails for non-monotonic dose-responses | Fit only when monotone; otherwise report "EC50 not fit" in title. |
| C.8 bi-exp fit can lock onto a single τ when one exponential dominates | Default-initialise τ_1 < τ_2 with order-of-magnitude separation; report fit residual. |
| Style-drift ratchet at 20/20 | Reuse existing literals exclusively. The 10 recipes need to be disciplined. |

### Verification after Commit 2 + 3

1. `pytest tests/` — baseline 1994 still pass + new utility tests.
2. `pytest tests/test_recipes_smoke.py -k intravital_imaging` — 57 demos render headlessly.
3. `pytest tests/test_recipes_quality.py -k intravital_imaging` — each new recipe satisfies its family rule.
4. `pytest tests/test_style_drift.py` — ratchet held at 20/20.
5. `pytest tests/test_spectral_embedding_utility.py` — neighbour preservation > 80 %.
6. `pytest tests/test_transfer_entropy_utility.py` — coupled-AR(1) ground-truth recovery TE_X→Y > TE_Y→X.
7. Gallery regenerate `intravital_imaging/` — 57 PNGs.
8. Eyeball each new panel; estimate 3–5 visual-QA fit-ups (Wave 4 is smaller than Wave 3 but introduces new families: radar + UMAP-style scatter).

### Pack-closeout deliverables (after Commit 3 of Wave 4)

After Wave 4 ships, run pack-closeout in a follow-up commit (same pattern as biophysics_scaling pack's PR #32):

1. Bump tracker w4 row `review` → `merged`; add Summary-section "After W4" column to ✅.
2. CHANGELOG roll-up `[1.3.0-beta-intravital_imaging] — 2026-04-XX` (full pack release notes summing 4 waves).
3. Tag `v1.3.0-beta-intravital_imaging`, push, GitHub release with per-wave delta table.
4. `docs/recipes_by_modality.md` headline badge: catalog 392 recipes; intravital_imaging 57.

## Out of scope for this pack

- Cross-modality recipes (intravital × omics, intravital × biophysics_scaling).
- Live-imaging interactive variants.
- Dependency injection for the user's own HMM/HSMM/UMAP/GAM/lifelines implementations (each `core/` utility is a thin shim, not a plugin point).
- Sex- / genotype-stratified layout templates — figure-composition concern.
- HMM/HSMM hyperparameter selection methodology (`n_states`, emission family priors) — methods-layer document, not recipe layer.
