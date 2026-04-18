# Recipe catalog format

`figures catalog --json` prints the following shape. Parse it as your
ground truth for every decision.

```json
{
  "version": "0.1.0a0",
  "modalities": [
    {
      "name": "sensitivity_analysis",
      "description": "Global sensitivity (Sobol, Morris)...",
      "aesthetic": {
        "modality_name": "sensitivity_analysis",
        "primary_palette": "okabe_ito",
        "continuous_cmap": "viridis",
        "ratio_cmap": "RdBu_r",
        "density_cmap": "magma",
        "annotation_style": {...},
        "inset_convention": null,
        "required_scale_bars": false,
        "label_vocabulary": {...},
        "color_anchor": null,
        "spine_color": "#333333"
      },
      "recipes": [
        {
          "name": "sobol_first_total_pair",
          "path": "panelforge_figures.recipes.sensitivity_analysis.sobol_first_total_pair.render",
          "contract": "SobolIndicesInput",
          "family": "sobol_bar",
          "answers_question": "Which parameters carry most of the variance...",
          "required_fields": ["parameter_names", "S1", "ST"],
          "optional_fields": ["S1_ci", "ST_ci", "output_label"],
          "alternatives_in_modality": ["morris_elementary_effects", "interaction_matrix_sobol"],
          "file_format_hints": ["parquet", "csv", "pickle"],
          "n_points_typical": "8-30 parameters",
          "gallery_png": "docs/gallery/sensitivity_analysis/sobol_first_total_pair.png",
          "example_manifest": "skill/example_manifests/sensitivity_analysis_manuscript.yaml"
        },
        ...
      ]
    },
    ...
  ],
  "contracts": ["SobolIndicesInput", "MorrisEEInput", ...],
  "adapters": ["tabular", "numpy_npz", "pandas_pickle", "passthrough"],
  "transforms": ["aggregate_group", "derive_columns", "left_join", "melt_long", "merge_on", "pivot_wide"],
  "themes": ["bpj", "cell", "default", "devcell", "fct_grant", "horizon", "nature", "ncb", "neuron", "pnas", "sttt", "trends"],
  "palettes": [
    {"name": "okabe_ito", "n_colors": 8, "semantic_keys": [], "description": "..."},
    ...
  ]
}
```

## Field-by-field semantics (recipes)

| Field | Use when |
|---|---|
| `name` | module-local identifier |
| `path` | the fully-qualified render function |
| `family` | drives the quality gate + style grouping (`sobol_bar`, `radar`, …) |
| `answers_question` | top-level matching criterion for user intent |
| `required_fields` | must be satisfiable by the data source or via transforms |
| `optional_fields` | nice-to-have enhancements |
| `alternatives_in_modality` | what to mention in your justification to the user |
| `file_format_hints` | narrow candidates by what the user has on disk |
| `gallery_png` | the preview image path — always mention this |

## When to call the catalog

- Once per bootstrap/resurvey/add-figure session (cache in memory).
- Never hardcode recipe names — the version you're running against may
  differ from what's documented.
