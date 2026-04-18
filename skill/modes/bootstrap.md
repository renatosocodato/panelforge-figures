# Bootstrap mode

Used when `figures.manifest.yaml` does not yet exist in the manuscript repo.

## 1. Load the catalog

```
figures catalog --json > /tmp/pf_catalog.json
```

Parse it. Index by `modalities[*].name` and by `family`. Note each
recipe's `answers_question`, `required_fields`, `file_format_hints`,
`alternatives_in_modality`, and `gallery_png` path.

## 2. Survey the repository

1. List tracked files: `git ls-files`.
2. Identify candidate data directories via common names:
   `data/`, `analysis/`, `outputs/`, `results/`, `runs/`, `bundle/`,
   `processed/`.
3. Glob for data files:
   ```
   *.csv *.tsv *.parquet *.feather *.npz *.pkl *.rds *.h5ad
   *.h5 *.mat *.nc *.tif *.tiff *.czi *.nd2
   ```
4. Read `README.md` and `CLAUDE.md` if present — they often state the
   analysis plan or naming conventions.
5. For each candidate file, probe shape/columns:
   - Tabular: `pandas.read_csv/parquet(..., nrows=5).columns.tolist()`.
   - `.npz`: `np.load(..., allow_pickle=False).files`.
   - `.pkl`: safe-load only if the manuscript author has OK'd it and the
     file is inside the repo (`pandas.read_pickle`).

## 3. Classify each data source by modality

Use multiple signals to classify each candidate source into a modality:

- **Directory names**: `fret/`, `redox/`, `sobol/`, `gillespie/`,
  `rhoa_dynamics/`, `morphometry/`, `gcamp/`, `2p_intravital/`,
  `omics/`, `sc/`, `mixed_models/`, `dose_response/`, `network/`,
  `diffusion/`, `spatial/`, `kaplan_meier/`, `cryoem/`.
- **Column-name patterns**:
  - `S1, S1_ci, ST, parameters` → sensitivity_analysis (Sobol).
  - `mu_star, sigma` → sensitivity_analysis (Morris).
  - `log2fc, padj` → omics_differential.
  - `run_id, state, dwell_s` → gillespie_stochastic.
  - `ratio, time_s, roi, stim` → fret_biosensors or calcium_signaling.
  - `cell_id, x_um, y_um, frame` → intravital_imaging or diffusion.
  - `process_len_um, cv_velocity` → actin_microtubule_morphometry.
- **File-format hints**: `.h5ad` → single_cell_embeddings;
  `.czi/.nd2/.tif` → intravital_imaging or morphometry;
  `.mrc/.star` → cryoem_and_structure.
- **Filename tokens**: `ratio`, `gcamp`, `dwell`, `sobol`, `sweep`,
  `volcano`, `phase`, `hysteresis`, `kaplan`, `power`.

## 4. Consult the catalog for recipe candidates

For each classified source, list the recipes in that modality whose
`required_fields` and `file_format_hints` plausibly match the source's
columns/shape. Collect at least the top candidate and one alternative
(use `alternatives_in_modality`).

## 5. Propose the figure plan with justifications

Group related data sources into coherent composite figures (2×2, 3×2,
3×3). For each proposed figure, format a readable table like:

```
Figure 1 · Parameter sensitivity — double (1×2)
  A. sensitivity_analysis.sobol_first_total_pair
        ← file: analysis/sobol/indices.parquet
        because:  columns (S1, ST, parameter_names) match this recipe.
        instead of: morris_elementary_effects — rejected because the
                    data has bootstrap CI columns, so S1/ST pairing is
                    the tighter claim.
  B. sensitivity_analysis.convergence_diagnostic_sobol
        ← file: analysis/sobol/convergence_trace.parquet
        because:  n_samples column + per-parameter ST trajectory matches.
        instead of: no modality-specific alternative.
```

**If any panel falls back to a generic recipe, flag that loudly:**

```
!! I'm falling back to a generic recipe (meta_and_diagnostic.qc_metric_radar)
   for data/qc_metrics.csv because no modality-specific recipe in the
   modality I inferred (omics_differential) matches this shape. Consider
   either stubbing a local adapter that reshapes the data or writing a
   custom recipe.
```

## 6. Get user approval

Accept / amend / drop per figure. Iterate only on the plan — do not
write any files yet.

## 7. For approved figures: write files

### Local adapters (if needed)

For any data source that no built-in adapter handles, generate a small
adapter at:
```
figures/adapters/local/<name>.py
```
using `skill/templates/local_adapter_skeleton.py`. Keep it under ~80
lines. It must define a `load(source, **options)` callable.

### Manifest

Write `figures.manifest.yaml` per the approved plan. Include
`catalog_fingerprint` (from `figures catalog | head` or
`figures write-catalog --out /tmp/pf.json` and grep "sha256:").

### Theme override (optional)

If the user named a venue, generate `figures.theme.toml` with the
matching theme name. Otherwise default to `theme: default`.

### Extend `.gitignore`

Add:
```
figures/outputs/
figures/cache/
```

### Optional CI workflow

If the repo uses GitHub Actions, offer to generate
`.github/workflows/figures.yml` that runs `figures validate` +
`figures render` on every PR.

## 8. Universal finishing steps

Run:
```
figures validate figures.manifest.yaml
figures render figures.manifest.yaml
```

Summarize files added + figure outputs + paths. Offer to commit and PR.
