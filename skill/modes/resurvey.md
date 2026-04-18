# Resurvey mode

Used when `figures.manifest.yaml` already exists and the user asks to
refresh or adapt figures — typically after new data landed, paths moved,
or the installed package version bumped.

## 1. Load existing manifest

```python
from panelforge_figures.manifest import load_manifest
m = load_manifest("figures.manifest.yaml")
```

Capture `m.catalog_fingerprint` — this is what the manifest was written
against.

## 2. Compute catalog delta

Generate the current fingerprint and compare:

```
figures catalog --json > /tmp/pf_catalog.json
```

```python
import hashlib, json
current_fp = "sha256:" + hashlib.sha256(
    json.dumps(json.load(open("/tmp/pf_catalog.json")), sort_keys=True).encode()
).hexdigest()
```

If the fingerprints differ, the catalog has shifted since this manifest
was written. Note which modalities/recipes are new — any of them may
let you upgrade existing panels.

## 3. Re-scan the repository

Identify:

- **Missing data sources** — files the manifest references that no
  longer exist. Flag as orphaned entries.
- **Moved data sources** — files with the same basename but different
  path. Propose updating the `source:` field.
- **New data sources** — files present in the repo that no manifest
  panel references. Propose new figures for them.

## 4. Diff-style proposal

```
CHANGES
  Modified:
    fig_1.A: source moved
       - analysis/old/sobol.parquet
       + analysis/sobol/indices.parquet

  Upgrades available (new in catalog):
    fig_2.A: currently generic volcano_labeled_repelled;
             catalog now has omics_differential.multi_contrast_volcano_grid
             which better fits your 3-contrast experiment.
             [apply / skip]

  New sources (no panel references them):
    analysis/gillespie/dwell_times.parquet
      → propose: gillespie_stochastic.dwell_time_log_violin
        instead of: ensemble_mean_variance_tube (wrong shape)
      [accept / skip]

  Orphans (referenced source missing):
    fig_3.B → analysis/morphometry/legacy_shapes.csv   [drop / investigate]
```

## 5. Get per-change approval

Iterate only on the plan.

## 6. Rewrite manifest preserving user comments

Use `ruamel.yaml.YAML()` (round-trip) so user-authored comments and
key order survive. Replace `catalog_fingerprint` with the current one.

## 7. Universal finishing steps

Run `figures validate` + `figures render` + summary diff + commit offer.
