"""Tests for the Wave-3 project-inference module (``project_scan.py``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from panelforge_figures.manifest.intake import IntakeAnswer
from panelforge_figures.manifest.project_scan import (
    InferredAnswer,
    ProjectScanResult,
    scan_project,
    to_intake_pre_filled,
)

# ─────────────────────────── helpers ────────────────────────────────────


AVAILABLE_MODALITIES = (
    "actin_microtubule_morphometry",
    "biophysics_scaling",
    "intravital_imaging",
    "rhogtpase_dynamics",
    "calcium_signaling",
    "spatial_statistics",
    "diffusion_and_tracking",
    "fret_biosensors",
    "redox_imaging",
    "single_cell_embeddings",
    "omics_differential",
    "mixed_effects_models",
    "network_and_pathway",
    "dose_response_pharmacology",
    "gillespie_stochastic",
    "clinical_cohort",
    "cryoem_and_structure",
    "sensitivity_analysis",
    "grant_and_conceptual",
    "meta_and_diagnostic",
)


def _seed(root: Path, files: dict[str, str]) -> None:
    """Materialise a synthetic project tree under ``root``."""
    for relpath, body in files.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


# ───────────────────────────── tests ────────────────────────────────────


def test_empty_project_yields_defaults(tmp_path: Path) -> None:
    """No documents + just an empty data/ → all answers at default confidence."""
    (tmp_path / "data").mkdir()

    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    assert isinstance(result, ProjectScanResult)
    assert result.panelforge_yaml_present is False
    assert set(result.answers.keys()) == {
        "factorial_design",
        "equivalence_claims",
        "manuscript_anchor",
        "dynamics_needed",
        "dimensionality",
        "modalities_in_scope",
        "hard_filters",
        "shortlist_size",
    }

    # Defaults — confidences should all sit in the 0.3-0.7 default band.
    for ans in result.answers.values():
        assert isinstance(ans, InferredAnswer)
        assert 0.3 <= ans.confidence <= 0.7

    # Spec-default values
    assert result.answers["factorial_design"].value is False
    assert result.answers["equivalence_claims"].value is False
    assert result.answers["manuscript_anchor"].value == "none"
    assert result.answers["dynamics_needed"].value == "static"
    assert result.answers["dimensionality"].value == "2D"
    assert result.answers["hard_filters"].value == {
        "compartment_aware": False,
        "scale_aware": False,
        "factorial_only": False,
    }
    assert result.answers["shortlist_size"].value == 12


def test_disc1_project_infers_anchor_equivalence_3d_compartment(tmp_path: Path) -> None:
    """A DISC1 manuscript with the canonical keyword cluster."""
    _seed(
        tmp_path,
        {
            "manuscript.md": (
                "# DISC1 cortical migration in lissencephaly\n\n"
                "We use TOST equivalence testing with pre-registered bounds.\n"
                "Imaging is performed on Airyscan z-stacks for compartment-aware\n"
                "morphometry of actin protrusions.\n"
            ),
            "methods.md": (
                "Equivalence margins were set at +/- 0.2.  We compare\n"
                "whole-cell vs protrusion compartments.\n"
            ),
        },
    )

    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    # Anchor → DISC1 with high confidence
    anchor = result.answers["manuscript_anchor"]
    assert anchor.value == "DISC1"
    assert anchor.confidence >= 0.9

    # Equivalence claims clearly true
    eq = result.answers["equivalence_claims"]
    assert eq.value is True
    assert eq.confidence >= 0.7

    # Dimensionality is 3D or mixed (z-stack signal)
    dim = result.answers["dimensionality"]
    assert dim.value in {"3D", "mixed"}
    assert dim.confidence >= 0.7

    # Compartment-aware hard filter flips on
    hf = result.answers["hard_filters"]
    assert hf.value["compartment_aware"] is True


def test_cdc42_factorial_project_infers_anchor_and_factorial(tmp_path: Path) -> None:
    """A Cdc42 conditional-knockout 2x2 factorial project."""
    _seed(
        tmp_path,
        {
            "methods.md": (
                "We used Cdc42 CKO mice in a 2x2 sex x genotype factorial design.\n"
                "Statistical analysis: ANOVA with interaction term across "
                "sex and genotype.\n"
            ),
            "manuscript.md": (
                "Cdc42 is essential for protrusion stability; this is the\n"
                "manuscript anchor.\n"
            ),
        },
    )

    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    anchor = result.answers["manuscript_anchor"]
    assert anchor.value == "CDC42"
    assert anchor.confidence >= 0.7

    fd = result.answers["factorial_design"]
    assert fd.value is True
    assert fd.confidence >= 0.7


def test_panelforge_yaml_explicit_config_wins(tmp_path: Path) -> None:
    """A panelforge.project.yaml file sets fields at confidence 1.0."""
    _seed(
        tmp_path,
        {
            "panelforge.project.yaml": (
                "anchor: DISC1\n"
                "factorial: true\n"
                "shortlist_size: 7\n"
                "modalities: [rhogtpase_dynamics, sensitivity_analysis]\n"
            ),
        },
    )

    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    assert result.panelforge_yaml_present is True

    assert result.answers["manuscript_anchor"].value == "DISC1"
    assert result.answers["manuscript_anchor"].confidence == 1.0

    assert result.answers["factorial_design"].value is True
    assert result.answers["factorial_design"].confidence == 1.0

    assert result.answers["shortlist_size"].value == 7
    assert result.answers["shortlist_size"].confidence == 1.0

    mod = result.answers["modalities_in_scope"]
    assert mod.value == ("rhogtpase_dynamics", "sensitivity_analysis")
    assert mod.confidence == 1.0


def test_data_timeseries_csv_biases_dynamics_to_live_or_kymograph(tmp_path: Path) -> None:
    """A CSV with t_s/frame columns → dynamics_needed leans toward live."""
    _seed(
        tmp_path,
        {
            "data/timeseries_t_s_frame.csv": (
                "t_s,frame,intensity\n0.0,0,1.2\n0.5,1,1.4\n"
            ),
        },
    )

    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    dy = result.answers["dynamics_needed"]
    assert dy.value in {"live", "kymograph"}
    assert dy.confidence > 0.5


def test_to_intake_pre_filled_filters_low_confidence(tmp_path: Path) -> None:
    """Answers below the threshold are dropped from the intake pre-fill dict."""
    # Empty project → most answers are at default (≤0.7 except shortlist).
    (tmp_path / "data").mkdir()
    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    pre = to_intake_pre_filled(result, confidence_threshold=0.7)

    # All retained answers have confidence ≥ 0.7
    for ans in pre.values():
        assert isinstance(ans, IntakeAnswer)
        assert ans.confidence >= 0.7
        assert ans.source == "inferred"

    # All dropped answers had confidence < 0.7
    for field_name, raw in result.answers.items():
        if raw.confidence < 0.7:
            assert field_name not in pre

    # And the question_id mapping is the canonical one.
    if "shortlist_size" in pre:
        assert pre["shortlist_size"].question_id == 8


def test_to_intake_pre_filled_with_yaml_keeps_all_high_conf(tmp_path: Path) -> None:
    """A panelforge.project.yaml drives confidence to 1.0 → everything retained."""
    _seed(
        tmp_path,
        {
            "panelforge.project.yaml": (
                "anchor: CDC42\nfactorial: true\nshortlist_size: 9\n"
            ),
        },
    )
    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)
    pre = to_intake_pre_filled(result)

    assert "manuscript_anchor" in pre
    assert pre["manuscript_anchor"].value == "CDC42"
    assert pre["manuscript_anchor"].confidence == 1.0

    assert "factorial_design" in pre
    assert pre["factorial_design"].value is True

    assert "shortlist_size" in pre
    assert pre["shortlist_size"].value == 9


def test_files_read_records_provenance(tmp_path: Path) -> None:
    """``files_read`` should include all priority-1 documents that were present."""
    _seed(
        tmp_path,
        {
            "manuscript.md": "# project\n",
            "methods.md": "methods\n",
            "panelforge.project.yaml": "anchor: none\n",
        },
    )
    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)
    names = {p.name for p in result.files_read}
    assert "manuscript.md" in names
    assert "methods.md" in names
    assert "panelforge.project.yaml" in names


def test_inferred_answer_label_bands(tmp_path: Path) -> None:
    """Confidence bands map to the documented labels."""
    _seed(
        tmp_path,
        {
            "panelforge.project.yaml": "anchor: DISC1\n",
        },
    )
    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)

    # 1.0 confidence → "[inferred]"
    assert result.answers["manuscript_anchor"].label == "[inferred]"
    # 0.3-0.5 confidence → "[asking]"
    assert result.answers["equivalence_claims"].label == "[asking]"


@pytest.mark.parametrize("missing_dir", ["data", "figures"])
def test_missing_optional_dirs_do_not_crash(tmp_path: Path, missing_dir: str) -> None:
    """The scanner is resilient to missing data/ or figures/ directories."""
    _seed(tmp_path, {"manuscript.md": "tiny project\n"})
    # ensure neither data/ nor figures/ exists
    assert not (tmp_path / missing_dir).exists()
    result = scan_project(tmp_path, available_modalities=AVAILABLE_MODALITIES)
    # Still have all 8 answers
    assert len(result.answers) == 8
