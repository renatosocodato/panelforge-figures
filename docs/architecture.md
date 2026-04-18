# Architecture

## Three layers

### Core (`src/panelforge_figures/core/`)

The shared, modality-agnostic substrate. Every recipe reaches into core —
no recipe should reach into another modality.

- `style.py` — rcParams baseline (Helvetica stack, 600-dpi savefig, spines
  left/bottom, outward ticks, `pdf.fonttype = 42`).
- `palette.py` — 13 registered palettes with semantic lookups.
- `primitives.py` — halo'd labels, smart_fmt, right-of-CI label placement,
  colored bracket markers, density-alpha scatter, 400-resample bootstrap
  CI bands, violin + ring markers, phase-portrait decorators.
- `layout.py` — 8 figure-size presets + panel gridspec + panel tagging
  + suptitle/subtitle helper.
- `export.py` — multi-format PDF/PNG/SVG export.
- `contract.py` — pydantic `RecipeContract` base, `RecipeMetadata`,
  `RecipeFamily` enum, global registry + `@register_recipe` decorator.
- `aesthetic_base.py` — abstract `ModalityAesthetic` contract.

### Modality (`src/panelforge_figures/recipes/<modality>/`)

One Python subpackage per scientific domain. Each holds:

- `_aesthetic.py` — **defines the modality's visual DNA** as
  `AESTHETIC: ModalityAesthetic`. Encodes which palette this domain
  uses, what continuous colormap it prefers, whether its figures
  need scale bars, whether it has conventional insets, etc.
- `__init__.py` — calls `register_modality(...)` with a description and
  the `AESTHETIC` instance, then imports every recipe module so their
  `@register_recipe` decorators fire.
- One `.py` file per recipe — each defines its own pydantic contract,
  a `_demo()` function returning a realistic synthetic contract, and a
  single `render(contract, ax=None, **_)` function decorated with
  `@register_recipe(...)`.

### Theme (`src/panelforge_figures/themes/`)

Per-venue rcParams overlays (Nature, Cell, PNAS, Dev Cell, BPJ, Neuron,
NCB, STTT, Trends, FCT grant, Horizon Europe, plus a `default`).
Themes never override modality aesthetics — they tune labels, axes,
line weights per venue.

## Data flow for one figure

```
figures.manifest.yaml
    │
    ▼
manifest/schema.py  ← pydantic validation
    │
    ▼
manifest/resolver.py
    │
    ├── adapter (tabular | numpy_npz | pandas_pickle | passthrough | local.*)
    ├── transforms (melt_long, pivot_wide, aggregate_group, …)
    │
    ▼
recipe contract (pydantic)
    │
    ▼
recipe.render(contract, ax=…)
    │
    ├── AESTHETIC.apply_to_ax(ax)        ← modality DNA
    ├── apply_base_style() + theme()     ← core + venue
    └── primitives + palette              ← shared craft
    │
    ▼
multi_format_export → PDF/PNG/SVG at 600 dpi
```

## The four commitments

1. **Modality-first recipes.** Recipe names describe the scientific claim
   they visualize, not the shape they draw. `bistability_hysteresis`,
   not `xy_plot_with_arrows`. Shapes live in primitives.

2. **Per-modality visual DNA.** Every recipe in a modality imports and
   applies its modality's `_aesthetic.py` on every call. The aesthetic
   compliance test AST-inspects every recipe to confirm this happens.

3. **Gallery as CI artifact.** On every PR, `figures gallery regenerate`
   produces a PNG per recipe. A diff against the committed gallery flags
   drift; humans review before accepting.

4. **The bootstrap skill proposes with justification.** When surveying
   an unfamiliar manuscript repo, the skill reads the catalog (with every
   recipe's `answers_question` and `alternatives_in_modality`) and shows
   the user *why* it picked each recipe versus others in the same
   modality. Generic fallbacks are flagged loudly; they are never silent.

## Quality gate

Three layers of test over the registry:

- `test_recipes_smoke.py` — every recipe's `demo_contract()` renders
  without exception.
- `test_recipes_quality.py` — per-family geometric invariants
  (e.g., sobol_bar recipes must contain ≥3 bar-or-scatter marks + ≥3
  numeric annotations; gantt must contain ≥3 task bars + ≥1 milestone
  marker; radar must live on a polar axis with ≥2 drawn objects).
- `test_aesthetic_compliance.py` — every recipe source imports from
  `._aesthetic` and calls `AESTHETIC.apply_to_ax`/`apply_to_fig`.

CI fails if any of these regresses. This is what makes every recipe
ship at a consistent fidelity, not just 18 things that happen to render.
