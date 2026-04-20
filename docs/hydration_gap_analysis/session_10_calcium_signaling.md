# Session 10 — Gap Analysis: `calcium_signaling` (6 → 15, +9)

**Branch:** `v1.1/session-10-calcium_signaling`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`calcium_signaling` is the scaffold-v4.3 GCaMP6f integration modality.
v1.0 ships the raster-+-mean-rate, trace stack, condition-level event-
frequency split violin, wave-propagation front, spike-triggered average,
and pairwise synchronization matrix (6 recipes). Missing are the
**per-cell amplitude distribution**, **peri-event alignment
histogram**, **population synchrony over time** (not just pairwise),
**network-burst detection**, **wave-speed map**, **per-cell freq × amp
landscape**, **calcium × FRET joint panel**, **oscillation-phase polar**,
and **stimulus-triggered cell × time heatmap** reviewers expect.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `calcium_propagation_wavefront` | `heatmap` | spatial wave-front isochrones |
| 2 | `event_frequency_by_condition` | `split_violin` | per-cell **frequency** per condition |
| 3 | `event_raster_with_rate` | `timecourse_hierarchical_ci` | raster + mean-rate overlay |
| 4 | `gcamp_trace_stack` | `diagnostic_curve` | per-cell ΔF/F traces |
| 5 | `spike_triggered_average` | `timecourse_hierarchical_ci` | STA mean trace + CI |
| 6 | `synchronization_matrix` | `matrix` | pairwise sync, static |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Event-property distributions (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| C1 | `calcium_event_amplitude_distribution` | Across cells, how are Ca²⁺ event **amplitudes** distributed, per condition? | `event_frequency_by_condition` (**frequency**, not amplitude) | Measurement: event amplitude (ΔF/F peak), not count / rate. Visual: ridge / stacked density per condition. Distinct quantity from every existing recipe. | `ridge_by_group` |
| C2 | `calcium_event_onset_alignment` | Aligned to each Ca²⁺ event onset (PETH), what is the per-cell event probability vs lag? | `spike_triggered_average` (**continuous amplitude** averaged to the spike, not a count histogram) | Measurement: peri-event time histogram (binned count / bin), not a mean waveform. Different statistic (rate around event vs ΔF/F waveform). | `timecourse_hierarchical_ci` |

### Population dynamics (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| C3 | `population_synchronization_timeline` | How does a population-level synchronization coefficient evolve over time? | `synchronization_matrix` (**pairwise, static** over the whole window) | Measurement: single scalar sync(t) curve, not pairwise sync. Different aggregation (temporal vs spatial). | `diagnostic_curve` |
| C4 | `network_burst_detection_overlay` | Where along the recording do network bursts occur, overlaid on the raster + rate? | `event_raster_with_rate` (raw raster + rate, **no burst detection**) | Adds burst-detection overlay: shaded burst epochs + onset/offset markers on the existing raster grammar, plus burst-count callout. Distinct annotation layer. | `timecourse_hierarchical_ci` |

### Spatial + landscape (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| C5 | `calcium_wave_speed_map` | Across the field, what is the local wave-propagation **speed** (μm/s)? | `calcium_propagation_wavefront` (**isochrones of arrival time**, not speed field) | Measurement: per-pixel speed = |∇t|⁻¹ where t is arrival time. Different physical quantity (rate vs arrival time). | `heatmap` |
| C6 | `single_cell_calcium_landscape` | Per cell, how does **event frequency** relate to **event amplitude**? | `event_frequency_by_condition` (frequency only); `calcium_event_amplitude_distribution` (amplitude only) | Measurement: **2-D per-cell scatter** of (frequency, amplitude) with density contour and per-condition hulls. Distinct joint distribution. | `scatter_collapse` |

### Cross-modal + polar + stim-triggered (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| C7 | `calcium_and_fret_joint_plot` | For cells recorded simultaneously in Ca²⁺ and FRET, how do the two activity measures covary? | None — no cross-modal joint panel exists in `calcium_signaling` | Measurement: per-cell (Ca²⁺ event rate, FRET ratio) joint scatter with marginal histograms and Pearson r. Distinct cross-modality grammar. | `scatter_collapse` |
| C8 | `oscillation_frequency_polar` | Per cell, where does the dominant oscillation phase fall on the unit circle? | `synchronization_matrix` (pairwise sync, no phase); `spike_triggered_average` (waveform, no phase) | Measurement: **phase on unit circle** per cell (dominant oscillation). Visual: polar scatter with mean resultant vector R. Different axis (angular) and statistic. | `radar` |
| C9 | `stimulus_triggered_calcium_heatmap` | Around a stimulus onset, how do all cells' ΔF/F traces align (cell × time heatmap)? | `gcamp_trace_stack` (per-cell line traces, not a heatmap); `spike_triggered_average` (mean, not per-cell matrix) | Measurement: **cell × time** matrix aligned to stimulus, heatmap grammar. Different shape (2-D matrix vs stacked lines or mean curve). | `heatmap` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different quantity, aggregation, or visual grammar).
3. **No grammar duplication** — `heatmap` × 3 after this session (wavefront isochrones / speed field / cell × time stim-triggered), `timecourse_hierarchical_ci` × 4 (raster+rate / STA / PETH / burst overlay) all with distinct axis semantics, `scatter_collapse` × 2 (freq × amp landscape / Ca²⁺ × FRET).

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic` (`microglia_states` palette).
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 9 → modality goes from **6 → 15** recipes. Total catalog goes from **224 → 233**. Tests projected: **1171 → ~1216** (5 per recipe × 9).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
