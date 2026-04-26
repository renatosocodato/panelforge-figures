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
| w1 | Substrate (+5): A.4 dwell-time, A.5 sojourn-survival, A.6 hazard-rate, A.8 emission-distribution, A.10 HMM-vs-HSMM model-comparison + shared contracts + HMM/HSMM/KM utilities | **gap-analysis** | `beta-intravital-imaging-w1` | — | Wave 1 gap analysis in review |
| w2 | Decoding products + latency primitives (+11): A.1, A.2, A.3, A.7, A.9, A.11, A.12 + B.4, B.5, B.6, B.7 | pending | — | — | Depends on w1 |
| w3 | Commitment kinetics + biophysics block (+16): B.1, B.2, B.3, B.8–B.15 + C.1, C.2, C.3, C.4, C.5 | pending | — | — | Depends on w2; ships GAM utility (Wave 3 footnote in plan §3) |
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

## Out of scope for this pack

- Cross-modality recipes (intravital × omics, intravital × biophysics_scaling).
- Live-imaging interactive variants.
- Dependency injection for the user's own HMM/HSMM/UMAP/GAM/lifelines implementations (each `core/` utility is a thin shim, not a plugin point).
- Sex- / genotype-stratified layout templates — figure-composition concern.
- HMM/HSMM hyperparameter selection methodology (`n_states`, emission family priors) — methods-layer document, not recipe layer.
