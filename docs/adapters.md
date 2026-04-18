# Adapters

An adapter is a callable that takes a `source` + `**options` and returns a
pandas `DataFrame`, a `dict`, or a recipe-appropriate payload. The manifest
references adapters by name.

## Built-in adapters

| Name | Accepts | Returns |
|---|---|---|
| `tabular` | CSV, TSV, Parquet, Feather, jsonl | `pandas.DataFrame` (optional column rename + select) |
| `numpy_npz` | `.npz` | `dict[str, np.ndarray]` (optional key select) |
| `pandas_pickle` | `.pkl` / `.pickle` | whatever pandas unpickles (DataFrame, dict, etc.) |
| `passthrough` | any Python object | the object itself — used for in-memory demos |

## Manifest syntax

```yaml
- id: A
  recipe: sensitivity_analysis.sobol_first_total_pair
  data:
    source: "analysis/sobol/indices.parquet"
    adapter: tabular
    options:
      engine: pyarrow
    columns: {sobol_s1: S1, sobol_st: ST, param: parameter_names}
    select: [parameter_names, S1, ST]
    transforms:
      - name: aggregate_group
        group_cols: [parameter_names]
        value_col: S1
        how: mean
```

## Local adapters (per-manuscript)

When no built-in adapter can load a data source, ship a Python file at
`figures/adapters/local/<name>.py` in the manuscript repo. It must
define a `load(source, **options)` callable. Reference it in the manifest
as `adapter: local.<name>`.

Skeleton (`skill/templates/local_adapter_skeleton.py`):

```python
"""Local adapter for <data shape>. Referenced in manifest as 'local.<name>'."""

from pathlib import Path

def load(source, **options):
    path = Path(source)
    # ...read path, coerce columns, return DataFrame or dict
    return ...
```

## Chaining transforms

Transforms run in order after the adapter. Each is a dict with a `name`
field and adapter-like keyword arguments:

- `melt_long` / `pivot_wide`
- `aggregate_group` (any pandas aggregation name)
- `left_join` / `merge_on`
- `derive_columns` (via `DataFrame.eval` — no arbitrary exec)
