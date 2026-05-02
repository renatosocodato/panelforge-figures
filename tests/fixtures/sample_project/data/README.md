# Data files

Two CSVs accompany the `DISC1` manuscript. Both are small (< 5 KB) and
synthetic — they reproduce the schema of the live dataset for figure-
generation and unit-test purposes.

## `morphometry_per_cell.csv`

One row per cell × compartment (60 rows / 30 cells × 2 compartments;
the test fixture ships 30 of these for compactness).

| column | meaning | unit |
|---|---|---|
| `cell_id` | unique cell identifier | — |
| `genotype` | `WT` or `Disc1_HET` | — |
| `cortical_layer` | `II_III` or `V_VI` | — |
| `compartment` | `soma` or `protrusion` | — |
| `area_um2` | projected 2D area | µm² |
| `perimeter_um` | convex-hull perimeter | µm |
| `branch_order` | maximum Sholl-like branch generation | integer |
| `sholl_intersections` | number of Sholl-ring crossings | integer |

## `effect_sizes.csv`

Bootstrap-derived effect-size table — one row per feature × scale ×
compartment.

| column | meaning |
|---|---|
| `feature` | feature name from `morphometry_per_cell.csv` |
| `scale` | `cell` or `population` |
| `compartment` | `soma` or `protrusion` |
| `d` | Cohen's *d* point estimate |
| `ci_lo` | 2.5 % bootstrap percentile |
| `ci_hi` | 97.5 % bootstrap percentile |

Effect sizes are computed against the WT reference. Negative values
indicate `Disc1_HET < WT`.
