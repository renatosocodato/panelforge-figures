"""Tests for ``manifest.reporting_checklists`` — Elevation 12 (v3.6.0).

Covers:

* Each of the four checklist generators emits the expected number of
  items: ARRIVE 2.0 = 10, CONSORT 2010 = 25, STARD 2015 = 30,
  MIQE >= 40.
* ``auto_classify_item`` heuristics: keyword match flips to
  ``present``; absent keywords leave ``unknown``; ARRIVE-2a flips to
  ``present`` when a contract.min_n is set; ARRIVE-4a flips when a
  randomisation seed appears in the provenance sidecar.
* ``render_checklist_latex`` / ``render_checklist_markdown`` include
  every item.
* CLI smoke for each of the four ``figures checklist`` subcommands.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.reporting_checklists import (
    ARRIVE_2_0_ITEMS,
    CONSORT_2010_ITEMS,
    MIQE_ITEMS,
    STARD_2015_ITEMS,
    Checklist,
    ChecklistError,
    ChecklistItem,
    ChecklistItemStatus,
    ChecklistKind,
    auto_classify_item,
    generate_arrive_checklist,
    generate_consort_checklist,
    generate_miqe_checklist,
    generate_stard_checklist,
    render_checklist_latex,
    render_checklist_markdown,
)

# ─────────────────────────── 1. constant tables surface ────────────────────────


def test_arrive_table_has_ten_items() -> None:
    assert len(ARRIVE_2_0_ITEMS) == 10


def test_consort_table_has_25_items() -> None:
    assert len(CONSORT_2010_ITEMS) == 25


def test_stard_table_has_30_items() -> None:
    assert len(STARD_2015_ITEMS) == 30


def test_miqe_table_has_at_least_40_items() -> None:
    assert len(MIQE_ITEMS) >= 40


def test_arrive_item_ids_are_unique() -> None:
    ids = [item[0] for item in ARRIVE_2_0_ITEMS]
    assert len(ids) == len(set(ids))


def test_consort_item_ids_are_unique() -> None:
    ids = [item[0] for item in CONSORT_2010_ITEMS]
    assert len(ids) == len(set(ids))


def test_stard_item_ids_are_unique() -> None:
    ids = [item[0] for item in STARD_2015_ITEMS]
    assert len(ids) == len(set(ids))


def test_miqe_item_ids_are_unique() -> None:
    ids = [item[0] for item in MIQE_ITEMS]
    assert len(ids) == len(set(ids))


# ─────────────────────────── 2. generate_* basic shape ────────────────────────


def test_generate_arrive_returns_correct_kind(tmp_path: Path) -> None:
    cl = generate_arrive_checklist(tmp_path)
    assert isinstance(cl, Checklist)
    assert cl.kind == ChecklistKind.arrive
    assert len(cl.items) == 10


def test_generate_consort_returns_correct_kind(tmp_path: Path) -> None:
    cl = generate_consort_checklist(tmp_path)
    assert cl.kind == ChecklistKind.consort
    assert len(cl.items) == 25


def test_generate_stard_returns_correct_kind(tmp_path: Path) -> None:
    cl = generate_stard_checklist(tmp_path)
    assert cl.kind == ChecklistKind.stard
    assert len(cl.items) == 30


def test_generate_miqe_returns_correct_kind(tmp_path: Path) -> None:
    cl = generate_miqe_checklist(tmp_path)
    assert cl.kind == ChecklistKind.miqe
    assert len(cl.items) >= 40


def test_generator_raises_on_missing_project_root(tmp_path: Path) -> None:
    with pytest.raises(ChecklistError):
        generate_arrive_checklist(tmp_path / "no_such_dir")


# ─────────────────────────── 3. auto_classify_item heuristics ──────────────────


def test_auto_classify_keyword_match_flips_to_present(tmp_path: Path) -> None:
    """A manuscript containing 'sample size n=30 per group' marks ARRIVE-2a present."""
    status, evidence, _ = auto_classify_item(
        "ARRIVE-2a",
        "Sample size",
        "Sample size for each experimental group",
        project_root=tmp_path,
        manuscript_text="we used a sample size of n=30 per group",
    )
    assert status == ChecklistItemStatus.present
    assert "sample size" in evidence.lower() or "n=" in evidence.lower()


def test_auto_classify_no_evidence_returns_unknown(tmp_path: Path) -> None:
    status, evidence, _ = auto_classify_item(
        "ARRIVE-5a",
        "Blinding",
        "Whether the investigators were blinded",
        project_root=tmp_path,
        manuscript_text="we did stuff",
    )
    assert status == ChecklistItemStatus.unknown
    assert evidence == ""


def test_auto_classify_contract_evidence_for_sample_size(tmp_path: Path) -> None:
    """ARRIVE-2a flips to present when contract_fields.any_min_n is True."""
    status, evidence, loc = auto_classify_item(
        "ARRIVE-2a",
        "Sample size",
        "...",
        project_root=tmp_path,
        manuscript_text=None,
        contract_fields={"any_min_n": True},
    )
    assert status == ChecklistItemStatus.present
    assert "min_n_per_group" in evidence or "min_n_per_group" in loc.lower() or "statistical_contract" in loc.lower()


def test_auto_classify_randomisation_seed_via_provenance(tmp_path: Path) -> None:
    """ARRIVE-4a flips to present when a provenance.json carries a random_seed."""
    workspace = tmp_path / "panelforge_workspace" / "figures"
    workspace.mkdir(parents=True)
    sidecar = workspace / "figure_1.pdf.provenance.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "figure_path": "figure_1.pdf",
                "figure_sha256": "a" * 64,
                "rendered_at": "2026-01-01T00:00:00Z",
                "recipe": {},
                "data": {"sources": [], "column_mapping": {}},
                "scorer": {"random_seed": 42},
            }
        ),
        encoding="utf-8",
    )
    status, evidence, _ = auto_classify_item(
        "ARRIVE-4a",
        "Randomisation",
        "Strategy used to randomise",
        project_root=tmp_path,
    )
    assert status == ChecklistItemStatus.present
    assert "random_seed" in evidence


def test_auto_classify_organism_yaml_for_arrive_8a(tmp_path: Path) -> None:
    """ARRIVE-8a flips to present when organisms block is in YAML."""
    pytest.importorskip("yaml")
    (tmp_path / "panelforge.project.yaml").write_text(
        "organisms:\n  - name: C57BL/6J\n    source: JAX\n    identifier: RRID\n",
        encoding="utf-8",
    )
    status, _, loc = auto_classify_item(
        "ARRIVE-8a",
        "Experimental animals",
        "Species, strain, sex, age",
        project_root=tmp_path,
    )
    assert status == ChecklistItemStatus.present
    assert "panelforge.project.yaml" in loc


def test_auto_classify_unknown_prefix_returns_unknown(tmp_path: Path) -> None:
    status, _, _ = auto_classify_item(
        "FOO-1",
        "Section",
        "Description",
        project_root=tmp_path,
    )
    assert status == ChecklistItemStatus.unknown


# ─────────────────────────── 4. checklist counts add up ────────────────────────


def test_checklist_counts_sum_to_total_items(tmp_path: Path) -> None:
    cl = generate_arrive_checklist(tmp_path)
    total = cl.n_present + cl.n_absent + cl.n_not_applicable + cl.n_unknown
    assert total == len(cl.items)


def test_checklist_with_manuscript_flips_some_items(tmp_path: Path) -> None:
    """A rich manuscript triggers ``present`` on multiple ARRIVE items."""
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(
        """\
# Methods
We used n=30 mice per group. Animals were randomised to control or treatment.
Investigators were blinded to group allocation. Mice were C57BL/6J obtained
from Jackson Laboratory. We measured the primary outcome at day 7.
Anesthesia was provided with isoflurane. Statistical analysis used a
two-way ANOVA with Bonferroni correction. Cohen's d is reported with
95% CI. Inclusion and exclusion criteria are listed below.
""",
        encoding="utf-8",
    )
    cl = generate_arrive_checklist(tmp_path, manuscript_path=manuscript)
    assert cl.n_present >= 5
    # At minimum the obvious keywords should fire.
    by_id = {it.item_id: it for it in cl.items}
    assert by_id["ARRIVE-2a"].status == ChecklistItemStatus.present  # sample size
    assert by_id["ARRIVE-8a"].status == ChecklistItemStatus.present  # mice / C57BL/6J
    assert by_id["ARRIVE-5a"].status == ChecklistItemStatus.present  # blinding


# ─────────────────────────── 5. renderers ────────────────────────────────────


def test_render_checklist_latex_contains_every_item(tmp_path: Path) -> None:
    cl = generate_arrive_checklist(tmp_path)
    body = render_checklist_latex(cl)
    assert "longtable" in body
    for it in cl.items:
        assert it.item_id in body


def test_render_checklist_markdown_contains_every_item(tmp_path: Path) -> None:
    cl = generate_consort_checklist(tmp_path)
    body = render_checklist_markdown(cl)
    assert "CONSORT 2010" in body
    for it in cl.items:
        assert it.item_id in body
    # Status checkboxes appear.
    assert "[?]" in body or "[x]" in body or "[ ]" in body


def test_render_checklist_latex_status_symbols_present(tmp_path: Path) -> None:
    """Render must include at least one status colour macro."""
    cl = generate_miqe_checklist(tmp_path)
    body = render_checklist_latex(cl)
    # By default all items are ``unknown`` → orange ?
    assert "textcolor" in body
    assert "?" in body


def test_render_checklist_markdown_includes_summary_line(tmp_path: Path) -> None:
    cl = generate_stard_checklist(tmp_path)
    body = render_checklist_markdown(cl)
    assert "present" in body.lower()
    assert "absent" in body.lower()


# ─────────────────────────── 6. CLI smoke (one per kind) ──────────────────────


def test_cli_checklist_arrive_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["checklist", "arrive", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "ARRIVE 2.0" in result.output


def test_cli_checklist_consort_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["checklist", "consort", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "CONSORT 2010" in result.output


def test_cli_checklist_stard_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["checklist", "stard", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "STARD 2015" in result.output


def test_cli_checklist_miqe_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["checklist", "miqe", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "MIQE" in result.output


def test_cli_checklist_out_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "arrive.md"
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "checklist", "arrive", str(tmp_path),
            "--format", "markdown",
            "--out", str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "ARRIVE 2.0" in body


def test_checklist_item_dataclass_default_status_is_unknown() -> None:
    item = ChecklistItem(
        item_id="ARRIVE-1a",
        section="Study design",
        description="...",
    )
    assert item.status == ChecklistItemStatus.unknown
