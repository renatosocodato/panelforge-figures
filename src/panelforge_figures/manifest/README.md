# `panelforge_figures.manifest` — package map

`manifest/` is the largest package in panelforge-figures (~42 modules). It sits
**downstream of `core/` and `recipes/`** in the dependency layering: it reads the
recipe registry (populated by `core.contract.ensure_all_imported`) and turns it
into a discovery, rendering, provenance, and pre-submission-audit pipeline. It
never registers recipes itself.

This README is an in-package index. For the design rationale behind each
subsystem (and the honest list of trade-offs), read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.
Cross-subsystem calls inside `manifest/` are almost all **lazy imports** so each
module stays independently importable before its dependencies exist.

---

## Subsystems at a glance

| Subsystem | Modules | What it does |
|---|---|---|
| **Discovery** | `scoring`, `tag_taxonomy`, `auto_tag`, `catalog`, `intake`, `project_scan` | Score recipes against a project profile, tag them, emit the agent-facing JSON index, run the 8-question intake. |
| **Recommendation** | `family_recommender`, `novelty_scout`, `scout` | Read-only advisory pipelines: figure-family suggestions, literature-novelty classification, multi-figure narrative plan. |
| **Databind / render** | `data_bridge`, `resolver`, `render_loop`, `render_cache`, `figure_composition`, `figure_schema` | Bind data files to contracts, drive the per-recipe render loop, compose multi-panel figures, short-circuit re-renders via a sha-keyed cache. |
| **Stats / provenance** | `statistical_audit`, `provenance`, `reproducibility`, `power`, `power_families` | Pre-render statistical gate, content-addressed provenance sidecars, reproducibility lockfiles, power analysis. |
| **Manuscript** | `execute_plan`, `manuscript_parse`, `manuscript_collision`, `manuscript_scaffold`, `manuscript_blueprint`, `manuscript_alignment` | Orchestrate scaffold → render → caption → manuscript; parse, reconcile, and inverse-import manuscripts. |
| **Auditors** | the 10 listed below | Best-effort, mostly non-mutating Pass/Warn/Fail reports read from provenance sidecars + parsed manuscript. |
| **Extensibility / learning** | `recipe_authoring`, `vision_input`, `telemetry`, `weight_calibration` | Scaffold new recipes, seed intake from reference figures, opt-in telemetry, offline weight calibration. |

---

## Two core flows

### bind → render → cache → compose

```
data files ──► data_bridge ──► (contract fields bound)
                  │
                  ▼
            render_loop ──► get_recipe(name).render(contract, ax)
                  │                 │
                  │                 ├──► provenance sidecar (provenance.py)
                  │                 └──► statistical_audit (pre-render gate)
                  ▼
            render_cache (sha-keyed: recipe-source + contract + data)
                  │  fresh? skip : re-render
                  ▼
         figure_composition ──► multi-panel Figure from a YAML FigureSpec
                                 (all-or-nothing; reuses the render core)
```

### discovery → recommendation

```
project dir ──► project_scan ──► intake (8 questions) ──► ProjectProfile
                                                              │
                  registry (core.contract) ──► scoring ──► ScoredRecipe shortlist
                                                              │
                                          ┌───────────────────┴───────────────────┐
                                          ▼                                        ▼
                            family_recommender / novelty_scout            catalog.emit_index_json
                                          │                                (agent-facing recipes_index.json)
                                          ▼
                                       scout ──► ProjectScoutReport (YAML plan, human-approved)
```

---

## The 10 auditors

Each is independent, best-effort, reads the per-figure `<figure>.provenance.json`
sidecar (an implicit, un-typed cross-module contract), and emits a structured
report. `ci_runner` is the integration hub that lazy-imports the others and maps
each bespoke verdict onto a common `StepStatus`. None of the ten is re-exported
from `manifest/__init__.py` (kept import-cheap).

| Module | Elevation | CLI verb | Purpose |
|---|---|---|---|
| `venue_auditor` | E16 | `figures audit-venue` | Audit a manuscript + figures package against a target venue's locked rules (incl. a pixel-based color-blind check). |
| `bias_auditor` | E17 | `figures audit-bias` | Flag visualization-honesty defects encoded in the recipe/audit metadata (never inspects pixels). |
| `xref_linter` | E13 | `figures lint xrefs` | Lint figure cross-references (missing/duplicate/out-of-order). |
| `claim_check` | E2 | `figures verify-claims` | Extract "Figure N shows X" sentences and verify them against the audit; three-valued (SUPPORTED / UNSUPPORTED / UNVERIFIABLE). |
| `caption` | — | `figures caption` | Emit markdown caption stubs per figure from the audit + contract. |
| `citation_inserter` | E14 | `figures cite suggest` | The only mutating auditor: insert citations from the Consensus cache (always backs up to `.bak`, refuses to double-cite). |
| `star_methods` | E12 | `figures star-methods` | Generate STAR Methods scaffolding (Cell/Nature/Science/eLife). |
| `reporting_checklists` | E12 | `figures checklist <name>` | Emit ARRIVE / CONSORT / STARD / MIQE reporting checklists. |
| `status_dashboard` | E20 | `figures status` | Single-screen reproducibility / audit status overview. |
| `ci_runner` | — | `figures ci-audit` | Run the canonical audit chain in one sandboxed pass; `skip_missing_inputs` so early-phase projects run green. |

---

## Vocabulary glossary

The codebase was built as a sequence of numbered build steps by separate "build
agents." These labels recur in docstrings and are otherwise undefined:

- **Elevation (E*N*)** — a numbered capability increment (e.g. E16 = venue
  auditor, E17 = bias auditor). The primary unit of feature growth. "E-number"
  and "Elevation N" are the same thing.
- **Sprint (e.g. Sprint 1A, Sprint 2A)** — an earlier-era grouping of build work,
  used mainly in `provenance`, `plugins`, and `projects`. Predates the Elevation
  numbering.
- **Wave** — a release-cohort tag in the closed `TagWave` taxonomy
  (`tag_taxonomy.py`), e.g. `v1.2.0-beta-actin_microtubule_morphometry`. Used by
  the auto-tagger and the deterministic tie-break sort, **not** a build-process
  label like Elevation/Sprint.
- **`_demo()` / demo contract** — every recipe ships a zero-external-data
  contract instance so it is runnable for smoke tests and the MCP server.

The Elevation/Sprint labels are otherwise only resolved in the spec docs below.

---

## Specs that exist (`docs/`)

These modules cite spec documents; the ones that exist in `docs/`:

- [`spec_statistical_contract.md`](../../../docs/spec_statistical_contract.md) — `statistical_audit`, `core.statistical_contract`
- [`spec_provenance_chain.md`](../../../docs/spec_provenance_chain.md) — `provenance`, `reproducibility`
- [`spec_composition_layer.md`](../../../docs/spec_composition_layer.md) — `figure_composition`, `figure_schema`
- [`spec_vision_input.md`](../../../docs/spec_vision_input.md) — `vision_input`
- [`spec_active_learning.md`](../../../docs/spec_active_learning.md) — `telemetry`, `weight_calibration`
- [`spec_cross_project.md`](../../../docs/spec_cross_project.md) — the sibling `projects/` package
- [`spec_project_plugins.md`](../../../docs/spec_project_plugins.md) — the sibling `plugins/` package
- [`spec_data_class_safety.md`](../../../docs/spec_data_class_safety.md) — the `safety/` gates consulted here

Other modules reference `docs/spec_*.md` files (e.g. `spec_manuscript_collision.md`,
`spec_figure_bias_auditor.md`) that are **not** present in this tree — treat those
citations as historical until the specs land.
