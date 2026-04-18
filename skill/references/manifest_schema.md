# Manifest schema (skill reference)

This mirrors `docs/manifest_schema.md`, framed for the skill's authoring
step. Always write the full file in one shot after the user approves the
plan. Use `ruamel.yaml` to preserve comments on edits; use `pyyaml` for
initial writes (round-trip quality matters less at bootstrap time).

## Canonical bootstrap manifest

```yaml
version: 1
theme: pnas
palette: journal_neutral
catalog_fingerprint: "sha256:<fp>"     # obtained from `figures catalog --json`
figures:
  - id: fig_1_sensitivity
    size: double
    suptitle: "Figure 1 · Parameter sensitivity"
    subtitle: "Sobol indices and convergence"
    panels:
      - id: A
        recipe: sensitivity_analysis.sobol_first_total_pair
        data:
          source: "analysis/sobol/indices.parquet"
          adapter: tabular
          columns: {param: parameter_names, s1: S1, st: ST}
        options:
          output_label: "steady-state RhoA"
      - id: B
        recipe: sensitivity_analysis.convergence_diagnostic_sobol
        data:
          source: "analysis/sobol/convergence_trace.parquet"
          adapter: tabular
export:
  formats: [pdf, png, svg]
  outdir: figures/outputs
  dpi: 600
```

## Rules

- Every `recipe:` must be `modality.name` (no bare names).
- `data.adapter` is either a built-in name or `local.<name>`.
- Keep panel `options` minimal — recipe defaults are chosen carefully.
- Always stamp `catalog_fingerprint` so `resurvey` can detect drift.

## Per-figure theme override (landing in a future commit)

```yaml
figures:
  - id: fig_grant
    theme: fct_grant         # override the manifest-wide theme
    ...
```

Today, override by splitting figures into two manifests or by calling
`apply_theme(...)` from Python and rendering programmatically.
