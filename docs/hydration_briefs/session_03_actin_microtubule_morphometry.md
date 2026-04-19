# Session 03 — `actin_microtubule_morphometry` (12 → 20, +8)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `actin_microtubule_morphometry`
- `SESSION_NUM`: `03`
- `V10_COUNT`: 12
- `V11_TARGET`: 20
- `PRIORITY_CONTEXT`: DISC1 Lissencephaly pipeline + scaffold v4.3 +
  Neuron supplementary. Danuser/Theriot aesthetic. Scale bars
  mandatory. Per-cell thumbnails common.

## Seed list

- `per_cell_thumbnail_grid_with_metrics` — 4x4 grid of segmented cells with metric annotation
- `branch_point_distribution` — spatial distribution of skeleton branch points
- `filament_length_vs_angle_heatmap` — 2D histogram of length × orientation
- `actin_mt_ratio_spatial_map` — ratio of actin to tubulin intensity across cell
- `process_tip_dynamics_timeline` — tip position over time with events
- `shape_descriptor_scatter_matrix` — pairwise plot of classical morphometrics
- `mitochondrial_axis_alignment` — compare organelle axes to cytoskeleton axes
- `branching_depth_sunburst_stratified` — sunburst stratified by condition

Follow the Part 2 template exactly. Do not modify any other modality.
