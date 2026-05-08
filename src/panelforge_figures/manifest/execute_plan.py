"""Plan executor (Elevation 9 — phase 2).

Given a ``figures_plan.yaml`` produced by ``scout_project`` (Build-A) the
executor walks every panel and runs the four-phase orchestration:

1. **Recipe scaffolding** — for any panel flagged ``is_gap=True``, lazily
   import :mod:`panelforge_figures.manifest.recipe_authoring` and write
   the missing recipe + smoke test (E6).  Gated by ``scaffold_recipes``.
2. **Render** — for every panel with a real recipe (after scaffolding,
   if applicable), call into the existing render path so a PDF / PNG
   land alongside their provenance sidecars.  Gated by ``render_figures``.
3. **Caption drafting** — for every successfully rendered figure, locate
   the ``*.provenance.json`` sidecar and call
   :func:`panelforge_figures.manifest.caption.draft_caption_from_provenance`
   (E5) to write ``panelforge_workspace/captions/figure_<id>.md``.  Gated
   by ``draft_captions``.
4. **Manuscript scaffold** — call into Build-B's
   :mod:`panelforge_figures.manifest.manuscript_scaffold` to generate
   ``manuscript/main.tex`` (or markdown) plus a ``references.bib`` stub.
   Gated by ``scaffold_manuscript``.

The executor is **tolerant**: per-panel exceptions are captured and
emitted as ``status="failed"`` rows in the returned
:class:`ExecutionResult`, but they never abort the loop.  Phase
dependencies that aren't yet on disk (e.g. Build-B's manuscript_scaffold
landing later in the merge) raise an ``ImportError`` that is caught and
soft-warned via the ``notes`` tuple — the caller still gets a valid
result.

Public surface
--------------
- :class:`ExecutionResult`         — frozen dataclass returned by
  :func:`execute_plan`.
- :class:`PanelExecutionStatus`    — string codes used in
  :attr:`ExecutionResult.panels_status`.
- :class:`ExecutionError`          — raised on plan-load failures only.
- :func:`execute_plan`             — main entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ExecutionError",
    "ExecutionResult",
    "PanelExecutionStatus",
    "execute_plan",
]


# ─────────────────────────── status codes ────────────────────────────────


class PanelExecutionStatus(str):
    """One per panel — string codes for stable JSON output.

    Subclassing :class:`str` (rather than :class:`enum.StrEnum`) keeps
    the values JSON-stable without forcing the consumer to import the
    enum: a downstream tool can compare ``status == "rendered"`` and the
    test would pass against either the literal or our class attribute.
    """

    rendered = "rendered"
    scaffolded_then_rendered = "scaffolded_then_rendered"
    skipped_gap = "skipped_gap"
    failed = "failed"


# ─────────────────────────── errors ─────────────────────────────────────


class ExecutionError(RuntimeError):
    """Raised on plan-load errors or unrecoverable execution failures.

    Per-panel render / scaffold / caption failures do *not* raise this —
    they are reported as ``status="failed"`` rows.  This exception is
    reserved for issues that prevent execution from making any progress
    (missing plan file, malformed YAML, unknown plan version, etc.).
    """


# ─────────────────────────── result dataclass ───────────────────────────


@dataclass(frozen=True)
class ExecutionResult:
    """Aggregate outcome of one :func:`execute_plan` run.

    Attributes
    ----------
    project_root
        Resolved absolute path to the project the plan was executed
        against.
    n_panels_attempted
        Number of panels in the plan, regardless of phase toggles.
        Phases that are toggled off don't change this number — they
        change the per-panel status.
    n_panels_rendered
        Panels whose status ended in ``rendered`` *or*
        ``scaffolded_then_rendered``.
    n_recipes_scaffolded
        Panels whose ``is_gap`` was True *and* whose scaffold step
        succeeded.
    n_captions_drafted
        Captions written in phase 3.
    manuscript_path
        Path to the manuscript scaffold written in phase 4, or ``None``
        if the phase was disabled / failed.
    panels_status
        One ``(panel_id, status, message)`` triple per panel, in the
        plan order.  ``message`` is a short human-readable hint; for
        successful renders this is the rendered path's ``str()``.
    notes
        Soft warnings (missing optional dependencies, deferred phases,
        etc.).  Always populated even on success when phases were
        disabled — the consumer can surface these to the user verbatim.
    """

    project_root: Path
    n_panels_attempted: int
    n_panels_rendered: int
    n_recipes_scaffolded: int
    n_captions_drafted: int
    manuscript_path: Path | None
    panels_status: tuple[tuple[str, str, str], ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


# ─────────────────────────── plan loading ───────────────────────────────


def _load_plan(plan_path: Path) -> Any:
    """Load a ``figures_plan.yaml`` via Build-A's loader.

    Importing this lazily lets the executor remain importable even when
    Build-A's ``scout`` module hasn't landed yet — useful for the merge
    window during the swarm build.
    """
    try:
        from panelforge_figures.manifest.scout import load_figure_plan_yaml
    except ImportError as exc:
        raise ExecutionError(
            f"cannot import scout.load_figure_plan_yaml — Build-A's module "
            f"may not be on disk yet: {exc}"
        ) from exc

    try:
        return load_figure_plan_yaml(plan_path)
    except Exception as exc:  # noqa: BLE001 — loader is third-party-ish
        raise ExecutionError(
            f"failed to load figures_plan from {plan_path}: {exc}"
        ) from exc


# ─────────────────────────── per-panel helpers ──────────────────────────


def _panel_attr(panel: Any, name: str, default: Any = None) -> Any:
    """Read an attribute from a panel object or mapping.

    The plan schema is owned by Build-A; we accept both a dataclass-like
    object (``panel.panel_id``) and a plain dict (``panel["panel_id"]``)
    so the executor stays robust to whatever shape lands.
    """
    if isinstance(panel, dict):
        return panel.get(name, default)
    return getattr(panel, name, default)


def _panel_id(panel: Any, fallback_index: int) -> str:
    """Best-effort panel identifier.

    Falls back to ``panel_<i>`` when the plan didn't supply one — keeps
    the per-panel status table readable even on minimal plans.
    """
    pid = _panel_attr(panel, "panel_id")
    if not pid:
        pid = _panel_attr(panel, "id")
    return str(pid) if pid is not None else f"panel_{fallback_index}"


def _scaffold_one_gap(
    panel: Any,
    *,
    project_root: Path,
    notes: list[str],
) -> tuple[bool, str]:
    """Try to scaffold a single gap panel.

    Returns ``(scaffolded, message)`` where ``message`` is a short status
    string suitable for the per-panel results table.
    """
    try:
        from panelforge_figures.manifest.recipe_authoring import (
            RecipeAuthoringError,
            scaffold_recipe,
            write_scaffold,
        )
    except ImportError as exc:
        notes.append(f"recipe_authoring unavailable: {exc}")
        return False, "scaffold-skipped: recipe_authoring unavailable"

    modality = _panel_attr(panel, "modality") or "meta_and_diagnostic"
    recipe_name = (
        _panel_attr(panel, "recipe_name")
        or _panel_attr(panel, "suggested_recipe_name")
        or _panel_attr(panel, "panel_id")
        or "scaffold_panel"
    )
    family = _panel_attr(panel, "family") or "comparison"
    research_question = (
        _panel_attr(panel, "research_question")
        or _panel_attr(panel, "question")
        or f"What does panel {_panel_id(panel, 0)} show?"
    )

    try:
        scaffold = scaffold_recipe(
            modality=str(modality),
            recipe_name=str(recipe_name).replace("-", "_"),
            family=str(family),
            research_question=str(research_question),
            project_root=project_root,
        )
        write_scaffold(scaffold, overwrite=False)
    except RecipeAuthoringError as exc:
        return False, f"scaffold-error: {exc}"
    except Exception as exc:  # noqa: BLE001 — keep loop running
        return False, f"scaffold-error: {type(exc).__name__}: {exc}"

    return True, f"scaffolded {scaffold.recipe_module_path.name}"


def _render_one_panel(
    panel: Any,
    *,
    project_root: Path,
    out_dir: Path,
    notes: list[str],
) -> tuple[bool, str, Path | None]:
    """Render a single panel via the existing render_loop path.

    The render path expects a :class:`RenderBinding` + matching
    :class:`RenderDataFile`.  We synthesise a minimal binding from the
    panel description; if the plan didn't include the data wiring (only
    a recipe full_name) the render is skipped with a clear message —
    this matches the v3.2.0 behaviour where unbound recipes show up as
    ``skipped_unbound``.
    """
    try:
        from panelforge_figures.manifest.render_loop import (
            EnvironmentalFailure,
            RenderBinding,
            RenderDataFile,
            render_shortlist,
        )
    except ImportError as exc:
        notes.append(f"render_loop unavailable: {exc}")
        return False, f"render-skipped: render_loop unavailable: {exc}", None

    full_name = _panel_attr(panel, "recipe_full_name")
    if not full_name:
        modality = _panel_attr(panel, "modality")
        recipe_name = _panel_attr(panel, "recipe_name")
        if modality and recipe_name:
            full_name = f"{modality}.{recipe_name}"
    if not full_name:
        return False, "render-skipped: panel has no recipe_full_name", None

    column_mapping = dict(_panel_attr(panel, "column_mapping", {}) or {})
    data_file_path = _panel_attr(panel, "data_file") or _panel_attr(
        panel, "data_path"
    )
    file_id = _panel_attr(panel, "data_file_id") or "data_0"

    data_files: list[Any] = []
    if data_file_path:
        data_files.append(RenderDataFile(file_id=file_id, path=Path(data_file_path)))

    binding = RenderBinding(
        full_name=str(full_name),
        fully_bound=bool(column_mapping and data_file_path),
        column_mapping=column_mapping,
        data_file_id=file_id if data_file_path else None,
    )

    try:
        log = render_shortlist(
            bindings=[binding],
            data_files=data_files,
            out_dir=out_dir,
        )
    except EnvironmentalFailure as exc:
        notes.append(f"render env-failure on {full_name}: {exc}")
        return False, f"render-error: env-failure: {exc}", None
    except Exception as exc:  # noqa: BLE001 — keep loop running
        notes.append(f"render exception on {full_name}: {exc}")
        return False, f"render-error: {type(exc).__name__}: {exc}", None

    if not log.outcomes:
        return False, "render-error: no outcome returned", None
    outcome = log.outcomes[0]
    if outcome.status == "success" and outcome.pdf_path is not None:
        return True, f"rendered {outcome.pdf_path.name}", outcome.pdf_path
    return False, f"render-{outcome.status}: {outcome.error_message or ''}", None


def _draft_caption_for_panel(
    panel_id: str,
    rendered_path: Path,
    *,
    captions_dir: Path,
    notes: list[str],
) -> bool:
    """Locate the provenance sidecar for ``rendered_path`` and draft a caption.

    Sidecars are emitted by the v1.8.0 provenance chain alongside every
    successful render.  Their canonical location is
    ``<rendered_path>.provenance.json``; we also accept the legacy
    ``<rendered_path>.provenance.json`` (same file, different stem) by
    falling back to ``<stem>.provenance.json``.
    """
    try:
        from panelforge_figures.manifest.caption import (
            CaptionError,
            draft_caption_from_provenance,
            render_caption_markdown,
        )
    except ImportError as exc:
        notes.append(f"caption unavailable: {exc}")
        return False

    candidate_a = rendered_path.with_suffix(rendered_path.suffix + ".provenance.json")
    candidate_b = rendered_path.with_suffix(".provenance.json")
    sidecar = next(
        (p for p in (candidate_a, candidate_b) if p.exists()),
        None,
    )
    if sidecar is None:
        notes.append(
            f"no provenance sidecar found for {rendered_path.name}; "
            "skipping caption"
        )
        return False

    try:
        draft = draft_caption_from_provenance(sidecar)
        markdown = render_caption_markdown(draft)
    except CaptionError as exc:
        notes.append(f"caption error for {panel_id}: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001 — keep loop running
        notes.append(f"caption exception for {panel_id}: {exc}")
        return False

    captions_dir.mkdir(parents=True, exist_ok=True)
    out_path = captions_dir / f"figure_{panel_id}.md"
    out_path.write_text(markdown, encoding="utf-8")
    return True


def _scaffold_manuscript(
    plan: Any,
    *,
    project_root: Path,
    venue: str,
    fmt: str,
    notes: list[str],
) -> Path | None:
    """Call into Build-B's ``scaffold_manuscript`` if available.

    Build-B's module may not be on disk during a Build-C-only test pass;
    we treat ``ImportError`` as a soft failure (note + ``None``) rather
    than aborting the whole execution.
    """
    try:
        from panelforge_figures.manifest.manuscript_scaffold import (
            ManuscriptFormat,
            ScaffoldError,
            Venue,
            scaffold_manuscript,
        )
    except ImportError as exc:
        notes.append(
            f"manuscript_scaffold unavailable (Build-B not landed?): {exc}"
        )
        return None

    try:
        result = scaffold_manuscript(
            plan,
            project_root=project_root,
            venue=Venue(venue),
            format=ManuscriptFormat(fmt),
            overwrite=True,
        )
    except ScaffoldError as exc:
        notes.append(f"manuscript scaffold error: {exc}")
        return None
    except Exception as exc:  # noqa: BLE001 — keep loop running
        notes.append(
            f"manuscript scaffold exception: {type(exc).__name__}: {exc}"
        )
        return None

    return getattr(result, "manuscript_path", None)


# ─────────────────────────── main entrypoint ────────────────────────────


def execute_plan(
    plan_path: Path,
    *,
    yes: bool = False,
    scaffold_recipes: bool = True,
    render_figures: bool = True,
    draft_captions: bool = True,
    scaffold_manuscript: bool = True,
    manuscript_venue: str = "cell",
    manuscript_format: str = "latex",
) -> ExecutionResult:
    """Execute a ``figures_plan.yaml`` end-to-end.

    See the module docstring for the four-phase pipeline.  Each phase
    honours a corresponding boolean flag; when *all* flags are off the
    result is a no-op (zero counters, zero rows, no manuscript).

    The ``yes`` flag suppresses interactive confirmation around scaffold
    operations.  In v3.3.0 the executor is non-interactive end-to-end
    (we never call ``input()``); the parameter is wired for forward
    compatibility with a CLI prompt that may land later.
    """
    plan_path = Path(plan_path)
    plan = _load_plan(plan_path)

    project_root = Path(_panel_attr(plan, "project_root") or plan_path.parent)
    project_root = project_root.resolve()

    panels = list(_panel_attr(plan, "panels", []) or [])
    if not panels:
        # An empty plan is not an error — it's a no-op.
        return ExecutionResult(
            project_root=project_root,
            n_panels_attempted=0,
            n_panels_rendered=0,
            n_recipes_scaffolded=0,
            n_captions_drafted=0,
            manuscript_path=None,
            panels_status=(),
            notes=("plan contained zero panels — nothing to execute",),
        )

    workspace = project_root / "panelforge_workspace"
    figures_dir = project_root / "figures"
    captions_dir = workspace / "captions"

    statuses: list[tuple[str, str, str]] = []
    notes: list[str] = []
    n_rendered = 0
    n_scaffolded = 0
    n_captions = 0

    # ── Phase 1 + 2: scaffold gaps then render every panel ────────────
    rendered_paths: dict[str, Path] = {}
    for i, panel in enumerate(panels):
        pid = _panel_id(panel, i)
        is_gap = bool(_panel_attr(panel, "is_gap", False))
        scaffolded_here = False

        if is_gap:
            if not scaffold_recipes:
                statuses.append(
                    (pid, PanelExecutionStatus.skipped_gap,
                     "gap-skipped (scaffold_recipes=False)")
                )
                continue
            ok, msg = _scaffold_one_gap(
                panel, project_root=project_root, notes=notes,
            )
            if ok:
                n_scaffolded += 1
                scaffolded_here = True
            else:
                statuses.append((pid, PanelExecutionStatus.failed, msg))
                continue

        if not render_figures:
            # Status reflects whether we scaffolded; without a render
            # we can't claim "rendered".
            label = "skipped (render_figures=False)"
            if scaffolded_here:
                label = "scaffolded; render skipped (render_figures=False)"
            statuses.append((pid, PanelExecutionStatus.skipped_gap, label))
            continue

        ok_r, msg_r, path_r = _render_one_panel(
            panel, project_root=project_root,
            out_dir=figures_dir, notes=notes,
        )
        if ok_r:
            n_rendered += 1
            status_code = (
                PanelExecutionStatus.scaffolded_then_rendered
                if scaffolded_here
                else PanelExecutionStatus.rendered
            )
            statuses.append((pid, status_code, msg_r))
            if path_r is not None:
                rendered_paths[pid] = path_r
        else:
            statuses.append((pid, PanelExecutionStatus.failed, msg_r))

    # ── Phase 3: caption drafts for everything we successfully rendered ─
    if draft_captions:
        for pid, path in rendered_paths.items():
            if _draft_caption_for_panel(
                pid, path, captions_dir=captions_dir, notes=notes,
            ):
                n_captions += 1
    else:
        notes.append("captions skipped (draft_captions=False)")

    # ── Phase 4: manuscript ─────────────────────────────────────────────
    manuscript_path: Path | None = None
    if scaffold_manuscript:
        manuscript_path = _scaffold_manuscript(
            plan,
            project_root=project_root,
            venue=manuscript_venue,
            fmt=manuscript_format,
            notes=notes,
        )
    else:
        notes.append("manuscript skipped (scaffold_manuscript=False)")

    return ExecutionResult(
        project_root=project_root,
        n_panels_attempted=len(panels),
        n_panels_rendered=n_rendered,
        n_recipes_scaffolded=n_scaffolded,
        n_captions_drafted=n_captions,
        manuscript_path=manuscript_path,
        panels_status=tuple(statuses),
        notes=tuple(notes),
    )
