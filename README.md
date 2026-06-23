# panelforge-figures

[![PyPI version](https://img.shields.io/pypi/v/panelforge-figures.svg)](https://pypi.org/project/panelforge-figures/)
[![Python versions](https://img.shields.io/pypi/pyversions/panelforge-figures.svg)](https://pypi.org/project/panelforge-figures/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20811170.svg)](https://doi.org/10.5281/zenodo.20811170)

A modality-first, publication-grade figure system for systems biology and
computational biophysics, with an embedded Claude Code skill for agentic
bootstrap inside any manuscript repository.

> 🤖 **Are you a CLI agent on first contact with this repo?** Read
> [`AGENT_BOOTSTRAP.md`](https://github.com/renatosocodato/panelforge-figures/blob/main/AGENT_BOOTSTRAP.md)
> — it tells you how to fetch
> [`recipes_index.json`](https://github.com/renatosocodato/panelforge-figures/blob/main/recipes_index.json)
> from raw GitHub without cloning, locate the recipes you need, and
> sparse-checkout only the modalities relevant to the user's project.

## Status

**`v2.0.0` — eight-elevation release**: 20 modalities, **448 recipes**,
CI-enforced typography + figure-integrity contract, **2895 passing
tests**. v2.0.0 turns the v1.6.1 recipe-discovery system into an
elite Claude-Code-dependent platform via 8 architectural elevations:
statistical contract → provenance → composition → plugins →
data-class safety → vision input → cross-project orchestration →
active-learning loop. Privacy-by-construction throughout (telemetry
off by default, never auto-uploaded; clinical data class blocks all
LLM/vision/telemetry channels). The 448-recipe catalog is
agent-discoverable via
[`recipes_index.json`](https://github.com/renatosocodato/panelforge-figures/blob/main/recipes_index.json)
+ [`AGENT_BOOTSTRAP.md`](https://github.com/renatosocodato/panelforge-figures/blob/main/AGENT_BOOTSTRAP.md)
— a CLI agent on a manuscript repo can fetch the index from raw
GitHub (no clone), score recipes via natural-language intake, and
render publication-grade PNGs end-to-end. Claude Code agents can use
[`CLAUDE_CODE_AUTONOMOUS.md`](https://github.com/renatosocodato/panelforge-figures/blob/main/CLAUDE_CODE_AUTONOMOUS.md)
for fully autonomous runs (Anthropic SDK harness with prompt-caching).
New to the system? Start with the
[`docs/AGENT_RECIPES.md`](https://github.com/renatosocodato/panelforge-figures/blob/main/docs/AGENT_RECIPES.md)
tutorial.

| | 0.1.0a0 | 0.1.0b1 | 0.1.0b2 | 0.1.0b3 | v1.0.0 | v1.5.0 | v1.6.0 | **v2.0.0** |
|---|---|---|---|---|---|---|---|---|
| Modalities | 3 | 7 | 11 | 15 | 20 | 20 | 20 | **20** |
| Recipes | 18 | 49 | 80 | 107 | 137 | 448 | 448 | **448** |
| Gallery PNGs | 18 | 49 | 80 | 107 | 137 | 448 | 448 | **448** |
| Themes | 12 | 12 | 12 | 12 | 12 | 12 | 12 | **12** |
| Tests | 113 | 237 | 361 | 469 | 736 | 2356 | ~2600 | **2895** |
| Agent-discoverable | — | — | — | — | — | — | yes ✓ | yes ✓ |
| 8 elevations | — | — | — | — | — | — | — | **yes** ✓ |

## Install

```bash
# Standard install
pip install panelforge-figures

# With seaborn for split-violin recipes
pip install panelforge-figures[seaborn]

# With autonomous Claude Code flow (Anthropic SDK)
pip install panelforge-figures[claude-autonomous]

# Development install (from source)
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

## Citation

If you use panelforge-figures in published work, please cite the archived
software release. GitHub renders [`CITATION.cff`](CITATION.cff) as a
**"Cite this repository"** button in the sidebar.

The software is permanently archived on Zenodo. The citable form is:

> Socodato, R. *panelforge-figures* (v3.14.1). Zenodo (2026).
> doi:[10.5281/zenodo.20811171](https://doi.org/10.5281/zenodo.20811171)

- **Version DOI** (cite v3.14.1 specifically): [`10.5281/zenodo.20811171`](https://doi.org/10.5281/zenodo.20811171)
- **Concept DOI** (always resolves to the latest release): [`10.5281/zenodo.20811170`](https://doi.org/10.5281/zenodo.20811170)

```bibtex
@software{socodato_panelforge_figures_2026,
  author    = {Socodato, Renato},
  title     = {panelforge-figures},
  version   = {3.14.1},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20811171},
  url       = {https://doi.org/10.5281/zenodo.20811171}
}
```

## License

MIT — see `LICENSE`.
