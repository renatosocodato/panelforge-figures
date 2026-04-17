# Changelog

All notable changes to `panelforge-figures` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows semantic versioning.

## [Unreleased]

## [0.1.0a0] — 2026-04-17

Initial alpha — scaffold, core, 3 of 20 modalities.

### Added

- Core layer: `style`, `palette`, `primitives`, `layout`, `export`, `contract`,
  `aesthetic_base`.
- 12 themes: `default`, `nature`, `cell`, `pnas`, `devcell`, `bpj`, `neuron`,
  `ncb`, `sttt`, `trends`, `fct_grant`, `horizon`.
- 13 palettes: `okabe_ito`, `sex_dimorphic`, `home_gate_trap`, `wt_ko`,
  `redox_bistable`, `fret_donor_acceptor`, `sex_x_genotype`,
  `timepoint_gradient`, `mechanism_class`, `cytoskeleton_components`,
  `rhogtpase_family`, `microglia_states`, `journal_neutral`.
- Adapters: `tabular`, `numpy_npz`, `pandas_pickle`, `passthrough`.
- Transforms: `reshape`, `aggregate`, `join`, `derive`.
- Manifest schema + resolver + catalog generator.
- CLI (`figures` entrypoint) with 11 subcommands.
- Modality 1 — `grant_and_conceptual` (6 recipes): `executive_summary_tile`,
  `timeline_gantt_with_milestones`, `work_package_flow`, `hypothesis_diagram`,
  `team_expertise_matrix`, `conceptual_triptych`.
- Modality 2 — `meta_and_diagnostic` (4 recipes): `power_analysis_by_effect_size`,
  `sample_size_decision_ladder`, `missing_data_pattern_matrix`,
  `qc_metric_radar`.
- Modality 3 — `sensitivity_analysis` (8 recipes): `sobol_first_total_pair`,
  `morris_elementary_effects`, `parameter_scan_2d_contour`,
  `dimensionless_pi_group_collapse`, `pi_group_rank_plot`,
  `fast_subspace_detection`, `convergence_diagnostic_sobol`,
  `interaction_matrix_sobol`.
- Gallery generator + 18 committed gallery PNGs.
- Quality gate, aesthetic compliance test framework, smoke test framework.
- Claude Code skill at `skill/SKILL.md` with `bootstrap`, `resurvey`,
  `add_figure` modes, plus references, example manifests, and templates.
- CI workflow on Python 3.11 and 3.12.

### Target for v0.1.0

Completes the remaining 17 modalities (119 recipes) in subsequent sessions,
following the order in `README.md`.
