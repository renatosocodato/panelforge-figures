"""Shared sub-contracts for the `meta_and_diagnostic` modality.

Pioneered by the `cytoskeletal_morphometry_companion` Wave 1 pack. The
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
