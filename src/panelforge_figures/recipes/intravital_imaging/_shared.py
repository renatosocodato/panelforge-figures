"""Shared sub-contracts for the `intravital_imaging` beta expansion pack.

Pioneered by the `biophysics_scaling` pack (Wave 1). The intravital
sub-contracts are richer because the modality juggles three orthogonal
data atoms: tip tracks, protrusion polylines (with time), and per-frame
tip centroid snapshots. Decision-layer recipes (Part A) consume
`DecodedStateSeries` and `ModelFitSummary`; commitment / latency
recipes (Part B) consume `LatencyDistribution` and `ProtrusionPolyline`;
orthogonal recipes (Part C) consume the rest.

Also exports a `_demo_state_palette()` helper so all decoding recipes
share the same `microglia_states` colour mapping (avoids palette drift
across A.1-A.12 demos).
"""

from __future__ import annotations

from pydantic import Field

from ...core import RecipeContract

# --- track + polyline atoms -------------------------------------------------


class TipTrack(RecipeContract):
    """One tip's XY trajectory, timestamps, and optional parent cell."""
    tip_id: str
    x_um: list[float]
    y_um: list[float]
    t_s: list[float]
    parent_cell_id: str | None = None


class ProtrusionPolyline(RecipeContract):
    """One protrusion as an ordered sequence of points, single timepoint."""
    protrusion_id: str
    xy_um: list[list[float]]                  # n_points x 2
    parent_cell_id: str
    born_s: float | None = None
    died_s: float | None = None               # None = still alive at end


class ProtrusionPolylineWithTime(RecipeContract):
    """A polyline observed at multiple timepoints."""
    protrusion_id: str
    parent_cell_id: str
    t_s: list[float]
    polyline_xy_um_per_t: list[list[list[float]]]   # n_t x n_points x 2
    length_um_per_t: list[float] | None = None
    curvature_per_s_per_t: list[list[float]] | None = None  # n_t x n_points


# --- canonical feature bundle -----------------------------------------------


class KinematicFeatureBundle(RecipeContract):
    """Canonical feature set consumed by Parts A, B, and most of C."""
    cell_id: str
    t_s: list[float]
    # tip-level
    tip_xy_um: list[list[float]] | None = None    # n_t x 2
    velocity_um_per_min: list[float] | None = None
    heading_deg: list[float] | None = None
    # protrusion-level
    polylines: list[ProtrusionPolylineWithTime] = Field(default_factory=list)
    length_um: list[float] | None = None
    length_rate_um_per_min: list[float] | None = None
    curvature_mean_per_um: list[float] | None = None
    turning_angle_deg: list[float] | None = None
    # optional orthogonal channels
    biosensor_ratio: list[float] | None = None
    cue_vector_deg: list[float] | None = None


# --- spatial point-pattern --------------------------------------------------


class TipCentroidSnapshot(RecipeContract):
    """One frame's tip centroids for spatial point-pattern analysis.

    The `window_polygon_um` is what makes intravital point-pattern
    recipes window-conditional rather than generic spatial statistics.
    """
    t_s: float
    xy_um: list[list[float]]                  # n_tips x 2
    window_polygon_um: list[list[float]]      # closed polygon (ROI)


# --- latency / survival -----------------------------------------------------


class LatencyDistribution(RecipeContract):
    """Uniform container for tau_reorient, tau_commit, tau_drift, etc."""
    label: str                                # e.g. "tau_reorient"
    condition: str
    values_s: list[float]
    censored: list[bool] | None = None        # True if right-censored
    n_subjects: int | None = None


# --- decoded states + model fit ---------------------------------------------


class DecodedStateSeries(RecipeContract):
    """Time-aligned sequence of decoded latent states for one cell/track."""
    cell_id: str
    t_s: list[float]
    state: list[str]
    posterior_prob: list[list[float]] | None = None   # n_t x n_states
    decoder: str = "HMM"                              # "HMM" | "HSMM"


class ModelFitSummary(RecipeContract):
    """AIC/BIC/CV log-likelihood per model per stratum."""
    stratum: str
    model: str                                # "HMM" | "HSMM"
    n_states: int
    log_likelihood: float
    aic: float
    bic: float
    cv_log_likelihood_mean: float | None = None
    cv_log_likelihood_sd: float | None = None


# --- shared demo palette ----------------------------------------------------


def _demo_state_palette(states: list[str]) -> dict[str, str]:
    """Map decoded states to colours from the `microglia_states` palette.

    Used by every Wave 1 / Wave 2 decoding recipe so the same state
    colours appear across A.4 (dwell), A.5 (survival), A.6 (hazard),
    A.8 (emission), A.10 (model comparison), and the Wave 2 recipes.
    """
    fixed = {
        "patrolling": "#1565C0",
        "scanning":   "#2E7D32",
        "engaged":    "#C62828",
        "S0":         "#1565C0",
        "S1":         "#2E7D32",
        "S2":         "#C62828",
        "S3":         "#6A1B9A",
        "S4":         "#E65100",
    }
    fallback_palette = ["#1565C0", "#2E7D32", "#C62828",
                        "#6A1B9A", "#E65100", "#455A64"]
    out: dict[str, str] = {}
    fallback_i = 0
    for s in states:
        if s in fixed:
            out[s] = fixed[s]
        else:
            out[s] = fallback_palette[fallback_i % len(fallback_palette)]
            fallback_i += 1
    return out
