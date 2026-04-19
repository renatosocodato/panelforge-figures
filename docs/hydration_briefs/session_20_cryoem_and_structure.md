# Session 20 — `cryoem_and_structure` (3 → 15, +12)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `cryoem_and_structure`
- `SESSION_NUM`: `20`
- `V10_COUNT`: 3
- `V11_TARGET`: 15
- `PRIORITY_CONTEXT`: Forward-looking — collaborator work that the
  program interfaces with.

## Seed list

- `b_factor_distribution_by_chain` — per-chain B-factor violin
- `ramachandran_plot` — Ramachandran with region shading
- `conformational_ensemble_rmsf` — RMSF per residue for ensemble
- `docking_pose_score_vs_rmsd` — docking score landscape
- `contact_map_with_secondary_structure` — contact map with annotation tracks
- `surface_electrostatics_colormap` — electrostatic potential surface colormap
- `domain_motion_decomposition` — principal mode of motion
- `hydrogen_bond_network_diagram` — H-bond graph
- `interface_area_vs_affinity` — BSA vs Kd scatter
- `cryosparc_2d_class_averages_grid` — 2D class averages grid
- `motion_correction_shift_vector` — per-frame shift vectors
- `local_resolution_volume_slice` — resolution slice through map

Follow the Part 2 template exactly. Do not modify any other modality.

---

*Final session. After this PR merges, tag `v1.1.0` and run the
end-of-v1.1 closeout steps documented in
[`docs/hydration_coordinator.md`](../hydration_coordinator.md).*
