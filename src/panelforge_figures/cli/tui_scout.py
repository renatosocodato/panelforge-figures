"""Interactive scout TUI (Elevation 15 — v3.9.0).

The ``figures scout --interactive`` flag launches a `textual <https://textual.textualize.io/>`_
based terminal UI on top of the existing read-only :func:`scout_project`
pipeline.  Users can browse the proposed multi-figure plan, accept or
reject individual panels, rewrite research questions inline, cycle
``target_novelty`` thresholds, and re-score a panel against the literature
on demand.  The TUI exits when the user presses ``q`` (commit) or ``ESC``
(cancel); on commit, the mutated plan is serialised back to disk via
:func:`save_figure_plan_yaml`.

Layout
------
Three panes, top-to-bottom Header / 3-column body / Footer::

    +---------------------------- Header --------------------------------+
    | tree (figures)  | panel detail            | novelty card           |
    |                 | recipe / question / role | class / N / verdict   |
    +---------------------------- Footer --------------------------------+

Key bindings
------------
* ``↑`` / ``↓``  – navigate panels
* ``ENTER``     – accept the current panel (default)
* ``x``         – reject the current panel (toggle if already rejected)
* ``e``         – edit the current panel's research question (modal)
* ``n``         – cycle ``target_novelty`` (maximal → balanced → permissive)
* ``r``         – re-score novelty for the current panel
* ``q``         – commit + quit (save filtered plan)
* ``escape``    – cancel + quit (no save)
* ``?``         – open the help screen

Public surface
--------------
:class:`InteractiveScoutError`  – raised on TUI failures or missing dep.
:class:`ScoutSession`          – mutable session state passed back to caller.
:func:`run_interactive_scout`  – the public entry point used by the CLI.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "InteractiveScoutError",
    "ScoutSession",
    "run_interactive_scout",
]


# ─────────────────────────── exceptions ──────────────────────────────────


class InteractiveScoutError(RuntimeError):
    """Raised on TUI failures or missing ``textual`` dependency."""


# ─────────────────────────── session state ───────────────────────────────


_NOVELTY_CYCLE: tuple[str, ...] = ("maximal", "balanced", "permissive")


@dataclass
class ScoutSession:
    """Mutable state accumulated during an interactive scouting session.

    The default semantics: every panel in the underlying plan is treated
    as *accepted* unless explicitly listed in ``rejected_panel_ids``.  This
    matches the existing non-interactive ``figures scout`` behaviour — the
    user only needs to take action when they want to *remove* a panel from
    the plan.

    Attributes
    ----------
    project_root :
        The project root passed to :func:`scout_project` — preserved so
        the session can be serialised back into a :class:`FigurePlan`.
    plan :
        The :class:`~panelforge_figures.manifest.scout.FigurePlan` returned
        by :func:`scout_project`.  Held as :class:`Any` to avoid importing
        scout at module load time.
    novelty_report :
        The plan-level :class:`FigurePlanNoveltyReport` (as a dict, as
        emitted by ``ProjectScoutReport.to_dict``), or ``None`` when
        novelty scoring was skipped.
    accepted_panel_ids :
        Explicit positive acceptances — populated when the user presses
        ``ENTER`` over a panel.  Not strictly required (the rejection set
        is authoritative), but useful for the footer counter.
    rejected_panel_ids :
        Panels the user has explicitly rejected; filtered out before
        saving.
    edited_research_questions :
        Mapping ``panel_id → new research_question`` for inline edits.
    target_novelty :
        The current novelty threshold band; cycles through
        ``maximal → balanced → permissive``.
    """

    project_root: Path
    plan: Any
    novelty_report: dict[str, Any] | None = None
    accepted_panel_ids: set[str] = field(default_factory=set)
    rejected_panel_ids: set[str] = field(default_factory=set)
    edited_research_questions: dict[str, str] = field(default_factory=dict)
    target_novelty: str = "maximal"

    # ── queries ──────────────────────────────────────────────────────

    def is_accepted(self, panel_id: str) -> bool:
        """Return True unless the panel was explicitly rejected.

        The default-accept semantics mirror the existing non-interactive
        scout: every panel survives to the saved plan unless the user
        actively rejects it.
        """
        return panel_id not in self.rejected_panel_ids

    def is_rejected(self, panel_id: str) -> bool:
        """Return True iff the panel was explicitly rejected."""
        return panel_id in self.rejected_panel_ids

    def all_panel_ids(self) -> list[str]:
        """Return every ``panel_id`` in the plan in narrative order."""
        out: list[str] = []
        for fig in getattr(self.plan, "figures", ()):
            for panel in getattr(fig, "panels", ()):
                pid = getattr(panel, "panel_id", None)
                if pid:
                    out.append(str(pid))
        return out

    def get_research_question(self, panel_id: str, default: str = "") -> str:
        """Return the edited research question, or the default if untouched."""
        if panel_id in self.edited_research_questions:
            return self.edited_research_questions[panel_id]
        return default

    # ── mutations ────────────────────────────────────────────────────

    def accept(self, panel_id: str) -> None:
        """Mark ``panel_id`` as explicitly accepted (and clear any rejection)."""
        self.rejected_panel_ids.discard(panel_id)
        self.accepted_panel_ids.add(panel_id)

    def reject(self, panel_id: str) -> None:
        """Toggle: if currently rejected, un-reject; otherwise reject."""
        if panel_id in self.rejected_panel_ids:
            self.rejected_panel_ids.discard(panel_id)
        else:
            self.rejected_panel_ids.add(panel_id)
            self.accepted_panel_ids.discard(panel_id)

    def edit_research_question(self, panel_id: str, new_question: str) -> None:
        """Store an inline edit to a panel's research question."""
        self.edited_research_questions[panel_id] = new_question

    def cycle_target_novelty(self) -> str:
        """Advance ``target_novelty`` one step around the cycle and return it."""
        try:
            idx = _NOVELTY_CYCLE.index(self.target_novelty)
        except ValueError:
            idx = -1
        nxt = _NOVELTY_CYCLE[(idx + 1) % len(_NOVELTY_CYCLE)]
        self.target_novelty = nxt
        return nxt

    # ── derived counters ─────────────────────────────────────────────

    def status_line(self) -> str:
        """Human-readable verdict footer: ``X accepted / Y rejected / Z edited``."""
        all_ids = self.all_panel_ids()
        n_accepted = sum(1 for pid in all_ids if self.is_accepted(pid))
        n_rejected = len(self.rejected_panel_ids)
        n_edited = len(self.edited_research_questions)
        return (
            f"{n_accepted} accepted / {n_rejected} rejected / "
            f"{n_edited} edited  ·  novelty: {self.target_novelty}"
        )


# ─────────────────────────── plan filtering ─────────────────────────────


def _build_filtered_plan(session: ScoutSession) -> Any:
    """Return a new FigurePlan reflecting accept/reject/edits from ``session``.

    Imports :mod:`panelforge_figures.manifest.scout` lazily so the
    surrounding module stays import-cheap.
    """
    from ..manifest.scout import FigurePlan, FigureSlot, PanelSlot

    new_figures: list[FigureSlot] = []
    for fig in getattr(session.plan, "figures", ()):
        kept_panels: list[PanelSlot] = []
        for panel in getattr(fig, "panels", ()):
            pid = str(getattr(panel, "panel_id", ""))
            if not session.is_accepted(pid):
                continue
            new_question = session.edited_research_questions.get(
                pid, panel.research_question
            )
            kept_panels.append(
                PanelSlot(
                    panel_id=panel.panel_id,
                    figure_id=panel.figure_id,
                    recipe_full_name=panel.recipe_full_name,
                    research_question=new_question,
                    data_file_hint=panel.data_file_hint,
                    role=panel.role,
                    is_gap=panel.is_gap,
                    suggested_recipe_name=panel.suggested_recipe_name,
                    suggested_research_question=panel.suggested_research_question,
                    rationale=panel.rationale,
                )
            )
        if not kept_panels:
            # Drop entire figure if no panels survived; matches existing
            # ``figures scout`` behaviour where empty figures aren't written.
            continue
        new_figures.append(
            FigureSlot(
                figure_id=fig.figure_id,
                title=fig.title,
                slot_kind=fig.slot_kind,
                panels=tuple(kept_panels),
            )
        )

    n_panels = sum(len(f.panels) for f in new_figures)
    n_gaps = sum(1 for f in new_figures for p in f.panels if p.is_gap)
    return FigurePlan(
        project_root=session.plan.project_root,
        project_id=session.plan.project_id,
        figures=tuple(new_figures),
        venue=session.plan.venue,
        n_figures=len(new_figures),
        n_panels=n_panels,
        n_gaps=n_gaps,
    )


def _novelty_lookup(
    novelty_report: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Index a novelty report dict by ``panel_id`` for fast lookup."""
    if not novelty_report:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for panel in novelty_report.get("panels", []) or []:
        pid = str(panel.get("panel_id", ""))
        if pid:
            out[pid] = panel
    return out


def _format_panel_detail(panel: Any, edited_question: str | None) -> str:
    """Render the middle pane content for a single :class:`PanelSlot`."""
    question = edited_question if edited_question is not None else (
        getattr(panel, "research_question", "") or ""
    )
    edited_marker = "  [edited]" if edited_question is not None else ""
    recipe = getattr(panel, "recipe_full_name", "") or "(gap)"
    role = getattr(panel, "role", "primary")
    data_hint = getattr(panel, "data_file_hint", None)
    is_gap = getattr(panel, "is_gap", False)
    suggested = getattr(panel, "suggested_recipe_name", None)
    rationale = getattr(panel, "rationale", "")

    lines: list[str] = []
    lines.append(f"[b]Panel {getattr(panel, 'panel_id', '?')}[/b]  ({role})")
    lines.append("")
    lines.append(f"[b]Recipe:[/b]   {recipe}")
    if is_gap:
        lines.append("[b]Status:[/b]   [yellow]GAP[/yellow]")
        if suggested:
            lines.append(f"[b]Suggest:[/b]  {suggested}")
    if data_hint:
        lines.append(f"[b]Data:[/b]     {data_hint}")
    lines.append("")
    lines.append(f"[b]Research question:[/b]{edited_marker}")
    lines.append(f"  {question}")
    if rationale:
        lines.append("")
        lines.append("[b]Rationale:[/b]")
        lines.append(f"  {rationale}")
    return "\n".join(lines)


def _format_novelty_card(novelty: dict[str, Any] | None) -> str:
    """Render the right pane content from a single panel's novelty entry."""
    if novelty is None:
        return "[dim]no novelty data for this panel[/dim]"
    cls = str(novelty.get("novelty_class", "unknown"))
    n_papers = int(novelty.get("consensus_n_papers", 0) or 0)
    strength = float(novelty.get("consensus_strength", 0.0) or 0.0)
    suggestion = str(novelty.get("suggestion", ""))
    rationale = str(novelty.get("rationale", ""))
    top = list(novelty.get("top_paper_titles", []) or [])

    color = {
        "ultra_novelty": "yellow",
        "hidden_novelty": "green",
        "incremental": "cyan",
        "repetition": "red",
    }.get(cls, "white")
    lines: list[str] = []
    lines.append(f"[b][{color}]{cls}[/{color}][/b]")
    lines.append("")
    lines.append(f"[b]n_papers:[/b]   {n_papers}")
    lines.append(f"[b]consensus:[/b]  {strength:.2f}")
    lines.append(f"[b]action:[/b]     {suggestion}")
    lines.append("")
    if rationale:
        lines.append("[b]why:[/b]")
        lines.append(f"  {rationale}")
        lines.append("")
    if top:
        lines.append("[b]top papers:[/b]")
        for t in top[:3]:
            lines.append(f"  · {t}")
    return "\n".join(lines)


# ─────────────────────────── textual app builder ────────────────────────


def _build_app(session: ScoutSession) -> Any:
    """Build the :class:`textual.app.App` subclass on demand.

    Defined inside a function so that ``textual`` is only imported when the
    user actually requests the TUI — the same lazy strategy used by the
    optional ``mcp`` and ``embeddings`` extras.
    """
    from textual import on
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.screen import ModalScreen
    from textual.widgets import (
        Footer,
        Header,
        Input,
        Static,
        Tree,
    )

    # ── modal: edit research question ────────────────────────────────

    class EditQuestionModal(ModalScreen[str | None]):
        """Modal prompting the user for a new research question."""

        BINDINGS = [
            Binding("escape", "dismiss(None)", "cancel"),
        ]

        def __init__(self, current: str) -> None:
            super().__init__()
            self._current = current

        def compose(self) -> ComposeResult:  # type: ignore[override]
            yield Vertical(
                Static("Edit research question  (ENTER to save, ESC to cancel)"),
                Input(value=self._current, id="rq-input"),
                id="edit-modal",
            )

        def on_input_submitted(self, event: Input.Submitted) -> None:
            self.dismiss(event.value)

    # ── modal: help screen ───────────────────────────────────────────

    HELP_TEXT = (
        "[b]panelforge scout — interactive TUI[/b]\n\n"
        "[b]Navigation[/b]\n"
        "  ↑ / ↓        select panel in the tree\n"
        "  q            commit + quit (save filtered plan)\n"
        "  escape       cancel + quit (no save)\n"
        "\n"
        "[b]Per-panel actions[/b]\n"
        "  ENTER        accept current panel\n"
        "  x            toggle reject for current panel\n"
        "  e            edit research question (modal)\n"
        "  r            re-score novelty for current panel\n"
        "\n"
        "[b]Plan-level actions[/b]\n"
        "  n            cycle target_novelty (maximal → balanced → permissive)\n"
        "  ?            this help screen\n"
    )

    class HelpModal(ModalScreen[None]):
        BINDINGS = [
            Binding("escape", "dismiss", "close"),
            Binding("question_mark", "dismiss", "close"),
        ]

        def compose(self) -> ComposeResult:  # type: ignore[override]
            yield Vertical(Static(HELP_TEXT), id="help-modal")

    # ── main app ─────────────────────────────────────────────────────

    class ScoutApp(App):
        """Interactive scout TUI; uses :class:`ScoutSession` as state."""

        CSS = """
        #plan-pane { width: 35%; border: round $accent; }
        #detail-pane { width: 40%; border: round $accent; padding: 1; }
        #novelty-pane { width: 25%; border: round $accent; padding: 1; }
        #edit-modal { background: $boost; padding: 2; width: 80; height: 7; }
        #help-modal { background: $boost; padding: 2; width: 70; height: 18; }
        """

        BINDINGS = [
            Binding("enter", "accept_panel", "accept"),
            Binding("x", "reject_panel", "reject"),
            Binding("e", "edit_question", "edit"),
            Binding("n", "cycle_novelty", "novelty"),
            Binding("r", "rescore_novelty", "rescore"),
            Binding("q", "commit_quit", "save+quit"),
            Binding("escape", "cancel_quit", "cancel"),
            Binding("question_mark", "show_help", "help"),
        ]

        def __init__(self, scout_session: ScoutSession) -> None:
            super().__init__()
            self.scout_session = scout_session
            self._committed = False
            self._novelty_index = _novelty_lookup(scout_session.novelty_report)
            self._panel_lookup: dict[str, Any] = {}
            for fig in getattr(scout_session.plan, "figures", ()):
                for p in getattr(fig, "panels", ()):
                    self._panel_lookup[str(p.panel_id)] = p

        # ── compose ──────────────────────────────────────────────────

        def compose(self) -> ComposeResult:  # type: ignore[override]
            yield Header()
            tree: Tree = Tree("plan", id="plan-tree")
            tree.show_root = False
            for fig in getattr(self.scout_session.plan, "figures", ()):
                fig_node = tree.root.add(
                    f"{fig.figure_id}  {fig.title}", expand=True
                )
                for panel in getattr(fig, "panels", ()):
                    label = self._panel_label(panel)
                    fig_node.add_leaf(label, data=str(panel.panel_id))
            yield Horizontal(
                Vertical(tree, id="plan-pane"),
                Static("[dim]select a panel[/dim]", id="detail-pane"),
                Static("[dim]select a panel[/dim]", id="novelty-pane"),
            )
            yield Footer()

        def on_mount(self) -> None:
            self.title = "panelforge scout"
            self.sub_title = self.scout_session.status_line()
            tree: Tree = self.query_one("#plan-tree", Tree)
            if tree.root.children:
                first_fig = tree.root.children[0]
                if first_fig.children:
                    tree.select_node(first_fig.children[0])
                    self._refresh_panes(str(first_fig.children[0].data))

        # ── helpers ──────────────────────────────────────────────────

        def _panel_label(self, panel: Any) -> str:
            """Format a panel-tree leaf label with status + colour."""
            pid = str(panel.panel_id)
            recipe = getattr(panel, "recipe_full_name", "") or "(gap)"
            mark = " "
            colour = ""
            if self.scout_session.is_rejected(pid):
                mark = "✗"
                colour = "[red]"
            elif pid in self.scout_session.accepted_panel_ids:
                mark = "✓"
                colour = "[green]"
            novelty = self._novelty_index.get(pid)
            if novelty:
                cls = str(novelty.get("novelty_class", ""))
                if cls == "ultra_novelty":
                    colour = colour or "[yellow]"
            close = "[/]" if colour else ""
            return f"{colour}{mark}{close} {pid}  {recipe}"

        def _refresh_tree_labels(self) -> None:
            tree: Tree = self.query_one("#plan-tree", Tree)
            for fig_node, fig in zip(tree.root.children, getattr(self.scout_session.plan, "figures", ()), strict=False):
                for leaf, panel in zip(fig_node.children, getattr(fig, "panels", ()), strict=False):
                    leaf.set_label(self._panel_label(panel))

        def _refresh_panes(self, panel_id: str) -> None:
            panel = self._panel_lookup.get(panel_id)
            if panel is None:
                return
            edited = self.scout_session.edited_research_questions.get(panel_id)
            detail = self.query_one("#detail-pane", Static)
            detail.update(_format_panel_detail(panel, edited))
            novelty_card = self.query_one("#novelty-pane", Static)
            novelty_card.update(_format_novelty_card(self._novelty_index.get(panel_id)))
            self.sub_title = self.scout_session.status_line()

        def _current_panel_id(self) -> str | None:
            tree: Tree = self.query_one("#plan-tree", Tree)
            node = tree.cursor_node
            if node is None or node.data is None:
                return None
            return str(node.data)

        # ── tree events ──────────────────────────────────────────────

        @on(Tree.NodeHighlighted)
        def _on_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
            if event.node.data is not None:
                self._refresh_panes(str(event.node.data))

        # ── actions ──────────────────────────────────────────────────

        def action_accept_panel(self) -> None:
            pid = self._current_panel_id()
            if pid is None:
                return
            self.scout_session.accept(pid)
            self._refresh_tree_labels()
            self._refresh_panes(pid)

        def action_reject_panel(self) -> None:
            pid = self._current_panel_id()
            if pid is None:
                return
            self.scout_session.reject(pid)
            self._refresh_tree_labels()
            self._refresh_panes(pid)

        def action_cycle_novelty(self) -> None:
            self.scout_session.cycle_target_novelty()
            self.sub_title = self.scout_session.status_line()

        def action_edit_question(self) -> None:
            pid = self._current_panel_id()
            if pid is None:
                return
            panel = self._panel_lookup.get(pid)
            if panel is None:
                return
            current = self.scout_session.edited_research_questions.get(
                pid, getattr(panel, "research_question", "") or ""
            )

            def _on_dismissed(result: str | None) -> None:
                if result is None:
                    return
                if result.strip():
                    self.scout_session.edit_research_question(pid, result.strip())
                    self._refresh_panes(pid)

            self.push_screen(EditQuestionModal(current), _on_dismissed)

        async def action_rescore_novelty(self) -> None:
            """Re-score novelty for the current panel.

            Lazy-imports the novelty scout and runs the (potentially blocking)
            ``Consensus.app`` call in a background thread via
            :func:`asyncio.to_thread` so the UI stays responsive.  Falls back
            to the mock client when no API key is configured — the same
            policy used by ``scout_project``.
            """
            pid = self._current_panel_id()
            if pid is None:
                return
            panel = self._panel_lookup.get(pid)
            if panel is None or getattr(panel, "is_gap", False):
                return

            try:
                novelty = await asyncio.to_thread(
                    _rescore_single_panel,
                    panel,
                    self.scout_session,
                )
            except Exception as exc:  # pragma: no cover — defensive
                novelty_card = self.query_one("#novelty-pane", Static)
                novelty_card.update(f"[red]rescore failed:[/red]\n  {exc}")
                return

            if novelty is None:
                return
            self._novelty_index[pid] = novelty
            self._refresh_tree_labels()
            self._refresh_panes(pid)

        def action_commit_quit(self) -> None:
            self._committed = True
            self.exit(result=True)

        def action_cancel_quit(self) -> None:
            self._committed = False
            self.exit(result=False)

        def action_show_help(self) -> None:
            self.push_screen(HelpModal())

    return ScoutApp


def _rescore_single_panel(
    panel: Any,
    session: ScoutSession,
) -> dict[str, Any] | None:
    """Score a single panel and return its serialised assessment.

    Centralised so the (blocking) network call lives outside the event
    loop.  Returns ``None`` on any failure rather than raising into the
    UI.
    """
    try:
        from ..manifest.novelty_scout import (
            MockConsensusClient,
            PanelCandidate,
            PanelRole,
            TargetNovelty,
            assess_panel_novelty,
        )
        from ..manifest.scout import _resolve_consensus_client  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover — defensive
        return None

    role_str = str(getattr(panel, "role", "primary")).lower()
    try:
        role = PanelRole(role_str)
    except ValueError:
        role = PanelRole.primary

    edited_q = session.edited_research_questions.get(
        str(panel.panel_id), getattr(panel, "research_question", "") or ""
    )
    candidate = PanelCandidate(
        panel_id=str(panel.panel_id),
        recipe_full_name=str(getattr(panel, "recipe_full_name", "") or ""),
        research_question=edited_q,
        role=role,
    )
    try:
        client = _resolve_consensus_client(None, True)  # mock by default for safety
    except Exception:
        client = MockConsensusClient()
    try:
        target = TargetNovelty(session.target_novelty)
    except ValueError:
        target = TargetNovelty.maximal
    try:
        assessment = assess_panel_novelty(candidate, client, target=target)
    except Exception:  # pragma: no cover — defensive
        return None
    return assessment.to_dict()


# ─────────────────────────── public entry ───────────────────────────────


def run_interactive_scout(
    project_root: Path,
    *,
    max_figures: int = 4,
    venue: str = "cell",
    target_novelty: str = "maximal",
    use_mock_novelty: bool = False,
    plan_out: Path = Path("figures_plan.yaml"),
    _app_factory: Any | None = None,
) -> Path:
    """Launch the textual TUI for interactive scouting.

    Pipeline
    --------
    1. Run :func:`scout_project` to produce the initial plan + novelty report.
    2. Wrap it in a :class:`ScoutSession`.
    3. Instantiate the textual ``ScoutApp`` and run it synchronously.
    4. If the user committed (``q``), filter the plan against the session
       state (drop rejected panels, apply edits) and save via
       :func:`save_figure_plan_yaml`.
    5. If the user cancelled (``ESC``), do not write anything.
    6. Return the plan path either way (callers can ``Path.exists()``
       check it).

    Parameters
    ----------
    project_root :
        The project to scout; passed through to :func:`scout_project`.
    max_figures :
        Forwarded to :func:`scout_project`.
    venue :
        Forwarded to :func:`scout_project`.
    target_novelty :
        Initial target novelty band; user can cycle via ``n`` once in the
        TUI.
    use_mock_novelty :
        Forwarded to :func:`scout_project`.  When True, prevents live API
        calls (useful for offline testing).
    plan_out :
        Path to write the committed plan to.  Created (or overwritten) on
        commit; not touched on cancel.
    _app_factory :
        Test seam — injects a fake app class so unit tests can exercise
        :func:`run_interactive_scout` without booting a real terminal.
        Production callers must leave this as ``None``.

    Raises
    ------
    InteractiveScoutError
        When ``textual`` is not installed (suggests the ``[tui]`` extra),
        or when the underlying scout pipeline raises.
    """
    if _app_factory is None:
        try:
            from textual.app import App  # noqa: F401
        except ImportError as exc:
            raise InteractiveScoutError(
                "textual not installed. Install with: "
                "pip install panelforge-figures[tui]"
            ) from exc

    try:
        from ..manifest.scout import save_figure_plan_yaml, scout_project
    except Exception as exc:  # pragma: no cover — defensive
        raise InteractiveScoutError(
            f"could not import scout pipeline: {exc}"
        ) from exc

    # ── step 1: produce the initial plan ─────────────────────────────
    try:
        report = scout_project(
            project_root,
            max_figures=max_figures,
            venue=venue,
            target_novelty=target_novelty,
            use_mock_novelty=use_mock_novelty,
            manuscript_policy="preserve",  # TUI doesn't surface collisions
        )
    except Exception as exc:
        raise InteractiveScoutError(f"scout pipeline failed: {exc}") from exc

    session = ScoutSession(
        project_root=Path(project_root),
        plan=report.figure_plan,
        novelty_report=report.novelty_report,
        target_novelty=target_novelty,
    )

    # ── step 2: run the textual app ──────────────────────────────────
    app_factory = _app_factory or _build_app(session)
    app = app_factory(session) if _app_factory is None else app_factory(session)
    try:
        result = app.run()
    except Exception as exc:  # pragma: no cover — defensive
        raise InteractiveScoutError(f"TUI session failed: {exc}") from exc

    # ── step 3: apply session edits + save ───────────────────────────
    if result is False:
        return plan_out  # cancelled — do not write

    filtered = _build_filtered_plan(session)
    save_figure_plan_yaml(filtered, plan_out)
    return plan_out
