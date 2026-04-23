"""Meta / diagnostic recipes — power, sample size, missingness, QC radar.

This modality lives upstream of the other 19: before anyone plots their
results, these figures report whether the data can support a conclusion at all.
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="meta_and_diagnostic",
    description=(
        "Pre-analysis and pre-submission diagnostics — power curves, "
        "sample-size decision ladders, missing-data patterns, multi-"
        "metric QC radars, PRISMA flow diagrams, publication-bias "
        "funnel plots, heterogeneity forests, leave-one-out sensitivity,"
        " per-sample QC heatmaps, missingness UpSet, 2-D outlier "
        "detection, cohort retention Sankeys, study × replication "
        "matrices, replicate correlograms, and batch-effect PCA."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    batch_effect_diagnostic_pca,
    data_quality_heatmap,
    effect_size_funnel_plot,
    heterogeneity_forest,
    missing_data_pattern_matrix,
    missingness_upset,
    outlier_detection_scatter,
    power_analysis_by_effect_size,
    prisma_flow_diagram,
    qc_metric_radar,
    replication_retrospective_matrix,
    reproducibility_correlogram,
    retention_vs_attrition_sankey,
    sample_size_decision_ladder,
    sensitivity_leave_one_out,
)

__all__ = [
    "AESTHETIC",
    "batch_effect_diagnostic_pca",
    "data_quality_heatmap",
    "effect_size_funnel_plot",
    "heterogeneity_forest",
    "missing_data_pattern_matrix",
    "missingness_upset",
    "outlier_detection_scatter",
    "power_analysis_by_effect_size",
    "prisma_flow_diagram",
    "qc_metric_radar",
    "replication_retrospective_matrix",
    "reproducibility_correlogram",
    "retention_vs_attrition_sankey",
    "sample_size_decision_ladder",
    "sensitivity_leave_one_out",
]
