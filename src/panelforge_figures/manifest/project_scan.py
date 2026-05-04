"""Project-inference module — pre-fills the 8-question intake from a working dir.

Wave 3 — see ``CLAUDE_CODE_AUTONOMOUS.md`` §4.

The scanner walks a *user* project directory (NOT the panelforge repo), reads
plain-text artefacts (``manuscript.md``, ``methods.md``, ``README.md``,
``panelforge.project.yaml``, ``*.bib``, the ``data/`` and ``figures/``
listings) and emits an :class:`InferredAnswer` per intake field with a
confidence in [0, 1].

The rule-set follows three priority bands:

* **Priority 1** (``panelforge.project.yaml``, ``manuscript.{md,tex}``,
  ``methods.{md,tex}``, root ``README.md``) — explicit configuration wins
  outright (confidence 1.0); manuscript/method keyword hits accumulate.
* **Priority 2** (``results.md``, ``discussion.md``, ``data/README.md``,
  ``figures/RENDER_REPORT.md``, ``*.bib``) — corroborating evidence,
  smaller weights.
* **Priority 3** (file listings, notebook metadata) — weakest signals.

Only the standard library is used — pyyaml is imported lazily, with a
tiny hand-rolled fallback so the module remains importable in minimal
environments.  Notebooks are *never* executed; only the JSON header is
parsed when present.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .intake import HARD_FILTER_KEYS, IntakeAnswer

# ─────────────────────────── data classes ───────────────────────────────


@dataclass(frozen=True)
class InferredAnswer:
    """One inferred answer plus provenance and confidence band."""

    field_name: str
    value: Any
    confidence: float
    sources: tuple[str, ...]
    label: str  # "[inferred]" | "[inferred — review]" | "[asking]"


@dataclass(frozen=True)
class ProjectScanResult:
    """Aggregated outcome of :func:`scan_project`."""

    project_root: Path
    answers: dict[str, InferredAnswer]
    files_read: tuple[Path, ...]
    panelforge_yaml_present: bool


# ─────────────────────────── confidence bands ───────────────────────────


def _band(conf: float) -> str:
    """Map a numeric confidence to a human-readable label."""
    if conf >= 0.9:
        return "[inferred]"
    if conf >= 0.7:
        return "[inferred — review]"
    return "[asking]"


def _cap(value: float, ceiling: float = 1.0) -> float:
    """Clamp ``value`` into ``[0, ceiling]``."""
    return max(0.0, min(ceiling, value))


# ─────────────────────────── file-reading helpers ───────────────────────


_YAML_NAMES = ("panelforge.project.yaml", "panelforge.project.yml")


def _safe_read_text(path: Path) -> str:
    """Best-effort UTF-8 read; returns empty string on any error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _list_files(directory: Path) -> tuple[Path, ...]:
    """Return a tuple of files (non-recursive) in ``directory``.

    Hidden files are skipped.  Returns empty tuple if missing/unreadable.
    """
    if not directory.is_dir():
        return ()
    try:
        return tuple(sorted(p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".")))
    except OSError:
        return ()


def _load_yaml(path: Path) -> dict[str, Any]:
    """Parse a YAML file with pyyaml if available; otherwise a tiny fallback.

    The fallback understands flat ``key: value`` / ``key: [a, b]`` / boolean /
    integer entries, which is enough for the panelforge.project.yaml schema
    documented in §4.  Anything more complex returns an empty dict.
    """
    text = _safe_read_text(path)
    if not text:
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except ImportError:
        return _parse_yaml_minimal(text)
    except yaml.YAMLError:                  # type: ignore[name-defined]
        # DEFECT-A9 fix (Wave-3 polish): malformed panelforge.project.yaml
        # falls back to the minimal parser instead of propagating
        # YAMLError out of scan_project.  If the minimal parser also
        # can't make sense of it, we return {} and the scanner falls
        # back to text-only inference.
        return _parse_yaml_minimal(text)


def _parse_yaml_minimal(text: str) -> dict[str, Any]:
    """Tiny YAML subset parser — flat ``key: value`` only."""
    out: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line or ":" not in line or line.startswith(" "):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            out[key] = tuple(t.strip().strip("\"'") for t in inner.split(",") if t.strip())
        elif value.lower() in {"true", "false"}:
            out[key] = value.lower() == "true"
        elif value.lstrip("-").isdigit():
            out[key] = int(value)
        elif value:
            out[key] = value.strip("\"'")
    return out


# ─────────────────────────── inference helpers ──────────────────────────


def _gather_text(root: Path) -> tuple[str, tuple[Path, ...]]:
    """Concatenate the text of all priority-1+2 documents under ``root``.

    Returns a lowercase blob plus the list of files actually consumed.
    """
    candidate_names = (
        "manuscript.md",
        "manuscript.tex",
        "methods.md",
        "methods.tex",
        "README.md",
        "results.md",
        "discussion.md",
    )
    blob_parts: list[str] = []
    consumed: list[Path] = []

    for name in candidate_names:
        p = root / name
        if p.is_file():
            blob_parts.append(_safe_read_text(p))
            consumed.append(p)

    data_readme = root / "data" / "README.md"
    if data_readme.is_file():
        blob_parts.append(_safe_read_text(data_readme))
        consumed.append(data_readme)

    render_report = root / "figures" / "RENDER_REPORT.md"
    if render_report.is_file():
        blob_parts.append(_safe_read_text(render_report))
        consumed.append(render_report)

    for bib in sorted(root.glob("*.bib")):
        blob_parts.append(_safe_read_text(bib))
        consumed.append(bib)

    return ("\n".join(blob_parts).lower(), tuple(consumed))


def _csv_columns(path: Path) -> tuple[str, ...]:
    """Return the (lowercased) header columns of a CSV file, or empty tuple."""
    text = _safe_read_text(path)
    if not text:
        return ()
    head = text.splitlines()[0] if text.splitlines() else ""
    return tuple(c.strip().lower() for c in head.split(",") if c.strip())


def _data_csv_columns(root: Path) -> set[str]:
    """Union of column names across CSV files under ``data/`` (one level)."""
    out: set[str] = set()
    data_dir = root / "data"
    if not data_dir.is_dir():
        return out
    for p in _list_files(data_dir):
        if p.suffix.lower() == ".csv":
            out.update(_csv_columns(p))
    return out


def _notebook_metadata_text(root: Path) -> str:
    """Return concatenated text from ``*.ipynb`` cells (markdown only).

    Notebooks are never executed; only the JSON is read to extract the
    markdown cells and metadata kernel name.  Errors are swallowed silently.
    """
    parts: list[str] = []
    try:
        nb_paths = list(root.glob("*.ipynb"))
    except OSError:
        return ""
    for nb_path in nb_paths:
        try:
            data = json.loads(_safe_read_text(nb_path))
        except (ValueError, OSError):
            continue
        meta = data.get("metadata", {}) if isinstance(data, dict) else {}
        if isinstance(meta, dict):
            parts.append(json.dumps(meta).lower())
        for cell in data.get("cells", []) if isinstance(data, dict) else []:
            if isinstance(cell, dict) and cell.get("cell_type") == "markdown":
                src = cell.get("source", "")
                if isinstance(src, list):
                    parts.append("".join(src))
                elif isinstance(src, str):
                    parts.append(src)
    return "\n".join(parts).lower()


# ─────────────────────────── per-question rules ─────────────────────────


def _infer_factorial_design(
    text: str, csv_cols: set[str], yaml_cfg: dict[str, Any]
) -> tuple[bool, float, list[str]]:
    if "factorial" in yaml_cfg:
        return bool(yaml_cfg["factorial"]), 1.0, ["panelforge.project.yaml"]

    used: list[str] = []
    conf = 0.0
    keyword_hits = 0
    for kw in ("2x2", "2×2", "factorial", "interaction term", "sex × genotype",
               "sex x genotype", "sex*genotype"):
        if kw in text:
            keyword_hits += 1
    if keyword_hits:
        conf += min(0.4 * keyword_hits, 0.9)
        used.append("manuscript/methods")

    factorial_cols = {"sex", "genotype", "condition", "treatment"}
    if csv_cols & factorial_cols:
        if len(csv_cols & factorial_cols) >= 2:
            conf += 0.3
            used.append("data/")

    if "anova" in text and "interaction" in text:
        conf += 0.3
        used.append("methods.anova")

    if conf > 0:
        return True, _cap(conf, 0.95), used
    return False, 0.3, ["default"]


def _infer_equivalence_claims(
    text: str, yaml_cfg: dict[str, Any] | None = None,
) -> tuple[bool, float, list[str]]:
    # W3-D-flagged gap: panelforge.project.yaml: equivalence: was not
    # honoured (other 4 YAML keys were).  Now consistent with siblings.
    if yaml_cfg is not None and "equivalence" in yaml_cfg:
        return bool(yaml_cfg["equivalence"]), 1.0, ["panelforge.project.yaml"]
    used: list[str] = []
    conf = 0.0
    for kw in ("tost", "equivalence", "null-accepting", "pre-registered bounds"):
        if kw in text:
            conf += 0.5
            used.append(f"keyword:{kw}")
    if "equivalence margin" in text or "equivalence bound" in text:
        conf += 0.4
        used.append("methods.margins")
    if "tost forest" in text or "equivalence forest" in text:
        conf += 0.3
        used.append("RENDER_REPORT")
    if conf > 0:
        return True, _cap(conf, 0.95), used
    return False, 0.3, ["default"]


def _infer_manuscript_anchor(
    text: str, yaml_cfg: dict[str, Any]
) -> tuple[str, float, list[str]]:
    if "anchor" in yaml_cfg:
        val = str(yaml_cfg["anchor"])
        return val, 1.0, ["panelforge.project.yaml"]

    has_disc1 = "disc1" in text or "lissencephaly" in text
    has_cdc42 = "cdc42" in text
    if has_disc1 and has_cdc42:
        return "both", 0.85, ["manuscript/methods"]
    if has_disc1:
        return "DISC1", 0.9, ["manuscript/methods"]
    if "cdc42 cko" in text or "cdc42 conditional knockout" in text:
        return "CDC42", 0.85, ["methods.cdc42_cko"]
    if has_cdc42:
        return "CDC42", 0.8, ["manuscript/methods"]
    return "none", 0.5, ["default"]


def _infer_dynamics_needed(
    text: str, csv_cols: set[str]
) -> tuple[str, float, list[str]]:
    has_kymo = "kymograph" in text
    has_live = any(
        kw in text
        for kw in ("live-cell", "live cell", "intravital", "two-photon time-lapse",
                   "two-photon time lapse", "time-lapse imaging")
    )
    has_pseudotime = any(
        kw in text
        for kw in ("pseudotime", "ordered trajectory", "actin drive index")
    )
    has_time_cols = bool(csv_cols & {"t_s", "time_min", "time_s", "frame", "timepoint"})

    if has_kymo:
        conf = 0.8 + (0.1 if has_time_cols else 0.0)
        return "kymograph", _cap(conf, 0.95), ["manuscript/methods.kymograph"]
    if has_live:
        conf = 0.8 + (0.1 if has_time_cols else 0.0)
        return "live", _cap(conf, 0.95), ["manuscript/methods.live"]
    if has_pseudotime:
        return "ordered_pseudotime", 0.8, ["manuscript/methods.pseudotime"]
    if has_time_cols:
        return "live", 0.6, ["data.time_columns"]
    return "static", 0.5, ["default"]


def _infer_dimensionality(
    text: str, csv_cols: set[str], data_files: tuple[Path, ...]
) -> tuple[str, float, list[str]]:
    keywords_3d = ("airyscan", "lattice light-sheet", "z-stack", "z stack",
                   "volumetric", "3d reconstruction")
    keywords_2d = ("2d segmentation", "epifluorescence", "max intensity projection",
                   "mip overlay")

    has_3d_kw = any(kw in text for kw in keywords_3d)
    has_2d_kw = any(kw in text for kw in keywords_2d)
    has_3d_cols = "z" in csv_cols and "x" in csv_cols and "y" in csv_cols
    has_3d_files = any(re.search(r"(_zstack|_3d|_z\d+)", p.name.lower()) for p in data_files)

    score_3d = (
        (0.8 if has_3d_kw else 0.0)
        + (0.7 if has_3d_cols and not has_3d_kw else 0.0)
        + (0.3 if has_3d_files and not has_3d_kw else 0.0)
    )
    score_2d = 0.8 if has_2d_kw else 0.0

    if score_3d >= 0.7 and score_2d >= 0.7:
        return "mixed", 0.85, ["manuscript/methods.mixed"]
    if score_3d >= 0.7:
        return "3D", _cap(score_3d), ["manuscript/methods.3d"]
    if score_2d >= 0.7:
        return "2D", _cap(score_2d), ["manuscript/methods.2d"]
    if score_3d > 0:
        return "3D", _cap(0.6 + score_3d / 2, 0.85), ["data/files.3d"]
    return "2D", 0.6, ["default"]


def _infer_modalities_in_scope(
    text: str,
    yaml_cfg: dict[str, Any],
    available: tuple[str, ...],
    data_dirs: tuple[Path, ...],
) -> tuple[tuple[str, ...], float, list[str]]:
    if "modalities" in yaml_cfg:
        raw = yaml_cfg["modalities"]
        if isinstance(raw, (list, tuple)):
            return tuple(str(x) for x in raw), 1.0, ["panelforge.project.yaml"]

    keyword_to_modality = {
        "actin_microtubule_morphometry": (
            "actin", "microtubule", "morphometry", "cytoskeleton"
        ),
        "biophysics_scaling": (
            "persistence length", "psd", "modulus", "scaling law"
        ),
        "intravital_imaging": ("in vivo", "two-photon", "intravital"),
        "rhogtpase_dynamics": ("rhogtpase", "rho gtpase", "cdc42 activity"),
        "calcium_signaling": ("calcium imaging", "gcamp", "ca2+ transient"),
        "spatial_statistics": ("ripley", "nearest-neighbor", "spatial point pattern"),
        "diffusion_and_tracking": ("msd", "single-particle tracking", "spt "),
        "fret_biosensors": ("fret biosensor", "raichu", "fret ratio"),
        "redox_imaging": ("rogfp", "redox imaging", "h2o2 sensor"),
        "single_cell_embeddings": ("umap", "scrna", "single-cell rna"),
        "omics_differential": ("differential expression", "deseq", "edge r"),
        "mixed_effects_models": ("mixed-effects", "lme4", "lmer"),
        "network_and_pathway": ("pathway enrichment", "kegg", "reactome"),
        "dose_response_pharmacology": ("dose-response", "ic50", "ec50"),
        "gillespie_stochastic": ("gillespie", "stochastic simulation"),
        "clinical_cohort": ("clinical cohort", "kaplan-meier", "kaplan meier"),
        "cryoem_and_structure": ("cryo-em", "cryoem", "atomic model"),
    }

    selected: list[str] = []
    used: list[str] = []
    for modality, keywords in keyword_to_modality.items():
        if modality not in available:
            continue
        if any(kw in text for kw in keywords):
            selected.append(modality)
            used.append(f"keyword:{modality}")

    data_dir_names = {p.name for p in data_dirs if p.is_dir()}
    for modality in available:
        if modality in data_dir_names and modality not in selected:
            selected.append(modality)
            used.append(f"data/{modality}")

    if selected:
        # Folder-name corroboration nudges confidence up.
        boost = 0.5 if any(s.startswith("data/") for s in used) else 0.0
        return tuple(selected), _cap(0.8 + boost, 0.95), used

    return tuple(available), 0.4, ["default"]


def _infer_hard_filters(text: str) -> tuple[dict[str, bool], float, list[str]]:
    used: list[str] = []
    out: dict[str, bool] = {k: False for k in HARD_FILTER_KEYS}
    if any(kw in text for kw in ("compartment", "whole-cell vs protrusion",
                                  "compartment-aware", "compartment aware")):
        out["compartment_aware"] = True
        used.append("keyword:compartment")
    if any(kw in text for kw in ("scale-aware", "scale aware",
                                  "polymer to network to territory", "hierarchical scale")):
        out["scale_aware"] = True
        used.append("keyword:scale")
    if used:
        return out, 0.8, used
    return out, 0.6, ["default"]


def _infer_shortlist_size(
    text: str, yaml_cfg: dict[str, Any]
) -> tuple[int, float, list[str]]:
    if "shortlist_size" in yaml_cfg:
        try:
            return int(yaml_cfg["shortlist_size"]), 1.0, ["panelforge.project.yaml"]
        except (TypeError, ValueError):
            pass

    # "figure plan: N panels" / "N panels rendered"
    m = re.search(r"figure[\s-]+plan[^.\n]{0,80}?(\d{1,2})\s+panel", text)
    if m:
        return int(m.group(1)), 0.8, ["manuscript.figure_plan"]

    m = re.search(r"rendered\s+(\d{1,2})\s+panels?", text)
    if m:
        return int(m.group(1)), 0.6, ["RENDER_REPORT"]

    return 12, 0.7, ["default"]


# ─────────────────────────── public API ─────────────────────────────────


_FIELD_ORDER = (
    "factorial_design",
    "equivalence_claims",
    "manuscript_anchor",
    "dynamics_needed",
    "dimensionality",
    "modalities_in_scope",
    "hard_filters",
    "shortlist_size",
)


def scan_project(
    project_root: Path = Path("."),
    *,
    available_modalities: tuple[str, ...] = (),
    confidence_threshold: float = 0.7,
) -> ProjectScanResult:
    """Walk the project directory, infer intake answers, return structured result.

    Reads only ``README.md`` / ``manuscript.{md,tex}`` / ``methods.{md,tex}`` /
    ``panelforge.project.yaml`` / ``*.bib`` plus listings of ``data/`` and
    ``figures/``.  Notebooks are parsed as JSON only — never executed.

    Parameters
    ----------
    project_root
        The user's working directory.  Must exist.
    available_modalities
        Registry's modality list.  Used to gate Q6 results to known names.
    confidence_threshold
        The minimum confidence for an answer to be kept by
        :func:`to_intake_pre_filled`.  Defaults to 0.7 (matches intake spec).

    Returns
    -------
    ProjectScanResult
        Frozen aggregate with one :class:`InferredAnswer` per intake field,
        the list of files actually read, and a flag indicating whether
        ``panelforge.project.yaml`` was present.

    Notes
    -----
    ``confidence_threshold`` is accepted for API symmetry but does not
    change which answers are returned — every intake field always gets
    exactly one :class:`InferredAnswer`.  Filtering happens in
    :func:`to_intake_pre_filled`, which honours the same parameter.
    """
    del confidence_threshold  # API-symmetric; filtering lives in to_intake_pre_filled
    root = Path(project_root).resolve()
    yaml_path: Path | None = None
    for name in _YAML_NAMES:
        p = root / name
        if p.is_file():
            yaml_path = p
            break
    yaml_cfg = _load_yaml(yaml_path) if yaml_path else {}
    has_yaml = yaml_path is not None

    blob, doc_files = _gather_text(root)
    nb_blob = _notebook_metadata_text(root)
    if nb_blob:
        blob = blob + "\n" + nb_blob

    data_files = _list_files(root / "data")
    csv_cols = _data_csv_columns(root)
    data_subdirs = tuple(p for p in (root / "data").iterdir() if p.is_dir()) \
        if (root / "data").is_dir() else ()

    files_read: list[Path] = list(doc_files)
    if yaml_path is not None:
        files_read.insert(0, yaml_path)

    answers: dict[str, InferredAnswer] = {}

    fd_val, fd_conf, fd_src = _infer_factorial_design(blob, csv_cols, yaml_cfg)
    answers["factorial_design"] = InferredAnswer(
        "factorial_design", fd_val, fd_conf, tuple(fd_src), _band(fd_conf)
    )

    eq_val, eq_conf, eq_src = _infer_equivalence_claims(blob, yaml_cfg)
    answers["equivalence_claims"] = InferredAnswer(
        "equivalence_claims", eq_val, eq_conf, tuple(eq_src), _band(eq_conf)
    )

    ma_val, ma_conf, ma_src = _infer_manuscript_anchor(blob, yaml_cfg)
    answers["manuscript_anchor"] = InferredAnswer(
        "manuscript_anchor", ma_val, ma_conf, tuple(ma_src), _band(ma_conf)
    )

    dy_val, dy_conf, dy_src = _infer_dynamics_needed(blob, csv_cols)
    answers["dynamics_needed"] = InferredAnswer(
        "dynamics_needed", dy_val, dy_conf, tuple(dy_src), _band(dy_conf)
    )

    dim_val, dim_conf, dim_src = _infer_dimensionality(blob, csv_cols, data_files)
    answers["dimensionality"] = InferredAnswer(
        "dimensionality", dim_val, dim_conf, tuple(dim_src), _band(dim_conf)
    )

    mod_val, mod_conf, mod_src = _infer_modalities_in_scope(
        blob, yaml_cfg, available_modalities, data_subdirs
    )
    answers["modalities_in_scope"] = InferredAnswer(
        "modalities_in_scope", mod_val, mod_conf, tuple(mod_src), _band(mod_conf)
    )

    hf_val, hf_conf, hf_src = _infer_hard_filters(blob)
    answers["hard_filters"] = InferredAnswer(
        "hard_filters", hf_val, hf_conf, tuple(hf_src), _band(hf_conf)
    )

    sl_val, sl_conf, sl_src = _infer_shortlist_size(blob, yaml_cfg)
    answers["shortlist_size"] = InferredAnswer(
        "shortlist_size", sl_val, sl_conf, tuple(sl_src), _band(sl_conf)
    )

    return ProjectScanResult(
        project_root=root,
        answers={k: answers[k] for k in _FIELD_ORDER},
        files_read=tuple(files_read),
        panelforge_yaml_present=has_yaml,
    )


def to_intake_pre_filled(
    result: ProjectScanResult,
    *,
    confidence_threshold: float = 0.7,
) -> dict[str, IntakeAnswer]:
    """Convert a :class:`ProjectScanResult` to the dict consumed by
    :func:`run_intake_interactive` as ``pre_filled``.

    Answers below ``confidence_threshold`` are dropped (the intake will then
    prompt the user explicitly with the spec default shown).
    """
    out: dict[str, IntakeAnswer] = {}
    field_to_qid = {
        "factorial_design": 1,
        "equivalence_claims": 2,
        "manuscript_anchor": 3,
        "dynamics_needed": 4,
        "dimensionality": 5,
        "modalities_in_scope": 6,
        "hard_filters": 7,
        "shortlist_size": 8,
    }
    for field_name, ans in result.answers.items():
        if ans.confidence < confidence_threshold:
            continue
        out[field_name] = IntakeAnswer(
            question_id=field_to_qid[field_name],
            field_name=field_name,
            value=ans.value,
            source="inferred",
            confidence=ans.confidence,
        )
    return out


__all__ = [
    "InferredAnswer",
    "ProjectScanResult",
    "scan_project",
    "to_intake_pre_filled",
]
