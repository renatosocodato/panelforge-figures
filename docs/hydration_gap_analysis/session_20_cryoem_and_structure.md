# Session 20 — Gap Analysis: `cryoem_and_structure` (6 → 15, +9, Path 2)

**Branch:** `v1.1/session-20-cryoem_and_structure`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`cryoem_and_structure` is the **final** session of the v1.1 hydration
plan. It underwrites collaborator cryo-EM / structural-biology work
that interfaces with the program. v1.0 currently ships **6 real
recipes** (coordinator listed 3 — plan-vs-reality mismatch; see
below): angular distribution, B-factor per residue, FSC resolution,
local-resolution surface, 2D class montage, and Ramachandran plot.
Missing are the **per-chain B-factor ridge**, **RMSF**, **docking
funnel**, **contact map**, **electrostatic-surface colormap**, **normal
mode decomposition**, **H-bond network**, **BSA-vs-affinity scatter**,
and **motion-correction shift field** reviewers expect.

> **Plan-vs-reality reconciliation (Path 2).** The coordinator
> records `cryoem_and_structure: 3 → 15`. Real v1.0 baseline is 6;
> two seed names (`ramachandran_plot`,
> `cryosparc_2d_class_averages_grid`) already ship as existing
> recipes, and `local_resolution_volume_slice` duplicates
> `local_resolution_surface`. Drop those 3 duplicate seeds and land
> **+9 new** to hit 6 + 9 = 15 — same Path-2 pattern as s16, s19.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `angular_distribution_hist` | `heatmap` | particle-orientation coverage |
| 2 | `bfactor_vs_residue` | `diagnostic_curve` | per-residue B-factor curve |
| 3 | `fsc_resolution_curve` | `diagnostic_curve` | FSC vs frequency |
| 4 | `local_resolution_surface` | `heatmap` | local res surface colormap |
| 5 | `particle_2d_class_montage` | `matrix` | 2D class montage |
| 6 | `ramachandran_plot` | `scatter_collapse` | φ/ψ Ramachandran |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits.

### Per-residue / per-chain stats (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `b_factor_distribution_by_chain` | Across chains, how do B-factor distributions differ (per-chain flexibility)? | `bfactor_vs_residue` (single per-residue curve) | Per-chain ridge stack of B-factor distributions with per-chain median markers — different grammar (distribution per chain, not trace). | `ridge_by_group` |
| N2 | `conformational_ensemble_rmsf` | From an MD / ensemble, which residues have highest RMS fluctuation? | `bfactor_vs_residue` (static B-factor) | Per-residue RMSF curve from an ensemble with per-region shading + secondary-structure ticks; different quantity (RMSF vs B-factor) and source (ensemble). | `diagnostic_curve` |

### Docking & contacts (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N3 | `docking_pose_score_vs_rmsd` | Does the docking score decrease as RMSD-to-native decreases (funnel-shaped landscape)? | None — no docking recipe | Per-pose scatter of score vs RMSD with funnel-envelope + near-native cluster marker. | `scatter_collapse` |
| N4 | `contact_map_with_secondary_structure` | Which residue pairs form contacts, with secondary-structure context? | None | Residue × residue contact map (imshow) with α-helix / β-sheet / loop tracks along both axes. | `matrix` |

### Surface & interface (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N5 | `surface_electrostatics_colormap` | What is the electrostatic potential on the molecular surface, and where are the positive / negative patches? | `local_resolution_surface` (density resolution, not electrostatics) | 2-D electrostatic-potential projection with RdBu_r colormap + surface-charge summary; different quantity and scale. | `heatmap` |
| N6 | `interface_area_vs_affinity` | Across complexes, does buried surface area (BSA) correlate with binding affinity (Kd)? | None | BSA × Kd log-log scatter with fitted trend line and high-affinity quadrant shading. | `scatter_collapse` |

### Dynamics & networks (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N7 | `domain_motion_decomposition` | Which normal modes / PCs capture most of the concerted-motion variance? | None | Horizontal bars per mode showing cumulative % variance + top-mode cartoon-arrow legend. | `ladder` |
| N8 | `hydrogen_bond_network_diagram` | Around a key residue, what is the hydrogen-bond network and occupancy per bond? | None | Central residue node with H-bond partners radially arranged; line thickness ∝ occupancy fraction. | `conceptual` |

### Microscopy pipeline QC (+1)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N9 | `motion_correction_shift_vector` | Per movie frame, how large and correlated were the motion-correction shifts? | `angular_distribution_hist` (orientations, not motion); `particle_2d_class_montage` (class averages) | Per-frame (dx, dy) quiver from a reference origin + cumulative-drift callout. | `conceptual` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (per-chain B-factor ridge, ensemble RMSF, docking funnel, contact map w/ SS, electrostatics, normal-mode variance, H-bond network, BSA-vs-Kd, motion-shift quiver).
3. **No grammar duplication** — `diagnostic_curve` × 1 (RMSF); `heatmap` × 1 (electrostatics); `matrix` × 1 (contact map); `scatter_collapse` × 2 (docking funnel, BSA-vs-Kd) on distinct axis pairs; `ridge_by_group` × 1, `ladder` × 1, `conceptual` × 2 (H-bond graph vs shift quiver) with distinct layouts.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic`.
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 9 → modality goes from **6 → 15** recipes. Total catalog goes from **319 → 328** — crossing the ≥320 v1.1 target. Tests projected: **1646 → ~1691** (5 per recipe × 9).

**This is the final session.** After merge + tag `v1.1.0-s20`, the closeout procedure from `docs/hydration_coordinator.md` runs: final tag `v1.1.0`, release-notes summary, README update, and a final gallery regeneration.

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
