# Recipes by modality

v1.0.0 stable: 20 modalities, 137 recipes.
v1.1 in progress: 151 recipes (s01 rhogtpase_dynamics +6, s02 fret_biosensors +8).

## v0.1.0-alpha (3 modalities, 18 recipes)

- **grant_and_conceptual** (6): executive summaries, Gantts, WP flows,
  hypothesis diagrams, team matrices, conceptual triptychs.
- **meta_and_diagnostic** (4): power curves, sample-size ladders,
  missing-data patterns, QC radars.
- **sensitivity_analysis** (8): Sobol / Morris / parameter scan / Pi-group
  collapse / interaction matrix / convergence / active subspace.

## v0.1.0-beta1 (4 modalities, 31 recipes)

- **mixed_effects_models** (9).
- **dose_response_pharmacology** (5).
- **biophysics_scaling** (5).
- **rhogtpase_dynamics** (12).

## v0.1.0-beta2 (4 modalities, 31 recipes)

- **gillespie_stochastic** (7).
- **redox_imaging** (8).
- **fret_biosensors** (10).
- **calcium_signaling** (6).

## v0.1.0-beta3 (4 modalities, 27 recipes)

- **omics_differential** (10): volcanos, MA plot, GSEA running-enrichment,
  ORA dotplot, UpSet set comparisons, differential rank ladder, pathway-flux
  bubble, effect-size vs significance, multi-contrast volcano grid,
  annotated cluster heatmap.
- **single_cell_embeddings** (7): UMAP categorical + continuous, pseudotime
  trajectory with arrow, expression dotplot by cluster, PCA biplot with
  loadings, 2D diffusion map, neighborhood composition stacked bars.
- **network_and_pathway** (5): regulatory hive, chord diagram, Sankey-like
  flux, module eigengene heatmap, centrality degree distribution.
- **diffusion_and_tracking** (5): MSD by condition with α fit, step-size
  distribution by condition, angle autocorrelation decay, confinement
  radius map, track persistence histogram.

## v1.0.0 — Session 5 (5 modalities, 30 recipes)

- **spatial_statistics** (6): Ripley's L, pair correlation, NN distances,
  Voronoi territories, KDE heatmap, Moran's I by lag.
- **clinical_cohort** (6): Kaplan-Meier by stratum, Cox forest, CONSORT
  flow, baseline characteristics, subgroup forest, outcome by quartile.
- **cryoem_and_structure** (6): FSC curve, angular distribution, local
  resolution, 2D class montage, Ramachandran, B-factor vs residue.
- **intravital_imaging** (6): cell-track field, two-photon depth
  projection, vessel-diameter kymograph, cell-shape descriptors by state,
  migration rose, time-to-homing survival.
- **actin_microtubule_morphometry** (6): filament orientation, branch-point
  density, persistence-length fit, protrusion length × velocity,
  cortical thickness by region, skeleton kymograph.

## v1.1.0-s02 — fret_biosensors hydration (+8, in progress)

Expands fret_biosensors from 10 to 18 recipes:

- **donor_acceptor_scatter_linearity** — sensor-linearity validation
  scatter with OLS fit, 95% CI, slope / R² callout.
- **fret_efficiency_vs_distance** — Förster-distance / physics
  calibration with fitted R₀.
- **paired_pre_post_stimulus** — per-cell pre/post connecting lines
  with Wilcoxon statistics.
- **biosensor_dose_response_matrix** — dose × time 2-D heatmap with
  iso-contours and peak-response marker.
- **kymograph_ratio_edge_to_center** — 1-D spatial × temporal
  kymograph along the cell radius.
- **ratio_map_with_segmentation_overlay** — ratio heatmap with cell
  outlines overlaid.
- **windowed_roi_ratio_trajectory** — per-window sub-cellular
  trajectories colour-coded by arc-length position.
- **fret_vs_scalar_activity_regression** — cross-method FRET-vs-
  orthogonal-scalar regression.

## v1.1.0-s01 — rhogtpase_dynamics hydration (+6, in progress)

Expands rhogtpase_dynamics from 12 to 18 recipes:

- **phase_portrait_with_trajectories** — streamplot + time-colored integrated
  trajectories from multiple ICs with stability-coded fixed points.
- **codim2_bifurcation_map** — two-parameter (µ, ν) plane with SN/Hopf/
  pitchfork curves and codim-2 points (cusp, BT).
- **potential_landscape_waddington_3d** — isometric 3-D Waddington surface
  with gradient-descent trajectories.
- **excitability_threshold_diagram** — FitzHugh-Nagumo with threshold curve
  and paired sub/super-threshold trajectories.
- **slow_manifold_projection** — geometric collapse of fast trajectories
  onto the slow manifold.
- **poincare_first_return_map** — 1-D discrete return map with cobweb
  iteration and slope-at-FP diagnostic.
