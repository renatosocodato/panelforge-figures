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
| w3 | Commitment kinetics + biophysics block (+16): B.1, B.2, B.3, B.8–B.15 + C.1, C.2, C.3, C.4, C.5 + GAM utility | **review** | `beta-intravital-imaging-w3` | — (PR #36 open) | 3 commits, 3 visual-QA fit-ups (B.3 legend, B.12 panel-title spacing + tick-label suppression, C.5 colorbar range), 6 GAM-utility tests, total tests 1908 → 1994 |
| w4 | Translational + reviewer-proof (+10): C.6, C.7, C.8, C.9, C.10, C.11, C.12, C.13, C.14, C.15 | pending | — | — | Depends on w3; closes pack |

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

## Out of scope for this pack

- Cross-modality recipes (intravital × omics, intravital × biophysics_scaling).
- Live-imaging interactive variants.
- Dependency injection for the user's own HMM/HSMM/UMAP/GAM/lifelines implementations (each `core/` utility is a thin shim, not a plugin point).
- Sex- / genotype-stratified layout templates — figure-composition concern.
- HMM/HSMM hyperparameter selection methodology (`n_states`, emission family priors) — methods-layer document, not recipe layer.
