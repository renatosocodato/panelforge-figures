# panelforge-figures

A modality-first, publication-grade figure system for systems biology and
computational biophysics, with an embedded Claude Code skill for agentic
bootstrap inside any manuscript repository.

## Status

`v1.0.0` stable; `v1.1.0-s14` in progress — 20 modalities, 271
recipes, CI-enforced typography + figure-integrity contract, 1406
passing tests. The v1.1 hydration plan (see
`docs/hydration_coordinator.md`) grows the catalogue to 320+ recipes
across 20 user-gated sessions.

| | 0.1.0a0 | 0.1.0b1 | 0.1.0b2 | 0.1.0b3 | **v1.0.0** |
|---|---|---|---|---|---|
| Modalities | 3 | 7 | 11 | 15 | **20** ✓ |
| Recipes | 18 | 49 | 80 | 107 | **137** ✓ |
| Gallery PNGs | 18 | 49 | 80 | 107 | **137** ✓ |
| Themes | 12 | 12 | 12 | 12 | **12** |
| Tests | 113 | 237 | 361 | 469 | **736** |

## Install

From this repo:

```bash
pip install git+https://github.com/renatosocodato/panelforge-figures.git
```

For development:

```bash
git clone https://github.com/renatosocodato/panelforge-figures.git
cd panelforge-figures
pip install -e .[dev]
```

## Quick start (end-user workflow)

1. `cd` into any manuscript repo.
2. Run `claude`.
3. Ask Claude to use the `panelforge-figures` skill.
4. Claude surveys the repo, proposes a figure plan **with justifications against
   alternatives in the same modality**, gets your approval, writes
   `figures.manifest.yaml` plus any local adapters, and runs the first render.
5. From then on, re-renders are agent-free:

```bash
figures render figures.manifest.yaml
```

## CLI

```
figures render      [MANIFEST]           # render all figures per manifest
figures validate    [MANIFEST]           # validate schema + data availability
figures catalog     [--json] [--by modality]
figures list-recipes [--by-modality] [--family FAMILY]
figures list-adapters
figures list-themes
figures list-palettes
figures gallery regenerate
figures gallery diff
figures show-recipe NAME
figures show-modality NAME
figures version
```

## Design commitments

1. **Modality-first recipes.** Recipe names describe the claim they visualize
   (`bistability_hysteresis`, `sex_stratified_cvvelocity`), not the shapes they
   draw.
2. **Per-modality visual DNA.** Each modality module defines an `_aesthetic.py`
   that every recipe inside the modality honors. CI enforces this.
3. **Gallery as CI artifact.** Every recipe ships a committed example PNG in
   `docs/gallery/<modality>/<recipe>.png`, regenerated on every PR and diffed
   for aesthetic drift.
4. **The bootstrap skill proposes with justification.** For every recipe it
   picks, it names at least one alternative in the same modality and explains
   why it was rejected. Any generic fallback is loudly flagged.

## Documentation

See `docs/` for:

- `architecture.md` — the core / modality / aesthetic layering
- `recipes_by_modality.md` — every recipe grouped by scientific domain
- `recipes_by_question.md` — every recipe grouped by the claim it supports
- `manifest_schema.md`
- `adding_a_recipe.md`, `adding_a_modality.md`
- `themes.md`, `palettes.md`, `adapters.md`

## Roadmap

See `CHANGELOG.md`. All 20 modalities from the initial roster landed
by v0.1.0:

`grant_and_conceptual`, `meta_and_diagnostic`, `sensitivity_analysis`,
`mixed_effects_models`, `dose_response_pharmacology`, `biophysics_scaling`,
`rhogtpase_dynamics`, `gillespie_stochastic`, `redox_imaging`,
`fret_biosensors`, `calcium_signaling`, `omics_differential`,
`single_cell_embeddings`, `network_and_pathway`, `diffusion_and_tracking`,
`spatial_statistics`, `clinical_cohort`, `cryoem_and_structure`,
`intravital_imaging`, `actin_microtubule_morphometry`.

## License

MIT — see `LICENSE`.
