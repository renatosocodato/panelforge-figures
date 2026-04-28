"""Shared sub-contracts for the `meta_and_diagnostic` modality.

Pioneered by the `disc1_manuscript_companion` Wave 1 pack. The
sub-contracts here are biology-agnostic — every Wave 1 recipe is a
universal QA / diagnostic primitive (PCA loadings, per-cell audit
tables, hypothesis-exclusion grids, model-residual structure
panels, RF confusion matrices, parameterization lineage diagrams).
Future packs that add reviewer-proof recipes can extend this
module.
"""

from __future__ import annotations

from pydantic import Field

from ...core import RecipeContract

# --- PCA loadings ----------------------------------------------------------


class LoadingsBundle(RecipeContract):
    """Variables × principal-components signed loadings.

    Used by `pca_loadings_heatmap`. Loadings are signed (negative
    means the feature contributes to the PC's negative direction).
    """
    feature_names: list[str]
    component_labels: list[str]                              # e.g. ["PC1", "PC2"]
    loadings: list[list[float]]                              # n_features x n_components
    explained_variance: list[float] | None = None            # one per component


# --- Per-cell audit --------------------------------------------------------


class CellAuditRow(RecipeContract):
    """One cell's per-metric audit record with quality flags.

    Used by `per_cell_audit_table_with_qa_flags`. Each row carries
    one cell_id and an arbitrary number of audit columns (mapped
    by name) plus the per-cell quality flag.
    """
    cell_id: str
    columns: dict[str, float]                                # column-name → value
    flag: str = Field(
        "pass",
        description="'pass' | 'borderline' | 'flag' | 'fail'",
    )
    note: str | None = None


# --- Hypothesis exclusion --------------------------------------------------


class ExclusionRow(RecipeContract):
    """One alternative hypothesis evaluated against multiple criteria.

    Used by `alternative_hypothesis_exclusion_table`. Verdicts are
    Helvetica-safe ASCII ('Y' / 'N' / '~') so the matrix renders
    cleanly without unicode glyphs.
    """
    hypothesis: str
    criteria: dict[str, str]                                 # criterion-name → 'Y' | 'N' | '~'
    overall_verdict: str = Field(
        "equivocal",
        description="'ruled_out' | 'equivocal' | 'consistent'",
    )


# --- Competing-model residuals --------------------------------------------


class CompetingModelFit(RecipeContract):
    """One model's predictions, observations, and residuals.

    Used by `competing_model_residual_panels`. ≥2 such fits get
    rendered side-by-side; the residual structure (size, shape,
    correlation with predicted) drives the model-selection
    narrative.
    """
    model_name: str
    predicted: list[float]
    observed: list[float]
    residuals: list[float]
    aic: float | None = None
    bic: float | None = None
    rmse: float | None = None


# --- Parameter-lineage edge -----------------------------------------------


class ParameterLineageEdge(RecipeContract):
    """One edge linking a modeled-input to its measured cellular readout.

    Used by `model_parameterization_lineage_panel`. Each edge
    carries the name of the modeled parameter on the left, the
    measurement that empirically constrains it on the right, and an
    optional one-line transformation note (e.g. "rolling-window
    median over 30 s").
    """
    modeled_input: str
    measurement: str
    transformation_note: str | None = None
    units: str | None = None


# --- Wave 1 (cdc42_factorial_companion) sub-contracts ----------------------


class BayesFactorRow(RecipeContract):
    """One null-acceptance audit row with BIC-derived BF_01.

    Used by `bayes_factor_arrow_plot`. Each row carries a label
    (descriptor name), the BIC values for null + alternative
    models, and a derived BF_01 + threshold class.
    """
    label: str
    bic_alt: float
    bic_null: float
    bf_01: float                                     # = exp((bic_alt - bic_null) / 2)
    threshold_class: str = Field(
        "anecdotal",
        description="'favours_alt' | 'anecdotal' | 'moderate' | "
                    "'strong' | 'decisive'",
    )


class PanelProvenanceRow(RecipeContract):
    """One panel's provenance ledger entry.

    Used by `panel_provenance_ledger_table`. Each row covers one
    main-text or supplementary panel with its dataset layer,
    sample-composition counts, support class, and manuscript
    status.
    """
    panel_id: str                                    # e.g. "Fig 1A"
    dataset_layer: str                               # "main" | "supp" | "methods"
    n_mice: int
    n_observations: int
    support_class: str = Field(
        "support_layer",
        description="'main_inference' | 'support_layer' | "
                    "'constraint_layer' | 'discovery_layer' | "
                    "'limitation_only'",
    )
    manuscript_status: str = "current"               # "current" | "revised" | ...
    note: str | None = None


class CrossContrastEntry(RecipeContract):
    """One cell of a cross-contrast correlation matrix.

    Used by `cross_contrast_correlation_matrix`. Each entry stores
    a single (row_contrast, col_contrast, correlation) triple; the
    recipe assembles these into the full N × N matrix.
    """
    row_contrast: str
    col_contrast: str
    correlation: float


class MultiverseSpec(RecipeContract):
    """One specification in a multiverse robustness audit.

    Used by `multiverse_specification_curve` and
    `multiverse_robustness_classification_bar`. Each spec carries
    the analytical-choice tuple (preprocessing × model × censoring),
    the resulting effect size, optional 95 % CI bounds, and a
    classification tier.
    """
    spec_id: str                                     # short id
    spec_label: str                                  # human-readable
    effect_size: float
    ci_lo: float | None = None
    ci_hi: float | None = None
    classification: str = Field(
        "NON_SIG",
        description="'ROBUST' | 'FRAGILE' | 'NON_SIG'",
    )


class ProxyAlignmentEntry(RecipeContract):
    """One in-sample vs LOOCV alignment row.

    Used by `proxy_alignment_in_vs_loocv_forest`. Each entry
    captures a proxy / readout name, its in-sample R² (full-fit),
    and the leave-one-out cross-validated R²; the gap between the
    two diagnoses overfit / generalisation.
    """
    proxy: str                                       # e.g. "vel_sd"
    in_sample_R2: float
    loocv_R2: float
    p_value: float | None = None
    n_units: int | None = None
