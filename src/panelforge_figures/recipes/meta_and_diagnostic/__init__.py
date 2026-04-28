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
    alternative_hypothesis_exclusion_table,
    batch_effect_diagnostic_pca,
    bayes_factor_arrow_plot,
    competing_model_residual_panels,
    cross_contrast_correlation_matrix,
    data_quality_heatmap,
    effect_size_funnel_plot,
    heterogeneity_forest,
    missing_data_pattern_matrix,
    missingness_upset,
    model_parameterization_lineage_panel,
    multiverse_robustness_classification_bar,
    multiverse_specification_curve,
    outlier_detection_scatter,
    panel_provenance_ledger_table,
    pca_loadings_heatmap,
    per_cell_audit_table_with_qa_flags,
    power_analysis_by_effect_size,
    prisma_flow_diagram,
    proxy_alignment_in_vs_loocv_forest,
    qc_metric_radar,
    random_forest_confusion_loocv,
    replication_retrospective_matrix,
    reproducibility_correlogram,
    retention_vs_attrition_sankey,
    sample_size_decision_ladder,
    sensitivity_leave_one_out,
)

__all__ = [
    "AESTHETIC",
    "alternative_hypothesis_exclusion_table",
    "batch_effect_diagnostic_pca",
    "bayes_factor_arrow_plot",
    "competing_model_residual_panels",
    "cross_contrast_correlation_matrix",
    "data_quality_heatmap",
    "effect_size_funnel_plot",
    "heterogeneity_forest",
    "missing_data_pattern_matrix",
    "missingness_upset",
    "model_parameterization_lineage_panel",
    "multiverse_robustness_classification_bar",
    "multiverse_specification_curve",
    "outlier_detection_scatter",
    "panel_provenance_ledger_table",
    "pca_loadings_heatmap",
    "per_cell_audit_table_with_qa_flags",
    "power_analysis_by_effect_size",
    "prisma_flow_diagram",
    "proxy_alignment_in_vs_loocv_forest",
    "qc_metric_radar",
    "random_forest_confusion_loocv",
    "replication_retrospective_matrix",
    "reproducibility_correlogram",
    "retention_vs_attrition_sankey",
    "sample_size_decision_ladder",
    "sensitivity_leave_one_out",
]
