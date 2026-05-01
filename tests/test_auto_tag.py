"""Tests for the closed-taxonomy auto-tagger (Wave 2).

The unit tests are *table-driven* over seeded synthetic fixtures, so each
rule can be validated without depending on the live recipe registry.  A
single smoke test at the end exercises `auto_tag_all()` against the live
registry and asserts that every recipe receives all eight tag keys.
"""

from __future__ import annotations

from typing import Any

import pytest

from panelforge_figures.manifest.auto_tag import (
    TAG_KEYS,
    UNKNOWN,
    auto_tag_all,
    auto_tag_recipe,
)

# ─────────────────────────── unit fixtures ──────────────────────────────


def _tag(
    *,
    name: str,
    modality: str = "rhogtpase_dynamics",
    family: str = "phase_portrait",
    answers_question: str = "",
    required_fields: tuple[str, ...] = (),
    optional_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Helper — invoke the tagger with sensible defaults."""
    return auto_tag_recipe(
        name=name,
        modality=modality,
        family=family,
        answers_question=answers_question,
        required_fields=required_fields,
        optional_fields=optional_fields,
    )


# ─────────────────────────── shape contract ─────────────────────────────


def test_returned_dict_has_all_eight_tag_keys() -> None:
    tags = _tag(name="phase_portrait_bistable")
    assert set(tags.keys()) == set(TAG_KEYS)
    assert len(TAG_KEYS) == 8


def test_required_optional_fields_unused_but_accepted() -> None:
    """Signature accepts the fields without consulting them in current ruleset."""
    a = _tag(name="phase_portrait_bistable", required_fields=("x",))
    b = _tag(name="phase_portrait_bistable", required_fields=("x", "y"))
    assert a == b


# ─────────────────────────── anchor rules ───────────────────────────────


def test_anchor_disc1_substring_in_question() -> None:
    tags = _tag(
        name="phase_portrait_bistable",
        answers_question="What does the DISC1 mutant landscape look like?",
    )
    assert tags["anchor"] == "DISC1"


def test_anchor_cdc42_substring_in_question() -> None:
    tags = _tag(
        name="phase_portrait_bistable",
        answers_question="How does Cdc42 expression vary with sex × genotype?",
    )
    assert tags["anchor"] == "CDC42"


def test_anchor_rhoa_from_question() -> None:
    tags = _tag(
        name="phase_portrait_bistable",
        answers_question="When does RhoA oscillate, and where is the limit cycle?",
    )
    assert tags["anchor"] == "RhoA"


def test_anchor_rac1_from_question() -> None:
    tags = _tag(
        name="rac1_activation_field",
        answers_question="What does the RAC1 activation field show?",
    )
    assert tags["anchor"] == "RAC1"


def test_anchor_grant_modality_is_generic() -> None:
    tags = _tag(
        name="hypothesis_diagram",
        modality="grant_and_conceptual",
        family="conceptual",
        answers_question="Hypothesis schematic.",
    )
    assert tags["anchor"] == "generic"


def test_anchor_combo_disc1_plus_cdc42() -> None:
    tags = _tag(
        name="cross_anchor_panel",
        answers_question="Compare DISC1 mutant with Cdc42-CKO microglia.",
    )
    assert tags["anchor"] == "DISC1+CDC42"


def test_anchor_unknown_when_no_match() -> None:
    tags = _tag(
        name="generic_qa_panel",
        modality="meta_and_diagnostic",
        family="matrix",
        answers_question="A generic biology-agnostic QA matrix.",
    )
    assert tags["anchor"] == UNKNOWN


# ─────────────────────────── dimensionality rules ───────────────────────


def test_dimensionality_default_2d() -> None:
    assert _tag(name="phase_portrait_bistable")["dimensionality"] == "2D"


def test_dimensionality_3d_from_z_stack() -> None:
    assert _tag(name="airyscan_z_stack_volume")["dimensionality"] == "3D"


def test_dimensionality_3d_from_volumetric() -> None:
    assert _tag(name="volumetric_isosurface_panel")["dimensionality"] == "3D"


def test_dimensionality_1d_radial_profile() -> None:
    assert _tag(name="intensity_radial_profile")["dimensionality"] == "1D"


def test_dimensionality_scalar_callout() -> None:
    assert _tag(name="scalar_callout_panel")["dimensionality"] == "scalar"


# ─────────────────────────── dynamics rules ─────────────────────────────


def test_dynamics_static_default() -> None:
    assert _tag(name="phase_portrait_bistable")["dynamics"] == "static"


def test_dynamics_kymograph_from_name() -> None:
    assert _tag(name="curvature_kymograph_per_cell")["dynamics"] == "kymograph"


def test_dynamics_live_from_survival() -> None:
    assert _tag(name="cox_survival_forest")["dynamics"] == "live"


def test_dynamics_live_from_residence_time() -> None:
    assert (
        _tag(name="residence_time_kaplan_meier_with_ks_overlay")["dynamics"]
        == "live"
    )


def test_dynamics_ordered_pseudotime_from_family() -> None:
    tags = _tag(
        name="behavioral_fingerprint_trio_composite",
        family="timecourse_hierarchical_ci",
    )
    assert tags["dynamics"] == "ordered_pseudotime"


# ─────────────────────────── factorial rule ─────────────────────────────


def test_factorial_true_from_sex_x_genotype() -> None:
    tags = _tag(
        name="sex_x_genotype_interaction_forest",
        modality="mixed_effects_models",
        family="coef_forest",
    )
    assert tags["factorial"] is True


def test_factorial_true_from_two_way_anova() -> None:
    tags = _tag(
        name="two_way_anova_summary_plot",
        modality="mixed_effects_models",
        family="coef_forest",
    )
    assert tags["factorial"] is True


def test_factorial_unknown_default() -> None:
    assert _tag(name="phase_portrait_bistable")["factorial"] == UNKNOWN


# ─────────────────────────── equivalence rule ───────────────────────────


def test_equivalence_true_from_tost() -> None:
    tags = _tag(
        name="equivalence_forest_with_tost_bounds",
        modality="biophysics_scaling",
    )
    assert tags["equivalence"] is True


def test_equivalence_true_from_question_text() -> None:
    tags = _tag(
        name="generic_panel",
        answers_question="TOST equivalence check across conditions.",
    )
    assert tags["equivalence"] is True


def test_equivalence_unknown_default() -> None:
    assert _tag(name="phase_portrait_bistable")["equivalence"] == UNKNOWN


# ─────────────────────────── compartment-aware rule ─────────────────────


def test_compartment_aware_true_from_compartment() -> None:
    tags = _tag(name="compartment_paired_delta_scatter")
    assert tags["compartment_aware"] is True


def test_compartment_aware_true_from_whole_cell() -> None:
    tags = _tag(name="whole_cell_vs_protrusion_density")
    assert tags["compartment_aware"] is True


def test_compartment_aware_unknown_default() -> None:
    assert (
        _tag(name="phase_portrait_bistable")["compartment_aware"] == UNKNOWN
    )


# ─────────────────────────── scale-aware rule ───────────────────────────


def test_scale_aware_true_for_biophysics_scaling_modality() -> None:
    tags = _tag(
        name="energy_landscape_1d_cartoon",
        modality="biophysics_scaling",
    )
    assert tags["scale_aware"] is True


def test_scale_aware_true_from_multiscale_name() -> None:
    tags = _tag(name="multiscale_governance_diagram", modality="grant_and_conceptual")
    assert tags["scale_aware"] is True


def test_scale_aware_unknown_default() -> None:
    assert _tag(name="phase_portrait_bistable")["scale_aware"] == UNKNOWN


# ────────────────────────────── wave rule ───────────────────────────────


def test_wave_default_v1_0() -> None:
    tags = _tag(name="phase_portrait_bistable", modality="rhogtpase_dynamics")
    assert tags["wave"] == "v1.0"


def test_wave_biophysics_scaling_pack() -> None:
    tags = _tag(
        name="energy_landscape_1d_cartoon",
        modality="biophysics_scaling",
    )
    assert tags["wave"] == "v1.2.0-beta-biophysics_scaling"


def test_wave_intravital_imaging_pack() -> None:
    tags = _tag(
        name="state_kinematic_spectral_embedding",
        modality="intravital_imaging",
    )
    assert tags["wave"] == "v1.3.0-beta-intravital_imaging"


def test_wave_cdc42_pack_recipe() -> None:
    tags = _tag(
        name="bayes_factor_arrow_plot",
        modality="meta_and_diagnostic",
        family="coef_forest",
    )
    assert tags["wave"] == "v1.5.0-beta-factorial_design_companion"


def test_wave_disc1_pack_recipe() -> None:
    tags = _tag(
        name="alternative_hypothesis_exclusion_table",
        modality="meta_and_diagnostic",
        family="matrix",
    )
    assert tags["wave"] == "v1.4.0-beta-cytoskeletal_morphometry_companion"


# ─────────────────────────── determinism check ──────────────────────────


def test_auto_tag_recipe_is_deterministic() -> None:
    """Same input → identical dict, repeated calls."""
    kwargs = dict(
        name="bayes_factor_arrow_plot",
        modality="meta_and_diagnostic",
        family="coef_forest",
        answers_question="Bayes-factor arrow plot for cdc42 sex × genotype.",
    )
    a = auto_tag_recipe(**kwargs)
    b = auto_tag_recipe(**kwargs)
    assert a == b


# ─────────────────────────── representative recipes table ───────────────
#
# A single parametrised case spanning all 8 tag dimensions.  Each row
# encodes a known-good recipe and the *minimum* tag values it must hit;
# we don't assert on tags that aren't load-bearing for that row.

_REPRESENTATIVE_CASES: list[dict[str, Any]] = [
    # (1) Pure phase portrait — RhoA anchor, 2D, static.
    {
        "name": "phase_portrait_bistable",
        "modality": "rhogtpase_dynamics",
        "family": "phase_portrait",
        "answers_question": (
            "What does the bistable RhoA landscape look like — two wells and a saddle?"
        ),
        "expected": {
            "anchor": "RhoA",
            "dimensionality": "2D",
            "dynamics": "static",
            "wave": "v1.0",
        },
    },
    # (2) Equivalence + biophysics_scaling pack + scale-aware.
    {
        "name": "equivalence_forest_with_tost_bounds",
        "modality": "biophysics_scaling",
        "family": "coef_forest",
        "answers_question": "TOST equivalence forest across conditions.",
        "expected": {
            "equivalence": True,
            "scale_aware": True,
            "wave": "v1.2.0-beta-biophysics_scaling",
        },
    },
    # (3) Cdc42 pack — factorial + scale_aware + cdc42 wave.
    {
        "name": "two_way_anova_summary_plot",
        "modality": "mixed_effects_models",
        "family": "coef_forest",
        "answers_question": "Two-way ANOVA summary for sex × genotype interaction.",
        "expected": {
            "factorial": True,
            "anchor": UNKNOWN,
            "wave": "v1.5.0-beta-factorial_design_companion",
        },
    },
    # (4) Cdc42 pack — explicit Cdc42 anchor in question.
    {
        "name": "sex_x_genotype_interaction_forest",
        "modality": "mixed_effects_models",
        "family": "coef_forest",
        "answers_question": "How does Cdc42 expression × sex interact?",
        "expected": {
            "factorial": True,
            "anchor": "CDC42",
        },
    },
    # (5) Compartment-aware + DISC1 wave (W3 disc1 pack recipe).
    {
        "name": "mt_mesh_density_compartment_compare",
        "modality": "actin_microtubule_morphometry",
        "family": "split_violin",
        "answers_question": "How does MT mesh density differ by compartment?",
        "expected": {
            "compartment_aware": True,
            "wave": "v1.4.0-beta-cytoskeletal_morphometry_companion",
        },
    },
    # (6) Kymograph dynamics.
    {
        "name": "curvature_kymograph_per_cell",
        "modality": "actin_microtubule_morphometry",
        "family": "heatmap",
        "answers_question": "Edge-curvature kymograph per cell.",
        "expected": {"dynamics": "kymograph"},
    },
    # (7) Ordered-pseudotime dynamics from family.
    {
        "name": "behavioral_fingerprint_trio_composite",
        "modality": "actin_microtubule_morphometry",
        "family": "timecourse_hierarchical_ci",
        "answers_question": "Pseudotime trio composite of behavioral state.",
        "expected": {"dynamics": "ordered_pseudotime"},
    },
    # (8) 3D Airyscan recipe.
    {
        "name": "airyscan_segmentation_mosaic",
        "modality": "actin_microtubule_morphometry",
        "family": "matrix",
        "answers_question": "Airyscan raw + segmentation mosaic with scale bars.",
        "expected": {"dimensionality": "3D"},
    },
    # (9) 1D radial profile.
    {
        "name": "intensity_radial_profile",
        "modality": "actin_microtubule_morphometry",
        "family": "scatter_collapse",
        "answers_question": "Radial intensity profile.",
        "expected": {"dimensionality": "1D"},
    },
    # (10) Generic / grant_and_conceptual.
    {
        "name": "hypothesis_diagram",
        "modality": "grant_and_conceptual",
        "family": "conceptual",
        "answers_question": "Hypothesis cartoon for the proposal.",
        "expected": {"anchor": "generic"},
    },
    # (11) Live dynamics from survival.
    {
        "name": "residence_time_kaplan_meier_with_ks_overlay",
        "modality": "intravital_imaging",
        "family": "diagnostic_curve",
        "answers_question": "Residence-time KM curve with KS overlay.",
        "expected": {
            "dynamics": "live",
            "wave": "v1.5.0-beta-factorial_design_companion",
        },
    },
]


@pytest.mark.parametrize("case", _REPRESENTATIVE_CASES, ids=lambda c: c["name"])
def test_representative_recipe_table(case: dict[str, Any]) -> None:
    tags = auto_tag_recipe(
        name=case["name"],
        modality=case["modality"],
        family=case["family"],
        answers_question=case["answers_question"],
    )
    for k, v in case["expected"].items():
        assert tags[k] == v, (
            f"recipe {case['name']!r}: tag {k!r} expected {v!r}, got {tags[k]!r}"
        )


# ─────────────────────────── live registry smoke ────────────────────────


def test_auto_tag_all_smoke() -> None:
    """Walk the live registry — no exceptions, every recipe gets 8 tags."""
    out = auto_tag_all()
    assert isinstance(out, dict)
    assert len(out) > 0, "registry walk returned an empty tag map"
    for full_name, tags in out.items():
        assert "." in full_name, f"unexpected full_name {full_name!r}"
        missing = set(TAG_KEYS) - set(tags.keys())
        assert not missing, f"{full_name}: missing tag keys {missing}"
        # Every value is either a known sentinel/string or a bool.
        for k, v in tags.items():
            assert isinstance(v, str | bool), (
                f"{full_name}.{k}: unexpected value type {type(v).__name__}"
            )
