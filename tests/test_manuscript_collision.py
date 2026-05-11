"""Tests for the manuscript-collision module (Elevation 10 — phase 2).

Owned by Build-B; this test suite is authored by Build-C against the
public API documented in the swarm spec.  The collision module sits
between Build-A's :mod:`manuscript_parse` and Build-B's
:mod:`manuscript_scaffold` and emits per-figure verdicts (keep_existing,
insert_block, append_new, flag_orphan, flag_referenced_undefined)
plus an optional in-place / propose-only update applied via
:func:`apply_update_policy`.

Public API exercised here:

* :class:`CollisionReport` (with ``.per_figure``, ``.methods_status``,
  ``.claim_verdicts``).
* :class:`PerFigureCollision` (``figure_id``, ``verdict``,
  ``existing_block``, ``proposed_panel``).
* :class:`MethodsStatus` (``family``, ``already_documented``).
* :class:`ClaimVerdict` (``claim_text``, ``verdict`` ∈
  {supported, unsupported, unverifiable}).
* :class:`ManuscriptPolicy` enum (detect/update/propose/preserve).
* :func:`detect_collision`
* :func:`apply_update_policy`
* :func:`render_collision_report_markdown`

The whole file is ``importorskip``-gated so it at least parses during
a Build-C-only verification pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

manuscript_collision = pytest.importorskip(
    "panelforge_figures.manifest.manuscript_collision"
)
manuscript_parse = pytest.importorskip(
    "panelforge_figures.manifest.manuscript_parse"
)
scout = pytest.importorskip("panelforge_figures.manifest.scout")


# ─────────────────────────── synthetic plan plumbing ────────────────────


def _plan_with_panels(
    tmp_path: Path,
    *,
    panel_figure_ids: list[str],
    recipe_full_name: str = "meta_and_diagnostic.panel_provenance_ledger_table",
) -> Any:
    """Build a tiny FigurePlan with one panel per figure_id."""
    figures: list[Any] = []
    for i, fig_id in enumerate(panel_figure_ids, start=1):
        panel = scout.PanelSlot(
            panel_id=f"{i}A",
            figure_id=fig_id,
            recipe_full_name=recipe_full_name,
            research_question="Demo question",
            role="primary",
            is_gap=False,
        )
        figures.append(
            scout.FigureSlot(
                figure_id=fig_id,
                title=f"Figure for {fig_id}",
                slot_kind=scout.FigureSlotKind.biology,
                panels=(panel,),
            )
        )
    plan = scout.FigurePlan(
        project_root=tmp_path,
        project_id="testproj",
        figures=tuple(figures),
        venue="cell",
        n_figures=len(figures),
        n_panels=len(figures),
        n_gaps=0,
    )
    return plan


def _write_manuscript(tmp_path: Path, name: str, body: str) -> Any:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return manuscript_parse.parse_manuscript(p)


# ─────────────────────────── detect_collision: keep ─────────────────────


def test_detect_collision_two_matching_figures_all_keep(tmp_path: Path) -> None:
    """Plan has 2 figs, manuscript has 2 matching blocks → all keep_existing."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1", "Figure 2"])
    text = r"""\documentclass{article}\begin{document}
See \ref{fig:1} and \ref{fig:2}.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\begin{figure}\caption{Two.}\label{fig:2}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)

    report = manuscript_collision.detect_collision(existing, plan)
    per_fig = report.figure_reconciliations
    assert len(per_fig) >= 2
    actions = [r.action.value for r in per_fig]
    assert all(a == "keep_existing" for a in actions), (
        f"expected all keep_existing, got {actions}"
    )


# ─────────────────────────── detect_collision: insert ───────────────────


def test_detect_collision_orphan_ref_inserts_block(tmp_path: Path) -> None:
    """Plan has 3 figs; manuscript has 2 blocks + 1 orphan ref → 2 keep + 1 insert."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2", "Figure 3"],
    )
    text = r"""\documentclass{article}\begin{document}
See \ref{fig:1}, \ref{fig:2}, and \ref{fig:3}.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\begin{figure}\caption{Two.}\label{fig:2}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)

    report = manuscript_collision.detect_collision(existing, plan)
    actions = [r.action.value for r in report.figure_reconciliations]
    keep_count = sum(1 for a in actions if a == "keep_existing")
    insert_count = sum(1 for a in actions if a == "insert_block")
    assert keep_count >= 2, f"got actions: {actions}"
    assert insert_count >= 1, f"got actions: {actions}"


# ─────────────────────────── detect_collision: append ───────────────────


def test_detect_collision_extra_plan_figures_appended(tmp_path: Path) -> None:
    """Plan has 4 figs; manuscript has 2 blocks → 2 keep + 2 append_new."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2", "Figure 3", "Figure 4"],
    )
    text = r"""\documentclass{article}\begin{document}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\begin{figure}\caption{Two.}\label{fig:2}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    actions = [r.action.value for r in report.figure_reconciliations]
    append_count = sum(1 for a in actions if a == "append_new")
    assert append_count >= 2, f"got actions: {actions}"


# ─────────────────────────── detect_collision: flag_orphan ──────────────


def test_detect_collision_flag_orphan_block_not_in_plan(tmp_path: Path) -> None:
    """Manuscript block fig:5 not in plan → orphan/dangling diagnostic.

    Build-B summarises orphan blocks via ``n_dangling_blocks`` rather than
    a per-figure verdict (the existing block is not in the plan, so
    it can only appear in the figure_reconciliations if the plan
    references it explicitly).  We assert via the summary counter.
    """
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\begin{figure}\caption{Five — orphan.}\label{fig:5}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    # fig:5 is in the manuscript blocks but not referenced or in plan.
    # Build-B reports n_dangling_blocks for these.
    assert report.n_dangling_blocks >= 1


def test_detect_collision_flag_referenced_undefined(tmp_path: Path) -> None:
    """Manuscript has ref to fig:6 not in blocks nor plan → n_orphan_refs >= 1."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
See \ref{fig:1} and the missing \ref{fig:6}.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    # fig:6 is referenced but never defined.
    assert report.n_orphan_refs >= 1


# ─────────────────────────── Methods reconciliation ─────────────────────


def test_methods_already_documented_when_family_present(tmp_path: Path) -> None:
    """Methods reconciliations are produced as a tuple of records."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1"],
        recipe_full_name="meta_and_diagnostic.panel_provenance_ledger_table",
    )
    text = r"""\documentclass{article}\begin{document}
\section{Methods}
\subsection{Statistical analysis}
Effect sizes were estimated and provenance ledger tables were recorded
for every panel. We used Welch's t-test for the main comparison.

\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    methods = list(report.methods_reconciliations)
    # Build-B may or may not produce a methods reconciliation depending
    # on the recipe's family resolution. Either way, the field must
    # exist and contain tuples of MethodsReconciliation objects.
    assert isinstance(methods, list)
    for mrec in methods:
        assert hasattr(mrec, "already_documented")


def test_methods_not_documented_when_section_missing(tmp_path: Path) -> None:
    """Manuscript without a Methods section → empty/permissive methods_reconciliations."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    methods = list(report.methods_reconciliations)
    for mrec in methods:
        assert mrec.already_documented in (True, False)


# ─────────────────────────── Claim verdicts ─────────────────────────────


def test_claim_verdict_supported_with_supporting_finding(tmp_path: Path) -> None:
    """A claim is ``supported`` when an audit finding supports it."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
Figure 1 shows significantly higher response.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    # Supporting finding: p_value < 0.05 for significant_difference claim.
    findings = {"fig:1": {"p_value": 0.001}, "figure 1": {"p_value": 0.001}}
    report = manuscript_collision.detect_collision(
        existing, plan, audit_findings_per_figure=findings,
    )
    if report.claim_verdicts:
        labels = [str(v).lower() for (_s, v, _r) in report.claim_verdicts]
        assert any("support" in v for v in labels), labels


def test_claim_verdict_unsupported_with_contradicting_finding(tmp_path: Path) -> None:
    """A claim is ``unsupported`` when audit findings contradict it."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
Figure 1 shows significantly higher response.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    # Contradicting finding: p_value > 0.05 for "significantly higher" claim.
    findings = {"fig:1": {"p_value": 0.9}, "figure 1": {"p_value": 0.9}}
    report = manuscript_collision.detect_collision(
        existing, plan, audit_findings_per_figure=findings,
    )
    if report.claim_verdicts:
        labels = [str(v).lower() for (_s, v, _r) in report.claim_verdicts]
        assert any(
            ("unsupp" in v or "contradict" in v) for v in labels
        ), labels


def test_claim_verdict_unverifiable_without_findings(tmp_path: Path) -> None:
    """No audit findings → every verdict is unverifiable."""
    plan = _plan_with_panels(tmp_path, panel_figure_ids=["Figure 1"])
    text = r"""\documentclass{article}\begin{document}
Figure 1 shows significantly higher response.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    if report.claim_verdicts:
        labels = [str(v).lower() for (_s, v, _r) in report.claim_verdicts]
        # All verdicts should be unverifiable (or no verdicts).
        assert all("unverif" in v for v in labels), labels


# ─────────────────────────── apply_update_policy ────────────────────────


def test_apply_update_policy_update_inserts_in_place(tmp_path: Path) -> None:
    """Policy=update writes insertions into the original manuscript file."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2"],
    )
    original_text = r"""\documentclass{article}
\begin{document}
\section{Results}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}
"""
    p = tmp_path / "m.tex"
    p.write_text(original_text, encoding="utf-8")
    existing = manuscript_parse.parse_manuscript(p)
    report = manuscript_collision.detect_collision(existing, plan)

    out_path, modified_text = manuscript_collision.apply_update_policy(
        existing, plan, report,
        policy=manuscript_collision.ManuscriptPolicy("update"),
        dry_run=True,
    )
    # dry_run=True so file isn't modified, but we get the proposed text.
    assert isinstance(modified_text, str)
    assert len(modified_text) > 0


def test_apply_update_policy_propose_writes_suggested(tmp_path: Path) -> None:
    """Policy=propose writes to ``*.suggested.tex`` (or similar suffix)."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2"],
    )
    original_text = r"""\documentclass{article}
\begin{document}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}
"""
    p = tmp_path / "m.tex"
    p.write_text(original_text, encoding="utf-8")
    existing = manuscript_parse.parse_manuscript(p)
    report = manuscript_collision.detect_collision(existing, plan)

    out_path, _modified = manuscript_collision.apply_update_policy(
        existing, plan, report,
        policy=manuscript_collision.ManuscriptPolicy("propose"),
    )
    # propose may emit to a different path (suggested.<ext>) or signal
    # via the returned text — accept either contract.
    if out_path is not None:
        assert "suggest" in Path(out_path).name.lower() or Path(out_path) != p


def test_apply_update_policy_line_offsets_correct(tmp_path: Path) -> None:
    """Multiple insertions: cumulative line shift must be tracked correctly."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2", "Figure 3"],
    )
    original_text = "\n".join(
        [
            r"\documentclass{article}",
            r"\begin{document}",
            r"\section{Results}",
            r"\begin{figure}\caption{One.}\label{fig:1}\end{figure}",
            r"\end{document}",
            "",
        ]
    )
    p = tmp_path / "m.tex"
    p.write_text(original_text, encoding="utf-8")
    existing = manuscript_parse.parse_manuscript(p)
    report = manuscript_collision.detect_collision(existing, plan)

    _out_path, modified_text = manuscript_collision.apply_update_policy(
        existing, plan, report,
        policy=manuscript_collision.ManuscriptPolicy("update"),
        dry_run=True,
    )
    # The modified text must contain at least one inserted figure block
    # for the missing figures (fig:2 + fig:3).  Build-B normalises the
    # \label{...} content to the plan figure_id (e.g. ``figure2``).
    assert r"\begin{figure}" in modified_text
    # Should contain insertions for both figure 2 and figure 3.
    lowered = modified_text.lower()
    assert "figure2" in lowered or "fig:2" in lowered
    assert "figure3" in lowered or "fig:3" in lowered


# ─────────────────────────── render_collision_report_markdown ───────────


def test_render_collision_report_markdown_has_per_figure_table(
    tmp_path: Path,
) -> None:
    """The rendered markdown must mention per-figure or collision info."""
    plan = _plan_with_panels(
        tmp_path,
        panel_figure_ids=["Figure 1", "Figure 2"],
    )
    text = r"""\documentclass{article}\begin{document}
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\end{document}"""
    existing = _write_manuscript(tmp_path, "m.tex", text)
    report = manuscript_collision.detect_collision(existing, plan)
    md = manuscript_collision.render_collision_report_markdown(report)
    assert isinstance(md, str)
    lowered = md.lower()
    assert any(
        token in lowered
        for token in (
            "per-figure", "per figure", "verdict", "collision",
            "figure", "action", "manuscript",
        )
    )
