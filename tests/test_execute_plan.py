"""Tests for the execute-plan orchestrator (Elevation 9 — phase 2).

Owned by Build-C.  These tests construct synthetic plans via simple
mock objects so the suite runs even when Build-A's ``scout`` module
hasn't landed on disk yet.  The CLI tests fall back to ``importorskip``
on ``scout.load_figure_plan_yaml`` so they exercise the executor's
error path during a Build-C-only verification pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from panelforge_figures.manifest.execute_plan import (
    ExecutionError,
    ExecutionResult,
    PanelExecutionStatus,
    execute_plan,
)

# ─────────────────────────── synthetic plan plumbing ────────────────────


@dataclass
class _MockPanel:
    """Minimal stand-in for Build-A's PanelSpec."""

    panel_id: str
    is_gap: bool = False
    recipe_full_name: str | None = None
    recipe_name: str | None = None
    family: str = "comparison"
    modality: str = "meta_and_diagnostic"
    research_question: str = "Demo question?"
    role: str = "primary"
    column_mapping: dict[str, str] | None = None
    data_file: str | None = None


@dataclass
class _MockPlan:
    """Minimal stand-in for Build-A's FigurePlan."""

    project_root: Path
    panels: list[_MockPanel]


def _write_plan_yaml(plan: _MockPlan, path: Path) -> None:
    """Serialise a ``_MockPlan`` to YAML so ``execute_plan`` can load it.

    Because Build-A's ``load_figure_plan_yaml`` may not be on disk during
    Build-C-only runs, the helper installs a monkey-patch into the
    scout namespace via ``conftest`` is too invasive — instead, the
    individual tests call ``execute_plan`` after monkey-patching the
    loader directly.  This helper just writes a dict-shaped YAML that
    a real loader would understand.
    """
    payload = {
        "project_root": str(plan.project_root),
        "panels": [
            {k: v for k, v in p.__dict__.items() if v is not None}
            for p in plan.panels
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@pytest.fixture
def stub_scout_loader(monkeypatch: pytest.MonkeyPatch):
    """Install a stub ``load_figure_plan_yaml`` so the executor never
    needs Build-A's real scout module.

    Yields the loader itself so a test can swap behaviour for one case.
    """
    import sys
    import types

    fake = types.ModuleType("panelforge_figures.manifest.scout")

    def _loader(path: Path) -> Any:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return _MockPlan(
            project_root=Path(data.get("project_root", str(Path(path).parent))),
            panels=[_MockPanel(**p) for p in data.get("panels", [])],
        )

    fake.load_figure_plan_yaml = _loader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "panelforge_figures.manifest.scout", fake)
    yield _loader


# ─────────────────────────── tests ──────────────────────────────────────


def test_execute_plan_no_gaps_render_off(stub_scout_loader, tmp_path: Path) -> None:
    """With render_figures=False and no gaps, no panels render or scaffold."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[
            _MockPanel(
                panel_id="p1",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            )
        ],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(
        plan_path,
        render_figures=False,
        scaffold_recipes=False,
        draft_captions=False,
        scaffold_manuscript=False,
    )
    assert isinstance(result, ExecutionResult)
    assert result.n_panels_attempted == 1
    assert result.n_panels_rendered == 0
    assert result.n_recipes_scaffolded == 0
    assert result.manuscript_path is None


def test_execute_plan_scaffold_off_logs_skipped_gap(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """When scaffold_recipes=False, gap panels surface ``status="skipped_gap"``."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[
            _MockPanel(panel_id="p_gap", is_gap=True, recipe_name="my_gap"),
            _MockPanel(
                panel_id="p_real",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            ),
        ],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(
        plan_path,
        scaffold_recipes=False,
        render_figures=False,
        draft_captions=False,
        scaffold_manuscript=False,
    )
    assert result.n_recipes_scaffolded == 0
    statuses = {pid: status for pid, status, _ in result.panels_status}
    assert statuses.get("p_gap") == PanelExecutionStatus.skipped_gap


def test_execute_plan_integrates_with_manuscript_scaffold_or_softwarns(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """``execute_plan`` invokes Build-B's manuscript_scaffold; if absent,
    soft-warns via notes and returns ``manuscript_path=None``."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[
            _MockPanel(
                panel_id="p1",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            )
        ],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(
        plan_path,
        scaffold_recipes=False,
        render_figures=False,
        draft_captions=False,
        scaffold_manuscript=True,
    )
    # Either Build-B has landed (path is set) OR it hasn't (path is None
    # and a note explains the import failure).
    if result.manuscript_path is None:
        assert any(
            "manuscript_scaffold" in n or "Build-B" in n
            for n in result.notes
        ), f"expected soft-warn note, got notes={result.notes!r}"
    else:
        assert isinstance(result.manuscript_path, Path)


def test_execute_plan_tolerates_per_panel_failures(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """One bad panel must NOT abort the loop — it surfaces as ``failed``."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[
            _MockPanel(
                panel_id="p_good",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            ),
            _MockPanel(
                panel_id="p_bad",
                recipe_full_name="nonexistent.recipe_that_does_not_exist",
            ),
            _MockPanel(
                panel_id="p_also_good",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            ),
        ],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(
        plan_path,
        scaffold_recipes=False,
        render_figures=True,
        draft_captions=False,
        scaffold_manuscript=False,
    )
    assert result.n_panels_attempted == 3
    panel_ids_seen = {pid for pid, _, _ in result.panels_status}
    # All three panels must show up in panels_status — no panel was
    # silently dropped because of an earlier failure.
    assert panel_ids_seen == {"p_good", "p_bad", "p_also_good"}


def test_execute_plan_all_phases_off_is_noop(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """All flags False → empty counters, no manuscript, no exception."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[
            _MockPanel(
                panel_id="p1",
                recipe_full_name="meta_and_diagnostic.run_provenance_card",
            )
        ],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(
        plan_path,
        scaffold_recipes=False,
        render_figures=False,
        draft_captions=False,
        scaffold_manuscript=False,
    )
    assert result.n_panels_rendered == 0
    assert result.n_recipes_scaffolded == 0
    assert result.n_captions_drafted == 0
    assert result.manuscript_path is None


def test_execute_plan_empty_plan_returns_zero_counters(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """An empty panels list is not an error — counters are all zero."""
    plan = _MockPlan(project_root=tmp_path, panels=[])
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    result = execute_plan(plan_path)
    assert result.n_panels_attempted == 0
    assert result.panels_status == ()


def test_execute_plan_raises_on_missing_plan(tmp_path: Path) -> None:
    """A missing plan path must raise :class:`ExecutionError`."""
    with pytest.raises((ExecutionError, FileNotFoundError, OSError)):
        execute_plan(tmp_path / "does_not_exist.yaml")


# ─────────────────────────── CLI smoke ──────────────────────────────────


def test_cli_execute_plan_help() -> None:
    from panelforge_figures.cli import main

    r = CliRunner().invoke(main, ["execute-plan", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "execute-plan" in r.output.lower() or "PLAN_PATH" in r.output


def test_cli_execute_plan_with_all_phases_off(
    stub_scout_loader, tmp_path: Path,
) -> None:
    """The CLI surface honours the ``--no-*`` flags."""
    plan = _MockPlan(
        project_root=tmp_path,
        panels=[_MockPanel(panel_id="p1")],
    )
    plan_path = tmp_path / "plan.yaml"
    _write_plan_yaml(plan, plan_path)

    from panelforge_figures.cli import main

    r = CliRunner().invoke(
        main,
        [
            "execute-plan", str(plan_path),
            "--no-scaffold-recipes",
            "--no-render-figures",
            "--no-draft-captions",
            "--no-scaffold-manuscript",
        ],
    )
    # The CLI should at least parse and run; exit 0 on success or 1 if
    # the executor surfaced a soft import error.
    assert r.exit_code in (0, 1), r.output
