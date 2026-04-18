"""Meta / diagnostic recipes — power, sample size, missingness, QC radar.

This modality lives upstream of the other 19: before anyone plots their
results, these figures report whether the data can support a conclusion at all.
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="meta_and_diagnostic",
    description=(
        "Pre-analysis diagnostics — power curves, sample-size decision ladders, "
        "missing-data patterns, and multi-metric QC radars."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    missing_data_pattern_matrix,
    power_analysis_by_effect_size,
    qc_metric_radar,
    sample_size_decision_ladder,
)

__all__ = [
    "AESTHETIC",
    "missing_data_pattern_matrix",
    "power_analysis_by_effect_size",
    "qc_metric_radar",
    "sample_size_decision_ladder",
]
