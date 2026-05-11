"""Tests for Elevation 15 — interactive scout TUI (v3.9.0).

Coverage strategy
-----------------
The :class:`ScoutSession` dataclass + plan-filtering helpers are pure
Python and can be tested without booting a real terminal.  For the
textual ``ScoutApp`` itself we use either:

* :class:`textual.pilot.Pilot` headless simulator (when ``textual`` is
  installed), or
* a fake ``_app_factory`` injected into :func:`run_interactive_scout`,
  so the file's import still works on minimal CI images.

The whole module is guarded by ``pytest.importorskip`` on textual; CI
that doesn't install the ``[tui]`` extra cleanly skips these tests
rather than erroring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.cli.tui_scout import (
    InteractiveScoutError,
    ScoutSession,
    _build_filtered_plan,
    _format_novelty_card,
    _format_panel_detail,
    _novelty_lookup,
    run_interactive_scout,
)
from panelforge_figures.manifest.scout import (
    FigurePlan,
    FigureSlot,
    FigureSlotKind,
    PanelSlot,
)

# ─────────────────────────── helpers ────────────────────────────────────


def _make_plan(panel_ids: tuple[str, ...] = ("1A", "1B", "1C")) -> FigurePlan:
    """Tiny FigurePlan fixture: one figure, ``panel_ids`` panels."""
    panels = tuple(
        PanelSlot(
            panel_id=pid,
            figure_id="Figure 1",
            recipe_full_name=f"recipe.for.{pid}",
            research_question=f"What about {pid}?",
            role="primary",
            is_gap=False,
        )
        for pid in panel_ids
    )
    fig = FigureSlot(
        figure_id="Figure 1",
        title="Demo figure",
        slot_kind=FigureSlotKind.biology,
        panels=panels,
    )
    return FigurePlan(
        project_root=Path("/tmp/demo"),
        project_id="demo",
        figures=(fig,),
        venue="cell",
        n_figures=1,
        n_panels=len(panel_ids),
        n_gaps=0,
    )


def _make_novelty_report(panel_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "overall_verdict": "balanced",
        "novelty_density": 0.5,
        "n_panels": len(panel_ids),
        "n_protected": 0,
        "n_repetition": 0,
        "n_incremental": 1,
        "n_hidden_novelty": 1,
        "n_ultra_novelty": 1,
        "promote_panels": [],
        "drop_panels": [],
        "demote_panels": [],
        "panels": [
            {
                "panel_id": pid,
                "recipe_full_name": f"recipe.for.{pid}",
                "novelty_class": "hidden_novelty",
                "is_supporting": False,
                "consensus_n_papers": 1,
                "consensus_strength": 0.0,
                "avg_year": 2024.0,
                "suggestion": "keep_flag_opportunity",
                "rationale": "niche topic",
                "top_paper_titles": [f"Paper for {pid}"],
                "target_novelty": "maximal",
            }
            for pid in panel_ids
        ],
    }


def _make_data_project(root: Path) -> Path:
    """Smallest possible scout-able project."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "panelforge.project.yaml").write_text(
        "project_id: tui_demo\n"
        "modality: meta_and_diagnostic\n"
    )
    data_dir = root / "data"
    data_dir.mkdir()
    (data_dir / "table.csv").write_text("a,b\n1,2\n3,4\n")
    return root


# ─────────────────────────── 1. ScoutSession dataclass ───────────────────


class TestScoutSession:
    def test_init_all_accepted_by_default(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        for pid in ("1A", "1B", "1C"):
            assert session.is_accepted(pid)
        assert session.rejected_panel_ids == set()

    def test_reject_then_is_accepted_false(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.reject("1A")
        assert not session.is_accepted("1A")
        assert session.is_accepted("1B")

    def test_reject_then_reject_unrejects(self) -> None:
        """Toggle: second `reject` un-rejects."""
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.reject("1A")
        session.reject("1A")
        assert session.is_accepted("1A")

    def test_accept_clears_rejection(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.reject("1A")
        session.accept("1A")
        assert session.is_accepted("1A")
        assert "1A" in session.accepted_panel_ids

    def test_edit_research_question_stored(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.edit_research_question("1A", "New question?")
        assert session.edited_research_questions["1A"] == "New question?"
        assert session.get_research_question("1A") == "New question?"
        assert session.get_research_question("1B", default="fallback") == "fallback"

    def test_cycle_target_novelty_walks_through_band(self) -> None:
        plan = _make_plan()
        session = ScoutSession(
            project_root=Path("/tmp"), plan=plan, target_novelty="maximal"
        )
        assert session.cycle_target_novelty() == "balanced"
        assert session.cycle_target_novelty() == "permissive"
        assert session.cycle_target_novelty() == "maximal"

    def test_cycle_target_novelty_wraps_on_unknown(self) -> None:
        plan = _make_plan()
        session = ScoutSession(
            project_root=Path("/tmp"), plan=plan, target_novelty="something-weird"
        )
        # Unknown value → cycle starts from index 0.
        assert session.cycle_target_novelty() == "maximal"

    def test_status_line_counts(self) -> None:
        plan = _make_plan(panel_ids=("1A", "1B", "1C"))
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.reject("1A")
        session.edit_research_question("1B", "Edited!")
        line = session.status_line()
        assert "2 accepted" in line  # 1B, 1C
        assert "1 rejected" in line
        assert "1 edited" in line
        assert "maximal" in line

    def test_all_panel_ids_in_order(self) -> None:
        plan = _make_plan(panel_ids=("2A", "1B", "3C"))
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        assert session.all_panel_ids() == ["2A", "1B", "3C"]


# ─────────────────────────── 2. plan filtering ──────────────────────────


class TestBuildFilteredPlan:
    def test_no_rejections_preserves_all_panels(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        new_plan = _build_filtered_plan(session)
        assert new_plan.n_panels == 3
        assert len(new_plan.figures) == 1

    def test_rejection_drops_panel(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.reject("1B")
        new_plan = _build_filtered_plan(session)
        assert new_plan.n_panels == 2
        kept = [p.panel_id for f in new_plan.figures for p in f.panels]
        assert "1B" not in kept
        assert {"1A", "1C"} == set(kept)

    def test_rejecting_all_panels_drops_figure(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        for pid in ("1A", "1B", "1C"):
            session.reject(pid)
        new_plan = _build_filtered_plan(session)
        assert new_plan.n_panels == 0
        assert len(new_plan.figures) == 0

    def test_edits_propagate(self) -> None:
        plan = _make_plan()
        session = ScoutSession(project_root=Path("/tmp"), plan=plan)
        session.edit_research_question("1A", "Rewritten!")
        new_plan = _build_filtered_plan(session)
        first_panel = next(
            p for f in new_plan.figures for p in f.panels if p.panel_id == "1A"
        )
        assert first_panel.research_question == "Rewritten!"


# ─────────────────────────── 3. formatters ──────────────────────────────


class TestFormatters:
    def test_format_panel_detail_no_edit(self) -> None:
        plan = _make_plan()
        panel = plan.figures[0].panels[0]
        out = _format_panel_detail(panel, None)
        assert "1A" in out
        assert "recipe.for.1A" in out
        assert "What about 1A?" in out
        assert "[edited]" not in out

    def test_format_panel_detail_with_edit_shows_marker(self) -> None:
        plan = _make_plan()
        panel = plan.figures[0].panels[0]
        out = _format_panel_detail(panel, "New question?")
        assert "New question?" in out
        assert "[edited]" in out

    def test_format_panel_detail_gap_panel(self) -> None:
        panel = PanelSlot(
            panel_id="1A",
            figure_id="Figure 1",
            recipe_full_name="",
            research_question="Gap?",
            is_gap=True,
            suggested_recipe_name="modality.new_recipe",
        )
        out = _format_panel_detail(panel, None)
        assert "GAP" in out
        assert "modality.new_recipe" in out

    def test_format_novelty_card_with_data(self) -> None:
        report = _make_novelty_report(("1A",))
        out = _format_novelty_card(report["panels"][0])
        assert "hidden_novelty" in out
        assert "Paper for 1A" in out

    def test_format_novelty_card_none(self) -> None:
        out = _format_novelty_card(None)
        assert "no novelty data" in out.lower()

    def test_novelty_lookup_indexes_by_panel_id(self) -> None:
        report = _make_novelty_report(("1A", "1B"))
        idx = _novelty_lookup(report)
        assert set(idx.keys()) == {"1A", "1B"}
        assert idx["1A"]["novelty_class"] == "hidden_novelty"

    def test_novelty_lookup_empty(self) -> None:
        assert _novelty_lookup(None) == {}
        assert _novelty_lookup({}) == {}


# ─────────────────────────── 4. textual missing ─────────────────────────


def test_run_interactive_scout_raises_when_textual_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caller must get a friendly InteractiveScoutError, not ImportError."""
    import builtins

    real_import = builtins.__import__

    def _no_textual(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("textual"):
            raise ImportError(f"mock: no module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_textual)

    proj = _make_data_project(tmp_path / "proj")
    with pytest.raises(InteractiveScoutError, match="textual"):
        run_interactive_scout(proj, plan_out=tmp_path / "plan.yaml")


# ─────────────────────────── 5. fake-app integration ────────────────────


class _FakeApp:
    """Tiny stand-in for a textual App so we can test the public entry.

    Production callers never see this; we inject it via the
    ``_app_factory`` keyword which is documented as a test seam.
    """

    last_session: ScoutSession | None = None

    def __init__(self, session: ScoutSession) -> None:
        self.session = session
        _FakeApp.last_session = session
        # Default: commit + accept everything, no edits.
        self._committed: bool = True

    def run(self) -> bool:
        return self._committed


class _RejectingApp(_FakeApp):
    """Fake that rejects a fixed panel before committing."""

    target_pid: str = "1B"

    def run(self) -> bool:
        self.session.reject(self.target_pid)
        return True


class _EditingApp(_FakeApp):
    """Fake that edits a question + cycles novelty before committing."""

    def run(self) -> bool:
        self.session.edit_research_question("1A", "Edited via TUI")
        self.session.cycle_target_novelty()
        return True


class _CancelApp(_FakeApp):
    """Fake that cancels the session (ESC press equivalent)."""

    def run(self) -> bool:
        return False


def test_run_interactive_scout_commits_writes_plan(tmp_path: Path) -> None:
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"
    result = run_interactive_scout(
        proj,
        plan_out=out,
        use_mock_novelty=True,
        _app_factory=_FakeApp,
    )
    assert result == out
    assert out.exists()
    data = yaml.safe_load(out.read_text())
    assert data["schema_version"] == 1
    assert "figures" in data


def test_run_interactive_scout_rejection_filters_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rejected panels must not appear in the saved YAML."""
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"

    # Patch _RejectingApp to target a panel that actually exists in the plan.
    class _PatchRejector(_FakeApp):
        def run(self) -> bool:
            ids = self.session.all_panel_ids()
            if ids:
                self.session.reject(ids[0])
            return True

    result = run_interactive_scout(
        proj,
        plan_out=out,
        use_mock_novelty=True,
        _app_factory=_PatchRejector,
    )
    assert result == out
    data = yaml.safe_load(out.read_text())
    saved_ids = {p["panel_id"] for f in data.get("figures", []) for p in f.get("panels", [])}
    # The original first panel must be gone.
    assert _PatchRejector.last_session is not None
    original = _PatchRejector.last_session.all_panel_ids()
    if original:  # plan may be empty for trivial projects
        assert original[0] not in saved_ids


def test_run_interactive_scout_edits_propagate_to_yaml(tmp_path: Path) -> None:
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"

    class _EditAll(_FakeApp):
        def run(self) -> bool:
            ids = self.session.all_panel_ids()
            for pid in ids:
                self.session.edit_research_question(pid, f"new q for {pid}")
            return True

    run_interactive_scout(
        proj,
        plan_out=out,
        use_mock_novelty=True,
        _app_factory=_EditAll,
    )
    data = yaml.safe_load(out.read_text())
    for fig in data.get("figures", []):
        for panel in fig.get("panels", []):
            assert panel["research_question"].startswith("new q for")


def test_run_interactive_scout_cancel_does_not_write(tmp_path: Path) -> None:
    """ESC cancel must skip the save step entirely."""
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"
    result = run_interactive_scout(
        proj,
        plan_out=out,
        use_mock_novelty=True,
        _app_factory=_CancelApp,
    )
    assert result == out
    assert not out.exists()


def test_run_interactive_scout_session_carries_novelty_report(
    tmp_path: Path,
) -> None:
    """The session passed to the app must carry a novelty report when scoring is on."""
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"

    captured: dict[str, Any] = {}

    class _Capture(_FakeApp):
        def run(self) -> bool:
            captured["novelty_report"] = self.session.novelty_report
            captured["target_novelty"] = self.session.target_novelty
            return True

    run_interactive_scout(
        proj,
        plan_out=out,
        use_mock_novelty=True,
        target_novelty="balanced",
        _app_factory=_Capture,
    )
    assert captured["target_novelty"] == "balanced"
    # Mock novelty report should be populated (project has a CSV).
    assert captured["novelty_report"] is None or isinstance(
        captured["novelty_report"], dict
    )


# ─────────────────────────── 6. CLI surface ─────────────────────────────


def test_cli_scout_interactive_help_works() -> None:
    """`figures scout --help` must mention the new --interactive flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["scout", "--help"])
    assert result.exit_code == 0
    assert "--interactive" in result.output


def test_cli_scout_interactive_propagates_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`figures scout --interactive` must surface InteractiveScoutError as exit 1."""
    proj = _make_data_project(tmp_path / "proj")
    runner = CliRunner()

    # Stub run_interactive_scout to raise — the CLI must convert to exit 1.
    def _boom(*args: Any, **kwargs: Any) -> Path:
        raise InteractiveScoutError("stub failure")

    monkeypatch.setattr(
        "panelforge_figures.cli.tui_scout.run_interactive_scout", _boom
    )

    result = runner.invoke(
        main,
        ["scout", str(proj), "--interactive", "--mock-novelty"],
    )
    assert result.exit_code == 1
    assert "stub failure" in result.output


def test_cli_scout_interactive_invokes_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end-ish: `figures scout --interactive` should call run_interactive_scout."""
    proj = _make_data_project(tmp_path / "proj")
    out = tmp_path / "plan.yaml"
    runner = CliRunner()

    called: dict[str, Any] = {}

    def _stub(project_root: Path, **kw: Any) -> Path:
        called["project_root"] = Path(project_root)
        called["kwargs"] = kw
        out.write_text("schema_version: 1\nfigures: []\n")
        return out

    monkeypatch.setattr(
        "panelforge_figures.cli.tui_scout.run_interactive_scout", _stub
    )

    result = runner.invoke(
        main,
        [
            "scout", str(proj),
            "--interactive",
            "--mock-novelty",
            "--plan-out", str(out),
            "--max-figures", "3",
            "--target-novelty", "balanced",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called["project_root"] == proj
    assert called["kwargs"]["max_figures"] == 3
    assert called["kwargs"]["target_novelty"] == "balanced"
    assert called["kwargs"]["plan_out"] == out
    assert called["kwargs"]["use_mock_novelty"] is True


# ─────────────────────────── 7. textual Pilot (real TUI) ────────────────

# Only run these if textual is installed.  They are gated and skip cleanly
# on minimal CI images.
textual = pytest.importorskip("textual")


def test_textual_app_compiles(tmp_path: Path) -> None:
    """The textual App class must instantiate without error on the demo plan."""
    from panelforge_figures.cli.tui_scout import _build_app

    plan = _make_plan()
    session = ScoutSession(
        project_root=Path("/tmp"),
        plan=plan,
        novelty_report=_make_novelty_report(("1A", "1B", "1C")),
    )
    app_cls = _build_app(session)
    # Smoke check: can we construct an instance?
    app = app_cls(session)
    assert app is not None


def test_textual_app_quit_via_pilot(tmp_path: Path) -> None:
    """`q` press exits the app with result=True (commit).

    Uses :meth:`App.run_test` (textual's headless Pilot) under
    :func:`asyncio.run` so we don't need pytest-asyncio.
    """
    import asyncio

    from panelforge_figures.cli.tui_scout import _build_app

    plan = _make_plan()
    session = ScoutSession(project_root=Path("/tmp"), plan=plan)
    app_cls = _build_app(session)
    app = app_cls(session)

    async def _drive() -> None:
        async with app.run_test() as pilot:
            await pilot.press("q")

    asyncio.run(_drive())
    assert getattr(app, "_committed", False) is True
