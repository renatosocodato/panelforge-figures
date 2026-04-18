# Manifest schema

The manifest is a single YAML file, `figures.manifest.yaml`, that describes
every figure in a manuscript. It is the one-and-only contract between the
agentic bootstrap skill (which writes the file) and the deterministic engine
(which renders it).

## Full schema

```yaml
version: 1                              # int; required
theme: pnas                             # string; default 'default'
palette: journal_neutral                # string; default 'journal_neutral'
catalog_fingerprint: "sha256:..."       # optional; stamped at bootstrap time
figures:                                # list[FigureSpec]; required, ≥1
  - id: fig_1                           # string; required
    recipe_family: sensitivity_analysis # optional hint for aesthetics
    size: double                        # FIGSIZE_PRESETS key or explicit [w,h]
    suptitle: "Figure 1 · …"            # optional
    subtitle: "…muted 9pt…"             # optional
    panels:                             # list[PanelSpec]; ≥1
      - id: A                           # string; required
        recipe: modality.recipe_name    # fully qualified, required
        title: "optional per-panel"     # optional
        data:                           # DataSpec; required
          source: "path/or/object"
          adapter: tabular              # or 'local.<name>'
          options: {}
          columns: {src_col: dst_col}   # rename map
          select: [col_a, col_b]        # post-rename keep list
          transforms: []                # list of {name, ...kwargs}
        options: {}                     # kwargs passed to the recipe render
    export:                             # optional per-figure override
      formats: [pdf, png, svg]
      outdir: figures/outputs
      dpi: 600
export:                                 # manifest-wide default
  formats: [pdf, png]
  outdir: figures/outputs
  dpi: 600
```

## Validation

- `recipe` must be fully qualified as `modality.name` (no bare recipe name).
- The resolver checks that the recipe is in the registry; unknown recipes
  cause a validation error.
- `figures validate` additionally tries to load each panel's data (skip
  with `--skip-data`).

## Data resolution order

For each panel:

1. Resolve `adapter` via the registry, or `load_local_adapter` if prefixed
   `local.`.
2. Call `adapter(source, **merged_options)` where merged options layer
   `columns`/`select` into `options`.
3. Apply each `transforms[...]` entry in order.
4. Pass the resulting object to the recipe's contract via
   `contract.model_validate(data)` when possible; fall back to raw data.
5. Call `recipe.render(contract, ax, **panel.options)`.

## Layout

Panel grid is chosen automatically per `len(panels)`:

- 1 → 1×1
- 2 → 1×2
- 3 → 1×3
- 4 → 2×2
- 5–6 → 2×3
- 7–9 → 3×3

Larger grids are not supported; split into multiple figures.

## Catalog fingerprint

`figures catalog-fingerprint` emits a `sha256:` hash of the current
catalog. The skill stamps this into the manifest at bootstrap time;
`resurvey` compares it to the current fingerprint to detect whether the
installed package has shifted the catalog since the manifest was written.
