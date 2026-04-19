# Session 01 — Gap Analysis: `rhogtpase_dynamics` (12 → 18, +6)

**Branch:** `v1.1/session-01-rhogtpase_dynamics`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Existing coverage (v1.0, 12 recipes)

| # | Recipe | Question answered |
|---|---|---|
| 1 | `basin_of_attraction_map` | Which initial condition flows to which steady state? |
| 2 | `bifurcation_hopf` | Where does the 1-parameter Hopf occur? |
| 3 | `bifurcation_pitchfork` | Where does the symmetric state lose stability? |
| 4 | `bifurcation_saddle_node` | Where do stable branches collide? Where is hysteresis? |
| 5 | `nullcline_intersection_annotated` | Where do x/y nullclines cross, and with what stability? |
| 6 | `phase_portrait_bistable` | Two-well bistable landscape (streamplot + wells) |
| 7 | `phase_portrait_oscillator` | Limit cycle in phase space |
| 8 | `phase_portrait_tristable` | HOME / GATE / TRAP three-well landscape |
| 9 | `potential_landscape_1d` | How does U(x) change across conditions? |
| 10 | `potential_landscape_2d_heatmap` | Top-down heatmap of U(x, y) |
| 11 | `quasi_steady_state_reduction` | Does QSS reproduce full 2D dynamics? (time series) |
| 12 | `timescale_separation_diagnostic` | Is there clean fast/slow separation? |

## Visual gaps identified

1. No recipe showing **explicit integrated trajectories** from multiple initial conditions overlaid on a phase plane. Existing phase portraits show only streamplot flow fields — good for structure, but no "here's what the dynamics actually do from ICs" story.
2. No **two-parameter (codimension-2) bifurcation map**. We cover Hopf / SN / pitchfork each in isolation as 1-parameter diagrams, but not the canonical `(μ, ν)`-plane with curves of SN / Hopf / codim-2 points (Bogdanov–Takens, cusp).
3. No **Waddington-style 3D landscape projection**. The 2D heatmap is flat top-down; the Waddington (isometric 3D with development narrative) is a distinct visual grammar used in grant / conceptual figures and review panels.
4. No **excitability** recipe. Excitable systems (stable rest + threshold + large excursion) are their own canonical class alongside bistable / oscillator / tristable. Missing in the current roster.
5. No **phase-space slow-manifold projection**. `quasi_steady_state_reduction` shows the *time-series* comparison of full vs reduced dynamics — it does not show the *geometric* collapse of fast trajectories onto a slow curve in phase space.
6. No **discrete-time / return-map** recipe. For limit cycles, a first-return (Poincaré) map captures periodic-orbit stability via a 1D discrete map, a Tyson/Novák standard.

## Proposed 6 recipes

| # | name | answers_question | contract | required_fields | optional_fields | closest_existing_alternative | why_distinct | visual_signature | data_shape_hints |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `phase_portrait_with_trajectories` | How do solution trajectories from multiple initial conditions relax onto the attractor landscape? | new per-recipe `TrajectoryPhaseInput` (Pydantic) | `x_grid`, `y_grid`, `u`, `v` (flow field), `trajectories` (list of per-IC arrays of (t, x, y)), `fixed_points` | `attractor_labels`, `time_color` (bool), `title` | `phase_portrait_bistable` | Existing phase portraits render only the streamplot and fixed-point markers; this recipe *overlays a family of N integrated trajectories* with time-colored line segments from marked ICs. Different semantic layer (dynamics, not just structure). | Streamplot in muted grey as backdrop; 6-12 colored trajectory curves time-colored by `viridis`; open-circle IC markers; filled/hollow fixed-point dots per aesthetic; thin grey nullcline dashes. | CSV/parquet: one row per `(traj_id, t, x, y)`; or pickle with dict of numpy arrays. Typical `N_traj = 8-20`, 200-2000 timepoints each. |
| 2 | `codim2_bifurcation_map` | In the (µ, ν) parameter plane, where are the saddle-node / Hopf / pitchfork curves and the codim-2 points (Bogdanov-Takens, cusp)? | new per-recipe `Codim2Input` (Pydantic) | `mu_range`, `nu_range`, `sn_curves` (list of parametric `(mu, nu)` arrays), `hopf_curves`, `codim2_points` (list of `{label, mu, nu}` dicts) | `pitchfork_curves`, `regime_shading` (list of polygons with labels like "bistable", "oscillatory"), `title` | `bifurcation_saddle_node` (1-param) | 1-parameter bifurcation diagrams collapse one axis; a codim-2 map shows the *joint* parameter structure. This is categorically different — it's the organizing diagram that embeds every 1-param slice. | Dark-grey / red / blue curves for SN / Hopf / pitchfork; hollow-circle codim-2 points with halo'd labels (`BT`, `cusp`); softly shaded regime regions (`home_gate_trap` palette) underneath; axis labels are the two control parameters. | CSV or YAML: one curve per key, plus a list of codim-2 points. Typically 200-500 points per curve. |
| 3 | `potential_landscape_waddington_3d` | What does the RhoA/Rac1 potential landscape look like as a Waddington-style 3D surface, with sample development trajectories down the slope? | new per-recipe `Waddington3DInput` (Pydantic) | `x_grid`, `y_grid`, `U` (2D array), | `trajectories_xy` (list of xy-traj snapping to the surface), `well_labels`, `view_elevation_deg`, `view_azimuth_deg`, `title` | `potential_landscape_2d_heatmap` (top-down flat) | Flat heatmap gives density; the Waddington renders the *geometric* landscape as a 3D surface with the canonical "ball rolling down" development narrative. Different grammar — used in grants, conceptual panels, commentaries. | `ax.plot_surface` on a 3D axes with `viridis` shading; sample trajectory lines projected onto the surface in red; ball markers at start/end; camera set to ~30° elevation, -60° azimuth for the classical Waddington view. | Same 2D grid data as existing `potential_landscape_2d_heatmap` + optional trajectories as `list[np.ndarray]`. |
| 4 | `excitability_threshold_diagram` | What distinguishes sub-threshold (decays) from super-threshold (large excursion) perturbations of a stable resting state? | new per-recipe `ExcitabilityInput` (Pydantic) | `x_grid`, `y_grid`, `u`, `v`, `rest_point`, `saddle_point`, `stable_manifold`, `unstable_manifold`, `sub_threshold_traj`, `super_threshold_traj` | `nullclines` (x and y), `title` | `phase_portrait_oscillator` | Excitable ≠ oscillatory. Excitability needs a rest + a saddle + the saddle's stable manifold (the threshold *separatrix*). The distinguishing visual is a pair of trajectories from nearly-identical ICs, one that decays back to rest and one that loops around the slow manifold before returning. No current recipe captures this. | Streamplot backdrop; saddle's stable manifold drawn in dark grey as the *threshold*; two sample trajectories in contrasting colors (blue = sub, red = super) from closely-spaced ICs; annotation box reads "threshold (stable manifold of saddle)". | Phase-plane arrays plus two trajectory arrays. Typical grid 50×50; trajectories 500-2000 pts. |
| 5 | `slow_manifold_projection` | How do fast trajectories geometrically collapse onto the slow invariant manifold in phase space? | new per-recipe `SlowManifoldInput` (Pydantic) | `x_grid`, `y_grid`, `u`, `v`, `slow_manifold_curve` (xs, ys), `fast_trajectories` (list of (x(t), y(t)) arrays) | `epsilon` (timescale ratio), `title` | `quasi_steady_state_reduction` (time-series) | The existing QSS recipe plots `x_full(t)` vs `x_reduced(t)` — a temporal comparison. The slow-manifold recipe is *geometric*: it shows the curve of the slow manifold in the (x, y) plane, with fast trajectories sweeping in orthogonal to the manifold and then sliding along it. These answer fundamentally different questions. | Streamplot backdrop muted; the slow manifold drawn as a thick continuous green-amber curve labeled `y = g(x) (slow manifold)`; 6-10 fast-trajectory threads in faint blue showing the rapid approach + slow slide; arrowheads midway indicating direction. ε value in a stat callout pill. | Grid fields + per-trajectory xy arrays. Grid ≥50×50; ≥6 trajectories. |
| 6 | `poincare_first_return_map` | For a limit-cycle system, what is the first-return map `x_{n+1} = P(x_n)` on a Poincaré section, and what fixed points / periodic orbits does it reveal? | new per-recipe `ReturnMapInput` (Pydantic) | `x_n`, `x_n_plus_1`, `section_description` (str) | `cobweb_trajectory` (list of (x_n, x_{n+1}) pairs from iterating an IC), `fit_line` (dict with slope, intercept), `title` | *(no alternative in roster — this is a new discrete-dynamics axis)* | The only discrete-time recipe in the modality. Return maps compress continuous-time limit-cycle stability into 1D discrete dynamics; they expose period-doubling cascades / chaos routes that continuous phase portraits cannot. Orthogonal visual vocabulary. | Scatter or line of `(x_n, x_{n+1})`; diagonal `y = x` reference in grey dashed; cobweb stepping in red arrows from an IC; fixed points of the map (where the scatter meets diagonal) highlighted as filled/hollow dots per stability. | `x_n`, `x_{n+1}` paired floats (typically 500-5000 Poincaré crossings). |

## Contract additions

All 6 recipes use **new per-recipe Pydantic contracts** local to their own `.py` file (the established pattern across v1.0 recipes). **No changes required to `core/contract.py`**. This keeps v1.1's core-architecture-frozen invariant trivially satisfied for this session.

## Family tags

All 6 map onto existing `RecipeFamily` enum values — no new quality-rule families needed:

| Recipe | Family tag |
|---|---|
| `phase_portrait_with_trajectories` | `phase_portrait` |
| `codim2_bifurcation_map` | `bifurcation` |
| `potential_landscape_waddington_3d` | `heatmap` (3D surface still satisfies the "needs an image/mesh surface" quality rule) |
| `excitability_threshold_diagram` | `phase_portrait` |
| `slow_manifold_projection` | `phase_portrait` |
| `poincare_first_return_map` | `diagnostic_curve` |

## Implementation plan (Commit 2, pending approval)

1. Add 6 new recipe files under `src/panelforge_figures/recipes/rhogtpase_dynamics/`.
2. Extend `__init__.py` to import and expose them.
3. No touches to `_aesthetic.py` — the existing Tyson/Novák visual DNA (`home_gate_trap` palette, filled/hollow fixed-point convention, streamplot+nullcline grammar) covers all 6 without modification.
4. Each recipe ≥ 80 lines, honors `AESTHETIC.apply_to_ax`, includes realistic `demo_contract()`.
5. Regenerate the 6 new gallery PNGs via `figures gallery regenerate --modality rhogtpase_dynamics`.
6. Update `docs/recipes_by_modality.md` + `docs/recipes_by_question.md` via catalog regeneration.

## Test impact

Expected test count increase: **+18** (6 recipes × 3 layers: smoke + quality + cross-modality QA). Aesthetic-compliance tests are per-recipe at import-time — add 6 more. Style-drift ceiling (20 distinct fontsize literals) stays inside with room.

Current test count: **736**. Projected after this session: **754**.

---

## STOP — awaiting user approval

> **Please review the 6 proposed recipes above and reply with one of:**
>
> - **"approved"** — I will proceed to Commit 2 (implementation) with the exact roster above.
> - **"approved with changes: …"** — list any edits (rename, swap, adjust scope) and I will proceed with the revised roster.
> - **"rejected"** — I will revise the gap analysis and re-propose.
>
> No recipe code will be written until this approval step completes.
