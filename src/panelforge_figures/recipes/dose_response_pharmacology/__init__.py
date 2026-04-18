"""Dose-response pharmacology figures — Hill fits, IC50 forests, Schild, isobolograms."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="dose_response_pharmacology",
    description=(
        "Hill-fit curves with CI, IC50 forests across compounds, Schild "
        "regression for receptor antagonism, isobolograms for combination "
        "pharmacology, and 2D combo heatmaps."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    drug_combo_heatmap,
    hill_fit_with_ci,
    ic50_forest_across_compounds,
    isobologram_combination,
    schild_regression,
)

__all__ = [
    "AESTHETIC",
    "drug_combo_heatmap",
    "hill_fit_with_ci",
    "ic50_forest_across_compounds",
    "isobologram_combination",
    "schild_regression",
]
