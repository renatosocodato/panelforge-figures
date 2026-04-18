# Adapter guide

Every data source in a manifest runs through `adapter → transforms → contract`.
You pick the adapter; the engine runs the transforms.

## Decision tree

```
is the data in a CSV/TSV/Parquet/Feather/jsonl?           → tabular
is it a .npz (multi-array)?                                → numpy_npz
is it a pandas-pickled DataFrame or dict?                  → pandas_pickle
is it already a Python object (in-memory demo)?            → passthrough
is it any other bespoke format (SALib pickle, custom HDF5)? → local.<name>
```

## Worked example: SALib Sobol pickle → SobolIndicesInput

Suppose `analysis/sobol/results.pkl` is a dict produced by SALib's
`sobol.analyze()`:

```python
{
  "S1": array([...]),
  "S1_conf": array([...]),
  "ST": array([...]),
  "ST_conf": array([...]),
  "names": ["k_on", "k_off", ...]
}
```

Write `figures/adapters/local/salib_sobol.py`:

```python
"""Load SALib Sobol.analyze() pickle → SobolIndicesInput-shaped dict."""

from pathlib import Path
import pandas as pd

def load(source, **options):
    path = Path(source)
    obj = pd.read_pickle(path)
    return {
        "parameter_names": list(obj["names"]),
        "S1": list(obj["S1"]),
        "ST": list(obj["ST"]),
        "S1_ci": [(s - c, s + c) for s, c in zip(obj["S1"], obj["S1_conf"])],
        "ST_ci": [(s - c, s + c) for s, c in zip(obj["ST"], obj["ST_conf"])],
        "output_label": options.get("output_label", "model output"),
    }
```

Reference in the manifest:

```yaml
- id: A
  recipe: sensitivity_analysis.sobol_first_total_pair
  data:
    source: "analysis/sobol/results.pkl"
    adapter: local.salib_sobol
    options:
      output_label: "steady-state RhoA activity"
```

## Transforms

Chain after the adapter, each is a dict with `name: <transform>`:

```yaml
transforms:
  - name: melt_long
    id_vars: [parameter]
    var_name: which_index
    value_name: value
  - name: aggregate_group
    group_cols: [parameter]
    value_col: value
    how: mean
```

Full list via `figures catalog --json | jq '.transforms'`.

## Do not

- Do not perform heavy computation inside an adapter — push it upstream
  into the analysis pipeline. The adapter is for **shape coercion**.
- Do not modify the installed package to add adapters. Always write
  locally under `figures/adapters/local/`.
- Do not open network connections from an adapter. Adapters must read
  from the local filesystem.
