# Session 01 — `rhogtpase_dynamics` (12 → 18, +6)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `rhogtpase_dynamics`
- `SESSION_NUM`: `01`
- `V10_COUNT`: 12
- `V11_TARGET`: 18
- `PRIORITY_CONTEXT`: This modality drives Manuscript 3 biophysics,
  µRedoxScape, and the scaffold v4.3 FRET-RhoA ODE figures. It is the
  most visually load-bearing modality in the user's program. Hydrate
  with care for the Tyson/Novák dynamics-paper aesthetic.

## Seed list for the gap analysis (refine during the analysis phase)

- `phase_portrait_with_trajectories` — overlay sample solution trajectories on streamplot
- `potential_waddington_2d` — Waddington-style sloped 2D landscape projection
- `codimension2_bifurcation` — two-parameter bifurcation map with curves of saddle-node and Hopf
- `excitability_threshold_diagram` — shows threshold crossing dynamics (Class I/II)
- `slow_manifold_projection` — fast-slow decomposition visualization
- `return_map_first_return` — Poincaré first-return map for oscillators

Follow the Part 2 template exactly. Do not modify any other modality.
