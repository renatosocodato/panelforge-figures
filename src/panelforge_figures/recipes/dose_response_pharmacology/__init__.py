"""Dose-response pharmacology figures — Hill fits, IC50, Schild, SAR, selectivity, polypharmacology."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="dose_response_pharmacology",
    description=(
        "Hill-fit curves with CI and sex-stratified variants, IC50 forests "
        "across compounds and dose-normalised fold-EC50 forests, Schild "
        "regression for receptor antagonism, isobolograms and drug-combo "
        "heatmaps and Bliss × Loewe synergy scatter, dose × time response "
        "matrices, washout/rebound kinetics, IC50-vs-Ki concordance, "
        "selectivity tornadoes, pharmacophore activity SAR heatmaps, "
        "compound-cluster SAR panels, polypharmacology radar."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    compound_cluster_structure_activity,
    dose_normalized_ec50_forest,
    dose_response_sex_stratified,
    dose_response_time_matrix,
    drug_combo_heatmap,
    hill_fit_with_ci,
    ic50_forest_across_compounds,
    ic50_vs_target_affinity_scatter,
    isobologram_combination,
    pharmacophore_activity_heatmap,
    polypharmacology_radar,
    response_rebound_kinetics,
    schild_regression,
    selectivity_index_tornado,
    synergy_score_bliss_loewe,
)

__all__ = [
    "AESTHETIC",
    "compound_cluster_structure_activity",
    "dose_normalized_ec50_forest",
    "dose_response_sex_stratified",
    "dose_response_time_matrix",
    "drug_combo_heatmap",
    "hill_fit_with_ci",
    "ic50_forest_across_compounds",
    "ic50_vs_target_affinity_scatter",
    "isobologram_combination",
    "pharmacophore_activity_heatmap",
    "polypharmacology_radar",
    "response_rebound_kinetics",
    "schild_regression",
    "selectivity_index_tornado",
    "synergy_score_bliss_loewe",
]
