"""Cross-project portfolio + diff module — Sprint 3A.

See ``docs/spec_cross_project.md`` §4, §5.2, §5.3 for design.

Turns the per-user :class:`Registry` into a portfolio view: pairwise
recipe diff, inverted-index aggregation, and a terminal / PNG heatmap.
Read-only consumer — never writes to the registry.

Manifest reading tolerates two shapes: the simple ``panels:`` top-level
form (spec §4 example) and the canonical
``figures[*].panels[*].recipe`` form used by
:class:`panelforge_figures.manifest.schema.Manifest`. Missing or
malformed manifests warn but never raise so a half-broken project
doesn't crash the portfolio view.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import ProjectEntry, Registry  # sibling — Build-A's scope

__all__ = [
    "DiffReport",
    "PortfolioSummary",
    "RecipeUsage",
    "aggregate_portfolio",
    "diff_projects",
    "load_project_recipe_set",
    "render_heatmap_png",
    "render_heatmap_terminal",
    "top_n_recipes",
]


# --------------------------------------------------------------------------- #
# Public dataclasses                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RecipeUsage:
    """One row in the portfolio top-N table.

    ``recipe_full_name`` is the fully qualified ``modality.recipe``
    string; ``project_count`` is the number of registered projects whose
    manifest references the recipe; ``project_ids`` is sorted.
    """

    recipe_full_name: str
    project_count: int
    project_ids: tuple[str, ...]


@dataclass(frozen=True)
class DiffReport:
    """Output of :func:`diff_projects`.

    The ``suggestion`` is the heuristic shared-methods nudge: set iff
    ``len(shared) >= 3`` (spec §4); otherwise ``None``.
    """

    project_a_id: str
    project_b_id: str
    a_only: tuple[str, ...]
    b_only: tuple[str, ...]
    shared: tuple[str, ...]
    suggestion: str | None


@dataclass(frozen=True)
class PortfolioSummary:
    """Aggregate view across the registry.

    ``recipes_by_project`` is the forward map; ``recipe_to_projects`` is
    the inverted index. ``project_ids`` preserves registry insertion
    order, restricted to projects whose manifest was successfully read.
    """

    n_projects: int
    n_distinct_recipes: int
    project_ids: tuple[str, ...]
    recipes_by_project: dict[str, frozenset[str]]
    recipe_to_projects: dict[str, frozenset[str]]


# --------------------------------------------------------------------------- #
# Manifest reading                                                            #
# --------------------------------------------------------------------------- #


def _extract_recipes_from_manifest(data: Any) -> set[str]:
    """Pull recipe full-names from a parsed manifest dict.

    Tolerates the simple ``panels:`` top-level form and the canonical
    ``figures[*].panels[*].recipe`` form. Panels without a ``recipe``
    field are silently skipped.
    """
    recipes: set[str] = set()
    if not isinstance(data, dict):
        return recipes

    panels = data.get("panels")
    if isinstance(panels, list):
        for panel in panels:
            if isinstance(panel, dict):
                recipe = panel.get("recipe")
                if isinstance(recipe, str) and recipe:
                    recipes.add(recipe)

    figures = data.get("figures")
    if isinstance(figures, list):
        for fig in figures:
            if not isinstance(fig, dict):
                continue
            fig_panels = fig.get("panels")
            if not isinstance(fig_panels, list):
                continue
            for panel in fig_panels:
                if isinstance(panel, dict):
                    recipe = panel.get("recipe")
                    if isinstance(recipe, str) and recipe:
                        recipes.add(recipe)

    return recipes


def load_project_recipe_set(entry: ProjectEntry) -> frozenset[str]:
    """Return the frozenset of recipe full-names referenced by the project's
    ``panelforge_workspace/manifest.yaml``.

    Missing file, parse error, or unrecognised shape all return an empty
    frozenset and emit a :class:`RuntimeWarning`.
    """
    manifest_path = Path(entry.path) / "panelforge_workspace" / "manifest.yaml"
    if not manifest_path.is_file():
        warnings.warn(
            f"manifest not found for project {entry.id!r}: {manifest_path}",
            RuntimeWarning,
            stacklevel=2,
        )
        return frozenset()

    try:
        text = manifest_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (OSError, yaml.YAMLError) as exc:
        warnings.warn(
            f"failed to read manifest for project {entry.id!r} "
            f"({manifest_path}): {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return frozenset()

    return frozenset(_extract_recipes_from_manifest(data))


# --------------------------------------------------------------------------- #
# Diff (two projects)                                                         #
# --------------------------------------------------------------------------- #


_SHARED_THRESHOLD = 3
_SUGGESTION_TEMPLATE = (
    "Suggestion: extract a `shared_methods.figure.yaml` using the {n} shared "
    "recipes — single source of truth for common methods across both papers."
)


def diff_projects(registry: Registry, a_id: str, b_id: str) -> DiffReport:
    """Recipe-overlap analysis between two registered projects.

    Loads each project's manifest, computes set differences, and emits
    the heuristic suggestion text iff at least three recipes are shared.

    Raises :class:`KeyError` if either id is unknown.
    """
    entry_a = registry.projects[a_id]
    entry_b = registry.projects[b_id]

    set_a = load_project_recipe_set(entry_a)
    set_b = load_project_recipe_set(entry_b)

    shared = tuple(sorted(set_a & set_b))
    a_only = tuple(sorted(set_a - set_b))
    b_only = tuple(sorted(set_b - set_a))

    suggestion: str | None = None
    if len(shared) >= _SHARED_THRESHOLD:
        suggestion = _SUGGESTION_TEMPLATE.format(n=len(shared))

    return DiffReport(
        project_a_id=a_id,
        project_b_id=b_id,
        a_only=a_only,
        b_only=b_only,
        shared=shared,
        suggestion=suggestion,
    )


# --------------------------------------------------------------------------- #
# Portfolio aggregation                                                       #
# --------------------------------------------------------------------------- #


def aggregate_portfolio(registry: Registry) -> PortfolioSummary:
    """Build the portfolio summary across every entry in the registry.

    Iterates ``registry.projects`` in insertion order, loads each
    manifest, and assembles forward + inverted maps. Projects whose
    path no longer exists are skipped with a :class:`RuntimeWarning`;
    they simply do not appear in the summary.
    """
    project_ids: list[str] = []
    recipes_by_project: dict[str, frozenset[str]] = {}
    recipe_to_projects: dict[str, set[str]] = {}

    for project_id, entry in registry.projects.items():
        if not Path(entry.path).exists():
            warnings.warn(
                f"project path missing for {project_id!r}: {entry.path}; "
                "skipping in portfolio aggregation",
                RuntimeWarning,
                stacklevel=2,
            )
            continue

        recipe_set = load_project_recipe_set(entry)
        project_ids.append(project_id)
        recipes_by_project[project_id] = recipe_set
        for recipe in recipe_set:
            recipe_to_projects.setdefault(recipe, set()).add(project_id)

    inverted: dict[str, frozenset[str]] = {
        recipe: frozenset(pids) for recipe, pids in recipe_to_projects.items()
    }

    return PortfolioSummary(
        n_projects=len(project_ids),
        n_distinct_recipes=len(inverted),
        project_ids=tuple(project_ids),
        recipes_by_project=recipes_by_project,
        recipe_to_projects=inverted,
    )


def top_n_recipes(summary: PortfolioSummary, n: int = 10) -> list[RecipeUsage]:
    """Up to ``n`` recipes sorted by ``(project_count desc, name asc)``."""
    rows: list[RecipeUsage] = [
        RecipeUsage(
            recipe_full_name=recipe,
            project_count=len(pids),
            project_ids=tuple(sorted(pids)),
        )
        for recipe, pids in summary.recipe_to_projects.items()
    ]
    rows.sort(key=lambda r: (-r.project_count, r.recipe_full_name))
    return rows[:n]


# --------------------------------------------------------------------------- #
# Heatmap renderers                                                           #
# --------------------------------------------------------------------------- #


def _truncate(name: str, width: int) -> str:
    """Truncate / pad ``name`` to exactly ``width`` columns."""
    if len(name) <= width:
        return name.ljust(width)
    if width <= 1:
        return name[:width]
    return name[: width - 1] + "…"


def render_heatmap_terminal(
    summary: PortfolioSummary,
    *,
    bullet: str = "•",
    empty: str = "·",
    project_id_width: int = 8,
) -> str:
    """Unicode terminal heatmap (spec §5.3).

    Rows are recipes (use-count desc, alphabetic on ties); columns are
    project IDs in registry insertion order. Recipe names are truncated
    to a sensible width; project columns are padded to
    ``project_id_width``.
    """
    project_ids = summary.project_ids
    if not project_ids:
        return "Portfolio summary — 0 projects, 0 distinct recipes used\n"

    ordered_recipes = sorted(
        summary.recipe_to_projects.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )

    # Recipe-name column width: clamp to [30, 50].
    name_width = max(
        (min(len(r), 50) for r, _ in ordered_recipes),
        default=30,
    )
    name_width = max(30, min(name_width, 50))

    short_ids = [_truncate(pid, project_id_width) for pid in project_ids]

    lines: list[str] = [
        f"Portfolio summary — {summary.n_projects} projects, "
        f"{summary.n_distinct_recipes} distinct recipes used",
        "",
        " " * name_width + "  " + " ".join(short_ids),
    ]

    for recipe, used_in in ordered_recipes:
        cells = [
            (bullet if pid in used_in else empty).center(project_id_width)
            for pid in project_ids
        ]
        lines.append(_truncate(recipe, name_width) + "  " + " ".join(cells))

    return "\n".join(lines) + "\n"


def render_heatmap_png(
    summary: PortfolioSummary,
    output_path: Path,
    *,
    figsize: tuple[float, float] = (8.0, 6.0),
) -> Path:
    """Matplotlib heatmap PNG.

    Rows = recipes (use-count desc, then alphabetic); columns =
    project IDs in registry order. Plain binary cmap. Returns the
    ``output_path`` for caller convenience. Matplotlib is imported
    lazily so the module stays cheap to import.
    """
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    import numpy as np

    project_ids = summary.project_ids
    ordered_recipes = sorted(
        summary.recipe_to_projects.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )

    n_rows = len(ordered_recipes)
    n_cols = len(project_ids)
    grid = np.zeros((max(n_rows, 1), max(n_cols, 1)), dtype=int)
    for r_idx, (_recipe, used_in) in enumerate(ordered_recipes):
        for c_idx, pid in enumerate(project_ids):
            if pid in used_in:
                grid[r_idx, c_idx] = 1

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(grid, aspect="auto", cmap="binary", vmin=0, vmax=1)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(project_ids, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([recipe for recipe, _ in ordered_recipes], fontsize=7)
    ax.set_title(
        f"Recipe Portfolio Heatmap "
        f"({summary.n_projects} projects, "
        f"{summary.n_distinct_recipes} recipes)"
    )
    fig.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
