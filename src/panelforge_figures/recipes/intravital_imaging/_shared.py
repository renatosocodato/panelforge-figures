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


# --- biosensor + dose-time atoms (Wave 4) -----------------------------------


class BiosensorField(RecipeContract):
    """One cell's spatial biosensor signal at a single timepoint.

    The grid is in cell-local coordinates (rows × cols); the recipe
    knows about its physical units via `pixel_um`. Used by C.6
    (`biosensor_activation_field_per_cell`).
    """
    cell_id: str
    sensor_label: str                              # e.g. "ROCK biosensor"
    intensity_grid: list[list[float]]              # n_rows x n_cols
    pixel_um: float = 0.5
    baseline_intensity: float | None = None        # for divergent cmap centring


class BiosensorTimeTrace(RecipeContract):
    """One cell's biosensor signal as a function of time at one dose.

    Used by C.7 (`biosensor_dose_response_curve`).
    """
    cell_id: str
    sensor_label: str
    dose: float
    dose_unit: str = "uM"
    t_s: list[float]
    intensity: list[float]                         # arbitrary units


class DoseTimeResponse(RecipeContract):
    """One cell's dose × time response surface.

    Used by C.11 (`dose_x_time_response_matrix`).
    """
    cell_id: str
    condition: str
    dose_grid: list[float]                         # n_doses
    t_s: list[float]                               # n_t
    response_grid: list[list[float]]               # n_doses x n_t
    response_label: str = "response (a.u.)"


# --- factorial_design_companion Wave 3 atoms --------------------------------


class StateSwitchSummary(RecipeContract):
    """Per-cell switching-frequency callout atom.

    Used by W3.7 (`state_entry_exit_with_switch_callout`). Bundles the
    decoded series with a precomputed switch rate (switches per minute),
    so the recipe can render a left-margin lollipop-style callout
    per cell row without recomputing transitions during render.
    """
    cell_id: str
    n_switches: int
    duration_min: float
    switch_rate_per_min: float


# --- shared demo palette ----------------------------------------------------


def _demo_state_palette(states: list[str]) -> dict[str, str]:
    """Map decoded states to the registered `microglia_states` palette.

    Uses the contemporary editorial palette (slate / teal / coral /
    purple / amber) registered in `core/palette.py` rather than the
    traditional MUI blue-green-red triad. Semantic state names
    (`homeostatic`, `surveillant`, `activated`, `DAM`, `proliferative`)
    map directly to the registered semantic keys; generic indexed
    labels (`S0`, `S1`, ...) fall through to the same colour ramp.

    Used by every Wave 1 / Wave 2 decoding recipe so the same state
    colours appear across A.4 (dwell), A.5 (survival), A.6 (hazard),
    A.8 (emission), A.10 (model comparison), and the Wave 2 recipes.
    """
    # Reuse the registered palette so colours stay aligned with the
    # rest of the modality (no parallel hex literal drift).
    from ...core.palette import get_palette
    pal = get_palette("microglia_states")
    semantic = pal.semantic   # keyed by 'homeostatic' / 'surveillant' / ...
    ordered_ramp = list(pal.colors)
    out: dict[str, str] = {}
    fallback_i = 0
    for s in states:
        if s in semantic:
            out[s] = semantic[s]
        elif s.startswith("S") and s[1:].isdigit():
            i = int(s[1:])
            out[s] = ordered_ramp[i % len(ordered_ramp)]
        else:
            out[s] = ordered_ramp[fallback_i % len(ordered_ramp)]
            fallback_i += 1
    return out
