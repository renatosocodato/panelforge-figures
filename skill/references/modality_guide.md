# Modality guide — classification hints

When surveying a manuscript repo, you need to classify each data source
into the most likely modality so you can narrow the recipe search.
This guide gives you signal priors for every v1.0 modality.

| Modality | Directory hints | Column hints | File-format hints | Filename tokens |
|---|---|---|---|---|
| fret_biosensors | `fret/`, `biosensor/` | `ratio`, `donor`, `acceptor`, `roi`, `stim_time` | `.tif`, `.npz`, `.parquet` | `ratio`, `fret`, `biosensor` |
| rhogtpase_dynamics | `rhoa_dynamics/`, `ode/` | `x`, `y`, `dx_dt`, `potential_U` | `.pkl`, `.npz` | `phase`, `bifurcation`, `landscape`, `nullcline` |
| gillespie_stochastic | `gillespie/`, `ssa/` | `run_id`, `state`, `dwell_s`, `t_transition` | `.parquet` | `dwell`, `trajectory`, `fpt` |
| redox_imaging | `redox/`, `h2o2/`, `roGFP/` | `ratio`, `reduced_frac`, `oxidized_frac`, `bimodality` | `.tif`, `.parquet` | `redox`, `bistable`, `hysteresis`, `paracrine` |
| actin_microtubule_morphometry | `morphometry/`, `skeleton/` | `cell_id`, `process_len_um`, `cv_velocity`, `branch_count` | `.csv`, `.parquet` | `skeleton`, `process`, `branching`, `kymograph` |
| **sensitivity_analysis** | `sobol/`, `morris/`, `sensitivity/` | `S1`, `S1_ci`, `ST`, `mu_star`, `sigma`, `parameter_names` | `.parquet`, `.pkl` | `sobol`, `morris`, `sweep`, `sensitivity` |
| mixed_effects_models | `mixed_effects/`, `glmm/`, `brms/` | `term`, `estimate`, `CI_lo`, `CI_hi`, `random_effect` | `.csv`, `.rds` | `forest`, `emmeans`, `random`, `posterior` |
| omics_differential | `deseq2/`, `limma/`, `diff_expr/` | `gene`, `log2fc`, `padj`, `pvalue` | `.csv`, `.parquet`, `.tsv` | `volcano`, `de`, `differential`, `gsea` |
| single_cell_embeddings | `sc/`, `scrna/`, `umap/` | `cluster`, `umap_1`, `umap_2`, `pseudotime` | `.h5ad`, `.parquet` | `umap`, `pseudotime`, `clusters` |
| intravital_imaging | `2p/`, `intravital/`, `live_imaging/` | `cell_id`, `x_um`, `y_um`, `frame`, `depth_um` | `.tif`, `.nd2`, `.czi`, `.parquet` | `2p`, `surveillance`, `kymograph`, `motility` |
| calcium_signaling | `gcamp/`, `calcium/` | `cell_id`, `fluorescence`, `event_time_s` | `.parquet`, `.csv` | `gcamp`, `calcium`, `event_raster`, `spike` |
| dose_response_pharmacology | `dose_response/`, `pharm/` | `dose`, `response`, `compound`, `IC50` | `.csv`, `.parquet` | `hill`, `ic50`, `dose`, `schild`, `combo` |
| network_and_pathway | `network/`, `grn/` | `source`, `target`, `weight`, `module` | `.graphml`, `.parquet`, `.tsv` | `hive`, `chord`, `pathway`, `centrality` |
| diffusion_and_tracking | `tracking/`, `trajectories/` | `track_id`, `msd`, `step_size`, `angle` | `.parquet`, `.csv` | `msd`, `track`, `diffusion` |
| spatial_statistics | `spatial/`, `spatial_stats/` | `x`, `y`, `point_id`, `K_r`, `g_r` | `.parquet` | `ripleys`, `pair_correlation`, `moran` |
| biophysics_scaling | `scaling/`, `collapse/` | `log_x`, `log_y`, `slope`, `collapse_factor` | `.csv`, `.parquet` | `scaling`, `collapse`, `master_curve` |
| cryoem_and_structure | `cryoem/`, `relion/`, `cs/` | `resolution`, `fsc`, `ctf_fit` | `.star`, `.csv`, `.mrc` | `fsc`, `ctf`, `angular_dist` |
| clinical_cohort | `clinical/`, `cohort/` | `subject_id`, `time`, `event`, `arm`, `treatment` | `.csv`, `.parquet` | `kaplan`, `km`, `cox`, `survival` |
| **grant_and_conceptual** | `grant/`, `proposal/`, `figures/` | — | `.yaml`, `.toml` | `wp`, `milestone`, `triptych` |
| **meta_and_diagnostic** | `qc/`, `diagnostics/` | `power`, `effect_size`, `missing_frac`, `metric` | `.csv`, `.parquet` | `power`, `qc`, `missing`, `radar` |

Bold rows are shipped in v0.1.0-alpha.

## Classification algorithm (sketch)

```python
def classify(data_source) -> tuple[str, float]:
    """Return (modality, confidence 0..1)."""
    score = {mod: 0.0 for mod in catalog.modalities}
    for signal_name, score_fn in SIGNALS:
        for mod, weight in score_fn(data_source).items():
            score[mod] += weight * SIGNAL_WEIGHTS[signal_name]
    best = max(score, key=score.get)
    total = sum(score.values())
    conf = score[best] / max(total, 1e-9)
    return best, conf
```

Signals to combine:

- Directory path match (weight 3)
- Column-name match (weight 4)
- File-format match (weight 2)
- Filename token match (weight 2)

Classifications with low confidence (e.g., < 0.4) should be called out
as ambiguous and surfaced to the user, not silently used.
