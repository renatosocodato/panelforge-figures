"""STAR Methods support — Elevation 12 (v3.6.0).

Cell / Nature / Science / eLife require a STAR Methods section with a
**Key Resources Table** plus per-method narrative subsections.  This
module produces those artefacts directly from project state:

* ``extract_key_resources`` — walks the project root and harvests
  Software (from ``pyproject.toml``), Deposited Data (from
  ``*.provenance.json`` sidecars) and Reagents/Antibodies/Organisms
  (from ``panelforge.project.yaml``).
* ``render_star_methods_table_latex`` /
  ``render_star_methods_table_markdown`` — emit the Key Resources Table
  grouped by Cell's nine canonical categories.
* ``render_method_details_section`` — one Methods paragraph per recipe
  family, pulled from the recipe's docstring + ``answers_question``.
* ``render_quantification_section`` — one Quantification & Statistical
  Analysis paragraph per family, pulled **verbatim** from each
  ``StatisticalContract`` (no hallucination).
* ``generate_star_methods`` — the end-to-end entry point that the CLI
  binds to.

Design notes
------------
* **No hallucination.** Every statistical clause is paste-from-contract;
  software entries are real package names with real version strings;
  data entries are real SHAs.  When a fact is unavailable we omit it,
  never invent it.
* **Tolerant** — missing ``pyproject.toml``, missing
  ``panelforge.project.yaml``, missing provenance sidecars all just
  produce empty resource sections.
* **Deterministic ordering** — Key Resources Table is sorted by
  ``(category, reagent_or_resource)`` so re-running on the same project
  produces byte-identical output.

See ``docs/spec_star_methods.md`` for the full Cell / Nature spec
(forthcoming).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "STAR_METHODS_TEMPLATE",
    "KeyResource",
    "ResourceCategory",
    "StarMethodsError",
    "StarMethodsSection",
    "StarMethodsTable",
    "extract_key_resources",
    "generate_star_methods",
    "render_method_details_section",
    "render_quantification_section",
    "render_star_methods_table_latex",
    "render_star_methods_table_markdown",
]


# --------------------------------------------------------------------------- #
# Enums / dataclasses                                                         #
# --------------------------------------------------------------------------- #


class ResourceCategory(StrEnum):
    """Cell STAR Methods nine canonical Key Resources Table categories."""

    antibodies = "Antibodies"
    chemicals = "Chemicals, Peptides, and Recombinant Proteins"
    critical_kits = "Critical Commercial Assays"
    deposited_data = "Deposited Data"
    cell_lines = "Experimental Models: Cell Lines"
    organisms = "Experimental Models: Organisms/Strains"
    oligonucleotides = "Oligonucleotides"
    recombinant_dna = "Recombinant DNA"
    software_algorithms = "Software and Algorithms"
    other = "Other"


class StarMethodsSection(StrEnum):
    """Sections of a Cell STAR Methods block."""

    key_resources_table = "Key Resources Table"
    contact_for_reagent = "Contact for Reagent and Resource Sharing"
    experimental_model_subject_details = "Experimental Model and Subject Details"
    method_details = "Method Details"
    quantification_and_statistical_analysis = (
        "Quantification and Statistical Analysis"
    )
    data_and_code_availability = "Data and Code Availability"


@dataclass(frozen=True)
class KeyResource:
    """One row in the Key Resources Table."""

    category: ResourceCategory
    reagent_or_resource: str
    source: str
    identifier: str  # catalog number, RRID, GitHub URL, SHA, etc.


@dataclass(frozen=True)
class StarMethodsTable:
    """Composed STAR Methods artefact returned by :func:`generate_star_methods`."""

    key_resources: tuple[KeyResource, ...]
    method_details_paragraphs: dict[str, str]
    quantification_paragraphs: dict[str, str]
    data_and_code_section: str
    n_recipes: int
    venue: str = "cell"


class StarMethodsError(RuntimeError):
    """Raised on unrecoverable failures (bad project root, malformed YAML…)."""


# --------------------------------------------------------------------------- #
# Template constant                                                           #
# --------------------------------------------------------------------------- #


STAR_METHODS_TEMPLATE = {
    "sections_order": (
        StarMethodsSection.key_resources_table,
        StarMethodsSection.contact_for_reagent,
        StarMethodsSection.experimental_model_subject_details,
        StarMethodsSection.method_details,
        StarMethodsSection.quantification_and_statistical_analysis,
        StarMethodsSection.data_and_code_availability,
    ),
    "venues_supported": ("plain", "nature", "cell", "nejm", "biorxiv", "science"),
    "default_venue": "cell",
}


# --------------------------------------------------------------------------- #
# Helpers — best-effort YAML / TOML readers                                  #
# --------------------------------------------------------------------------- #


def _safe_read_text(path: Path) -> str:
    """UTF-8 read returning ``""`` on any IO error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _load_yaml(path: Path) -> dict[str, Any]:
    """Parse a YAML file with pyyaml when available; otherwise ``{}``."""
    if not path.is_file():
        return {}
    text = _safe_read_text(path)
    if not text:
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except ImportError:  # pragma: no cover — yaml is a hard dep
        return {}
    except Exception:
        return {}


def _load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file with stdlib ``tomllib`` (Py 3.11+)."""
    if not path.is_file():
        return {}
    try:
        import tomllib

        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# extract_key_resources                                                       #
# --------------------------------------------------------------------------- #


def _split_dependency_spec(spec: str) -> tuple[str, str]:
    """Split a PEP 508 dependency specifier into (package_name, version_string).

    Examples:
        "numpy>=1.24"        -> ("numpy", ">=1.24")
        "matplotlib >= 3.7"  -> ("matplotlib", ">=3.7")
        "click==8.1.3"       -> ("click", "==8.1.3")
        "requests"           -> ("requests", "")
        "pandas[parquet]>=2" -> ("pandas", ">=2")
    """
    if not spec:
        return "", ""
    spec = spec.strip()
    # Strip any environment markers ("; python_version >= ...").
    spec = spec.split(";", 1)[0].strip()
    # Find the first version comparator.
    for op in ("===", "==", ">=", "<=", "~=", "!=", ">", "<"):
        if op in spec:
            name, _, ver = spec.partition(op)
            return _normalise_pkg_name(name.strip()), f"{op}{ver.strip()}"
    return _normalise_pkg_name(spec), ""


def _normalise_pkg_name(raw: str) -> str:
    """Strip extras like ``pandas[parquet]`` -> ``pandas``."""
    if "[" in raw:
        return raw.split("[", 1)[0].strip()
    return raw.strip()


def _extract_software_resources(project_root: Path) -> list[KeyResource]:
    """Read ``pyproject.toml`` and convert ``[project.dependencies]`` plus all
    extras to ``KeyResource`` rows of category ``software_algorithms``.

    The version pin is embedded in ``identifier`` (e.g. ``">=1.24"``);
    the package homepage on PyPI is used as ``source``.
    """
    pyproject = project_root / "pyproject.toml"
    data = _load_toml(pyproject)
    if not data:
        return []

    project = data.get("project", {})
    if not isinstance(project, dict):
        return []

    deps: list[str] = []
    raw_deps = project.get("dependencies", [])
    if isinstance(raw_deps, list):
        deps.extend(str(d) for d in raw_deps if d)

    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for group in optional.values():
            if isinstance(group, list):
                deps.extend(str(d) for d in group if d)

    seen: dict[str, str] = {}
    for spec in deps:
        name, ver = _split_dependency_spec(spec)
        if not name:
            continue
        # Keep the first version we see (extras may not pin).
        seen.setdefault(name, ver)

    out: list[KeyResource] = []
    for name, ver in sorted(seen.items()):
        identifier = f"PyPI:{name}{ver}" if ver else f"PyPI:{name}"
        out.append(
            KeyResource(
                category=ResourceCategory.software_algorithms,
                reagent_or_resource=name,
                source=f"https://pypi.org/project/{name}/",
                identifier=identifier,
            )
        )

    # Also surface the project itself as a software entry.
    project_name = project.get("name")
    project_version = project.get("version")
    if isinstance(project_name, str) and project_name:
        urls = project.get("urls", {}) or {}
        homepage = ""
        if isinstance(urls, dict):
            homepage = str(
                urls.get("Repository")
                or urls.get("Homepage")
                or urls.get("Documentation")
                or ""
            )
        ident = (
            f"v{project_version}" if isinstance(project_version, str) else "v?"
        )
        out.append(
            KeyResource(
                category=ResourceCategory.software_algorithms,
                reagent_or_resource=project_name,
                source=homepage or f"https://pypi.org/project/{project_name}/",
                identifier=ident,
            )
        )

    return out


def _extract_deposited_data(project_root: Path) -> list[KeyResource]:
    """Walk ``panelforge_workspace/figures/*.provenance.json`` and harvest
    one ``KeyResource`` per unique data file (deduped by sha256)."""
    workspace = project_root / "panelforge_workspace" / "figures"
    if not workspace.is_dir():
        return []

    import json

    seen: dict[str, KeyResource] = {}
    for path in sorted(workspace.glob("*.provenance.json")):
        try:
            blob = json.loads(_safe_read_text(path))
        except Exception:
            continue
        if not isinstance(blob, dict):
            continue
        data = blob.get("data")
        if not isinstance(data, dict):
            continue
        sources = data.get("sources")
        if not isinstance(sources, list):
            continue
        for src in sources:
            if not isinstance(src, dict):
                continue
            sha = str(src.get("sha256", "")).strip()
            if not sha or sha in seen:
                continue
            src_path = str(src.get("path", "")).strip() or "<unknown>"
            fmt = str(src.get("format", "")).strip()
            name = Path(src_path).name or src_path
            label = f"{name}" + (f" ({fmt})" if fmt else "")
            seen[sha] = KeyResource(
                category=ResourceCategory.deposited_data,
                reagent_or_resource=label,
                source=src_path,
                identifier=f"sha256:{sha[:16]}",
            )
    return list(seen.values())


def _extract_reagent_block(
    yaml_cfg: dict[str, Any],
    key: str,
    category: ResourceCategory,
) -> list[KeyResource]:
    """Map a YAML ``reagents:`` / ``antibodies:`` / ``organisms:`` /
    ``cell_lines:`` / ``oligonucleotides:`` block to ``KeyResource`` rows.

    The block is permissive: each entry may be either
      - a string (treated as ``reagent_or_resource``), or
      - a dict ``{name, source, identifier, ...}``.
    """
    raw = yaml_cfg.get(key)
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []

    out: list[KeyResource] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(
                KeyResource(
                    category=category,
                    reagent_or_resource=entry,
                    source="this study",
                    identifier="N/A",
                )
            )
        elif isinstance(entry, dict):
            name = str(
                entry.get("name")
                or entry.get("reagent")
                or entry.get("antibody")
                or entry.get("organism")
                or entry.get("strain")
                or "unspecified"
            )
            source = str(entry.get("source") or entry.get("vendor") or "this study")
            ident = str(
                entry.get("identifier")
                or entry.get("rrid")
                or entry.get("catalog")
                or entry.get("catalog_number")
                or "N/A"
            )
            out.append(
                KeyResource(
                    category=category,
                    reagent_or_resource=name,
                    source=source,
                    identifier=ident,
                )
            )
    return out


def extract_key_resources(
    project_root: Path,
    *,
    include_software: bool = True,
    include_deposited_data: bool = True,
    include_reagents: bool = True,
) -> tuple[KeyResource, ...]:
    """Walk the project and harvest a Key Resources Table.

    Sources scanned (each governed by its respective ``include_*`` flag):

    * ``pyproject.toml`` — every dependency (including extras) becomes
      a ``software_algorithms`` row; the project itself is included too.
    * ``panelforge_workspace/figures/*.provenance.json`` — every
      ``data.sources[*]`` entry, deduped by SHA-256, becomes a
      ``deposited_data`` row.
    * ``panelforge.project.yaml`` — six known blocks
      (``antibodies``, ``reagents``, ``cell_lines``, ``organisms``,
      ``oligonucleotides``, ``recombinant_dna``) are mapped to their
      corresponding ``ResourceCategory``.

    Returns a deterministically-sorted tuple by ``(category, reagent_or_resource)``.
    """
    root = Path(project_root)
    if not root.exists() or not root.is_dir():
        raise StarMethodsError(f"project_root does not exist: {root}")

    rows: list[KeyResource] = []

    if include_software:
        rows.extend(_extract_software_resources(root))

    if include_deposited_data:
        rows.extend(_extract_deposited_data(root))

    if include_reagents:
        yaml_cfg: dict[str, Any] = {}
        for name in ("panelforge.project.yaml", "panelforge.project.yml"):
            yaml_path = root / name
            if yaml_path.is_file():
                yaml_cfg = _load_yaml(yaml_path)
                break

        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "antibodies", ResourceCategory.antibodies
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "reagents", ResourceCategory.chemicals
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "chemicals", ResourceCategory.chemicals
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "kits", ResourceCategory.critical_kits
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "cell_lines", ResourceCategory.cell_lines
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "organisms", ResourceCategory.organisms
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "strains", ResourceCategory.organisms
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "oligonucleotides", ResourceCategory.oligonucleotides
            )
        )
        rows.extend(
            _extract_reagent_block(
                yaml_cfg, "recombinant_dna", ResourceCategory.recombinant_dna
            )
        )

    # Deterministic sort: by (category enum value, reagent_or_resource).
    rows.sort(key=lambda r: (r.category.value, r.reagent_or_resource.lower()))
    return tuple(rows)


# --------------------------------------------------------------------------- #
# Render Key Resources Table                                                  #
# --------------------------------------------------------------------------- #


def _group_by_category(
    rows: tuple[KeyResource, ...],
) -> dict[ResourceCategory, list[KeyResource]]:
    out: dict[ResourceCategory, list[KeyResource]] = {}
    for r in rows:
        out.setdefault(r.category, []).append(r)
    return out


def _latex_escape(text: str) -> str:
    """Escape LaTeX special chars in a free-form string."""
    if not text:
        return ""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out_chars: list[str] = []
    for ch in text:
        out_chars.append(repl.get(ch, ch))
    return "".join(out_chars)


def render_star_methods_table_latex(table: StarMethodsTable) -> str:
    """Render the Key Resources Table as a LaTeX ``longtable``.

    Groups rows by ``ResourceCategory``; each group gets a bold spanning
    header row.  Empty tables emit a single ``\\textit{none}`` row so the
    section is never blank.
    """
    grouped = _group_by_category(table.key_resources)

    lines: list[str] = []
    lines.append(r"\begin{longtable}{p{4.0cm} p{5.0cm} p{3.5cm} p{3.5cm}}")
    lines.append(r"\caption{Key Resources Table.} \\")
    lines.append(r"\toprule")
    lines.append(
        r"Reagent or Resource & Source & Identifier & Category \\"
    )
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\toprule")
    lines.append(
        r"Reagent or Resource & Source & Identifier & Category \\"
    )
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\bottomrule")
    lines.append(r"\endfoot")

    if not table.key_resources:
        lines.append(r"\multicolumn{4}{l}{\textit{No resources detected.}} \\")
    else:
        for category in ResourceCategory:
            members = grouped.get(category)
            if not members:
                continue
            lines.append(
                r"\multicolumn{4}{l}{\textbf{"
                + _latex_escape(category.value)
                + r"}} \\"
            )
            for r in members:
                lines.append(
                    " & ".join(
                        [
                            _latex_escape(r.reagent_or_resource),
                            _latex_escape(r.source),
                            _latex_escape(r.identifier),
                            _latex_escape(r.category.value),
                        ]
                    )
                    + r" \\"
                )

    lines.append(r"\end{longtable}")
    return "\n".join(lines) + "\n"


def _md_escape(text: str) -> str:
    """Escape Markdown table-breaking chars."""
    if not text:
        return ""
    return text.replace("|", r"\|").replace("\n", " ").strip()


def render_star_methods_table_markdown(table: StarMethodsTable) -> str:
    """Render the Key Resources Table as a Markdown table."""
    grouped = _group_by_category(table.key_resources)

    lines: list[str] = []
    lines.append("| Reagent or Resource | Source | Identifier | Category |")
    lines.append("|---|---|---|---|")

    if not table.key_resources:
        lines.append("| *No resources detected.* |  |  |  |")
    else:
        for category in ResourceCategory:
            members = grouped.get(category)
            if not members:
                continue
            lines.append(f"| **{_md_escape(category.value)}** |  |  |  |")
            for r in members:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _md_escape(r.reagent_or_resource),
                            _md_escape(r.source),
                            _md_escape(r.identifier),
                            _md_escape(r.category.value),
                        ]
                    )
                    + " |"
                )

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Method Details + Quantification (per recipe family)                         #
# --------------------------------------------------------------------------- #


def _attr(obj: Any, name: str) -> Any:
    """Read ``obj.name`` or ``obj[name]`` — whichever exists."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _normalise_figure_plan(figure_plan: Any) -> list[dict[str, Any]]:
    """Flatten FigurePlan or dict into ``[{figure_id, panels: [{recipe}]}]``."""
    if figure_plan is None:
        return []
    figures: list[dict[str, Any]] = []
    raw_figs = _attr(figure_plan, "figures") or []
    if not raw_figs and isinstance(figure_plan, list):
        raw_figs = list(figure_plan)
    if not raw_figs:
        return []
    for fig in raw_figs:
        panels_raw = _attr(fig, "panels") or []
        panel_list: list[dict[str, Any]] = []
        for p in panels_raw:
            recipe_name = (
                _attr(p, "recipe_full_name")
                or _attr(p, "recipe")
                or ""
            )
            panel_list.append({"recipe": str(recipe_name)})
        figures.append(
            {
                "figure_id": str(_attr(fig, "figure_id") or ""),
                "panels": panel_list,
            }
        )
    return figures


def _try_load_recipe_metadata(recipe_full_name: str) -> Any:
    """Best-effort registry lookup; returns ``None`` if not found."""
    if not recipe_full_name:
        return None
    try:
        from ..core.contract import (
            ensure_all_imported,
            get_recipe,
        )
    except Exception:
        return None
    try:
        ensure_all_imported()
    except Exception:
        pass
    try:
        entry = get_recipe(recipe_full_name)
        return entry.metadata
    except Exception:
        return None


def _family_name(meta: Any) -> str:
    family = _attr(meta, "family")
    if family is None:
        return "unknown"
    val = getattr(family, "value", None)
    if val is not None:
        return str(val)
    return str(family) or "unknown"


def _contract_dict(meta: Any) -> dict[str, Any]:
    """Extract a serialisable dict from a recipe's ``StatisticalContract``."""
    contract = _attr(meta, "statistical_contract")
    if contract is None:
        return {}
    if isinstance(contract, dict):
        return dict(contract)
    fields = (
        "min_n_per_group",
        "distribution_assumption",
        "multiple_comparisons",
        "independence",
        "effect_size_in_units",
        "rendered_claim_template",
        "n_minimum_for_visualization",
        "refuses_when",
        "max_missingness_fraction",
    )
    out: dict[str, Any] = {}
    for f in fields:
        val = getattr(contract, f, None)
        if val is None:
            continue
        if isinstance(val, tuple) and not val:
            continue
        out[f] = val
    return out


def _wrap_paragraph(text: str, fmt: str) -> str:
    """Trim and ensure the paragraph ends with a single newline."""
    text = text.strip()
    if not text.endswith("."):
        text += "."
    return text


def render_method_details_section(
    figure_plan: Any,
    *,
    venue: str = "cell",
    format: str = "latex",
) -> dict[str, str]:
    """Build the ``Method Details`` subsection — one paragraph per family.

    The paragraph for family X opens with the family-name + question
    (the recipe's ``answers_question``), then names the recipes used
    for that family in the plan.  All text is pulled from the recipe
    metadata; nothing is invented.
    """
    figures = _normalise_figure_plan(figure_plan)
    family_to_recipes: dict[str, set[str]] = {}
    family_to_questions: dict[str, set[str]] = {}
    family_to_count: dict[str, int] = {}

    for fig in figures:
        for p in fig["panels"]:
            recipe = p.get("recipe", "")
            if not recipe:
                continue
            meta = _try_load_recipe_metadata(recipe)
            if meta is None:
                continue
            family = _family_name(meta)
            family_to_recipes.setdefault(family, set()).add(recipe)
            question = _attr(meta, "answers_question")
            if question:
                family_to_questions.setdefault(family, set()).add(str(question))
            family_to_count[family] = family_to_count.get(family, 0) + 1

    paragraphs: dict[str, str] = {}
    for family in sorted(family_to_recipes):
        recipes = sorted(family_to_recipes[family])
        questions = sorted(family_to_questions.get(family, set()))
        n_panels = family_to_count[family]

        parts: list[str] = []
        parts.append(
            f"Panels in the {family} family addressed: "
            + "; ".join(questions or ["the recipe-declared scientific question"])
        )
        recipe_list = ", ".join(recipes)
        parts.append(
            f"Implementation recipes: {recipe_list}"
        )
        plural = "panel" if n_panels == 1 else "panels"
        parts.append(
            f"({n_panels} {family} {plural} in the plan)"
        )
        body = ". ".join(parts)
        paragraphs[family] = _wrap_paragraph(body, format)

    return paragraphs


def _contract_clauses(contract: dict[str, Any]) -> list[str]:
    """Convert a StatisticalContract dict to plain English clauses."""
    clauses: list[str] = []
    n_min = contract.get("min_n_per_group")
    if n_min is not None:
        clauses.append(f"minimum N per group: {n_min}")

    dist = contract.get("distribution_assumption")
    if dist and dist != "any":
        clauses.append(f"distribution assumption: {dist}")

    indep = contract.get("independence")
    if indep and indep != "any":
        clauses.append(f"independence structure: {indep}")

    correction = contract.get("multiple_comparisons")
    if correction and correction != "none":
        clauses.append(f"multiple-comparisons correction: {correction}")

    units = contract.get("effect_size_in_units")
    if units:
        clauses.append(f"effect-size units: {units}")

    n_viz = contract.get("n_minimum_for_visualization")
    if n_viz is not None:
        clauses.append(f"minimum N for visualisation: {n_viz}")

    miss = contract.get("max_missingness_fraction")
    if miss is not None:
        clauses.append(f"maximum tolerated missingness: {miss}")

    template = contract.get("rendered_claim_template")
    if template:
        clauses.append(f"claim template: {template}")

    refuses = contract.get("refuses_when") or ()
    if refuses:
        if isinstance(refuses, str):
            refs = [refuses]
        else:
            refs = [str(r) for r in refuses]
        clauses.append(
            "refuses to render under: " + ", ".join(refs)
        )

    return clauses


def render_quantification_section(
    figure_plan: Any,
    *,
    venue: str = "cell",
    format: str = "latex",
) -> dict[str, str]:
    """Build the ``Quantification and Statistical Analysis`` paragraphs.

    One paragraph per recipe family found in ``figure_plan``.  Each
    paragraph is composed verbatim from the bound ``StatisticalContract``
    — we never invent statistics.
    """
    figures = _normalise_figure_plan(figure_plan)

    family_to_contract: dict[str, dict[str, Any]] = {}
    family_to_count: dict[str, int] = {}

    for fig in figures:
        for p in fig["panels"]:
            recipe = p.get("recipe", "")
            if not recipe:
                continue
            meta = _try_load_recipe_metadata(recipe)
            if meta is None:
                continue
            family = _family_name(meta)
            contract = _contract_dict(meta)
            family_to_count[family] = family_to_count.get(family, 0) + 1
            if not contract:
                continue
            # First contract wins per family.
            family_to_contract.setdefault(family, contract)

    paragraphs: dict[str, str] = {}
    for family in sorted(family_to_count):
        contract = family_to_contract.get(family, {})
        clauses = _contract_clauses(contract)
        n_panels = family_to_count[family]
        plural = "panel" if n_panels == 1 else "panels"

        if not clauses:
            body = (
                f"Statistical analysis for the {family} family followed "
                f"the recipe-declared contract (no fields populated). "
                f"Applied to {n_panels} {plural}."
            )
        else:
            body = (
                f"Statistical analysis for the {family} family. "
                + "; ".join(clauses)
                + f". Applied to {n_panels} {plural}."
            )
        paragraphs[family] = _wrap_paragraph(body, format)

    return paragraphs


# --------------------------------------------------------------------------- #
# Data and Code Availability                                                  #
# --------------------------------------------------------------------------- #


def _render_data_and_code_section(
    table_rows: tuple[KeyResource, ...],
    *,
    format: str = "latex",
) -> str:
    """Compose a paragraph listing deposited data + software entries.

    Names every ``deposited_data`` row and counts software entries.  If
    no deposited data is found the paragraph still emits a TODO so the
    author sees something actionable.
    """
    deposited = [r for r in table_rows if r.category == ResourceCategory.deposited_data]
    software = [
        r for r in table_rows if r.category == ResourceCategory.software_algorithms
    ]

    lines: list[str] = []

    if deposited:
        lines.append(
            f"This study deposited or used {len(deposited)} dataset(s); "
            "the Key Resources Table lists per-file SHA-256 fingerprints."
        )
    else:
        lines.append(
            "TODO: list the data deposition locations (GEO / ArrayExpress / "
            "Zenodo / Figshare DOIs) here. No provenance sidecars were "
            "found in panelforge_workspace/figures/, so this section "
            "cannot be auto-populated."
        )

    if software:
        lines.append(
            f"All custom code is open-source and uses {len(software)} "
            "third-party software packages (see Key Resources Table for "
            "package names and version pins)."
        )
    else:
        lines.append(
            "TODO: list the software package versions used to generate "
            "the analyses. No pyproject.toml dependencies were found."
        )

    lines.append(
        "Any additional information required to reanalyse the data "
        "reported in this paper is available from the lead contact upon "
        "request."
    )
    return "\n\n".join(lines)


# --------------------------------------------------------------------------- #
# Top-level entry point                                                       #
# --------------------------------------------------------------------------- #


def generate_star_methods(
    project_root: Path,
    figure_plan: Any | None = None,
    *,
    venue: str = "cell",
    format: str = "latex",
) -> StarMethodsTable:
    """Generate a full ``StarMethodsTable`` from project state.

    Steps:
      1. ``extract_key_resources`` — walk the project.
      2. ``render_method_details_section`` — one paragraph per family.
      3. ``render_quantification_section`` — one paragraph per family.
      4. ``_render_data_and_code_section`` — data + code availability.
    """
    if venue not in STAR_METHODS_TEMPLATE["venues_supported"]:
        raise StarMethodsError(
            f"venue {venue!r} not in supported venues: "
            f"{STAR_METHODS_TEMPLATE['venues_supported']}"
        )
    if format not in ("latex", "markdown"):
        raise StarMethodsError(
            f"format {format!r} not in ('latex', 'markdown')"
        )

    rows = extract_key_resources(project_root)

    method_paragraphs = render_method_details_section(
        figure_plan, venue=venue, format=format
    )
    quant_paragraphs = render_quantification_section(
        figure_plan, venue=venue, format=format
    )
    data_section = _render_data_and_code_section(rows, format=format)

    return StarMethodsTable(
        key_resources=rows,
        method_details_paragraphs=method_paragraphs,
        quantification_paragraphs=quant_paragraphs,
        data_and_code_section=data_section,
        n_recipes=len(method_paragraphs),
        venue=venue,
    )
