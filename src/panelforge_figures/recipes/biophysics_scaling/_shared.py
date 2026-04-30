"""Shared sub-contracts for the `biophysics_scaling` beta expansion pack.

These Pydantic models are consumed by multiple recipes in the pack
(Parts A–D of `docs/biophysics_scaling_beta_pack_tracker.md`). The
pattern intentionally mirrors the nested-contract convention adopted
for other modalities that need cross-recipe vocabulary.

The canonical atom is `ScaleTaggedFeature`: a feature tagged with its
organizational scale (polymer / network / territory / geometry /
whole_cell) and spatial compartment (whole_cell / protrusion_internal).
Effect-size, censoring, validation, mediation, phase-map, trajectory,
tip-state, and PSD sub-contracts build on this atom.

Also exports:
- `OUTCOME_PALETTE_DEFAULT`: fallback three-colour dict for outcome
  coding when `BiophysicsScalingAesthetic.outcome_palette` is not
  overridden.
- `_demo_estimate_roster()`: shared helper that seeds a realistic
  10-feature `EffectSizeEstimate` roster with both compartments.
  Used by A.1 and B.1 demos so the two recipes produce mutually
  consistent example panels.
"""

from __future__ import annotations

from ...core import RecipeContract

# --- canonical feature object -----------------------------------------------


class ScaleTaggedFeature(RecipeContract):
    """One measured feature, tagged with organizational scale + compartment."""
    feature: str
    scale: str                      # "polymer" | "network" | "territory" | "geometry" | "whole_cell"
    compartment: str                # "whole_cell" | "protrusion_internal"
    units: str | None = None


# --- effect size + equivalence ----------------------------------------------


class TostZone(RecipeContract):
    """Symmetric or asymmetric TOST equivalence bounds."""
    lower: float
    upper: float
    units: str | None = None


class EffectSizeEstimate(RecipeContract):
    """One feature's effect with CI and pre-registered equivalence bounds."""
    feature: str
    scale: str
    compartment: str
    d: float
    ci_lo: float
    ci_hi: float
    tost: TostZone
    outcome_class: str              # "significant" | "null_accepting" | "equivocal"
    n_per_group: dict[str, int] | None = None


# --- censoring + robustness -------------------------------------------------


class CensoringMode(RecipeContract):
    """One pre-registered censoring / quality-gating mode."""
    label: str
    pre_registered: bool = True
    n_cells_retained: int | None = None
    description: str | None = None


class CensoringResult(RecipeContract):
    """One feature's effect under one censoring mode."""
    feature: str
    mode_label: str
    direction: int                  # sign(d), in {-1, 0, +1}
    d: float
    ci_lo: float
    ci_hi: float
    p_value: float
    passes_threshold: bool


# --- forward simulation validation ------------------------------------------


class ValidationMetric(RecipeContract):
    """One metric in a forward-simulation validation contract.

    Contract satisfied iff every empirical group-median lies inside
    the simulated group-specific CI. Generic over group labels and
    metric count — the anchor manuscript uses n=3, but the recipe
    accepts any n.
    """
    metric_label: str
    sim_median_by_group: dict[str, float]
    sim_ci_by_group: dict[str, tuple[float, float]]
    emp_median_by_group: dict[str, float]
    emp_ci_by_group: dict[str, tuple[float, float]]
    units: str | None = None
    higher_is: str | None = None    # "disordered" | "ordered" | None


# --- mediation / causal scaffold --------------------------------------------


class MediationPathEstimate(RecipeContract):
    """Path estimates for a three-node mediation (X -> M -> Y, X -> Y direct)."""
    predictor_label: str
    mediator_label: str
    outcome_label: str
    direct_beta: float
    direct_ci: tuple[float, float]
    direct_p_value: float
    indirect_beta: float
    indirect_ci: tuple[float, float]
    mediator_path_beta: float
    mediator_path_ci: tuple[float, float]
    outcome_path_beta: float
    outcome_path_ci: tuple[float, float]
    n_bootstrap: int = 2000


# --- phase space / regime ---------------------------------------------------


class PhaseMapGrid(RecipeContract):
    """2-D grid of a modelled quantity over (x_axis, y_axis), with groups.

    `robustness_neighborhood` is conventionally the convex hull of
    perturbed-parameter simulations. Override with an explicit polygon
    if the robustness-test domain is non-convex.
    """
    x_axis_label: str
    y_axis_label: str
    x_edges: list[float]
    y_edges: list[float]
    values: list[list[float]]
    group_density_contours: dict[str, list[list[float]]] | None = None
    iso_lines: dict[str, list[list[float]]] | None = None
    regime_corners: dict[str, tuple[float, float]] | None = None
    robustness_neighborhood: list[list[float]] | None = None


# --- ordered trajectory -----------------------------------------------------


class OrderedTrajectoryPoint(RecipeContract):
    """One cell projected onto an ordered axis (e.g. Actin Drive Index)."""
    cell_id: str
    group: str
    t_index: float                  # in [0, 1]
    value: float
    thumbnail_path: str | None = None


# --- tip-state frontier -----------------------------------------------------


class TipStateCall(RecipeContract):
    """Benchmark-closed tip-state classification at the actin frontier."""
    cell_id: str
    group: str
    tip_id: str
    frontier_position_um: float
    state: str                      # e.g. "S" | "non-S"
    confidence: float | None = None


# --- power spectral density -------------------------------------------------


class PSDCurve(RecipeContract):
    """One PSD curve for a channel / group."""
    label: str
    freq_hz: list[float]
    psd: list[float]
    ci_lo: list[float] | None = None
    ci_hi: list[float] | None = None
    active_gel_band_hz: tuple[float, float] | None = None


# --- dual-scale significance row (Wave 2 of cytoskeletal_morphometry_companion) ----


class MultiScaleSignificanceRow(RecipeContract):
    """One feature × one scale × one −log₁₀(p) value × tier-band.

    Used by `dual_scale_significance_lollipop` (W2.1 of the
    cytoskeletal_morphometry_companion pack). The recipe groups rows by
    `tier` (polymer / network / territory / geometry), arranges
    metrics within each tier as y-rows, and plots one diverging
    lollipop per (metric × scale) combination.
    """
    feature: str
    scale: str                   # "whole_cell" | "protrusion_internal" | other
    neg_log10_p: float
    tier: str                    # "polymer" | "network" | "territory" | ...
    direction: str = "neutral"   # "up" | "down" | "neutral" (sign of effect)


# --- Wave 3 (geometry + statistics) sub-contracts --------------------------


class CensoringCascadeRow(RecipeContract):
    """One (censoring rule × threshold) audit point.

    Used by W3.3 (`censoring_mode_waterfall_cascade`). Each row
    captures the per-feature estimate + CI under one of the
    pre-registered censoring modes. The waterfall layout offsets
    rows down-and-right so the cascade shape is visible.
    """
    feature: str
    censoring_mode: str                   # e.g. "default" | "loose" | "strict_R2" | "strict_n"
    threshold_label: str                  # e.g. "R^2 > 0.7" | "n_segments >= 60"
    estimate: float                       # signed point estimate
    ci_lo: float
    ci_hi: float


class ConfinementEnergyBundle(RecipeContract):
    """Per-cell Odijk-confinement free energy + per-genotype gauge bounds.

    Used by W3.4 (`confinement_energy_gauge_per_genotype`). Each
    cell carries the free-energy estimate (in k_B T units); the
    recipe's contract also exposes the buffered → unbuffered
    threshold so the gauge needle has a reference.
    """
    cell_id: str
    genotype: str
    free_energy_kBT: float
    width_um: float
    persistence_length_um: float


class ZSpanWidthSample(RecipeContract):
    """Per-cell z-span + width + Euler critical-length threshold.

    Used by W3.9 (`z_span_vs_width_with_euler_threshold`). The
    Euler threshold is a function of the per-cell persistence
    length and is computed by the producer, not the recipe.
    """
    cell_id: str
    condition: str
    width_um: float
    z_span_um: float
    euler_l_crit_um: float


# --- Wave 4 (narrative integration) sub-contracts --------------------------


class MeasuredSimulatedPair(RecipeContract):
    """Per-condition + per-metric measured + simulated quartile bundle.

    Used by W4.3 (`split_mirror_measured_vs_simulated`). Carries
    quartile-style summaries for both measured and simulated
    distributions; the recipe renders them as half-violins facing
    each other.
    """
    metric: str                                  # e.g. "coherency"
    condition: str
    measured_values: list[float]
    simulated_values: list[float]


class ForceBudgetTerm(RecipeContract):
    """One term in the protrusion force budget.

    Used by W4.6 (`force_budget_schematic_with_data`). Each term
    has a value with optional CI bounds and a sign convention
    (drag opposes motion, active pushes forward, etc.).
    """
    term: str                                    # e.g. "drag"
    value_pN: float
    ci_lo: float | None = None
    ci_hi: float | None = None
    sign: str = "+"                              # "+" | "-"


class ConfinementRatioSample(RecipeContract):
    """Per-cell confinement ratio (z-span / Euler L_crit).

    Used by W4.7 (`confinement_ratio_distribution_by_genotype`).
    Ratio > 1 means supercritical (confinement-driven buckling
    plausible), ≤ 1 means subcritical (buffered).
    """
    cell_id: str
    condition: str
    ratio: float                                 # z_span_um / euler_l_crit_um


class CompoundReadoutRow(RecipeContract):
    """One readout × one condition row of compound-forest values.

    Used by W4.8 (`splay_taper_polarity_displacement_compound`).
    Each row carries the per-cell distribution for one readout
    (splay-taper, polarity-displacement, ...) under one condition.
    """
    readout: str                                 # e.g. "splay_to_taper"
    condition: str
    values: list[float]
    ci_lo: float
    ci_hi: float


class SensitivitySweepCurve(RecipeContract):
    """One parameter-sweep curve per condition.

    Used by W4.9 (`sensitivity_sweep_alpha_width_seed_compound`).
    Each curve carries the parameter axis (e.g. alpha values),
    the per-condition mean response, and bootstrap CI ribbons.
    """
    parameter: str                               # e.g. "alpha"
    condition: str
    parameter_grid: list[float]
    mean_response: list[float]
    ci_lo: list[float]
    ci_hi: list[float]


# --- factorial_design_companion Wave 4 sub-contracts ------------------------


class QuartileOccupancyBin(RecipeContract):
    """One condition × quartile occupancy fraction.

    Used by W4.1 (`quartile_stacked_bar_by_factor`). Each row is one
    (condition, quartile) cell; `fraction` is the proportion of that
    condition's cells in that quartile (sums to 1.0 per condition).
    """
    condition: str                                 # "female · CTL" | ...
    quartile: int                                  # 1 (lowest) .. 4 (highest)
    fraction: float                                # in [0, 1]
    n_cells: int | None = None                     # for legend annotation


class RouteGeometryRow(RecipeContract):
    """One perturbation × route geometry scalar value.

    Used by W4.2 (`route_geometry_compact_screen`). Each row is one
    (perturbation, route) cell; `value` is the geometric scalar
    (e.g. mean route length, mean curvature, mean displacement) and
    `is_disrupted` flags routes where the perturbation breaks the
    geometry below a manuscript threshold.
    """
    perturbation: str                              # "MR-CKO" | "Vav-KO" | ...
    route: str                                     # "PIP3" | "Rho" | "Rac" | "Cdc42" | "lipid"
    value: float                                   # geometric scalar
    is_disrupted: bool = False                     # below manuscript threshold


class ResilienceIndexEntry(RecipeContract):
    """One condition's molecular resilience index + multiverse stability.

    Used by W4.3 (`molecular_resilience_index_bar`). Each entry carries
    a single resilience scalar (in [0, 1] or [-1, 1] depending on the
    manuscript convention) plus a multiverse-stability ribbon
    (low / high) that quantifies the spread across analytical
    specifications.
    """
    condition: str                                 # "female · CTL" | ...
    resilience_index: float
    stability_lo: float                            # multiverse low bound
    stability_hi: float                            # multiverse high bound
    is_robust: bool = False                        # passes ROBUST classification


class DissipationProxyRow(RecipeContract):
    """One cell's PCA coords + dissipation quartile + condition.

    Used by W4.4 (`dissipation_quartile_pca_with_ellipses`). Each row
    is one cell with its PC1, PC2 coordinates in the dissipation-proxy
    PCA space and the dissipation quartile (1..4) it falls into.
    """
    cell_id: str
    condition: str                                 # "female · CTL" | ...
    pc1: float
    pc2: float
    dissipation_quartile: int                      # 1 (low) .. 4 (high)


# --- outcome palette (local fallback) ---------------------------------------


OUTCOME_PALETTE_DEFAULT: dict[str, str] = {
    "significant": "#1565C0",
    "null_accepting": "#2E7D32",
    "equivocal": "#9E9E9E",
}


# --- demo roster helper (shared by A.1 and B.1) -----------------------------


def _demo_estimate_roster() -> list[EffectSizeEstimate]:
    """Seed a realistic 10-feature x 2-compartment EffectSizeEstimate roster.

    Anchors to the manuscript's 109/149 breakdown and typical TOST
    margins (±0.2 in standardized-d space). Used by A.1 and B.1 demos.
    """
    # Per-feature: (feature, scale, d_whole_cell, d_protrusion_internal)
    rows: list[tuple[str, str, float, float]] = [
        ("persistence_length_actin",   "polymer",      0.04,  0.06),   # null
        ("psd_motor_band",             "polymer",     -0.08,  0.09),   # null
        ("filament_mesh_size",         "network",      0.12, -0.11),   # equivocal
        ("orientation_alpha",          "network",      0.09,  0.72),   # sig protrusion
        ("curvature_ccf_peak",         "network",     -0.04,  0.58),   # sig protrusion
        ("territory_radius",           "territory",    0.62,  0.51),   # sig both
        ("standoff_distance",          "geometry",     0.44,  0.83),   # sig both
        ("protrusion_width",           "geometry",     0.35,  0.98),   # sig (protrusion stronger)
        ("cell_area",                  "whole_cell",   0.71,  0.12),   # sig whole-cell only
        ("soma_circularity",           "whole_cell",   0.38,  0.08),   # sig whole-cell only
    ]
    tost = TostZone(lower=-0.2, upper=0.2, units="Cohen_d")
    estimates: list[EffectSizeEstimate] = []
    for feature, scale, d_wc, d_pr in rows:
        for compartment, d in (("whole_cell", d_wc), ("protrusion_internal", d_pr)):
            ci_half = 0.18
            ci_lo = d - ci_half
            ci_hi = d + ci_half
            # Outcome classification matches tost_bounds_utility rules.
            if ci_hi < tost.lower or ci_lo > tost.upper:
                outcome = "significant"
            elif tost.lower <= ci_lo and ci_hi <= tost.upper:
                outcome = "null_accepting"
            else:
                outcome = "equivocal"
            estimates.append(EffectSizeEstimate(
                feature=feature,
                scale=scale,
                compartment=compartment,
                d=d,
                ci_lo=ci_lo,
                ci_hi=ci_hi,
                tost=tost,
                outcome_class=outcome,
                n_per_group={"WT": 7, "LI": 16},
            ))
    return estimates
