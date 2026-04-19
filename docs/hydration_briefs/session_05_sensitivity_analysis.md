# Session 05 — `sensitivity_analysis` (8 → 15, +7)

Run the v1.1 hydration session template from
[`docs/hydration_brief.md`](../hydration_brief.md) with these parameters:

- `MODALITY`: `sensitivity_analysis`
- `SESSION_NUM`: `05`
- `V10_COUNT`: 8
- `V11_TARGET`: 15
- `PRIORITY_CONTEXT`: Manuscript 3 Box 1 uses this heavily.
  Sobol-dominant. Must support FAST, Morris, and LHS workflows.

## Seed list

- `fast_sensitivity_spectrum` — FAST (Fourier Amplitude Sensitivity Test) power spectrum
- `lhs_parameter_space_coverage` — Latin hypercube sample visualization
- `tornado_diagram` — classic tornado one-at-a-time sensitivity
- `sensitivity_by_output_quantity` — matrix of indices across multiple outputs
- `sobol_bootstrap_convergence` — S1 convergence as sample count grows
- `interaction_network_sobol` — graph of parameter interactions with edge weights
- `sensitivity_time_evolution` — sensitivity indices as a function of output time

Follow the Part 2 template exactly. Do not modify any other modality.
