# Composition layer — multi-panel figure grammar

**Status:** proposal
**Version target:** v1.7.0
**Author:** _(W1 swarm scribe; placeholder for v2.0.0 owner)_
**Plan file:** _(to be assigned)_
**Spec siblings:** `docs/spec_*.md` (parallel v2.0.0 elevations)

**TL;DR.** v1.6.1 ships 448 single-panel recipes — each `render(contract, ax)` paints exactly one matplotlib axes. A real "Figure 3" in a paper has 4–6 panels, shared aesthetic, often a linked y-axis, and a panel-letter overlay (A/B/C). Today that requires 4–6 separate `figures generate` invocations plus a manual `gridspec` assembly in user code. This spec proposes a **composition layer** that elevates the unit of work from "one panel" to "one figure": a `panelforge.figure.yaml` schema declares a graph of recipes; a new `compose_figure(spec)` function in `manifest/render_loop.py` assembles them into a single PDF via matplotlib `gridspec`, propagates a shared aesthetic, and links axes when requested. The CLI gains `figures compose <figure.yaml>` (single), `figures compose-all` (sweep), and `figures compose-validate` (schema + recipe-existence dry-check).

---

## 1. Why now — the problem statement

The recipe catalog has matured to **448 recipes** across 19 modalities (post-PR #59). Recipes are individually publication-grade, but the manuscript-companion packs (`disc1_manuscript_companion`, `cdc42_factorial_companion`) have surfaced three concrete pain points:

1. **Multi-panel orchestration is manual.** A six-panel Figure 3 means: six manifest entries, six `figures generate` calls, six PDFs, then a hand-rolled `matplotlib.gridspec.GridSpec` notebook that re-imports the recipe modules and re-renders the panels into a shared `Figure`. The recipes themselves are reusable; the multi-panel assembly is not. Each manuscript reinvents the layout glue.
2. **No grammar exists for "tile this recipe by tag".** The CDC42 paper has a 2 × 2 factorial (sex × genotype) where the same `coef_forest` recipe wants to render once per factorial cell. There is no first-class way to express _partition this contract by `tags.sex`, then by `tags.genotype`, and emit four panels into a 2 × 2 grid_.
3. **Aesthetic and axis linking are ad-hoc.** When two scatter panels in the same figure should share a y-axis (so a reader's eye registers magnitude differences), the user must subclass the recipe or post-edit the saved PDF. Likewise, propagating a single palette / theme override across all panels of a figure currently requires editing each manifest entry.

The composition layer makes the **figure** — not the panel — the named, versioned, reproducible artefact. Recipes remain unchanged.

---

## 2. YAML schema — `panelforge.figure.yaml`

The figure spec sits alongside (not inside) `figures.manifest.yaml`. One file per figure; canonical filename ends `.figure.yaml`. Loaded by `figure_schema.load_figure_spec(path)`.

### 2.1 Top-level fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `figure_id` | string | yes | Stable identifier; used in PDF metadata + log lines. |
| `title` | string | no | Suptitle for the rendered figure. |
| `caption` | string | no | Long-form caption; written into PDF XMP metadata + sidecar `<id>.caption.txt`. |
| `output_path` | path | no | Defaults to `figures/<figure_id>.pdf`. |
| `layout` | object | yes | One of `grid`, `gridspec`, or `freeform` (mutually exclusive). |
| `shared_aesthetic` | string | no | Modality name; the modality's aesthetic block applies to every panel that doesn't override locally. |
| `panel_label_style` | object | no | Controls A/B/C overlays. See §2.4. |
| `panels` | list | yes | Panel specs; see §2.3. Required unless `partition_by` declared at figure scope. |
| `partition_by` | object | no | Auto-tile a single recipe by tag values; see §2.5. |
| `theme` | string | no | Theme name; defaults to inherited manifest theme. |
| `palette` | string | no | Palette name; defaults to inherited manifest palette. |

### 2.2 `layout` — three mutually exclusive variants

```yaml
# variant A — regular grid
layout:
  kind: grid
  rows: 3
  cols: 2
  hspace: 0.4   # optional
  wspace: 0.3   # optional
  width_ratios:  [1.0, 1.0]   # optional, defaults uniform
  height_ratios: [1.0, 1.0, 1.0]

# variant B — explicit gridspec for non-uniform layouts
layout:
  kind: gridspec
  rows: 3
  cols: 4
  cells:
    A: {row: 0, col: 0, rowspan: 1, colspan: 4}   # full top row
    B: {row: 1, col: 0, rowspan: 2, colspan: 1}   # left column
    C: {row: 1, col: 1, rowspan: 1, colspan: 3}
    D: {row: 2, col: 1, rowspan: 1, colspan: 3}

# variant C — freeform absolute placement
layout:
  kind: freeform
  figsize: [12, 8]   # inches
  # each panel must declare its own bbox in panels[].position
```

### 2.3 `panels` — per-panel spec

Each panel is a node in the figure graph:

```yaml
panels:
  - id: A
    recipe: meta_and_diagnostic.bayes_factor_arrow_plot
    data:
      source: data/disc1_bf_rows.csv
      adapter: tabular
    caption: "Bayesian evidence per descriptor"
    options: {}                          # forwarded to recipe contract
    shared_axis_with: B                  # optional — link y-axis to panel B
    shared_axis_kind: y                  # 'x' | 'y' | 'both'; default 'y'
    aesthetic_overrides: {}              # optional override of figure-level shared_aesthetic
    position: [0.05, 0.55, 0.4, 0.4]     # required only when layout.kind == freeform
```

Required: `id`, `recipe`, `data`. Reuses `manifest.schema.DataSpec` verbatim — no new data abstractions.

### 2.4 `panel_label_style`

```yaml
panel_label_style:
  enabled: true
  case: upper            # upper | lower
  position: top-left     # top-left | top-right | bottom-left | bottom-right
  offset: [-0.08, 1.05]  # axes-fraction units
  fontweight: bold
  fontsize: 11
```

Defaults match the prevailing house style: bold, top-left, 11pt, axes-fraction `(-0.08, 1.05)`.

### 2.5 `partition_by` — auto-tiling

For factorial figures, declare one recipe and partition by tag values. Each tag value yields one panel; panels are placed left-to-right, top-to-bottom into the declared `layout`.

```yaml
partition_by:
  recipe: mixed_effects_models.two_way_anova_summary_plot
  data:
    source: data/cdc42_anova_long.csv
  by:
    - tags.sex          # outer partition (rows)
    - tags.genotype     # inner partition (cols)
  panel_label_template: "{sex_value} {genotype_value}"
```

When `partition_by` is set, `panels` is populated synthetically at load time; the user may NOT also declare `panels`. Cardinality is checked: if `len(by_outer) * len(by_inner) > 12`, the loader raises `PartitionTooLarge` (see §9 risks).

---

## 3. Worked examples (3)

### 3.1 Example A — DISC1 Figure 3 (3 × 2 grid)

```yaml
figure_id: disc1_figure_3
title: "DISC1 perturbation panel"
caption: "Six-panel figure summarising DISC1 morphometry, dynamics, and Bayesian evidence."
output_path: figures/disc1_figure_3.pdf

layout:
  kind: grid
  rows: 3
  cols: 2
  hspace: 0.45
  wspace: 0.32

shared_aesthetic: meta_and_diagnostic
panel_label_style: {enabled: true, case: upper, position: top-left}

panels:
  - id: A
    recipe: actin_microtubule_morphometry.sholl_intersections_radial_histogram
    data: {source: tests/fixtures/data/disc1_sholl.csv}
    caption: "Sholl profile by genotype"
  - id: B
    recipe: intravital_imaging.state_entry_exit_with_switch_callout
    data: {source: tests/fixtures/data/disc1_state_raster.csv}
    caption: "State entry/exit raster"
    shared_axis_with: A
    shared_axis_kind: y
  - id: C
    recipe: omics_differential.proteome_phosphoproteome_pathway_scatter
    data: {source: tests/fixtures/data/disc1_omics_concordance.csv}
  - id: D
    recipe: mixed_effects_models.two_way_anova_summary_plot
    data: {source: tests/fixtures/data/disc1_anova.csv}
  - id: E
    recipe: meta_and_diagnostic.bayes_factor_arrow_plot
    data: {source: tests/fixtures/data/disc1_bf.csv}
  - id: F
    recipe: biophysics_scaling.molecular_resilience_index_bar
    data: {source: tests/fixtures/data/disc1_resilience.csv}
```

### 3.2 Example B — CDC42 Figure 4 (2 × 2 factorial via `partition_by`)

```yaml
figure_id: cdc42_figure_4_factorial
title: "Sex × genotype factorial — Cdc42 CKO"
output_path: figures/cdc42_figure_4_factorial.pdf

layout:
  kind: grid
  rows: 2
  cols: 2
  hspace: 0.40
  wspace: 0.30

shared_aesthetic: mixed_effects_models
panel_label_style: {enabled: true, case: upper, position: top-left}

partition_by:
  recipe: mixed_effects_models.sex_stratified_roc_loocv
  data:
    source: tests/fixtures/data/cdc42_roc_long.csv
  by:
    - tags.sex          # rows: F, M
    - tags.genotype     # cols: CTL, CKO
  panel_label_template: "{sex_value}-{genotype_value}"
```

This expands to four panels:

| Cell | Inferred id | sex | genotype |
|---|---|---|---|
| (0, 0) | `F-CTL` | F | CTL |
| (0, 1) | `F-CKO` | F | CKO |
| (1, 0) | `M-CTL` | M | CTL |
| (1, 1) | `M-CKO` | M | CKO |

### 3.3 Example C — graphical-abstract freeform (4 panels)

```yaml
figure_id: graphical_abstract_disc1
title: "Graphical abstract — DISC1 multi-modal summary"
output_path: figures/graphical_abstract_disc1.pdf

layout:
  kind: freeform
  figsize: [12, 8]

shared_aesthetic: meta_and_diagnostic
panel_label_style: {enabled: false}

panels:
  - id: hero
    recipe: meta_and_diagnostic.panel_provenance_ledger_table
    data: {source: tests/fixtures/data/disc1_provenance.csv}
    position: [0.04, 0.56, 0.55, 0.40]    # [left, bottom, width, height], figure-fraction
  - id: morpho
    recipe: actin_microtubule_morphometry.behavioral_fingerprint_trio_composite
    data: {source: tests/fixtures/data/disc1_fingerprint.csv}
    position: [0.62, 0.56, 0.34, 0.40]
  - id: omics
    recipe: omics_differential.module_concordance_signed_heatmap
    data: {source: tests/fixtures/data/disc1_modules.csv}
    position: [0.04, 0.06, 0.45, 0.42]
  - id: bayes
    recipe: meta_and_diagnostic.bayes_factor_arrow_plot
    data: {source: tests/fixtures/data/disc1_bf.csv}
    position: [0.54, 0.06, 0.42, 0.42]
```

---

## 4. API design (Python)

### 4.1 New module — `manifest/figure_schema.py` (~150 LOC)

```python
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .schema import DataSpec   # reused verbatim


class GridLayout(BaseModel):
    kind: Literal["grid"] = "grid"
    rows: int
    cols: int
    hspace: float | None = None
    wspace: float | None = None
    width_ratios:  list[float] | None = None
    height_ratios: list[float] | None = None


class GridspecCell(BaseModel):
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1


class GridspecLayout(BaseModel):
    kind: Literal["gridspec"] = "gridspec"
    rows: int
    cols: int
    cells: dict[str, GridspecCell]


class FreeformLayout(BaseModel):
    kind: Literal["freeform"] = "freeform"
    figsize: tuple[float, float] = (12.0, 8.0)


Layout = GridLayout | GridspecLayout | FreeformLayout


class PanelLabelStyle(BaseModel):
    enabled: bool = True
    case: Literal["upper", "lower"] = "upper"
    position: Literal["top-left", "top-right", "bottom-left", "bottom-right"] = "top-left"
    offset: tuple[float, float] = (-0.08, 1.05)
    fontweight: str = "bold"
    fontsize: float = 11.0


class PanelSpec(BaseModel):
    id: str
    recipe: str
    data: DataSpec
    caption: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    shared_axis_with: str | None = None
    shared_axis_kind: Literal["x", "y", "both"] = "y"
    aesthetic_overrides: dict[str, Any] = Field(default_factory=dict)
    position: tuple[float, float, float, float] | None = None  # freeform only

    @field_validator("recipe")
    @classmethod
    def _qualified(cls, v: str) -> str:
        if "." not in v:
            raise ValueError(f"recipe {v!r} must be 'modality.recipe'")
        return v


class PartitionBy(BaseModel):
    recipe: str
    data: DataSpec
    by: list[str]
    panel_label_template: str = "{value}"


class FigureSpec(BaseModel):
    figure_id: str
    title: str | None = None
    caption: str | None = None
    output_path: Path | None = None
    layout: Layout
    shared_aesthetic: str | None = None
    panel_label_style: PanelLabelStyle = Field(default_factory=PanelLabelStyle)
    theme: str | None = None
    palette: str | None = None
    panels: list[PanelSpec] = Field(default_factory=list)
    partition_by: PartitionBy | None = None

    @model_validator(mode="after")
    def _exactly_one_panel_source(self) -> "FigureSpec":
        if self.partition_by and self.panels:
            raise ValueError("declare either `panels` or `partition_by`, not both")
        if not self.partition_by and not self.panels:
            raise ValueError("must declare `panels` or `partition_by`")
        return self


def load_figure_spec(path: str | Path) -> FigureSpec: ...
```

### 4.2 New module — `manifest/figure_composition.py` (~300 LOC)

```python
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from ..core.contract import get_recipe
from .figure_schema import FigureSpec, PanelSpec, GridLayout, GridspecLayout, FreeformLayout
from .data_bridge import load_panel_data   # existing helper


def compose_figure(
    spec: FigureSpec,
    *,
    registry,
    data_files,
    out_dir: Path = Path("figures"),
) -> Path:
    """Render a multi-panel figure per spec; return the PDF path."""
    panels = _expand_partition(spec) if spec.partition_by else spec.panels
    fig, axes_by_id = _build_axes_grid(spec.layout, panels)
    _apply_shared_aesthetic(spec, panels, axes_by_id)
    for panel in panels:
        contract = _build_contract(panel, data_files=data_files, registry=registry)
        recipe = get_recipe(panel.recipe)
        recipe.render(contract, axes_by_id[panel.id])
    _link_shared_axes(panels, axes_by_id)
    _draw_panel_labels(spec, panels, axes_by_id)
    _draw_suptitle_and_caption(spec, fig)
    out_path = (spec.output_path or out_dir / f"{spec.figure_id}.pdf")
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_figure_yaml(yaml_path: Path, *, out_dir: Path = Path("figures")) -> Path:
    """Convenience wrapper: load YAML + compose."""
    spec = load_figure_spec(yaml_path)
    return compose_figure(spec, registry=..., data_files=..., out_dir=out_dir)
```

Helper functions (private):

| Helper | Responsibility |
|---|---|
| `_expand_partition(spec)` | Walk `partition_by.by`, materialise the cartesian product, build synthetic `PanelSpec` per cell. |
| `_build_axes_grid(layout, panels)` | Dispatch on `layout.kind`; return `(Figure, dict[panel_id, Axes])`. |
| `_apply_shared_aesthetic(spec, panels, axes_by_id)` | Look up modality aesthetic block; apply to each axes unless panel `aesthetic_overrides` set. |
| `_build_contract(panel, data_files, registry)` | Reuse `data_bridge.build_contract`; honours `panel.options`. |
| `_link_shared_axes(panels, axes_by_id)` | Walk `shared_axis_with`; call `ax.sharex` / `ax.sharey` post-hoc. |
| `_draw_panel_labels(spec, panels, axes_by_id)` | Honours `panel_label_style`; uses `ax.annotate` in axes-fraction units. |
| `_draw_suptitle_and_caption(spec, fig)` | `fig.suptitle(spec.title)` + caption sidecar write. |

### 4.3 Edits to existing modules

- `manifest/__init__.py` — re-export `FigureSpec`, `PanelSpec`, `compose_figure`, `render_figure_yaml`, `load_figure_spec`.
- `cli.py` — add `compose` group (see §5).

---

## 5. CLI surface

| Command | Behaviour |
|---|---|
| `figures compose <figure.yaml>` | Load + compose a single figure spec; emit PDF to `figures/<figure_id>.pdf`. Exit code 0 on success, 1 on schema error, 2 on render error. |
| `figures compose-all [--root figures/]` | Glob `*.figure.yaml` under root; compose each. Emits a summary table (figure_id × pages × elapsed_ms × status). |
| `figures compose-validate <figure.yaml>` | Schema check **only** (no render): parse YAML, validate Pydantic, verify each `recipe` resolves via `core.contract.get_recipe`, verify `shared_axis_with` references existing panel ids, verify `partition_by.by` keys exist in the data file's columns. |
| `figures compose-validate-all` | Sweep variant of above; CI-friendly. |

All four commands honour the global `-v / --verbose` flag and emit one `INFO` line per panel rendered.

---

## 6. Test surface

### 6.1 New test files

| File | Lines | Test count | Coverage |
|---|---|---|---|
| `tests/test_figure_composition.py` | ~250 | ~20 | Schema parse, gridspec layout, freeform layout, partition_by expansion, shared aesthetic propagation, shared-axis linking, panel-label drawing, end-to-end DISC1 fixture render. |
| `tests/test_figure_schema.py` | ~120 | ~10 | Pydantic validators (recipe FQN, mutually-exclusive panels/partition_by, partition cardinality cap). |
| `tests/test_compose_cli.py` | ~120 | ~8 | Click runner integration: `compose`, `compose-all`, `compose-validate` (success + the four failure modes). |

### 6.2 New fixtures directory

```
tests/fixtures/figure_specs/
├── disc1_figure_3.yaml          # Example A
├── cdc42_figure_4_factorial.yaml  # Example B
└── graphical_abstract_disc1.yaml  # Example C
```

Plus the panel data files under `tests/fixtures/data/` (some already exist from disc1/cdc42 packs; gaps to be filled by W1 implementation PR).

### 6.3 End-to-end acceptance test (excerpt)

```python
def test_disc1_figure_3_end_to_end(tmp_path: Path) -> None:
    spec = load_figure_spec("tests/fixtures/figure_specs/disc1_figure_3.yaml")
    pdf_path = compose_figure(spec, registry=..., data_files=..., out_dir=tmp_path)
    assert pdf_path.exists()
    pdf = pikepdf.open(pdf_path)
    assert len(pdf.pages) == 1               # one page, six panels
    text = extract_text(pdf_path)            # via pdfminer.six
    for label in "ABCDEF":
        assert f" {label} " in text          # each panel-label drawn
```

### 6.4 Required test assertions

- `compose-validate` catches: missing recipe FQN; unknown panel id in `shared_axis_with`; freeform without `position`; `partition_by` cardinality > 12.
- `partition_by` produces synthetic panel ids in deterministic row-major order.
- `aesthetic_overrides` on a single panel does NOT leak to siblings.
- `shared_axis_with: A` on panel B and on panel C correctly chains B and C onto A's axis.
- Re-rendering with the same fixture is byte-identical (modulo PDF metadata `/CreationDate`).

---

## 7. Files to create / modify

| File | Kind | LOC | Purpose |
|---|---|---|---|
| `src/panelforge_figures/manifest/figure_schema.py` | **NEW** | ~150 | Pydantic models (`FigureSpec`, `PanelSpec`, `Layout` union, `PartitionBy`, `PanelLabelStyle`); `load_figure_spec()`. |
| `src/panelforge_figures/manifest/figure_composition.py` | **NEW** | ~300 | `compose_figure()` + `render_figure_yaml()` + private helpers. |
| `src/panelforge_figures/manifest/__init__.py` | edit | +6 | Re-export composition API. |
| `src/panelforge_figures/cli.py` | edit | +60 | Add `compose`, `compose-all`, `compose-validate`, `compose-validate-all` commands. |
| `tests/test_figure_composition.py` | **NEW** | ~250 | ~20 tests (schema, layouts, partition, shared axes, end-to-end). |
| `tests/test_figure_schema.py` | **NEW** | ~120 | ~10 tests (Pydantic validators). |
| `tests/test_compose_cli.py` | **NEW** | ~120 | ~8 tests (Click runner). |
| `tests/fixtures/figure_specs/disc1_figure_3.yaml` | **NEW** | ~40 | Example A fixture. |
| `tests/fixtures/figure_specs/cdc42_figure_4_factorial.yaml` | **NEW** | ~25 | Example B fixture (partition_by). |
| `tests/fixtures/figure_specs/graphical_abstract_disc1.yaml` | **NEW** | ~35 | Example C fixture (freeform). |
| `docs/composition_layer.md` | **NEW** | ~200 | User-facing tutorial; cross-links from `docs/index.md`. |
| `docs/manifest_schema.md` | edit | +20 | Cross-link composition layer; clarify it does NOT replace per-panel rendering. |

Total net new code: ~1,000 LOC + ~500 lines of tests + ~200 lines of fixtures + ~220 lines of docs.

---

## 8. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Recipe aesthetic conflicts** — `split_violin` (teal palette) and `coef_forest` (red palette) in the same figure clash visually. | high | (a) `shared_aesthetic: <modality>` at figure scope applies to all; (b) per-panel `aesthetic_overrides` allows opt-out; (c) document a "house aesthetic" template per pack. |
| **Shared y-axis scope confusion** — user expects all `shared_axis_with: A` panels to use A's tick labels, but matplotlib only shares the limits. | medium | Restrict `shared_axis_with` to siblings in the same gridspec row (for `y`) or column (for `x`); raise `SharedAxisOutOfScope` otherwise. Document the limitation. |
| **`partition_by` cardinality blow-up** — a tag with 50 distinct values produces a 50-panel figure; matplotlib chokes and the panel labels are illegible. | medium | Hard cap: `len(by_outer) * len(by_inner) > 12 → PartitionTooLarge`. Suggest manual `panels` list as the workaround. |
| **Recipe call signature drift** — a future recipe might break `render(contract, ax)` (e.g. accept `(contract, ax, **opts)`). | low | Composition layer goes through `get_recipe(...).render(contract, ax)` — same interface as today's render loop. Future kwargs flow via `panel.options` → contract field. |
| **Caption sidecar collision with manifest** — manifest already writes a `caption` field; composition layer also wants one. | low | Composition writes `<figure_id>.caption.txt` next to the PDF; manifest captions remain per-panel. Documented divergence. |
| **PDF page count > 1 for over-large figures** — matplotlib will silently break a too-big figure into multiple pages. | low | Acceptance test asserts `len(pdf.pages) == 1`; on overflow, raise `FigureOversize` with the offending `figsize`. |
| **Determinism regression** — composition reorders panels (esp. partition_by row-major); could destabilise byte-for-byte CI. | medium | Snapshot tests use a deterministic seed + canonical PDF post-processing (strip `/CreationDate`); CI compares on PNG raster, not raw PDF bytes. |

---

## 9. Acceptance criteria (the 5-test gate that says "ship")

A v1.7.0 release ships only when **all five** of the following pass on `main`:

1. **DISC1 Figure 3 renders cleanly.** `figures compose tests/fixtures/figure_specs/disc1_figure_3.yaml` produces a single-page PDF with all six panels visible, panel labels A–F drawn, no matplotlib warnings, ≤ 5 s wall-clock.
2. **CDC42 factorial example tiles correctly.** `figures compose tests/fixtures/figure_specs/cdc42_figure_4_factorial.yaml` produces a 2 × 2 grid where the four cells correspond to (F-CTL, F-CKO, M-CTL, M-CKO) in row-major order; panel labels follow `panel_label_template`.
3. **`figures compose-validate` catches missing recipes BEFORE render.** Pointing the validator at a YAML with `recipe: meta_and_diagnostic.this_recipe_does_not_exist` exits with code 1, prints a single-line diagnostic, and **does not** create a PDF.
4. **Shared y-axis links work.** In Example A panels A and B, the y-axis limits are identical after composition; perturbing panel B's contract data changes both panels' y-limits in lockstep.
5. **Composition adds < 0.5 s overhead vs N×single-recipe renders.** Benchmark: render the same six panels via six `figures generate` calls vs one `figures compose`; the composition path's overhead beyond the sum of per-panel render times is **< 0.5 s** (measured on the project's standard CI runner).

---

## 10. Out of scope (explicit non-goals)

To keep v1.7.0 shippable, the following are **deferred** to later elevations and must not creep into this PR sequence:

1. **LaTeX-style cross-references between figures** (e.g. "see Figure 3 panel B"). Defer to v2.x; would require a separate cross-reference resolver and is orthogonal to composition.
2. **Nested composition (figures-of-figures).** A `FigureSpec` cannot contain another `FigureSpec` as a panel. Defer; if needed, the user composes intermediate PDFs and ImageMagick-stitches.
3. **Interactive composition (Jupyter widgets).** No `compose_interactive()`; the layer is offline-first. Defer to a notebook-companion package.
4. **Per-figure unit tests in the recipe quality suite.** `test_recipes_quality.py` continues to gate per-panel family rules; a parallel `test_figure_quality.py` that audits multi-panel figures for shared-aesthetic compliance is **out of scope** but is a clear follow-up.
5. **Animated / multi-page output.** `compose_figure` emits exactly one page. Multi-page support (per-condition page) defers to a `compose_book` elevation in v2.x.
6. **Cross-figure aesthetic inheritance.** Each `figure.yaml` is self-contained; there is no "global figure aesthetic" that all figures in a project inherit. The manifest's `theme` / `palette` provide the only shared baseline.
7. **Direct manifest integration.** `figures.manifest.yaml` does not gain a `compose:` block in v1.7.0. The two systems remain side-by-side; a unified manifest is a v2.0.0 elevation.

---

_End of spec — composition layer (v1.7.0 target)._
