# Session 15 — Gap Analysis: `diffusion_and_tracking` (5 → 15, +10)

**Branch:** `v1.1/session-15-diffusion_and_tracking`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`diffusion_and_tracking` is the downstream kin of `intravital_imaging`
— takes trajectories and extracts quantitative motion statistics. v1.0
ships **MSD by condition**, **step-size distribution**, **track
persistence-length histogram**, **angle-correlation decay** and **per-
track confinement-radius map** (5 recipes). Missing are the **single-
track α fit**, **state-coloured spaghetti**, **HMM dwell distribution**,
**spatial D heatmap**, **confinement-radius vs time**, **van Hove
jump-distance**, **track-direction polar**, **ergodicity EA-vs-TA MSD**,
**track-length CCDF** and **displacement-vs-state-residence** diagnostics
that SPT reviewers expect.

## Current 5-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `angle_correlation_decay` | `diagnostic_curve` | C(τ) directional memory |
| 2 | `confinement_radius_map` | `scatter_collapse` | spatial R_conf scatter |
| 3 | `msd_by_condition` | `diagnostic_curve` | per-condition pooled MSD vs τ |
| 4 | `step_size_distribution` | `ridge_by_group` | step-size ridge per condition |
| 5 | `track_persistence_hist` | `ridge_by_group` | persistence-length ridge per condition |

## Proposed 10 new recipes

All 10 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Per-track statistics (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `msd_anomalous_exponent_fit` | What is the **per-track** anomalous-diffusion exponent α, and how is α distributed across tracks? | `msd_by_condition` (pooled per condition, single α per condition) | **Per-track** α distribution + representative single-track MSD fit; shifts axis grammar from condition-level to track-level. | `scatter_collapse` |
| N2 | `track_length_distribution` | How long do tracks persist across conditions, and is there a photobleaching-censoring bias? | `track_persistence_hist` (persistence **length** — straightness, not duration); `step_size_distribution` (single-step, not multi-frame) | CCDF of track duration per condition with censoring marker; temporal-persistence (seconds) not path-persistence (μm). | `diagnostic_curve` |
| N3 | `jump_distance_van_hove` | Does P(Δr, Δt) follow a pure Gaussian (Brownian), or is it **non-Gaussian** (heterogeneity / anomalous)? | `step_size_distribution` (single-lag condition ridges) | **Van Hove self-correlation** at 3-5 lag times stacked, theoretical Gaussian overlay; multi-lag vs single-lag + Brownian reference. | `ridge_by_group` |

### State-aware motion (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N4 | `track_spaghetti_plot_colored_by_state` | Looking at raw trajectories, where do they switch **state** (confined / free / directed)? | `confinement_radius_map` (aggregate R, no trajectories) | Full trajectories drawn with per-segment colour by HMM-classified state, start/end markers. Qualitative visual not a summary statistic. | `scatter_collapse` |
| N5 | `hmm_state_dwell_distribution` | How long do tracks dwell in each HMM-classified state before switching? | `track_persistence_hist` (path-persistence); `angle_correlation_decay` (decorrelation time) | **Per-state dwell time** stacked ridges with mean-dwell markers; distinct statistic (state residence) from track-level persistence. | `ridge_by_group` |
| N6 | `displacement_vs_state_residence` | Conditional on how long a track has resided in a state, how does the next-step displacement distribution shift? | None — no residence-conditional displacement recipe | **State × Δr** heatmap with per-state-bin median overlay; 2D conditional axis grammar. | `matrix` |

### Spatial motion maps (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N7 | `diffusion_coefficient_heatmap_spatial` | Where in the field of view is diffusion fast vs slow? | `confinement_radius_map` (**R_conf** scatter, not binned D, uses scatter grammar) | **Gridded D(x, y)** heatmap with contour overlay; axis grammar is continuous-map (imshow) vs scatter. | `heatmap` |

### Direction & ergodicity (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `track_directionality_polar` | Is motion isotropic, or does it have a preferred direction in the field? | `angle_correlation_decay` (temporal decorrelation, not spatial direction) | **Polar histogram** of mean track-direction angle across all tracks, uniform-reference overlay. Different axis (polar). | `radar` |
| N9 | `ensemble_vs_time_averaged_msd` | Is motion **ergodic**? Do ensemble-averaged and time-averaged MSDs agree? | `msd_by_condition` (ensemble MSD only, no TA counterpart) | **EA-MSD** line + **per-track TA-MSD** scatter cloud with ergodicity-breaking parameter callout; compares two MSD definitions, not one across conditions. | `scatter_collapse` |

### Temporal single-track (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N10 | `confinement_radius_vs_time` | Does a track's confinement radius **evolve** — e.g. from confined to free? | `confinement_radius_map` (spatial static snapshot) | **Per-track R_conf(t)** trace with ensemble median band; temporal axis grammar (t, not x/y). | `timecourse_hierarchical_ci` |

## Distinctness summary

All 10 pass the three distinctness tests:

1. **No name collision** with the 5 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (per-track α, track duration, van Hove non-Gaussian, state-coloured raw trajectories, per-state dwell, residence-conditional displacement, spatial D map, directional polar, ergodicity EA-vs-TA, R_conf temporal evolution).
3. **No grammar duplication** — `scatter_collapse` × 3 (per-track α, spaghetti, EA-vs-TA) with distinct scatter semantics; `ridge_by_group` × 2 (van Hove lags, HMM dwells) on distinct axes; `diagnostic_curve` × 1 (track length CCDF); `heatmap` × 1, `matrix` × 1, `radar` × 1, `timecourse_hierarchical_ci` × 1.

## Cross-modality safety

`intravital_imaging` already ships `msd_curve_by_state` and
`velocity_distribution_by_state` (both pooled state-stratified curves).
These are distinct from:
- `msd_anomalous_exponent_fit` (per-track α, not pooled state MSD)
- `displacement_vs_state_residence` (residence-conditional, not state-only)
- `hmm_state_dwell_distribution` (dwell time, not velocity).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 10 recipes use the existing `ModalityAesthetic`.
- [x] All 10 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 10 → modality goes from **5 → 15** recipes. Total catalog goes from **271 → 281**. Tests projected: **1406 → ~1456** (5 per recipe × 10).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
