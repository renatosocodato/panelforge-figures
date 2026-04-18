# Add-figure mode

Used when the user wants to add a single new figure to an existing
manifest.

## 1. Ask the user for the scientific question

> "What question does this figure answer?"

Optionally ask for a modality hint ("is this a FRET figure, a sensitivity
figure, …?"). If the user describes the data instead, skip to step 3.

## 2. Filter catalog candidates by `answers_question`

Search the catalog's `answers_question` strings for the closest match.
Present 3–5 candidates to the user with:

- the recipe's gallery PNG path
- its `answers_question` text
- one `alternatives_in_modality` recipe with a brief "rejected because…"

```
Candidates:
  1. sensitivity_analysis.sobol_first_total_pair
       gallery: docs/gallery/sensitivity_analysis/sobol_first_total_pair.png
       answers: Which parameters carry most of the variance…
       alt:     morris_elementary_effects (rejected: your data is Sobol-index
                shape, not elementary-effects μ*/σ pairs)
  2. sensitivity_analysis.convergence_diagnostic_sobol
       gallery: ...
       answers: Have the Sobol estimates converged?
       alt:     sobol_first_total_pair (rejected: you asked about
                convergence, not the indices themselves)
  ...
```

## 3. Confirm choice + data

Once the user picks a recipe, confirm the data source path. Probe columns
as in bootstrap mode's step 2.

## 4. Compose the panel entry

```yaml
- id: <next letter>
  recipe: <modality>.<recipe>
  data:
    source: <path>
    adapter: <tabular|numpy_npz|pandas_pickle|local.xxx>
    options: {...}
    columns: {src_col: dst_col}
```

Write it into an existing figure (append to `panels:`) or create a new
figure block (`figures:` list append). Keep the manifest valid (one
recipe per panel, recipe must be `modality.name`).

## 5. Generate a local adapter if needed

If no built-in adapter fits, generate
`figures/adapters/local/<name>.py` via the skeleton template.

## 6. Universal finishing steps

Validate. Render *only the new figure* (you can use
`figures render --only <figure_id>` once that flag lands; for now,
render the whole manifest and highlight the new output).

Show the user the paths to the added files. Offer to commit.
