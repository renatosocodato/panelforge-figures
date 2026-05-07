# panelforge-figures v2.0.0 roadmap

8 elevations covering the conceptual + execution-wise gap between
v1.6.1 (system architecture shipped + production-grade for solo
research) and v2.0.0 (elite Claude-Code-dependent repo usage with
universal translatability across manuscript, research, and modeling
projects).

This document is the **index of executable scoping specs**.  Each
spec is a self-contained doc that the Phase-2 execution swarms
implement against, in the order shown below.

## Sprint sequencing (high → low project leverage)

| Sprint | Elevation | Spec | Target version | PR |
|---|---|---|---|---|
| **1A** (HIGH) | #2 Statistical contract | [`spec_statistical_contract.md`](spec_statistical_contract.md) | v1.7.0 | #61 |
| **1B** (HIGH) | #3 Provenance chain | [`spec_provenance_chain.md`](spec_provenance_chain.md) | v1.8.0 | #62 |
| **1C** (HIGH) | #1 Composition layer | [`spec_composition_layer.md`](spec_composition_layer.md) | v1.9.0 | #63 |
| **2A** (MEDIUM) | #4 Project plugins | [`spec_project_plugins.md`](spec_project_plugins.md) | v1.10.0 | #64 |
| **2B** (MEDIUM) | #8 Data-class safety | [`spec_data_class_safety.md`](spec_data_class_safety.md) | v1.11.0 | #65 |
| **2C** (MEDIUM) | #5 Vision input | [`spec_vision_input.md`](spec_vision_input.md) | v1.12.0 | #66 |
| **3A** (LOW) | #7 Cross-project orchestration | [`spec_cross_project.md`](spec_cross_project.md) | v1.13.0 | #67 |
| **3B** (LOW) | #6 Active learning | [`spec_active_learning.md`](spec_active_learning.md) | v1.14.0 | #68 |
| **3C** | Cross-cutting integration | (this PR + integration PR) | **v2.0.0** | #69 |

## Why this order

The 3-tier sequencing reflects **leverage for a solo scientific
researcher juggling biophysics + microglial-surveillance + multi-omic
+ clinical-cohort projects** (the system's primary user profile):

- **Sprint 1 (HIGH)**: every figure today is at risk of being mis-
  rendered (no statistical contract), unverifiable (no provenance),
  or one-panel-only (no composition).  These three are the
  category-defining differentiators.
- **Sprint 2 (MEDIUM)**: extensibility (#4 plugins), trust-mode
  defaults (#8 data-class), and modality-mismatched user input
  (#5 vision) — all unblock specific use cases but the system works
  without them.
- **Sprint 3 (LOW)**: portfolio-scale features (#7 cross-project,
  #6 active learning) need user-base scale before they pay off.

## Cross-cutting integration risks

- **#3 provenance + #6 active learning**: telemetry must NOT include
  source-data hashes the user opted out of via `data_class:
  clinical` (#8).
- **#5 vision input + #8 data-class**: vision API calls disabled in
  clinical mode; document in shared privacy block.
- **#1 composition + #2 statistical contract**: composed figures
  inherit the strictest contract among their panels.
- **#4 plugins + #2 statistical contract**: plugin recipes MUST
  declare their own contracts; default-permissive is OK but the
  audit-pipeline must walk plugin contracts identically.

These risks are tracked in the Phase-3 integration PR (#69) which
ships after sprints 1+2+3 land.

## Acceptance criterion for v2.0.0

After all 8 PRs + integration PR merge:

1. **Statistical rigor**: a recipe with 3-cell-per-group input is
   refused at audit time, not silently rendered.
2. **Reproducibility**: every committed figure has a sidecar
   `provenance.json` whose hashes match the registered data + recipe
   bytes; `figures provenance verify` is bit-identical against a
   fresh checkout.
3. **Composition**: a 6-panel "Figure 3" can be declared as a single
   `figure.yaml` and rendered to one PDF.
4. **Extensibility**: a project-local plugin extends the catalog
   without forking; `figures plugins list` discovers it.
5. **Safety**: `data_class: clinical` disables LLM Pass-3, vision
   API, and telemetry by enforcement (not by convention); column
   names containing `mrn`/`patient_dob` etc. trigger an audit.
6. **Vision**: a reference figure PNG produces a pre-filled intake
   profile that scores top-1 within the same wave-pack as the
   reference.
7. **Portfolio**: 4 registered projects produce a coherent
   `figures projects diff` showing recipe-overlap and uniques.
8. **Continuous learning**: opt-in telemetry of 1000 sessions
   produces deterministic suggested-weight adjustments.

## Total projected scope

- **8 specs** (this PR; ~23,000 words; ~178 KB).
- **9 implementation PRs** (sprints 1-3 + integration).
- **~3000 LOC** of new code across `src/panelforge_figures/manifest/`,
  `src/panelforge_figures/safety/`, `src/panelforge_figures/projects/`,
  `src/panelforge_figures/plugins/`.
- **~1500 LOC** of new tests + ~12 new fixture directories.
- **2587 → ~2900** total tests (estimated +313 from 8 elevations).
- Style-drift ratchet held at 20/20 throughout.
- ~6-8 working days of swarm execution.

## Execution model

Same multi-agent swarm pattern that delivered v1.6.0 + v1.6.1:

- **1 Soak-Agent per PR** verifying the prior PR's output in
  production conditions.
- **2-3 Build-Agents per PR** on disjoint files.
- **3-commit pattern** per PR (gap-analysis → implementation →
  gallery + polish).
- **Same CI gates**: pytest (no skips), ruff, drift check, gallery
  regen, style-drift ratchet, schema validation.

After v2.0.0 ships, the system is **category-defining**: no other
scientific plotting library does (statistical contract +
provenance + composition).  The trio is the elevation that takes
panelforge-figures from "production-ready tool" to "the visualisation
layer the open-science research stack didn't know it needed."
