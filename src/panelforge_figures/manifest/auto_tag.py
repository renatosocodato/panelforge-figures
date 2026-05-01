"""Auto-tagger — derive closed-taxonomy tags for the recipe registry.

Every registered recipe carries enough metadata (name, modality, family,
``answers_question`` text, required / optional fields) for a deterministic
rule-based tagger to label it along eight closed dimensions:

    anchor              "DISC1" / "CDC42" / "DISC1+CDC42" / "RhoA" / "RAC1" / "generic"
    dimensionality      "2D" / "3D" / "1D" / "scalar"
    dynamics            "static" / "kymograph" / "live" / "ordered_pseudotime"
    factorial           bool
    equivalence         bool
    compartment_aware   bool
    scale_aware         bool
    wave                "v1.0" / "v1.1.0-beta-..." / ... / "v1.5.0-beta-cdc42_factorial_companion"

Rules are intentionally conservative: when no rule fires, the tag value is
set to the sentinel ``"unknown"`` so a downstream YAML override layer can
add curated values without fighting the auto-tagger.

The module has zero new heavy dependencies — only ``re``, ``pathlib``, and
``subprocess`` from the stdlib.  ``auto_tag_all()`` walks the live registry
and returns ``{full_name: tag_dict}`` for the 448 recipes; the per-recipe
``auto_tag_recipe(...)`` is pure and importable in tests without touching
the registry.
"""

from __future__ import annotations

import re
from typing import Any

# Sentinel used when no high-confidence rule fires for a tag.
UNKNOWN: str = "unknown"

# All eight closed-taxonomy keys that *every* recipe carries in its tag dict.
TAG_KEYS: tuple[str, ...] = (
    "anchor",
    "dimensionality",
    "dynamics",
    "factorial",
    "equivalence",
    "compartment_aware",
    "scale_aware",
    "wave",
)


# ──────────────────────────── wave assignment ────────────────────────────
#
# Hard-coded modality → wave map derived from the CHANGELOG and pack
# trackers.  This is acceptable for Wave 2 of the recipe-discovery
# system: the auto-tagger only needs to *cover* the 448 recipes that
# already exist; wave assignments for future recipes get added here as
# new packs ship.

# Default wave for any modality not explicitly mapped (legacy v1.0 cohort).
_DEFAULT_WAVE: str = "v1.0"

# Modalities that shipped *as a whole* in a beta pack — every recipe in
# the modality belongs to that pack.  Pack-specific recipes scattered
# across pre-existing modalities (the cdc42 pack) are handled by an
# explicit name list further below.
_MODALITY_WAVE: dict[str, str] = {
    "biophysics_scaling": "v1.2.0-beta-biophysics_scaling",
    "intravital_imaging": "v1.3.0-beta-intravital_imaging",
}

# Recipes that shipped in `v1.5.0-beta-cdc42_factorial_companion` (PRs
# #44–#47; tag `v1.5.0-beta-cdc42_factorial_companion`).  25 recipes
# scattered across 6 pre-existing modalities, enumerated verbatim from
# `docs/cdc42_factorial_companion_pack_tracker.md`.
_CDC42_PACK_FULLNAMES: frozenset[str] = frozenset({
    # W1 — meta_and_diagnostic (+6)
    "meta_and_diagnostic.bayes_factor_arrow_plot",
    "meta_and_diagnostic.panel_provenance_ledger_table",
    "meta_and_diagnostic.cross_contrast_correlation_matrix",
    "meta_and_diagnostic.multiverse_robustness_classification_bar",
    "meta_and_diagnostic.multiverse_specification_curve",
    "meta_and_diagnostic.proxy_alignment_in_vs_loocv_forest",
    # W2 — omics_differential (+6)
    "omics_differential.proteome_phosphoproteome_pathway_scatter",
    "omics_differential.module_concordance_signed_heatmap",
    "omics_differential.pathway_space_triangulation_heatmap",
    "omics_differential.pathway_space_bridge_summary_heatmap",
    "omics_differential.gge_branch_selectivity_permutation_bar",
    "omics_differential.pathway_module_activity_with_sign_concordance",
    # W3 — mixed_effects_models (+4) + actin_mt (+2) + intravital (+1)
    "mixed_effects_models.two_way_anova_summary_plot",
    "mixed_effects_models.sex_stratified_roc_loocv",
    "mixed_effects_models.mediation_decomposition_slope_chart",
    "mixed_effects_models.pre_post_slope_chart_by_module",
    "actin_microtubule_morphometry.sholl_intersections_radial_histogram",
    "actin_microtubule_morphometry.behavioral_fingerprint_trio_composite",
    "intravital_imaging.state_entry_exit_with_switch_callout",
    # W4 — biophysics_scaling (+4) + intravital_imaging (+2)
    "biophysics_scaling.quartile_stacked_bar_by_factor",
    "biophysics_scaling.route_geometry_compact_screen",
    "biophysics_scaling.molecular_resilience_index_bar",
    "biophysics_scaling.dissipation_quartile_pca_with_ellipses",
    "intravital_imaging.transition_matrix_diagonal_dominance_callout",
    "intravital_imaging.residence_time_kaplan_meier_with_ks_overlay",
})

# Recipes that shipped in `v1.4.0-beta-disc1_manuscript_companion` (PRs
# #39–#43; tag `v1.4.0-beta-disc1_manuscript_companion`).  31 recipes
# scattered across 4 modalities, enumerated verbatim from
# `docs/disc1_manuscript_companion_pack_tracker.md`.
_DISC1_PACK_FULLNAMES: frozenset[str] = frozenset({
    # W1 — universal QA + diagnostic primitives (+6 in meta_and_diagnostic)
    "meta_and_diagnostic.pca_loadings_heatmap",
    "meta_and_diagnostic.per_cell_audit_table_with_qa_flags",
    "meta_and_diagnostic.alternative_hypothesis_exclusion_table",
    "meta_and_diagnostic.competing_model_residual_panels",
    "meta_and_diagnostic.random_forest_confusion_loocv",
    "meta_and_diagnostic.model_parameterization_lineage_panel",
    # W2 — cell territory + multiscale presentation (+7)
    "biophysics_scaling.dual_scale_significance_lollipop",
    "actin_microtubule_morphometry.pca_silhouette_glyph_morphospace",
    "actin_microtubule_morphometry.airyscan_to_zone_territory_triptych",
    "intravital_imaging.territory_zone_overlay_intravital",
    "actin_microtubule_morphometry.territory_contact_network_overlay",
    "actin_microtubule_morphometry.zone_fraction_alluvial_sankey",
    "actin_microtubule_morphometry.colocalization_raincloud_per_metric",
    # W3 — cytoskeleton geometry + statistics (+9)
    "actin_microtubule_morphometry.actin_mt_angle_rose_with_distance_inset",
    "actin_microtubule_morphometry.protrusion_outline_with_cleveland_summary",
    "biophysics_scaling.censoring_mode_waterfall_cascade",
    "biophysics_scaling.confinement_energy_gauge_per_genotype",
    "spatial_statistics.kinhom_inhomogeneous_isotropy",
    "actin_microtubule_morphometry.edge_gradient_intensity_profile",
    "actin_microtubule_morphometry.cortex_composite_zone_descriptors",
    "actin_microtubule_morphometry.mt_mesh_density_compartment_compare",
    "biophysics_scaling.z_span_vs_width_with_euler_threshold",
    # W4 — narrative integration + final supplements (+9)
    "actin_microtubule_morphometry.pseudotime_thumbnail_strip",
    "grant_and_conceptual.narrative_cascade_river_with_xrefs",
    "biophysics_scaling.split_mirror_measured_vs_simulated",
    "biophysics_scaling.permanova_null_distribution",
    "actin_microtubule_morphometry.overlap_juxtaposition_quantification",
    "biophysics_scaling.force_budget_schematic_with_data",
    "biophysics_scaling.confinement_ratio_distribution_by_genotype",
    "biophysics_scaling.splay_taper_polarity_displacement_compound",
    "biophysics_scaling.sensitivity_sweep_alpha_width_seed_compound",
})


# ─────────────────────────── regex toolkit ──────────────────────────────
#
# Patterns are pre-compiled at import time for determinism and speed.

# 3D / volumetric / xz-imaging cues — recipes whose *name* contains any of
# these tokens are tagged "3D".
_RE_DIM_3D = re.compile(
    r"(?:_3d\b|^3d_|_xz_|^xz_|_z_stack|_zstack|airyscan|volumetric|3d_volume|"
    r"depth_proj|cortex_thickness|isosurface|xy_xz)"
)

# 1D / linear-along-arc cues.
_RE_DIM_1D = re.compile(
    r"(?:radial_profile|along_arc|linescan|line_scan|edge_gradient_intensity_profile)"
)

# Scalar / single-number callouts.
_RE_DIM_SCALAR = re.compile(
    r"(?:^scalar_|scalar_callout|single_value)"
)

# Anchor manuscript cues — case-insensitive substring search in the
# ``answers_question`` text *plus* the recipe name.
_ANCHOR_PATTERNS: dict[str, re.Pattern[str]] = {
    "DISC1": re.compile(r"\bdisc1\b", re.IGNORECASE),
    "CDC42": re.compile(r"\bcdc42\b|\bcdc-?42\b", re.IGNORECASE),
    "RhoA": re.compile(r"\brhoa\b", re.IGNORECASE),
    "RAC1": re.compile(r"\brac1\b|\brac-?1\b", re.IGNORECASE),
}

# Dynamics — kymograph / live / time-to- name patterns.
_RE_KYMOGRAPH = re.compile(r"kymograph", re.IGNORECASE)
_RE_LIVE_TIME = re.compile(
    r"(?:survival|latency|time_to_|residence_time|live_imaging|hazard|kaplan_meier|km_)",
    re.IGNORECASE,
)

# Factorial design markers.
_RE_FACTORIAL = re.compile(
    r"(?:sex_x_genotype|sex_x_treatment|two_way_anova|interaction_forest|"
    r"factorial_fingerprint|by_factor)",
    re.IGNORECASE,
)

# Equivalence / TOST markers.
_RE_EQUIVALENCE = re.compile(r"(?:\btost\b|equivalence)", re.IGNORECASE)

# Compartment-awareness markers.
_RE_COMPARTMENT = re.compile(
    r"(?:compartment|whole_cell|protrusion_internal|protrusion_vs|tip_vs_shaft|"
    r"per_compartment|compartment_paired)",
    re.IGNORECASE,
)

# Scale-awareness markers (in addition to whole-modality coverage).
_RE_SCALE = re.compile(
    r"(?:multiscale|polymer_to_network|scale_continuum|cross_scale|dual_scale|"
    r"\bscale_)",
    re.IGNORECASE,
)


# ─────────────────────────── per-tag rules ──────────────────────────────


def _wave_for(*, name: str, modality: str) -> str:
    """Return the wave label.  Falls back to ``_DEFAULT_WAVE`` (v1.0)."""
    full = f"{modality}.{name}"
    if full in _CDC42_PACK_FULLNAMES:
        return "v1.5.0-beta-cdc42_factorial_companion"
    if full in _DISC1_PACK_FULLNAMES:
        return "v1.4.0-beta-disc1_manuscript_companion"
    if modality in _MODALITY_WAVE:
        return _MODALITY_WAVE[modality]
    return _DEFAULT_WAVE


def _dimensionality_for(*, name: str) -> str:
    """Default ``"2D"``; ``"3D"`` / ``"1D"`` / ``"scalar"`` only on strong cue."""
    n = name.lower()
    if _RE_DIM_3D.search(n):
        return "3D"
    if _RE_DIM_1D.search(n):
        return "1D"
    if _RE_DIM_SCALAR.search(n):
        return "scalar"
    return "2D"


def _anchor_for(*, name: str, modality: str, answers_question: str) -> str:
    """Return one of the six anchor values, or ``UNKNOWN``.

    ``grant_and_conceptual`` is always ``"generic"`` (its recipes are
    biology-agnostic narrative substrates, never anchor-specific).  All
    other modalities use a substring scan over the recipe name + the
    ``answers_question`` text.
    """
    if modality == "grant_and_conceptual":
        return "generic"

    haystack = f"{name} {answers_question}"
    hits: list[str] = [
        anchor for anchor, pat in _ANCHOR_PATTERNS.items() if pat.search(haystack)
    ]
    if not hits:
        return UNKNOWN
    if len(hits) == 1:
        return hits[0]
    # Multiple hits: prefer the canonical combo if both DISC1 and CDC42
    # surface together; otherwise pick the first deterministically.
    if "DISC1" in hits and "CDC42" in hits:
        return "DISC1+CDC42"
    return sorted(hits)[0]


def _dynamics_for(*, name: str, family: str) -> str:
    """``ordered_pseudotime`` from family; ``kymograph`` / ``live`` from name."""
    if family == "timecourse_hierarchical_ci":
        return "ordered_pseudotime"
    n = name.lower()
    if _RE_KYMOGRAPH.search(n):
        return "kymograph"
    if _RE_LIVE_TIME.search(n):
        return "live"
    return "static"


def _factorial_for(*, name: str, modality: str, family: str) -> bool | str:
    """``True`` on confident match; ``UNKNOWN`` otherwise."""
    if _RE_FACTORIAL.search(name):
        return True
    # ``mixed_effects_models`` recipes are *often* factorial-aware but not
    # always.  Only flag True when the name *also* mentions interaction or
    # an explicit factorial design — the regex above already handles that.
    return UNKNOWN


def _equivalence_for(*, name: str, answers_question: str) -> bool | str:
    if _RE_EQUIVALENCE.search(name) or _RE_EQUIVALENCE.search(answers_question):
        return True
    return UNKNOWN


def _compartment_aware_for(*, name: str) -> bool | str:
    if _RE_COMPARTMENT.search(name):
        return True
    return UNKNOWN


def _scale_aware_for(*, name: str, modality: str) -> bool | str:
    if modality == "biophysics_scaling":
        return True
    if _RE_SCALE.search(name):
        return True
    return UNKNOWN


# ────────────────────────────── public API ──────────────────────────────


def auto_tag_recipe(
    *,
    name: str,
    modality: str,
    family: str,
    answers_question: str,
    required_fields: tuple[str, ...] = (),
    optional_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a closed-taxonomy tag dict for a single recipe.

    Each of the eight tag keys (``TAG_KEYS``) is mapped to either:
      * a high-confidence value (``str`` or ``bool``), or
      * the sentinel ``UNKNOWN`` (``"unknown"``) when no rule fires.

    The function is *pure* — it never touches the registry, the file
    system, or the network.  ``required_fields`` / ``optional_fields``
    are accepted for API symmetry with the registry so future tag rules
    can be added without changing the signature; the current rule set
    consults only ``name`` / ``modality`` / ``family`` /
    ``answers_question``.
    """
    # Currently unused but reserved for future field-driven heuristics.
    _ = required_fields
    _ = optional_fields

    return {
        "anchor": _anchor_for(
            name=name, modality=modality, answers_question=answers_question
        ),
        "dimensionality": _dimensionality_for(name=name),
        "dynamics": _dynamics_for(name=name, family=family),
        "factorial": _factorial_for(name=name, modality=modality, family=family),
        "equivalence": _equivalence_for(name=name, answers_question=answers_question),
        "compartment_aware": _compartment_aware_for(name=name),
        "scale_aware": _scale_aware_for(name=name, modality=modality),
        "wave": _wave_for(name=name, modality=modality),
    }


def auto_tag_all() -> dict[str, dict[str, Any]]:
    """Walk the live registry and return ``{full_name: tag_dict}``.

    ``full_name`` is the dotted form ``"<modality>.<name>"`` matching
    `_RegistryEntry.full_name` from `core.contract`.  Importing the
    registry triggers `ensure_all_imported()` so the tag map covers
    every registered recipe.
    """
    # Local import keeps the module importable from contexts where the
    # full registry is not yet wired (e.g. unit tests for the rule set).
    from ..core.contract import ensure_all_imported, list_recipes

    ensure_all_imported()
    out: dict[str, dict[str, Any]] = {}
    for entry in list_recipes():
        meta = entry.metadata
        out[entry.full_name] = auto_tag_recipe(
            name=meta.name,
            modality=meta.modality,
            family=meta.family.value,
            answers_question=meta.answers_question,
            required_fields=meta.required_fields,
            optional_fields=meta.optional_fields,
        )
    return out


__all__ = [
    "TAG_KEYS",
    "UNKNOWN",
    "auto_tag_all",
    "auto_tag_recipe",
]
