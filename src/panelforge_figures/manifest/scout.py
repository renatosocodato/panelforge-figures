"""Project walker + figure-plan synthesizer (Elevation 9 — phase 2).

The ``figures scout PROJECT_ROOT`` command walks an entire user project,
inventories everything it finds, profiles every data file via the
:mod:`panelforge_figures.manifest.family_recommender` E8 pipeline, optionally
scores per-panel novelty against the literature via the
:mod:`panelforge_figures.manifest.novelty_scout` E9-phase1 pipeline, and
synthesises a **multi-figure narrative plan** (4-6 figures × 3-4 panels each)
plus a list of **recipe gaps** the user can fill via ``figures fill-gap``.

This module is **read-only**: nothing is rendered, scaffolded, or shipped to
disk other than the YAML serialisation of the proposed plan. The principled
stance is preserved: the human reviews the plan before any execution.

Public surface
--------------
:class:`DataFileEntry` / :class:`ModelEntry` / :class:`NotebookEntry` —
inventory entries; tolerant to missing directories.

:class:`ProjectInventory` — aggregate of everything :func:`walk_project`
discovers (data files, models, notebooks, manuscript, project YAML).

:class:`PanelSlot` / :class:`FigureSlot` / :class:`FigurePlan` — proposed
narrative plan; serialisable via :meth:`FigurePlan.to_dict`.

:class:`ProjectScoutReport` — top-level result returned by
:func:`scout_project`, also serialisable.

:func:`walk_project` — walk and inventory a project root.
:func:`synthesize_figure_plan` — build a 4-figure narrative plan from an
inventory using rule-based grouping (biology / kinetics / molecular /
quantitative).
:func:`scout_project` — end-to-end pipeline (walk → profile → recommend →
plan → novelty).
:func:`render_scout_report_markdown` — render a comprehensive Markdown
report for human review.
:func:`save_figure_plan_yaml` / :func:`load_figure_plan_yaml` — round-trip
the plan via PyYAML safe_load/dump (schema_version 1).
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "DataFileEntry",
    "FigurePlan",
    "FigureSlot",
    "FigureSlotKind",
    "ModelEntry",
    "NotebookEntry",
    "PanelSlot",
    "ProjectInventory",
    "ProjectScoutReport",
    "ScoutError",
    "load_figure_plan_yaml",
    "render_scout_report_markdown",
    "save_figure_plan_yaml",
    "scout_project",
    "synthesize_figure_plan",
    "walk_project",
]


# ──────────────────────────── exceptions ─────────────────────────────────


class ScoutError(RuntimeError):
    """Raised on inventory failures, missing project_root, etc."""


# ───────────────────────────── enums ─────────────────────────────────────


class FigureSlotKind(StrEnum):
    """Coarse narrative slot for a figure in the manuscript outline."""

    biology = "biology"               # what is the system / phenomenology
    kinetics = "kinetics"             # time / dynamics / transitions
    molecular = "molecular"           # omics / pathways
    quantitative = "quantitative"     # equivalence / TOST / Bayesian arrow
    diagnostic = "diagnostic"         # methodology / provenance / sensitivity


# ──────────────────────────── dataclasses ────────────────────────────────


@dataclass(frozen=True)
class DataFileEntry:
    """One data file found under ``data/``.

    ``profile_summary`` is the dict returned by
    :meth:`family_recommender.DataProfile.to_dict` and is filled by
    :func:`scout_project`; :func:`walk_project` leaves it ``None``.
    """

    path: Path
    size_bytes: int
    suffix: str
    profile_summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelEntry:
    """One model file found under ``models/``."""

    path: Path
    kind: str   # "ode" / "hmm" / "markov" / "py_class" / "json_artifact" / "unknown"
    size_bytes: int


@dataclass(frozen=True)
class NotebookEntry:
    """One Jupyter notebook found under ``notebooks/``."""

    path: Path
    size_bytes: int


@dataclass(frozen=True)
class ProjectInventory:
    """Aggregate of everything :func:`walk_project` finds in a project."""

    project_root: Path
    project_yaml_path: Path | None
    project_id: str | None
    modality: str | None
    data_class: str | None             # research / clinical / public
    data_files: tuple[DataFileEntry, ...]
    model_files: tuple[ModelEntry, ...]
    notebooks: tuple[NotebookEntry, ...]
    manuscript_path: Path | None
    has_existing_figures: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PanelSlot:
    """One panel in the proposed plan.

    ``recipe_full_name`` is empty when ``is_gap`` is True; in that case
    ``suggested_recipe_name`` and ``suggested_research_question`` describe
    the recipe the user should scaffold via ``figures fill-gap``.
    """

    panel_id: str                      # e.g. "1A"
    figure_id: str                     # e.g. "Figure 1"
    recipe_full_name: str              # registry recipe full_name; or "" if gap
    research_question: str
    data_file_hint: Path | None = None
    role: str = "primary"              # "primary" / "supporting" / "methodology"
    is_gap: bool = False
    suggested_recipe_name: str | None = None
    suggested_research_question: str | None = None
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "figure_id": self.figure_id,
            "recipe_full_name": self.recipe_full_name,
            "research_question": self.research_question,
            "data_file_hint": str(self.data_file_hint) if self.data_file_hint else None,
            "role": self.role,
            "is_gap": self.is_gap,
            "suggested_recipe_name": self.suggested_recipe_name,
            "suggested_research_question": self.suggested_research_question,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PanelSlot:
        hint = d.get("data_file_hint")
        return cls(
            panel_id=str(d["panel_id"]),
            figure_id=str(d["figure_id"]),
            recipe_full_name=str(d.get("recipe_full_name", "")),
            research_question=str(d.get("research_question", "")),
            data_file_hint=Path(hint) if hint else None,
            role=str(d.get("role", "primary")),
            is_gap=bool(d.get("is_gap", False)),
            suggested_recipe_name=d.get("suggested_recipe_name"),
            suggested_research_question=d.get("suggested_research_question"),
            rationale=str(d.get("rationale", "")),
        )


@dataclass(frozen=True)
class FigureSlot:
    """One figure in the proposed plan; holds 3-4 panels."""

    figure_id: str                     # "Figure 1"
    title: str
    slot_kind: FigureSlotKind
    panels: tuple[PanelSlot, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "title": self.title,
            "slot_kind": self.slot_kind.value,
            "panels": [p.to_dict() for p in self.panels],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FigureSlot:
        return cls(
            figure_id=str(d["figure_id"]),
            title=str(d.get("title", "")),
            slot_kind=FigureSlotKind(d.get("slot_kind", FigureSlotKind.biology.value)),
            panels=tuple(PanelSlot.from_dict(p) for p in d.get("panels", [])),
        )


@dataclass(frozen=True)
class FigurePlan:
    """The proposed multi-figure narrative plan emitted by the scout."""

    project_root: Path
    project_id: str | None
    figures: tuple[FigureSlot, ...]
    venue: str = "cell"
    n_figures: int = 0
    n_panels: int = 0
    n_gaps: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_root": str(self.project_root),
            "project_id": self.project_id,
            "venue": self.venue,
            "n_figures": self.n_figures,
            "n_panels": self.n_panels,
            "n_gaps": self.n_gaps,
            "figures": [f.to_dict() for f in self.figures],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FigurePlan:
        figures = tuple(FigureSlot.from_dict(f) for f in d.get("figures", []))
        n_panels = sum(len(f.panels) for f in figures)
        n_gaps = sum(1 for f in figures for p in f.panels if p.is_gap)
        return cls(
            project_root=Path(d.get("project_root", ".")),
            project_id=d.get("project_id"),
            figures=figures,
            venue=str(d.get("venue", "cell")),
            n_figures=int(d.get("n_figures", len(figures))),
            n_panels=int(d.get("n_panels", n_panels)),
            n_gaps=int(d.get("n_gaps", n_gaps)),
        )


@dataclass(frozen=True)
class ProjectScoutReport:
    """End-to-end scout result; serialisable for the CLI to dump as JSON.

    The ``collision_report`` field (E10) is populated by
    :func:`scout_project` when the inventory contains a manuscript and
    ``manuscript_policy != "preserve"``.  It holds a :class:`CollisionReport`
    (from :mod:`manuscript_collision`) which the rendered markdown surface
    presents as a per-figure status table.  Tolerant: ``None`` indicates
    either no manuscript was present, the collision check was disabled,
    or the collision module wasn't importable yet.
    """

    inventory: ProjectInventory
    figure_plan: FigurePlan
    novelty_report: dict[str, Any] | None
    recommendations_per_data_file: dict[str, list[dict[str, Any]]]
    notes: tuple[str, ...] = ()
    collision_report: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        collision_dict: Any = None
        if self.collision_report is not None:
            to_dict_fn = getattr(self.collision_report, "to_dict", None)
            if callable(to_dict_fn):
                try:
                    collision_dict = to_dict_fn()
                except Exception:  # pragma: no cover — defensive
                    collision_dict = str(self.collision_report)
            else:
                collision_dict = str(self.collision_report)
        return {
            "inventory": _inventory_to_dict(self.inventory),
            "figure_plan": self.figure_plan.to_dict(),
            "novelty_report": self.novelty_report,
            "recommendations_per_data_file": self.recommendations_per_data_file,
            "notes": list(self.notes),
            "collision_report": collision_dict,
        }


def _inventory_to_dict(inv: ProjectInventory) -> dict[str, Any]:
    """JSON-serialise a :class:`ProjectInventory` (small helper)."""
    return {
        "project_root": str(inv.project_root),
        "project_yaml_path": str(inv.project_yaml_path) if inv.project_yaml_path else None,
        "project_id": inv.project_id,
        "modality": inv.modality,
        "data_class": inv.data_class,
        "data_files": [
            {
                "path": str(d.path),
                "size_bytes": d.size_bytes,
                "suffix": d.suffix,
                "profile_summary": d.profile_summary,
            }
            for d in inv.data_files
        ],
        "model_files": [
            {"path": str(m.path), "kind": m.kind, "size_bytes": m.size_bytes}
            for m in inv.model_files
        ],
        "notebooks": [
            {"path": str(n.path), "size_bytes": n.size_bytes} for n in inv.notebooks
        ],
        "manuscript_path": str(inv.manuscript_path) if inv.manuscript_path else None,
        "has_existing_figures": inv.has_existing_figures,
        "notes": list(inv.notes),
    }


# ───────────────────────────── walk_project ──────────────────────────────


_DATA_SUFFIXES: frozenset[str] = frozenset({
    ".csv", ".tsv", ".parquet", ".pq", ".xlsx", ".xls",
    ".json", ".h5", ".h5ad",
})

_MODEL_SUFFIXES: frozenset[str] = frozenset({".py", ".json", ".pkl"})

_MANUSCRIPT_CANDIDATES: tuple[str, ...] = (
    "manuscript.tex",
    "manuscript.md",
    "main.tex",
    "paper.md",
    "README.md",
)

_PROJECT_YAML_CANDIDATES: tuple[str, ...] = (
    "panelforge.project.yaml",
    "panelforge.project.yml",
)


def _classify_model_file(path: Path) -> str:
    """Categorise a model file from filename hints."""
    name = path.name.lower()
    if "hmm" in name:
        return "hmm"
    if "markov" in name:
        return "markov"
    if "ode" in name:
        return "ode"
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "py_class"
    if suffix == ".json":
        return "json_artifact"
    if suffix == ".pkl":
        return "json_artifact"  # opaque blob — group with json_artifact
    return "unknown"


def _list_dir_files(directory: Path, suffixes: frozenset[str]) -> list[Path]:
    """Recursively collect files in ``directory`` whose suffix is in ``suffixes``.

    Hidden files (leading ``.``) are skipped. Missing directories return ``[]``.
    """
    if not directory.is_dir():
        return []
    out: list[Path] = []
    try:
        for p in sorted(directory.rglob("*")):
            if not p.is_file():
                continue
            if p.name.startswith("."):
                continue
            if p.suffix.lower() in suffixes:
                out.append(p)
    except OSError:
        return []
    return out


def _safe_size(path: Path) -> int:
    """Best-effort file-size lookup; returns 0 on any OSError."""
    try:
        return int(path.stat().st_size)
    except OSError:
        return 0


def _read_project_yaml(path: Path) -> dict[str, Any]:
    """Read a project YAML; tolerant to PyYAML missing/parse errors."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text:
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except ImportError:
        warnings.warn(
            "PyYAML not installed — project YAML metadata will not be read",
            RuntimeWarning,
            stacklevel=2,
        )
    except Exception as exc:  # pragma: no cover — defensive fallback
        warnings.warn(
            f"failed to parse {path}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
    return {}


def walk_project(project_root: Path) -> ProjectInventory:
    """Walk a project tree and inventory everything relevant.

    Tolerant: missing subdirectories produce empty tuples + an explanatory
    note; the only hard failure is a non-existent ``project_root``.
    """
    root = Path(project_root).expanduser()
    if not root.exists():
        raise ScoutError(f"project_root not found: {root}")
    if not root.is_dir():
        raise ScoutError(f"project_root is not a directory: {root}")

    notes: list[str] = []

    # ── project YAML ───────────────────────────────────────────────────
    project_yaml_path: Path | None = None
    project_id: str | None = None
    modality: str | None = None
    data_class: str | None = None
    for cand in _PROJECT_YAML_CANDIDATES:
        p = root / cand
        if p.is_file():
            project_yaml_path = p
            cfg = _read_project_yaml(p)
            project_id = (
                str(cfg["project_id"])
                if cfg.get("project_id") is not None
                else None
            )
            modality = (
                str(cfg["modality"])
                if cfg.get("modality") is not None
                else None
            )
            data_class = (
                str(cfg["data_class"])
                if cfg.get("data_class") is not None
                else None
            )
            break
    if project_yaml_path is None:
        notes.append("no panelforge.project.yaml found at project root")

    # ── data/ inventory ────────────────────────────────────────────────
    data_dir = root / "data"
    data_paths = _list_dir_files(data_dir, _DATA_SUFFIXES)
    if not data_dir.is_dir():
        notes.append("data/ directory missing")
    elif not data_paths:
        notes.append("data/ directory present but no recognised data files")
    data_files = tuple(
        DataFileEntry(
            path=p,
            size_bytes=_safe_size(p),
            suffix=p.suffix.lower(),
            profile_summary=None,
        )
        for p in data_paths
    )

    # ── models/ inventory ──────────────────────────────────────────────
    models_dir = root / "models"
    model_paths = _list_dir_files(models_dir, _MODEL_SUFFIXES)
    if not models_dir.is_dir():
        notes.append("models/ directory missing")
    model_files = tuple(
        ModelEntry(
            path=p,
            kind=_classify_model_file(p),
            size_bytes=_safe_size(p),
        )
        for p in model_paths
    )

    # ── notebooks/ inventory ───────────────────────────────────────────
    notebooks_dir = root / "notebooks"
    notebook_paths = _list_dir_files(notebooks_dir, frozenset({".ipynb"}))
    if not notebooks_dir.is_dir():
        notes.append("notebooks/ directory missing")
    notebooks = tuple(
        NotebookEntry(path=p, size_bytes=_safe_size(p)) for p in notebook_paths
    )

    # ── manuscript ─────────────────────────────────────────────────────
    manuscript_path: Path | None = None
    for cand in _MANUSCRIPT_CANDIDATES:
        p = root / cand
        if p.is_file():
            manuscript_path = p
            break
    if manuscript_path is None:
        notes.append("no manuscript file found (will need scaffolding)")

    # ── existing figures ───────────────────────────────────────────────
    workspace_figures = root / "panelforge_workspace" / "figures"
    has_existing_figures = False
    if workspace_figures.is_dir():
        try:
            has_existing_figures = any(
                p.is_file() and not p.name.startswith(".")
                for p in workspace_figures.rglob("*")
            )
        except OSError:
            has_existing_figures = False

    return ProjectInventory(
        project_root=root,
        project_yaml_path=project_yaml_path,
        project_id=project_id,
        modality=modality,
        data_class=data_class,
        data_files=data_files,
        model_files=model_files,
        notebooks=notebooks,
        manuscript_path=manuscript_path,
        has_existing_figures=has_existing_figures,
        notes=tuple(notes),
    )


# ──────────────────────── plan synthesis (rules) ─────────────────────────


# Preferred recipe full_names per slot — checked in order against the live
# registry; first match wins. These are reasonable starting points; any miss
# falls through to a recipe-gap entry.
_PREFERRED_PROVENANCE_RECIPES: tuple[str, ...] = (
    "meta_and_diagnostic.panel_provenance_ledger_table",
    "meta_and_diagnostic.per_cell_audit_table_with_qa_flags",
    "meta_and_diagnostic.alternative_hypothesis_exclusion_table",
)
_PREFERRED_EQUIVALENCE_RECIPES: tuple[str, ...] = (
    "biophysics_scaling.equivalence_forest_with_tost_bounds",
    "biophysics_scaling.scaling_exponent_ci_forest",
    "biophysics_scaling.dual_scale_significance_lollipop",
)
_PREFERRED_BAYES_ARROW_RECIPES: tuple[str, ...] = (
    "meta_and_diagnostic.bayes_factor_arrow_plot",
    "meta_and_diagnostic.heterogeneity_forest",
)
_PREFERRED_TIMECOURSE_RECIPES: tuple[str, ...] = (
    "biophysics_scaling.compartment_split_curvature_crosscorr",
    "biophysics_scaling.confinement_free_energy_vs_width_curve",
    "network_and_pathway.pathway_flux_streamgraph",
)
_PREFERRED_STATE_MACHINE_RECIPES: tuple[str, ...] = (
    "rhogtpase_dynamics.bifurcation_hopf",
    "rhogtpase_dynamics.basin_of_attraction_map",
)
_PREFERRED_DWELL_RECIPES: tuple[str, ...] = (
    "rhogtpase_dynamics.poincare_first_return_map",
    "rhogtpase_dynamics.timescale_separation_diagnostic",
)
_PREFERRED_VOLCANO_RECIPES: tuple[str, ...] = (
    "omics_differential.multi_contrast_volcano_grid",
    "omics_differential.volcano_labeled_repelled",
    "omics_differential.module_concordance_signed_heatmap",
)
_PREFERRED_PATHWAY_RECIPES: tuple[str, ...] = (
    "network_and_pathway.module_eigengene_heatmap",
    "omics_differential.ora_dotplot_by_ontology",
    "network_and_pathway.regulon_activity_heatmap",
)
_PREFERRED_HEATMAP_RECIPES: tuple[str, ...] = (
    "omics_differential.annotated_cluster_heatmap",
    "network_and_pathway.regulon_activity_heatmap",
)
_PREFERRED_FACTORIAL_RECIPES: tuple[str, ...] = (
    "biophysics_scaling.width_alignment_buffered_unbuffered_interaction",
    "biophysics_scaling.quartile_stacked_bar_by_factor",
)


# Substring keywords that mark a recipe (or panel) as supporting / methodology.
_SUPPORTING_KEYWORDS: tuple[str, ...] = (
    "control", "baseline", "calibration", "qc", "diagnostic",
    "provenance", "audit",
)


def _registry_full_names() -> set[str]:
    """Return the set of all registered recipe full_names; tolerant on failure."""
    try:
        from ..core.contract import ensure_all_imported, list_recipes
    except Exception:  # pragma: no cover — circular-import safety
        return set()
    try:
        ensure_all_imported()
    except Exception:  # pragma: no cover — missing optional modality
        pass
    try:
        return {entry.full_name for entry in list_recipes()}
    except Exception:  # pragma: no cover — defensive
        return set()


def _first_available(
    candidates: tuple[str, ...], registry: set[str]
) -> str | None:
    """Return the first recipe in ``candidates`` registered in ``registry``."""
    for c in candidates:
        if c in registry:
            return c
    return None


def _classify_role(recipe_full_name: str) -> str:
    """Assign a panel role from the recipe's full_name modality + keywords."""
    if not recipe_full_name:
        return "primary"
    modality_part = recipe_full_name.split(".", 1)[0].lower()
    if modality_part == "meta_and_diagnostic":
        return "methodology"
    name_l = recipe_full_name.lower()
    if any(kw in name_l for kw in _SUPPORTING_KEYWORDS):
        return "supporting"
    return "primary"


def _largest_data_file(inventory: ProjectInventory) -> Path | None:
    """Return the path of the largest data file, or None if none exist."""
    if not inventory.data_files:
        return None
    return max(inventory.data_files, key=lambda d: d.size_bytes).path


def _data_file_with_filename_keyword(
    inventory: ProjectInventory, keywords: tuple[str, ...]
) -> Path | None:
    """First data file whose name contains any of ``keywords`` (lower-case)."""
    for d in inventory.data_files:
        name_l = d.path.name.lower()
        if any(kw in name_l for kw in keywords):
            return d.path
    return None


def _data_file_with_profile_predicate(
    inventory: ProjectInventory, predicate: Any
) -> Path | None:
    """First data file whose profile_summary satisfies ``predicate``."""
    for d in inventory.data_files:
        if d.profile_summary is None:
            continue
        try:
            if predicate(d.profile_summary):
                return d.path
        except Exception:  # pragma: no cover — defensive
            continue
    return None


def _build_panel(
    *,
    panel_id: str,
    figure_id: str,
    preferred: tuple[str, ...],
    research_question: str,
    rationale: str,
    registry: set[str],
    data_file_hint: Path | None,
    suggested_gap_name: str,
    role_hint: str | None = None,
) -> PanelSlot:
    """Build a panel slot, resolving to a registered recipe or a recipe gap."""
    match = _first_available(preferred, registry)
    if match is not None:
        role = role_hint or _classify_role(match)
        return PanelSlot(
            panel_id=panel_id,
            figure_id=figure_id,
            recipe_full_name=match,
            research_question=research_question,
            data_file_hint=data_file_hint,
            role=role,
            is_gap=False,
            rationale=rationale,
        )
    # gap branch
    return PanelSlot(
        panel_id=panel_id,
        figure_id=figure_id,
        recipe_full_name="",
        research_question=research_question,
        data_file_hint=data_file_hint,
        role=role_hint or "primary",
        is_gap=True,
        suggested_recipe_name=suggested_gap_name,
        suggested_research_question=research_question,
        rationale=rationale + " (recipe gap — scaffold via figures fill-gap)",
    )


def _figure_1_biology(
    inventory: ProjectInventory, registry: set[str]
) -> FigureSlot | None:
    """Rule 1: phenomenological biology figure (always attempted)."""
    if not inventory.data_files:
        return None
    largest = _largest_data_file(inventory)
    second = inventory.data_files[1].path if len(inventory.data_files) >= 2 else largest
    detected_2x2 = any(
        (d.profile_summary or {}).get("detected_2x2") for d in inventory.data_files
    )
    panels: list[PanelSlot] = []

    panels.append(
        _build_panel(
            panel_id="1A",
            figure_id="Figure 1",
            preferred=(
                "biophysics_scaling.compartment_paired_delta_scatter",
                "biophysics_scaling.dual_scale_significance_lollipop",
                "actin_microtubule_morphometry.actin_mt_ratio_spatial_map",
            ),
            research_question="What is the central phenomenology of the system?",
            rationale="largest data file drives a primary descriptive panel",
            registry=registry,
            data_file_hint=largest,
            suggested_gap_name="comparison_descriptive_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="1B",
            figure_id="Figure 1",
            preferred=(
                "biophysics_scaling.confinement_ratio_distribution_by_genotype",
                "biophysics_scaling.persistence_length_lp_with_equivalence_bounds",
            ),
            research_question=(
                "How does the response distribute across the principal grouping factor?"
            ),
            rationale="paired data file → distribution-by-group panel",
            registry=registry,
            data_file_hint=second,
            suggested_gap_name="comparison_distribution_v1",
        )
    )
    if detected_2x2:
        panels.append(
            _build_panel(
                panel_id="1C",
                figure_id="Figure 1",
                preferred=_PREFERRED_FACTORIAL_RECIPES,
                research_question=(
                    "Is there an interaction between the two principal factors?"
                ),
                rationale="2×2 factorial detected in data profile",
                registry=registry,
                data_file_hint=largest,
                suggested_gap_name="factorial_2x2_v1",
            )
        )
    panels.append(
        _build_panel(
            panel_id=f"1{'D' if detected_2x2 else 'C'}",
            figure_id="Figure 1",
            preferred=_PREFERRED_PROVENANCE_RECIPES,
            research_question=(
                "What provenance, units, and quality flags accompany every panel?"
            ),
            rationale="every figure carries a provenance ledger as methodology",
            registry=registry,
            data_file_hint=None,
            suggested_gap_name="provenance_ledger_v1",
            role_hint="methodology",
        )
    )
    if len(panels) < 3:
        return None
    return FigureSlot(
        figure_id="Figure 1",
        title="System phenomenology and provenance",
        slot_kind=FigureSlotKind.biology,
        panels=tuple(panels[:4]),
    )


def _figure_2_kinetics(
    inventory: ProjectInventory, registry: set[str]
) -> FigureSlot | None:
    """Rule 2: kinetics / dynamics figure, if any time / paired / HMM evidence."""
    has_paired = any(
        (d.profile_summary or {}).get("has_paired_id") for d in inventory.data_files
    )
    has_time = any(
        (d.profile_summary or {}).get("has_time_column") for d in inventory.data_files
    )
    has_hmm = any(m.kind in ("hmm", "markov") for m in inventory.model_files)
    has_ode = any(m.kind == "ode" for m in inventory.model_files)
    if not (has_paired or has_time or has_hmm or has_ode):
        return None

    time_data = (
        _data_file_with_profile_predicate(
            inventory, lambda s: s.get("has_time_column", False)
        )
        or _data_file_with_filename_keyword(
            inventory, ("time", "kinetics", "trace", "kymo")
        )
        or _largest_data_file(inventory)
    )
    panels: list[PanelSlot] = []
    panels.append(
        _build_panel(
            panel_id="2A",
            figure_id="Figure 2",
            preferred=_PREFERRED_TIMECOURSE_RECIPES,
            research_question=(
                "How does the response evolve over time across conditions?"
            ),
            rationale=(
                "time column or repeated measures detected → timecourse panel"
            ),
            registry=registry,
            data_file_hint=time_data,
            suggested_gap_name="timecourse_hierarchical_ci_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="2B",
            figure_id="Figure 2",
            preferred=_PREFERRED_STATE_MACHINE_RECIPES,
            research_question=(
                "What discrete states does the system occupy, and how does it "
                "transition between them?"
            ),
            rationale=(
                "HMM/Markov model artifact present → state-machine panel"
                if has_hmm
                else "dynamical model present → state-machine panel"
            ),
            registry=registry,
            data_file_hint=time_data,
            suggested_gap_name="state_machine_transition_bootstrapped_heatmap_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="2C",
            figure_id="Figure 2",
            preferred=_PREFERRED_DWELL_RECIPES,
            research_question=(
                "What are the lifetimes / dwell times in each state?"
            ),
            rationale="dwell-time / lifetime characterisation of state dynamics",
            registry=registry,
            data_file_hint=time_data,
            suggested_gap_name="state_machine_dwell_time_v1",
        )
    )
    if len(panels) < 3:
        return None
    return FigureSlot(
        figure_id="Figure 2",
        title="Kinetics and state dynamics",
        slot_kind=FigureSlotKind.kinetics,
        panels=tuple(panels[:4]),
    )


_OMICS_KEYWORDS: tuple[str, ...] = (
    "abundance", "dge", "expression", "proteome", "transcripts",
    "phospho", "rnaseq", "scrna",
)


def _figure_3_molecular(
    inventory: ProjectInventory, registry: set[str]
) -> FigureSlot | None:
    """Rule 3: molecular pathway figure, if any data file is high-dim / omics."""
    omics_path = _data_file_with_filename_keyword(inventory, _OMICS_KEYWORDS)
    high_dim_path = _data_file_with_profile_predicate(
        inventory, lambda s: int(s.get("n_cols", 0)) > 30
    )
    primary = omics_path or high_dim_path
    if primary is None:
        return None

    huge_dim_path = _data_file_with_profile_predicate(
        inventory, lambda s: int(s.get("n_cols", 0)) > 60
    )
    panels: list[PanelSlot] = []
    panels.append(
        _build_panel(
            panel_id="3A",
            figure_id="Figure 3",
            preferred=_PREFERRED_VOLCANO_RECIPES,
            research_question=(
                "Which features show the largest and most reliable differences "
                "between conditions?"
            ),
            rationale="omics-shaped data → volcano / module-concordance panel",
            registry=registry,
            data_file_hint=primary,
            suggested_gap_name="volcano_multi_contrast_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="3B",
            figure_id="Figure 3",
            preferred=_PREFERRED_PATHWAY_RECIPES,
            research_question=(
                "Which pathways or modules are enriched among the differential "
                "features?"
            ),
            rationale="omics-shaped data → enrichment / pathway panel",
            registry=registry,
            data_file_hint=primary,
            suggested_gap_name="pathway_enrichment_v1",
        )
    )
    if huge_dim_path is not None:
        panels.append(
            _build_panel(
                panel_id="3C",
                figure_id="Figure 3",
                preferred=_PREFERRED_HEATMAP_RECIPES,
                research_question=(
                    "How are the top differential features structured across "
                    "samples?"
                ),
                rationale=">60 columns → annotated cluster heatmap",
                registry=registry,
                data_file_hint=huge_dim_path,
                suggested_gap_name="annotated_cluster_heatmap_v1",
            )
        )
    if len(panels) < 3:
        # Backfill with a methodology panel if we only have 2 primary panels.
        panels.append(
            _build_panel(
                panel_id="3C",
                figure_id="Figure 3",
                preferred=_PREFERRED_PROVENANCE_RECIPES,
                research_question=(
                    "What QC and provenance flags accompany the molecular panels?"
                ),
                rationale="methodology backfill for molecular figure",
                registry=registry,
                data_file_hint=None,
                suggested_gap_name="provenance_ledger_v1",
                role_hint="methodology",
            )
        )
    if len(panels) < 3:
        return None
    return FigureSlot(
        figure_id="Figure 3",
        title="Molecular pathway architecture",
        slot_kind=FigureSlotKind.molecular,
        panels=tuple(panels[:4]),
    )


def _figure_4_quantitative(
    inventory: ProjectInventory, registry: set[str]
) -> FigureSlot | None:
    """Rule 4: equivalence / TOST / Bayesian arrow figure (always attempted)."""
    if not inventory.data_files:
        return None
    primary = _largest_data_file(inventory)
    panels: list[PanelSlot] = []

    panels.append(
        _build_panel(
            panel_id="4A",
            figure_id="Figure 4",
            preferred=_PREFERRED_EQUIVALENCE_RECIPES,
            research_question=(
                "Are condition means practically equivalent within a "
                "pre-registered margin?"
            ),
            rationale="every paper needs an equivalence / TOST anchor",
            registry=registry,
            data_file_hint=primary,
            suggested_gap_name="equivalence_forest_with_tost_bounds_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="4B",
            figure_id="Figure 4",
            preferred=(
                "biophysics_scaling.log_log_scaling_with_slope_box",
                "biophysics_scaling.scaling_exponent_ci_forest",
                "biophysics_scaling.master_curve_collapse",
                "dose_response_pharmacology.crossover_scaling_diagnostic",
            ),
            research_question=(
                "Does a single scaling exponent / dose-response fit the data?"
            ),
            rationale="quantitative scaling-law / dose-response anchor",
            registry=registry,
            data_file_hint=primary,
            suggested_gap_name="scaling_law_v1",
        )
    )
    panels.append(
        _build_panel(
            panel_id="4C",
            figure_id="Figure 4",
            preferred=_PREFERRED_BAYES_ARROW_RECIPES,
            research_question=(
                "What is the Bayesian effect-size arrow across competing "
                "hypotheses?"
            ),
            rationale="Bayes-factor arrow communicates direction + uncertainty",
            registry=registry,
            data_file_hint=primary,
            suggested_gap_name="bayes_factor_arrow_v1",
            role_hint="methodology",
        )
    )
    if len(panels) < 3:
        return None
    return FigureSlot(
        figure_id="Figure 4",
        title="Quantitative validation and equivalence",
        slot_kind=FigureSlotKind.quantitative,
        panels=tuple(panels[:4]),
    )


def synthesize_figure_plan(
    inventory: ProjectInventory,
    *,
    max_figures: int = 4,
    venue: str = "cell",
) -> FigurePlan:
    """Build a multi-figure narrative plan from a :class:`ProjectInventory`.

    Applies four narrative rules in order (biology → kinetics → molecular →
    quantitative); each fires only when its triggers are present in the
    inventory. Each figure must have at least 3 candidate panels or it is
    skipped (no padding). The total figure count is capped at ``max_figures``.
    """
    registry = _registry_full_names()
    figures: list[FigureSlot] = []

    rule_results = [
        _figure_1_biology(inventory, registry),
        _figure_2_kinetics(inventory, registry),
        _figure_3_molecular(inventory, registry),
        _figure_4_quantitative(inventory, registry),
    ]
    for fig in rule_results:
        if fig is None:
            continue
        figures.append(fig)
        if len(figures) >= max_figures:
            break

    n_panels = sum(len(f.panels) for f in figures)
    n_gaps = sum(1 for f in figures for p in f.panels if p.is_gap)
    return FigurePlan(
        project_root=inventory.project_root,
        project_id=inventory.project_id,
        figures=tuple(figures),
        venue=venue,
        n_figures=len(figures),
        n_panels=n_panels,
        n_gaps=n_gaps,
    )


# ───────────────────────── end-to-end pipeline ───────────────────────────


def _resolve_consensus_client(
    consensus_client: Any | None,
    use_mock_novelty: bool,
) -> Any:
    """Resolve the Consensus client to use; warn if falling back to mock."""
    # Lazy import — keeps novelty_scout off the hot import path.
    from .novelty_scout import (
        ConsensusProClient,
        ConsensusUnavailableError,
        MockConsensusClient,
    )

    if consensus_client is not None:
        return consensus_client
    if use_mock_novelty:
        return MockConsensusClient()
    import os
    if os.environ.get("CONSENSUS_API_KEY"):
        try:
            return ConsensusProClient()
        except ConsensusUnavailableError as exc:
            warnings.warn(
                f"ConsensusProClient unavailable ({exc}); using MockConsensusClient",
                RuntimeWarning,
                stacklevel=2,
            )
            return MockConsensusClient()
    warnings.warn(
        "CONSENSUS_API_KEY not set; using MockConsensusClient (novelty scores "
        "will be permissive)",
        RuntimeWarning,
        stacklevel=2,
    )
    return MockConsensusClient()


def _profile_data_files_in_place(
    data_files: tuple[DataFileEntry, ...],
) -> tuple[DataFileEntry, ...]:
    """Profile every data file via E8; tolerant on per-file failures."""
    try:
        from .family_recommender import RecommenderError, profile_data
    except Exception:  # pragma: no cover — defensive
        return data_files
    out: list[DataFileEntry] = []
    for entry in data_files:
        summary: dict[str, Any] | None = None
        try:
            profile = profile_data(entry.path)
            summary = profile.to_dict()
        except RecommenderError as exc:
            warnings.warn(
                f"failed to profile {entry.path}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        except Exception as exc:  # pragma: no cover — defensive
            warnings.warn(
                f"unexpected profile error for {entry.path}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        out.append(
            DataFileEntry(
                path=entry.path,
                size_bytes=entry.size_bytes,
                suffix=entry.suffix,
                profile_summary=summary,
            )
        )
    return tuple(out)


def _recommend_per_data_file(
    data_files: tuple[DataFileEntry, ...],
) -> dict[str, list[dict[str, Any]]]:
    """Run E8 :func:`recommend_families` over every profiled data file."""
    try:
        from .family_recommender import (
            DataKind,
            DataProfile,
            GroupingStructure,
            recommend_families,
        )
    except Exception:  # pragma: no cover — defensive
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for entry in data_files:
        if entry.profile_summary is None:
            continue
        # Re-hydrate a DataProfile from its dict form (E8 to_dict is the
        # canonical projection; we reverse it here).
        try:
            kinds = {
                k: DataKind(v) for k, v in entry.profile_summary["column_kinds"].items()
            }
            profile = DataProfile(
                n_rows=int(entry.profile_summary["n_rows"]),
                n_cols=int(entry.profile_summary["n_cols"]),
                column_kinds=kinds,
                n_numeric=int(entry.profile_summary["n_numeric"]),
                n_categorical=int(entry.profile_summary["n_categorical"]),
                n_binary=int(entry.profile_summary["n_binary"]),
                n_missing_total=int(entry.profile_summary["n_missing_total"]),
                fraction_missing=float(entry.profile_summary["fraction_missing"]),
                grouping_structure=GroupingStructure(
                    entry.profile_summary["grouping_structure"]
                ),
                n_groups=int(entry.profile_summary["n_groups"]),
                n_per_group=dict(entry.profile_summary.get("n_per_group", {})),
                has_paired_id=bool(entry.profile_summary["has_paired_id"]),
                has_time_column=bool(entry.profile_summary["has_time_column"]),
                candidate_factor_columns=tuple(
                    entry.profile_summary.get("candidate_factor_columns", [])
                ),
                candidate_response_columns=tuple(
                    entry.profile_summary.get("candidate_response_columns", [])
                ),
                detected_2x2=bool(entry.profile_summary["detected_2x2"]),
                notes=tuple(entry.profile_summary.get("notes", [])),
            )
        except Exception:  # pragma: no cover — defensive
            continue
        try:
            recs = recommend_families(profile, top_k=3)
            out[str(entry.path)] = [
                {
                    "family": r.family,
                    "confidence": r.confidence,
                    "rationale": r.rationale,
                    "n_matching_recipes": r.n_matching_recipes,
                }
                for r in recs
            ]
        except Exception:  # pragma: no cover — defensive
            continue
    return out


def _plan_to_panel_candidates(
    plan: FigurePlan, *, modality: str | None
) -> list[Any]:
    """Build novelty-scout :class:`PanelCandidate` inputs from the plan."""
    from .novelty_scout import PanelCandidate, PanelRole

    role_map = {
        "primary": PanelRole.primary,
        "supporting": PanelRole.supporting,
        "methodology": PanelRole.methodology,
    }
    out: list[Any] = []
    for fig in plan.figures:
        for p in fig.panels:
            # Skip gaps — novelty scoring needs a recipe full_name; gaps can
            # be re-scored after the user fills them.
            if p.is_gap or not p.recipe_full_name:
                continue
            out.append(
                PanelCandidate(
                    panel_id=f"panel-{p.panel_id}",
                    recipe_full_name=p.recipe_full_name,
                    research_question=p.research_question,
                    role=role_map.get(p.role, PanelRole.auto),
                    figure_id=p.figure_id,
                    modality=modality,
                )
            )
    return out


def scout_project(
    project_root: Path,
    *,
    max_figures: int = 4,
    venue: str = "cell",
    target_novelty: str = "maximal",
    consensus_client: Any | None = None,
    use_mock_novelty: bool = False,
    manuscript_policy: str = "detect",
) -> ProjectScoutReport:
    """End-to-end project scout (read-only, no execution).

    Pipeline
    --------
    1. :func:`walk_project` → :class:`ProjectInventory`.
    2. Profile every data file via E8 :func:`profile_data` (lazy import) →
       fill ``DataFileEntry.profile_summary``.
    3. Recommend families per data file (E8) →
       ``recommendations_per_data_file``.
    4. :func:`synthesize_figure_plan` → :class:`FigurePlan`.
    5. If ``target_novelty != "none"``: build a :class:`PanelCandidate`
       list from the plan, score it via :func:`score_figure_plan` (E9-phase
       1) → ``novelty_report.to_dict()``. Otherwise ``novelty_report`` is
       ``None``.
    6. If ``inventory.manuscript_path`` is set and
       ``manuscript_policy != "preserve"``: parse the manuscript and detect
       collisions against the proposed plan; attach the resulting
       :class:`CollisionReport` to the result.  The check is tolerant —
       any failure becomes a soft warning, not a hard error.
    7. Emit :class:`ProjectScoutReport`.

    Consensus-client routing
    ------------------------
    * Explicit ``consensus_client`` → use it.
    * ``use_mock_novelty`` True → :class:`MockConsensusClient`.
    * ``CONSENSUS_API_KEY`` env var set → :class:`ConsensusProClient`.
    * Otherwise → :class:`MockConsensusClient` (with a ``RuntimeWarning``).

    ``manuscript_policy`` options
    -----------------------------
    * ``"detect"``  → parse manuscript + emit collision report (default).
    * ``"update"``  → same as detect (mutation happens in execute_plan).
    * ``"propose"`` → same as detect (mutation happens in execute_plan).
    * ``"preserve"`` → skip the collision check entirely.
    """
    inventory = walk_project(project_root)

    # ── profile data files (lazy-loads pandas) ─────────────────────────
    profiled_data = _profile_data_files_in_place(inventory.data_files)
    inventory_profiled = ProjectInventory(
        project_root=inventory.project_root,
        project_yaml_path=inventory.project_yaml_path,
        project_id=inventory.project_id,
        modality=inventory.modality,
        data_class=inventory.data_class,
        data_files=profiled_data,
        model_files=inventory.model_files,
        notebooks=inventory.notebooks,
        manuscript_path=inventory.manuscript_path,
        has_existing_figures=inventory.has_existing_figures,
        notes=inventory.notes,
    )

    recommendations = _recommend_per_data_file(profiled_data)
    plan = synthesize_figure_plan(
        inventory_profiled, max_figures=max_figures, venue=venue
    )

    novelty_dict: dict[str, Any] | None = None
    notes: list[str] = []
    if target_novelty != "none":
        try:
            from .novelty_scout import TargetNovelty, score_figure_plan
        except Exception as exc:  # pragma: no cover — defensive
            warnings.warn(
                f"novelty_scout unavailable: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            try:
                target = TargetNovelty(target_novelty)
            except ValueError:
                warnings.warn(
                    f"unknown target_novelty {target_novelty!r}; defaulting to maximal",
                    RuntimeWarning,
                    stacklevel=2,
                )
                target = TargetNovelty.maximal
            client = _resolve_consensus_client(consensus_client, use_mock_novelty)
            candidates = _plan_to_panel_candidates(plan, modality=inventory.modality)
            if not candidates:
                notes.append(
                    "no recipe-bearing panels in plan; novelty scoring skipped"
                )
            else:
                try:
                    report = score_figure_plan(candidates, client, target=target)
                    novelty_dict = report.to_dict()
                except Exception as exc:  # pragma: no cover — defensive
                    warnings.warn(
                        f"novelty scoring failed: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
    else:
        notes.append("novelty scoring disabled (target_novelty='none')")

    # ── E10: manuscript collision detection ───────────────────────────
    collision_report: Any | None = None
    if (
        inventory_profiled.manuscript_path is not None
        and manuscript_policy != "preserve"
    ):
        try:
            from .manuscript_collision import detect_collision
            from .manuscript_parse import parse_manuscript
        except ImportError as exc:
            warnings.warn(
                f"manuscript collision modules unavailable: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            notes.append(
                "manuscript present but collision module not importable yet"
            )
        else:
            try:
                existing = parse_manuscript(inventory_profiled.manuscript_path)
                collision_report = detect_collision(existing, plan)
            except Exception as exc:
                warnings.warn(
                    f"manuscript collision check failed: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                notes.append(f"manuscript collision check failed: {exc}")
    elif (
        inventory_profiled.manuscript_path is not None
        and manuscript_policy == "preserve"
    ):
        notes.append(
            "manuscript collision check skipped (policy=preserve)"
        )

    return ProjectScoutReport(
        inventory=inventory_profiled,
        figure_plan=plan,
        novelty_report=novelty_dict,
        recommendations_per_data_file=recommendations,
        notes=tuple(notes),
        collision_report=collision_report,
    )


# ─────────────────────────── markdown rendering ──────────────────────────


def _format_size(size_bytes: int) -> str:
    """Pretty-print a byte count: ``1.2 MB``, ``842 KB``, ``243 B``."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _model_kind_summary(models: tuple[ModelEntry, ...]) -> str:
    """Compact summary like ``2 ODE, 1 HMM, 1 Markov``."""
    counts: dict[str, int] = {}
    for m in models:
        counts[m.kind] = counts.get(m.kind, 0) + 1
    if not counts:
        return ""
    parts = [f"{n} {k.upper() if len(k) <= 5 else k.title()}" for k, n in counts.items()]
    return ", ".join(parts)


def render_scout_report_markdown(report: ProjectScoutReport) -> str:
    """Render a comprehensive Markdown summary of the scout result."""
    inv = report.inventory
    plan = report.figure_plan
    lines: list[str] = []

    lines.append("# Project Scout Report")
    lines.append("")
    pid = inv.project_id or inv.project_root.name
    header = f"**Project**: {pid}"
    if inv.modality:
        header += f"  ·  modality: {inv.modality}"
    if inv.data_class:
        header += f"  ·  data_class: {inv.data_class}"
    lines.append(header)
    lines.append("")

    # ── inventory ──────────────────────────────────────────────────────
    lines.append("## Inventory")
    total_data_bytes = sum(d.size_bytes for d in inv.data_files)
    lines.append(
        f"- {len(inv.data_files)} data files ({_format_size(total_data_bytes)})"
    )
    model_summary = _model_kind_summary(inv.model_files)
    if model_summary:
        lines.append(f"- {len(inv.model_files)} model files ({model_summary})")
    else:
        lines.append(f"- {len(inv.model_files)} model files")
    lines.append(f"- {len(inv.notebooks)} notebooks")
    if inv.manuscript_path:
        lines.append(f"- manuscript: `{inv.manuscript_path.name}`")
    else:
        lines.append("- manuscript: NOT FOUND — will need scaffolding")
    lines.append(
        f"- existing figures: {'present' if inv.has_existing_figures else '0'}"
    )
    lines.append("")

    # ── per-data-file recommendations ─────────────────────────────────
    if report.recommendations_per_data_file:
        lines.append("## Per-data-file recommendations (top-3 families each)")
        lines.append("")
        lines.append("| Data file | shape | top families |")
        lines.append("|-----------|-------|--------------|")
        for d in inv.data_files:
            recs = report.recommendations_per_data_file.get(str(d.path), [])
            shape = "?"
            if d.profile_summary is not None:
                shape = (
                    f"{d.profile_summary.get('n_rows', '?')}×"
                    f"{d.profile_summary.get('n_cols', '?')}"
                )
            top = (
                ", ".join(
                    f"{r['family']} ({r['confidence']:.2f})" for r in recs[:3]
                )
                or "(none)"
            )
            lines.append(f"| `{d.path.name}` | {shape} | {top} |")
        lines.append("")

    # ── figure plan ────────────────────────────────────────────────────
    lines.append(
        f"## Proposed {plan.n_figures}-figure narrative plan "
        f"({plan.n_panels} panels, {plan.n_gaps} gaps; venue={plan.venue})"
    )
    lines.append("")
    for fig in plan.figures:
        lines.append(f"### {fig.figure_id} — {fig.title}  [{fig.slot_kind.value}]")
        for panel in fig.panels:
            if panel.is_gap:
                line = (
                    f"- Panel {panel.panel_id} — RECIPE GAP — "
                    f"suggested: `{panel.suggested_recipe_name}` — {panel.role}"
                )
            else:
                line = (
                    f"- Panel {panel.panel_id} — `{panel.recipe_full_name}` — "
                    f"{panel.role} — matched"
                )
            lines.append(line)
            if panel.research_question:
                lines.append(f"    - Q: {panel.research_question}")
            if panel.rationale:
                lines.append(f"    - rationale: {panel.rationale}")
        lines.append("")

    # ── novelty assessment ─────────────────────────────────────────────
    if report.novelty_report is not None:
        nr = report.novelty_report
        verdict = nr.get("overall_verdict", "?")
        density = nr.get("novelty_density", 0.0)
        lines.append("## Novelty assessment (target: maximal)")
        lines.append("")
        lines.append(f"- Verdict: **{verdict}** (density {density:.2f})")
        promote = nr.get("promote_panels", [])
        drop = nr.get("drop_panels", [])
        demote = nr.get("demote_panels", [])
        lines.append(
            f"- Promote: {', '.join(promote) if promote else '(none)'}"
        )
        lines.append(
            f"- Drop: {', '.join(drop) if drop else '(none)'}"
        )
        lines.append(
            f"- Demote: {', '.join(demote) if demote else '(none)'}"
        )
        lines.append(f"- Recipe gaps: {plan.n_gaps}")
        lines.append("")
    elif plan.n_gaps:
        lines.append(f"_(novelty scoring disabled or unavailable; {plan.n_gaps} "
                     "recipe gap(s) flagged)_")
        lines.append("")

    # ── manuscript collision report (E10) ──────────────────────────────
    if report.collision_report is not None:
        lines.append("## Manuscript collision report")
        lines.append("")
        try:
            from .manuscript_collision import render_collision_report_markdown
            collision_md = render_collision_report_markdown(report.collision_report)
            # The downstream renderer usually emits its own H1; strip it
            # so the section fits inside the scout report cleanly.
            for cl in collision_md.splitlines():
                if cl.startswith("# "):
                    continue
                lines.append(cl)
        except Exception:  # pragma: no cover — defensive fallback
            cr_dict = (
                report.collision_report.to_dict()
                if hasattr(report.collision_report, "to_dict")
                else {}
            )
            lines.append(
                f"- collision_report attached "
                f"(per-figure: {len(cr_dict.get('per_figure', []) or [])})"
            )
        lines.append("")

    # ── notes & next steps ─────────────────────────────────────────────
    if inv.notes:
        lines.append("## Inventory notes")
        for n in inv.notes:
            lines.append(f"- {n}")
        lines.append("")
    if report.notes:
        lines.append("## Scout notes")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("## Suggested next commands")
    lines.append("")
    lines.append("```")
    lines.append("figures execute-plan figures_plan.yaml --yes")
    if plan.n_gaps:
        lines.append("# (after scaffolding gaps via)")
        lines.append("figures fill-gap <gap-name>")
    lines.append("```")

    return "\n".join(lines).rstrip() + "\n"


# ─────────────────────────── YAML round-trip ─────────────────────────────


def save_figure_plan_yaml(plan: FigurePlan, path: Path) -> Path:
    """Serialise a :class:`FigurePlan` to YAML at ``path``.

    The file always carries ``schema_version: 1`` at the top level. The
    full plan is round-trippable via :func:`load_figure_plan_yaml`.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise ScoutError(
            "PyYAML is required to save figure plans; install with: pip install pyyaml"
        ) from exc
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(plan.to_dict(), sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return out_path


def load_figure_plan_yaml(path: Path) -> FigurePlan:
    """Load a :class:`FigurePlan` from a YAML file written by :func:`save_figure_plan_yaml`."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise ScoutError(
            "PyYAML is required to load figure plans; install with: pip install pyyaml"
        ) from exc
    in_path = Path(path)
    if not in_path.is_file():
        raise ScoutError(f"figure plan file not found: {in_path}")
    text = in_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ScoutError(f"failed to parse {in_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ScoutError(f"figure plan YAML must be a mapping at the top level: {in_path}")
    schema_version = data.get("schema_version", 1)
    if schema_version != 1:
        warnings.warn(
            f"figure plan schema_version={schema_version}; expected 1 — proceeding",
            RuntimeWarning,
            stacklevel=2,
        )
    return FigurePlan.from_dict(data)


# ──────────────────────────── helpers (export) ───────────────────────────


def _scout_report_to_json(report: ProjectScoutReport, *, indent: int = 2) -> str:
    """Convenience: serialise a :class:`ProjectScoutReport` as JSON."""
    return json.dumps(report.to_dict(), indent=indent, default=str)
