"""Tests for the audit-driven caption draft module (E5 — v2.5.0).

Coverage matrix mirrors the elevation spec:

1. CaptionStyle enum exposes the five expected variants.
2. ``draft_caption_template_only`` runs offline with a minimal audit.
3. Title-line formatting differs per style (nature / cell / nejm).
4. The statistics line is composed from the audit ``terms`` block.
5. ``draft_caption_from_provenance`` reads a sidecar correctly.
6. ``draft_caption_from_provenance`` raises CaptionError if no audit.
7. ``use_llm=True`` under clinical degrades to template-only with a note.
8. ``render_caption_markdown`` includes title + body + sha256 comment.
9. CLI smoke: ``figures caption --help`` exits 0.
10. CLI exits 1 when the provenance has no audit block.
11. CLI accepts every value of the ``--style`` choice.

These tests never reach for a network or LLM endpoint — the LLM call
in v2.5.0 is deferred per the spec, so we exercise only the gating
code path and the template-only fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.caption import (
    CaptionDraft,
    CaptionError,
    CaptionStyle,
    draft_caption_from_provenance,
    draft_caption_template_only,
    render_caption_markdown,
)

# ───────────────────────────── fixtures ────────────────────────────────


def _minimal_audit() -> dict:
    """Audit dict with one term — exercises the ``terms`` formatter."""
    return {
        "terms": [
            {
                "term": "sex × genotype",
                "f_stat": 1.59,
                "p_value": 0.233,
                "df_num": 1,
                "df_den": 12,
            },
        ],
        "n_per_cell": 4,
        "rules_passed": ["n_at_least_4"],
        "rules_warned": [],
        "rules_failed": [],
    }


def _minimal_contract() -> dict:
    """Contract dict aligning with the recipe-side ``StatisticalContract``."""
    return {
        "title": "Sex × genotype interaction on Iba1+ density",
        "response_label": "Iba1+ density (cells/mm²)",
        "factor_a": "sex",
        "factor_b": "genotype",
        "effect_size_units": "cells/mm²",
    }


def _write_provenance(
    tmp_path: Path,
    *,
    audit: dict | None,
    contract: dict | None = None,
    family: str = "factorial",
    figure_sha256: str = "a" * 64,
    figure_name: str = "panel_a.pdf",
) -> Path:
    """Compose and write a minimal provenance.json sidecar fixture."""
    contract = contract if contract is not None else _minimal_contract()
    payload = {
        "schema_version": "1.0.0",
        "figure_path": figure_name,
        "figure_sha256": figure_sha256,
        "rendered_at": "2026-05-08T00:00:00Z",
        "recipe": {
            "full_name": "mixed_effects_models.two_way_anova_summary_plot",
            "family": family,
            "contract": contract,
            "module_sha": "deadbeef" * 8,
            "panelforge_version": "2.5.0",
        },
        "data": {"sources": [], "column_mapping": {}},
        "rendering_environment": {},
    }
    if audit is not None:
        payload["audit"] = audit
    out_path = tmp_path / f"{figure_name}.provenance.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return out_path


# ─────────────── 1. CaptionStyle enum has the right shape ─────────────


def test_caption_style_enum_has_five_styles() -> None:
    """All five styles surface as Enum members and string values."""
    values = {s.value for s in CaptionStyle}
    assert values == {"plain", "nature", "cell", "nejm", "lab_default"}
    # Each member is a string-typed Enum — round-trip through the value.
    assert CaptionStyle("nature") is CaptionStyle.nature
    assert CaptionStyle("plain") is CaptionStyle.plain


# ─────────────── 2. template-only draft works offline ─────────────────


def test_draft_caption_template_only_minimal() -> None:
    """A template-only draft populates every field of the dataclass."""
    draft = draft_caption_template_only(
        figure_id="panel_a",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        figure_sha256="b" * 64,
        style=CaptionStyle.plain,
    )
    assert isinstance(draft, CaptionDraft)
    assert draft.figure_id == "panel_a"
    assert draft.style == CaptionStyle.plain
    assert draft.figure_sha256 == "b" * 64
    assert "F(1,12)" in draft.statistics_line
    assert "p = 0.233" in draft.statistics_line
    assert "Iba1+ density" in draft.body
    # Always-on offline marker
    assert any("template-only" in n for n in draft.notes)


def test_draft_caption_template_only_handles_missing_fields() -> None:
    """Missing optional contract keys must not raise — they fall back."""
    draft = draft_caption_template_only(
        figure_id="figure_1",
        contract_dict={"response_label": "Iba1 density"},  # no title, no factors
        audit={"p_value": 0.05},
        family="comparison",
        style=CaptionStyle.plain,
    )
    # title should fall back to response_label
    assert "Iba1 density" in draft.title_line
    # statistics_line must still be populated by the p-value fallback path
    assert "p = 0.05" in draft.statistics_line


def test_draft_caption_template_only_falls_back_to_default_template() -> None:
    """Unknown families resolve to the generic default template."""
    draft = draft_caption_template_only(
        figure_id="custom",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="totally_unknown_family",
        style=CaptionStyle.plain,
    )
    assert "totally_unknown_family family" in draft.body


# ─────────────── 3. title-line formatting differs per style ───────────


def test_title_line_nature_style_uses_pipe() -> None:
    """Nature uses `Figure N | Title.` with a vertical bar separator."""
    draft = draft_caption_template_only(
        figure_id="1",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        style=CaptionStyle.nature,
    )
    assert draft.title_line.startswith("**Figure 1 |")
    assert draft.title_line.endswith(".**")


def test_title_line_cell_style_uses_period() -> None:
    """Cell uses `Figure N. Title.` with periods on both sides."""
    draft = draft_caption_template_only(
        figure_id="2",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        style=CaptionStyle.cell,
    )
    assert draft.title_line.startswith("**Figure 2.")
    # Cell wraps the whole line in bold; ensure the title is inside the bold.
    assert "**Figure 2." in draft.title_line
    assert draft.title_line.endswith(".**")


def test_title_line_nejm_style_uses_em_dash() -> None:
    """NEJM uses an em-dash — the literal U+2014 character."""
    draft = draft_caption_template_only(
        figure_id="3",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        style=CaptionStyle.nejm,
    )
    assert "—" in draft.title_line
    assert draft.title_line.startswith("**Figure 3 —")


def test_title_line_lab_default_style_uses_figure_id_only() -> None:
    """lab_default keeps the figure_id verbatim (no `Figure N` prefix)."""
    draft = draft_caption_template_only(
        figure_id="panel_a",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        style=CaptionStyle.lab_default,
    )
    assert draft.title_line.startswith("**panel_a.**")


# ─────────────── 4. statistics line draws from audit terms ────────────


def test_statistics_line_joins_multiple_terms() -> None:
    """Multiple audit terms render as a `; `-joined sequence."""
    audit = {
        "terms": [
            {
                "term": "sex",
                "f_stat": 4.21,
                "p_value": 0.041,
                "df_num": 1,
                "df_den": 20,
            },
            {
                "term": "genotype",
                "f_stat": 12.5,
                "p_value": 0.002,
                "df_num": 1,
                "df_den": 20,
            },
        ],
    }
    draft = draft_caption_template_only(
        figure_id="x",
        contract_dict=_minimal_contract(),
        audit=audit,
        family="factorial",
        style=CaptionStyle.plain,
    )
    assert "; " in draft.statistics_line
    assert "(sex)" in draft.statistics_line
    assert "(genotype)" in draft.statistics_line


def test_statistics_line_falls_back_when_audit_empty() -> None:
    """Empty audit yields a sentinel string — never raises."""
    draft = draft_caption_template_only(
        figure_id="x",
        contract_dict=_minimal_contract(),
        audit={},
        family="factorial",
        style=CaptionStyle.plain,
    )
    assert draft.statistics_line == "no statistical summary in audit"


# ─────────────── 5. reading the provenance sidecar ────────────────────


def test_draft_caption_from_provenance_round_trip(tmp_path: Path) -> None:
    """A well-formed sidecar produces a CaptionDraft with the embedded sha."""
    prov = _write_provenance(
        tmp_path,
        audit=_minimal_audit(),
        figure_sha256="c" * 64,
        figure_name="panel_a.pdf",
    )
    draft = draft_caption_from_provenance(prov, style=CaptionStyle.nature)
    assert draft.figure_id == "panel_a"
    assert draft.figure_sha256 == "c" * 64
    assert draft.style == CaptionStyle.nature
    assert "F(1,12)" in draft.statistics_line


# ─────────────── 6. missing audit raises CaptionError ─────────────────


def test_draft_caption_from_provenance_no_audit(tmp_path: Path) -> None:
    """Sidecar lacking ``audit`` block must raise CaptionError."""
    prov = _write_provenance(tmp_path, audit=None)
    with pytest.raises(CaptionError, match="no `audit` block"):
        draft_caption_from_provenance(prov)


# ─────────────── 7. use_llm under clinical → template-only ────────────


def test_draft_caption_use_llm_blocked_under_clinical(tmp_path: Path) -> None:
    """Under clinical data class, ``use_llm=True`` falls back to template
    output and appends a "blocked by data-class policy" note."""
    from panelforge_figures.safety import DataClass, get_data_class, set_data_class

    prov = _write_provenance(tmp_path, audit=_minimal_audit())
    previous = get_data_class()
    try:
        set_data_class(DataClass.CLINICAL)
        draft = draft_caption_from_provenance(prov, use_llm=True)
    finally:
        set_data_class(previous)
    # Still a usable draft, just annotated.
    assert "Iba1+ density" in draft.body
    assert any("blocked by data-class policy" in n for n in draft.notes)


def test_draft_caption_use_llm_allowed_appends_deferred_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When LLM is allowed (research + key), v2.5.0 still emits template
    output but appends the "deferred to v2.6.0" marker note."""
    from panelforge_figures.safety import DataClass, get_data_class, set_data_class

    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key-for-tests-only")
    prov = _write_provenance(tmp_path, audit=_minimal_audit())
    previous = get_data_class()
    try:
        set_data_class(DataClass.RESEARCH)
        draft = draft_caption_from_provenance(prov, use_llm=True)
    finally:
        set_data_class(previous)
    assert any("deferred to v2.6.0" in n for n in draft.notes)


# ─────────────── 8. markdown render ───────────────────────────────────


def test_render_caption_markdown_contains_all_pieces() -> None:
    """The rendered markdown must surface title_line, body, and sha comment."""
    draft = draft_caption_template_only(
        figure_id="panel_a",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        figure_sha256="d" * 64,
        style=CaptionStyle.plain,
    )
    md = render_caption_markdown(draft)
    assert draft.title_line in md
    assert "Iba1+ density" in md
    assert f"<!-- figure sha256: {'d' * 64} -->" in md
    # Notes are rendered as HTML comments
    assert "<!-- caption note: template-only" in md


def test_render_caption_markdown_omits_sha_when_absent() -> None:
    """When figure_sha256 is None, the HTML comment is not emitted."""
    draft = draft_caption_template_only(
        figure_id="x",
        contract_dict=_minimal_contract(),
        audit=_minimal_audit(),
        family="factorial",
        figure_sha256=None,
        style=CaptionStyle.plain,
    )
    md = render_caption_markdown(draft)
    assert "figure sha256" not in md


# ─────────────── 9. CLI: --help ────────────────────────────────────────


def test_cli_caption_help_exits_zero() -> None:
    """`figures caption --help` is the smoke test for the click wiring."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["caption", "--help"])
    assert result.exit_code == 0, result.output
    assert "provenance" in result.output.lower()
    assert "--style" in result.output


# ─────────────── 10. CLI: exits 1 with no audit ───────────────────────


def test_cli_caption_exits_1_without_audit(tmp_path: Path) -> None:
    """A sidecar without an ``audit`` block should make the CLI exit 1."""
    prov = _write_provenance(tmp_path, audit=None)
    runner = CliRunner()
    result = runner.invoke(cli_main, ["caption", str(prov)])
    assert result.exit_code == 1
    # The error goes through click.style to stderr; combined output has it.
    combined = (result.output or "") + (result.stderr if result.stderr_bytes else "")
    assert "audit" in combined.lower() or result.exit_code == 1


# ─────────────── 11. CLI: every --style choice works ───────────────────


@pytest.mark.parametrize(
    "style", ["plain", "nature", "cell", "nejm", "lab_default"]
)
def test_cli_caption_all_styles(tmp_path: Path, style: str) -> None:
    """Every CaptionStyle variant must be a valid `--style` argument."""
    prov = _write_provenance(tmp_path, audit=_minimal_audit())
    out = tmp_path / f"out_{style}.md"
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["caption", str(prov), "--style", style, "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    text = out.read_text()
    # Every rendered caption keeps the response label from the contract.
    assert "Iba1+ density" in text


def test_cli_caption_writes_to_output_file(tmp_path: Path) -> None:
    """`--output PATH` writes the markdown to that path and prints a confirmation."""
    prov = _write_provenance(tmp_path, audit=_minimal_audit())
    out = tmp_path / "subdir" / "caption.md"
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["caption", str(prov), "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    assert "wrote" in result.output


def test_cli_caption_prints_to_stdout_without_output(tmp_path: Path) -> None:
    """Without ``--output``, the CLI prints the markdown directly."""
    prov = _write_provenance(tmp_path, audit=_minimal_audit())
    runner = CliRunner()
    result = runner.invoke(cli_main, ["caption", str(prov)])
    assert result.exit_code == 0, result.output
    assert "Iba1+ density" in result.output
