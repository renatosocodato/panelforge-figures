# Session 02 — Gap Analysis: `fret_biosensors` (10 → 18, +8)

**Branch:** `v1.1/session-02-fret_biosensors`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Existing coverage (v1.0, 10 recipes)

| # | Recipe | Question answered |
|---|---|---|
| 1 | `donor_acceptor_dual_channel` | Raw donor/acceptor channel images side-by-side |
| 2 | `dose_response_hill_fret` | EC50 of a compound on the FRET readout |
| 3 | `fret_signal_to_noise_map` | Where in the field is FRET signal quality usable? |
| 4 | `ratio_distribution_by_condition` | How does the per-cell ratio distribution shift across conditions? |
| 5 | `ratio_heatmap_over_field` | Spatial ratio pattern at a given timepoint (2-D) |
| 6 | `ratio_timecourse_hierarchical_ci` | How does the ratio evolve over time across conditions (hierarchical CI)? |
| 7 | `roi_ratio_summary_grid` | ROI × timepoint matrix summarising ratios |
| 8 | `sensor_calibration_curve` | What is the sensor's Kd and dynamic range vs ligand? |
| 9 | `single_cell_ratio_trajectories` | Per-cell trajectories partitioned into responder / weak / non-responder |
| 10 | `stimulus_response_fan` | Fan of per-cell traces post-stimulus with mean envelope |

## Visual gaps identified

1. **No sensor-linearity validation recipe.** Biosensor figures routinely need a control panel demonstrating the donor/acceptor pair behaves linearly (slope, R²). The existing `donor_acceptor_dual_channel` shows raw images, not the linearity diagnostic.
2. **No Förster-distance / physics calibration recipe.** `sensor_calibration_curve` covers the *biochemical* calibration (Kd vs ligand) but not the *physical* FRET-efficiency-vs-distance curve that anchors a FRET measurement to molecular geometry.
3. **No paired pre/post-stimulus comparison.** Paired plots with per-cell connecting lines + paired statistics are a stats-gate staple; `ratio_distribution_by_condition` shows unpaired distributions only.
4. **No dose × time integration.** `dose_response_hill_fret` shows dose only; `ratio_timecourse_hierarchical_ci` shows time only. A dose × time heatmap of ratio change is missing.
5. **No edge-to-centre kymograph.** `ratio_heatmap_over_field` is a single-timepoint 2-D image; `ratio_timecourse_hierarchical_ci` is time-only. The spatial-temporal kymograph along a 1-D cell axis (edge → interior) — canonical for Rac/Rho wave dynamics — is missing.
6. **No segmentation-overlay variant of the ratio field.** The existing ratio heatmap is a pure field; many biosensor figures need cell outlines overlaid so single-cell contributions are identifiable.
7. **No windowed / per-region ROI trajectory recipe.** `single_cell_ratio_trajectories` is per whole cell; `roi_ratio_summary_grid` is a static matrix. Tracking N sub-cellular windows (e.g. along a migrating leading edge) along time is a distinct grammar.
8. **No FRET-vs-orthogonal-activity regression.** To ground FRET measurements against a gold standard (e.g. phospho-ERK intensity, mechanical readout), a scatter + regression with `r` / slope annotation is essential. No current recipe covers it.

## Proposed 8 recipes

| # | name | answers_question | contract | required_fields | optional_fields | closest_existing_alternative | why_distinct | visual_signature | data_shape_hints |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `donor_acceptor_scatter_linearity` | Does the donor / acceptor intensity pair behave linearly across the dynamic range, as required for FRET-ratio interpretability? | new per-recipe `DALinearityInput` | `donor`, `acceptor` | `condition_labels`, `fit_line`, `title` | `donor_acceptor_dual_channel` | Existing recipe shows *images*; this is a *validation scatter* with linear fit + R² + slope annotation. Different grammar (quantitative diagnostic vs. raw image). | Scatter of donor vs. acceptor pixel/ROI pairs (alpha-by-density), ordinary-least-squares fit line with 95% CI band, callout with slope and R². Aspect ratio square. | CSV / parquet: two aligned numeric columns (donor, acceptor), typical n ≈ 5 000–50 000 pixel pairs. |
| 2 | `fret_efficiency_vs_distance` | What is the fitted Förster radius $R_0$, and how closely do measured FRET efficiencies track the theoretical $1/(1 + (r/R_0)^6)$ curve? | new per-recipe `FRETDistanceInput` | `distances_nm`, `efficiency` | `efficiency_sem`, `fitted_R0_nm`, `title` | `sensor_calibration_curve` | Calibration curve currently covers the *biochemical* calibration (Kd vs ligand); this is the *physical* FRET-efficiency-vs-distance curve that anchors the sensor to molecular geometry. | Scatter of measured (distance, efficiency) with error bars, overlaid theoretical $E = 1/(1 + (r/R_0)^6)$ curve, vertical dashed line at fitted $R_0$ with halo label, axis in nm. | CSV: distance in nm (0.1–15 nm typical), efficiency in [0, 1], optional SEM. n = 6–50 standards. |
| 3 | `paired_pre_post_stimulus` | For each cell, does the FRET ratio change significantly from pre-stimulus to post-stimulus, and how large is the per-cell shift? | new per-recipe `PairedPrePostInput` | `pre_values`, `post_values` | `cell_ids`, `paired_pvalue`, `mean_delta`, `title` | `ratio_distribution_by_condition` | Existing recipe is an *unpaired* distribution comparison; this recipe keeps per-cell identity through the pairing (connecting line per cell), which unlocks paired statistics and is the canonical "does each cell respond?" grammar. | Two x-positions ("pre", "post") with per-cell dots connected by thin grey lines, mean ± SEM markers overlaid, paired-t / Wilcoxon p-value callout at top. | CSV: cell_id, pre, post (N × 3). Typical N = 20–200 cells. |
| 4 | `biosensor_dose_response_matrix` | How does the FRET ratio change jointly as a function of dose and time, and where in (dose, time) is the response maximal? | new per-recipe `DoseTimeMatrixInput` | `doses`, `times_s`, `delta_ratio` | `hill_surface_overlay`, `title` | `dose_response_hill_fret`, `ratio_timecourse_hierarchical_ci` | Existing recipes separate the two axes — Hill fit in dose or hierarchical CI in time. This recipe *integrates* dose × time in a single heatmap, revealing kinetic differences between high and low doses. | 2-D imshow with dose on y (log), time on x; `RdBu_r` anchored at $\\Delta = 0$; optional contour lines at $\\Delta = 0.1, 0.2, 0.3$; peak-response marker. | CSV or npz: dose vector, time vector, matrix shape `(n_dose, n_time)`. |
| 5 | `kymograph_ratio_edge_to_center` | Along a 1-D axis from cell edge to centre, how does the FRET ratio propagate in time (waves, gradients)? | new per-recipe `EdgeKymoInput` | `distance_um`, `time_s`, `ratio` | `edge_velocity`, `title` | `ratio_heatmap_over_field`, `ratio_timecourse_hierarchical_ci` | Field heatmap is single-timepoint 2-D; timecourse is time-only. This is *spatial-temporal* along a 1-D cell axis — the canonical Rac/Rho wave kymograph. | Horizontal axis = time, vertical axis = distance from edge (0 = edge at top); `RdBu_r` anchored at 1.0; optional edge-propagation velocity line overlaid and annotated. | CSV or npz: distance vector (0–40 μm), time vector (0–120 s), matrix shape `(n_distance, n_time)`. |
| 6 | `ratio_map_with_segmentation_overlay` | What is the spatial FRET-ratio pattern of the field, with cell outlines overlaid so per-cell contributions are identifiable? | new per-recipe `RatioSegMapInput` | `x_um`, `y_um`, `ratio`, `segmentation_polygons` | `cell_labels`, `title` | `ratio_heatmap_over_field` | Existing ratio map is a *pure* field; this adds the segmentation boundaries (polygon outlines in white) and per-cell labels so you can attribute each coloured region to a specific cell. Publication default when the paper quantifies single-cell statistics. | 2-D ratio heatmap via `imshow` with white cell-outline polygons overlaid (via `ax.plot` polylines from segmentation), optional cell-ID text annotations at centroids, mandatory scale bar. | tiff/npz: 2-D ratio array + list of per-cell polygon vertex lists. 50–500 cells typical. |
| 7 | `windowed_roi_ratio_trajectory` | Along a migrating cell's leading edge or a chosen perimeter path, how does the FRET ratio in each of N windowed sub-ROIs evolve over time? | new per-recipe `WindowedROIInput` | `time_s`, `window_positions`, `ratio_matrix` | `window_labels`, `title` | `single_cell_ratio_trajectories`, `roi_ratio_summary_grid` | Single-cell trajectories are per whole cell; ROI grid is a static matrix. This recipe tracks *dynamic* per-region trajectories with an explicit spatial ordering (windows along a perimeter) colored by position (edge → interior). | Per-window line plot of ratio vs time, lines color-gradient-coded by window index (e.g. `viridis` from 0 at edge to N at centre); inset showing the window arrangement schematic. | CSV or npz: time vector, ratio matrix shape `(n_windows, n_time)`. Typical n_windows = 8–24. |
| 8 | `fret_vs_scalar_activity_regression` | Does the FRET ratio correlate with an independent scalar activity measure (e.g. phospho-ERK, mechanical readout), and with what slope and $r$? | new per-recipe `FRETVsScalarInput` | `fret_ratio`, `scalar_activity`, `scalar_label` | `condition`, `fit_line`, `title` | `sensor_calibration_curve` | Calibration uses ligand as the x-axis; this ties FRET to *a second experimental readout* (orthogonal ground truth). Different validation grammar — answers "is this FRET signal real?". | Scatter of FRET ratio vs the scalar reference measure, color-coded by condition when provided, linear-fit line with 95% CI band, Pearson $r$ / slope / p callout. | CSV: per-observation `fret_ratio`, `scalar_activity`, optional `condition`. Typical n = 30–500. |

## Contract additions

All 8 recipes use **new per-recipe Pydantic contracts** local to their own `.py` file (the established pattern; matches Session 01). **No changes required to `core/contract.py`**.

## Family tags

All 8 map onto existing `RecipeFamily` enum values — no new quality-rule families needed:

| Recipe | Family tag | Rationale |
|---|---|---|
| `donor_acceptor_scatter_linearity` | `scatter_collapse` | Scatter + linear fit — trivially passes the ≥ 2 scatter + ≥ 1 line rule. |
| `fret_efficiency_vs_distance` | `diagnostic_curve` | Calibration curve with legend. |
| `paired_pre_post_stimulus` | `diagnostic_curve` | N connecting lines + legend. |
| `biosensor_dose_response_matrix` | `heatmap` | imshow-based. |
| `kymograph_ratio_edge_to_center` | `heatmap` | imshow-based. |
| `ratio_map_with_segmentation_overlay` | `heatmap` | imshow + overlay. |
| `windowed_roi_ratio_trajectory` | `diagnostic_curve` | Many lines + legend. |
| `fret_vs_scalar_activity_regression` | `scatter_collapse` | Scatter + regression. |

## Implementation plan (Commit 2, pending approval)

1. Add 8 new recipe files under `src/panelforge_figures/recipes/fret_biosensors/`.
2. Extend `__init__.py` to import and expose them.
3. No changes to `_aesthetic.py` — the existing `fret_donor_acceptor` palette + ratio-anchored `RdBu_r` + mandatory scale bars cover every new recipe without modification.
4. Each recipe ≥ 80 lines, honors `AESTHETIC.apply_to_ax` (or `apply_to_fig` for split-panel recipes), includes realistic `demo_contract()`.
5. Regenerate the 8 new gallery PNGs via `figures gallery regenerate --modality fret_biosensors`.
6. Update `docs/recipes_by_modality.md` + `docs/recipes_by_question.md` with session-02 entries.

## Test impact

Expected test count increase: **+24** (8 recipes × 3 layers: smoke + quality + cross-modality QA). Style-drift ratchet (≤ 20 distinct fontsize literals, ≤ 20 distinct linewidth literals) stays inside with room, provided implementation sticks to existing scale values — which the codebase discipline already enforces.

Current test count: **766**. Projected after this session: **790**.

---

## STOP — awaiting user approval

> Please review the 8 proposed recipes above and reply with one of:
>
> - **"approved"** — I will proceed to Commit 2 (implementation) with the exact roster above.
> - **"approved with changes: …"** — list any edits (rename, swap, adjust scope) and I will proceed with the revised roster.
> - **"rejected"** — I will revise the gap analysis and re-propose.
>
> No recipe code will be written until this approval step completes.
