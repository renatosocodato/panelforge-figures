# Session 07 — Gap Analysis: `intravital_imaging` (6 → 15, +9 · Path 2)

**Branch:** `v1.1/session-07-intravital_imaging`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Reality check — baseline discrepancy

The hydration coordinator lists this modality at `V10_COUNT: 8`. The **actual** v1.0 file count in `src/panelforge_figures/recipes/intravital_imaging/` is **6** (cell_track_trajectory_field, two_photon_depth_projection, vessel_diameter_kymograph, cell_shape_descriptors_by_state, migration_rose_diagram, time_to_homing_survival). The plan's end-target is **15**.

This is a "Path 2 reconciliation" situation (same pattern as s03):

- **Path 1 — strict +7 seeds**: land 6 → 13. Two recipes short of the plan's 15-target; follow-up session needed to close.
- **Path 2 — hit the 15-target**: land 6 → 15 by adding the **7 seeds + 2 additional gap-closers** that are natural for the modality (MSD curve, velocity-distribution split violin).
- **Path 3 — abort**: defer entire session pending re-plan.

**Proposed: Path 2 (+9) — matches prior precedent in session 03 where we accepted the real baseline and added enough to hit the end-target in one session.**

## Context — what this session is

`intravital_imaging` powers the **Neuron** figures and the formalised
**2P witness** strategy (15 named analysis families). v1.0 ships
single-cell trajectory + z-depth projection + vessel kymograph + shape
violins + migration rose + homing survival. Missing are the multi-cell
field view, event rasters, pre/post territory change, surveillance
efficiency, contact matrices, laser-injury radial response, multi-
channel overlay, plus ensemble MSD and raw velocity distributions.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `cell_shape_descriptors_by_state` | `split_violin` | circularity / elongation **per shape state** |
| 2 | `cell_track_trajectory_field` | `scatter_collapse` | individual tracks across a field |
| 3 | `migration_rose_diagram` | `radar` | heading histogram (directional bias) |
| 4 | `time_to_homing_survival` | `diagnostic_curve` | Kaplan-Meier-style homing curves |
| 5 | `two_photon_depth_projection` | `heatmap` | **generic z-stack** color-by-depth MIP |
| 6 | `vessel_diameter_kymograph` | `heatmap` | diameter vs length × time |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Seeds from the brief (+7)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `depth_projected_microglia_field` | Across a multi-cell field, where are individual cells in (x, y) and at what depth z? | `two_photon_depth_projection` (**generic volumetric** z-stack MIP, single z-stack input) | Measurement: **per-cell (x, y, z) centroids** from a multi-cell field, not a volumetric array. Visual: 2-D scatter with marker color encoding depth + marker size encoding cell size. Different input (cell table, not z-stack) and different aggregation (per-cell, not per-voxel). | `heatmap` |
| N2 | `process_event_timeline` | Per cell, when do discrete events (retraction, extension, contact, lysis) occur across the observation window? | None — no event-raster grammar in modality | Measurement: **discrete events per cell** on a time axis. Visual: raster-style matrix (cells × time) with event-type markers, per-row state background. Different data structure than any existing recipe. | `matrix` |
| N3 | `territory_change_pre_post` | How does each cell's surveyed territory change from pre to post condition? | `cell_track_trajectory_field` (tracks, not territory polygons) | Measurement: **paired polygon areas** per cell, pre vs post. Visual: paired outline polygons with connecting paired-sample lines + mean ΔA callout. Different aggregation (per-cell territory, not trajectory). | `scatter_collapse` |
| N4 | `surveillance_efficiency_metric` | Across conditions, how does the surveillance-efficiency metric (area / time / cell) compare, with CI? | None — no dedicated surveillance-metric recipe | Measurement: condition-level composite metric with 95 % CI and a reference baseline. Visual: horizontal forest-style bars sorted by estimate. | `coef_forest` |
| N5 | `cell_cell_contact_frequency_matrix` | For N cells, how often does each pair make contact over time? | None — no pairwise contact view | Measurement: symmetric **cell × cell** contact-count matrix (or normalised contact rate). Visual: heatmap with threshold annotations and top-pair callouts. | `matrix` |
| N6 | `laser_injury_response_radial` | At distance r from an ablation site, how does the cellular response curve (e.g. density or chemotaxis-index) evolve over time? | None — no injury-response grammar | Measurement: **radial profile over time** following a localised stimulus. Visual: time-coloured curves of response(r) with t=0 reference. | `timecourse_hierarchical_ci` |
| N7 | `multi_channel_intravital_overlay` | How do two (or more) intravital channels co-register across a field, with a shared scale-bar and a per-channel histogram sidebar? | `two_photon_depth_projection` (single-channel depth MIP, no multi-channel blend); `vessel_diameter_kymograph` (single-scalar temporal view) | Measurement: **multi-channel RGB blend** of an intravital field, not a depth-coded MIP. Visual: RGB overlay with mandatory scale bar and a small per-channel histogram inset. Different input (multi-channel 2-D) and different visual grammar (RGB blend, not depth-colour). | `heatmap` |

### Additional gap-closers to hit 15-target (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `msd_curve_by_state` | As a function of lag time, what is the mean-squared displacement per morphological state, and is motion sub-diffusive / diffusive / super-diffusive (α)? | `cell_track_trajectory_field` (**raw tracks**, not ensemble statistic); `time_to_homing_survival` (survival, not MSD) | Measurement: **ensemble MSD(τ) per state** on a log-log axis with α-slope fit annotation. Standard intravital analysis (reviewer-mandatory); no existing ensemble-statistic recipe. | `timecourse_hierarchical_ci` |
| N9 | `velocity_distribution_by_state` | For each morphological state, how do the instantaneous-speed distributions compare? | `cell_shape_descriptors_by_state` (**shape descriptors** per state — not velocity); `migration_rose_diagram` (angles only, not speed) | Measurement: **instantaneous speed** per state. Visual: split violin with median / quartile overlays. Different quantity (speed, not circularity / elongation / angle) from every existing recipe. | `split_violin` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (different unit of analysis, different physical quantity, or different visual grammar).
3. **No grammar duplication** — `heatmap` is used 4× after this session but each is clearly distinct (generic depth-coded z-stack MIP / per-cell (x,y,z) scatter / vessel-diameter kymograph / multi-channel RGB blend). `matrix` × 2, `split_violin` × 2, `diagnostic_curve` × 1, `radar` × 1, `scatter_collapse` × 2, `coef_forest` × 1, `timecourse_hierarchical_ci` × 2.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic` (`microglia_states` palette, magma cmap, RdBu_r for ratios).
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Three choices:**

- **Path 1** (+7 seeds literal, 6 → 13): skip N8 / N9; land seven. Follow-up catch-up session needed later.
- **Path 2** (+9, 6 → 15) — **recommended**: matches the plan's end-target in one session and the s03 precedent.
- **Path 3** (abort): replan.

To approve Path 2, reply "approved". To choose Path 1, reply "path 1". To abort, reply "abort".

On Path 2, total catalog goes from **201 → 210**. Tests projected: **1056 → ~1101** (5 per recipe × 9).
