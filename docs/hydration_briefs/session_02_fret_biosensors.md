# Session 02 — `fret_biosensors` (10 → 18, +8)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `fret_biosensors`
- `SESSION_NUM`: `02`
- `V10_COUNT`: 10
- `V11_TARGET`: 18
- `PRIORITY_CONTEXT`: Scaffold v4.3 FRET-RhoA manuscript is active.
  This modality needs the vocabulary for publication-quality
  biosensor figures across ratiometric imaging, single-cell
  heterogeneity, and stimulus-response characterization.

## Seed list

- `windowed_roi_ratio_trajectory` — per-window ROI tracking on dynamic cells
- `ratio_map_with_segmentation_overlay` — FRET ratio colored by cell body + outline
- `donor_acceptor_scatter_linearity` — control plot for sensor linearity
- `fret_efficiency_vs_distance` — calibration against known distance
- `biosensor_dose_response_matrix` — dose × time heatmap of ratio change
- `kymograph_ratio_edge_to_center` — spatial-temporal kymograph
- `paired_pre_post_stimulus` — per-cell pre/post ratio change connected lines
- `fret_vs_scalar_activity_regression` — correlate FRET with independent activity measure

Follow the Part 2 template exactly. Do not modify any other modality.
