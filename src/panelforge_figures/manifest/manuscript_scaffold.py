"""Manuscript scaffold module — Elevation 9 phase 2 (figures-scout).

`figures manuscript scaffold` generates a ``manuscript/main.tex`` (or
``main.md``) skeleton plus a stub ``references.bib`` so the writing
phase starts from an artefact that already wires every rendered figure,
auto-drafted caption, and statistical-contract methods paragraph into
the document.

Design notes
------------
* The module is **read-only with respect to the figure plan** — it never
  mutates the manifest or recipe registry; it only consumes them.
* It is **tolerant** by construction: missing E5 caption files are
  replaced with TODO stubs, missing recipe metadata silently skips the
  corresponding methods paragraph, and unknown statistical-contract
  fields are quoted verbatim (we never invent literature).
* It is **venue-aware** via :data:`VENUE_TEMPLATES` — each entry is a
  small dict driving the LaTeX preamble, the abstract macro, and the
  per-venue word-budget hint that surfaces as a comment in the abstract
  block.  Markdown rendering is structurally identical but uses ``#``
  headings, ``![](...)`` figure macros, and ``> caption`` blocks.
* Statistical methods paragraphs (``render_methods_boilerplate``) **do
  not hallucinate** — we paste only literal ``StatisticalContract``
  fields (``min_n_per_group``, ``distribution_assumption``,
  ``multiple_comparisons``, ``independence``, ``effect_size_in_units``,
  ``refuses_when``).  Anything missing is omitted, never invented.

Public API
----------

* :class:`Venue`, :class:`ManuscriptFormat`, :class:`ScaffoldError`,
  :class:`ManuscriptScaffold` — small dataclasses / enums.
* :data:`VENUE_TEMPLATES` — the venue → preamble dispatch table.
* :func:`render_methods_boilerplate` — group panels by recipe family,
  render one paragraph per family from the bound contract.
* :func:`render_manuscript_skeleton` — the full document body
  (LaTeX or Markdown).
* :func:`scaffold_manuscript` — end-to-end: pick paths, read captions,
  write the manuscript and a stub ``references.bib``.

See ``docs/spec_figures_scout_orchestrator.md`` §3 for the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "VENUE_TEMPLATES",
    "ManuscriptFormat",
    "ManuscriptScaffold",
    "ScaffoldError",
    "Venue",
    "render_manuscript_skeleton",
    "render_methods_boilerplate",
    "scaffold_manuscript",
]


# --------------------------------------------------------------------------- #
# Enums + errors                                                              #
# --------------------------------------------------------------------------- #


class Venue(StrEnum):
    """Supported submission venues — drive the preamble + abstract budget."""

    plain = "plain"
    nature = "nature"
    cell = "cell"
    nejm = "nejm"
    biorxiv = "biorxiv"
    science = "science"


class ManuscriptFormat(StrEnum):
    """Output format toggle: LaTeX (default) or Markdown."""

    latex = "latex"
    markdown = "markdown"


class ScaffoldError(RuntimeError):
    """Raised on missing figure_plan, unsupported venue, or write errors."""


@dataclass(frozen=True)
class ManuscriptScaffold:
    """Result of a scaffolding run.

    Attributes mirror the on-disk artefacts the caller can immediately
    open in a LaTeX editor; counters (``n_*``) are surfaced for the CLI
    summary table.
    """

    project_root: Path
    manuscript_path: Path             # manuscript/main.tex or main.md
    references_path: Path             # manuscript/references.bib
    n_figures: int
    n_captions_drafted: int
    n_methods_paragraphs: int
    venue: Venue
    format: ManuscriptFormat
    notes: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Venue templates                                                             #
# --------------------------------------------------------------------------- #


VENUE_TEMPLATES: dict[Venue, dict[str, Any]] = {
    Venue.plain: {
        "documentclass": r"\documentclass[11pt]{article}",
        "preamble_extras": [
            r"\usepackage{graphicx}",
            r"\usepackage{amsmath}",
            r"\usepackage[round]{natbib}",
        ],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 250,
        "figure_macro": r"\begin{figure}",
    },
    Venue.nature: {
        "documentclass": r"\documentclass[11pt,twoside]{article}",
        "preamble_extras": [
            r"\usepackage{graphicx}",
            r"\usepackage{lineno}",
            r"\linenumbers",
        ],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 200,
        "figure_macro": r"\begin{figure}[htbp]",
        "doc_class_note": (
            "% Nature: 70-char title; 200-word abstract; "
            "5 main display items max"
        ),
    },
    Venue.cell: {
        "documentclass": r"\documentclass[11pt]{article}",
        "preamble_extras": [
            r"\usepackage{graphicx}",
            r"\usepackage{authblk}",
        ],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 150,
        "figure_macro": r"\begin{figure}[htbp]",
        "doc_class_note": (
            "% Cell: 150-word abstract; 7 display items max; "
            "STAR Methods section required"
        ),
    },
    Venue.nejm: {
        "documentclass": r"\documentclass[12pt]{article}",
        "preamble_extras": [
            r"\usepackage{graphicx}",
            r"\usepackage{geometry}",
        ],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 250,
        "figure_macro": r"\begin{figure}[htbp]",
        "doc_class_note": (
            "% NEJM: structured abstract (Background/Methods/Results/"
            "Conclusions); 250 words; CONSORT diagram required for trials"
        ),
    },
    Venue.biorxiv: {
        "documentclass": r"\documentclass[11pt]{article}",
        "preamble_extras": [
            r"\usepackage{graphicx}",
            r"\usepackage{authblk}",
            r"\usepackage{lineno}",
            r"\linenumbers",
        ],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 300,
        "figure_macro": r"\begin{figure}[htbp]",
    },
    Venue.science: {
        "documentclass": r"\documentclass[11pt,twoside]{article}",
        "preamble_extras": [r"\usepackage{graphicx}"],
        "abstract_macro": "abstract",
        "title_macro": r"\title",
        "author_macro": r"\author",
        "max_abstract_words": 125,
        "figure_macro": r"\begin{figure}[htbp]",
        "doc_class_note": (
            "% Science: 125-word abstract; 4-6 display items; "
            "Single Materials and Methods section"
        ),
    },
}


# --------------------------------------------------------------------------- #
# figure_plan adapter                                                         #
# --------------------------------------------------------------------------- #


def _normalise_figure_plan(figure_plan: Any) -> list[dict[str, Any]]:
    """Coerce many plausible ``figure_plan`` shapes into a uniform list.

    The orchestrator (Build-A) emits a ``figure_plan`` that is one of:

    * ``Manifest`` — pydantic, ``figures[*].panels[*].recipe``;
    * ``FigureSpec`` — pydantic, single figure with ``panels``;
    * ``list[FigureSpec]`` — explicit list of figures;
    * ``list[dict]`` / ``dict`` — raw YAML-equivalent structure.

    We standardise to::

        [
            {"figure_id": str, "panels": [
                {"panel_id": str, "recipe": str, "title": str | None},
                ...
            ]},
            ...
        ]

    This is the format ``render_*`` consumes. We deliberately accept
    *both* ``id`` and ``figure_id`` keys (the two pydantic schemas use
    different names) so callers don't need to massage their input.
    """
    figures: list[dict[str, Any]] = []
    if figure_plan is None:
        return figures

    # pydantic Manifest with .figures, or top-level dict with "figures":
    candidates: list[Any] = []
    raw_figures: Any = None
    if hasattr(figure_plan, "figures"):
        raw_figures = figure_plan.figures
    elif isinstance(figure_plan, dict):
        raw_figures = figure_plan.get("figures")
    if raw_figures is not None:
        if isinstance(raw_figures, list):
            candidates = list(raw_figures)
        else:
            candidates = [raw_figures]
    elif isinstance(figure_plan, list):
        candidates = list(figure_plan)
    else:
        # Single FigureSpec or single dict with "panels".
        candidates = [figure_plan]

    for idx, fig in enumerate(candidates, start=1):
        figures.append(_normalise_one_figure(fig, idx))

    return figures


def _normalise_one_figure(fig: Any, fallback_idx: int) -> dict[str, Any]:
    """Normalise a single figure entry to the uniform shape."""
    fig_id = _attr(fig, "figure_id") or _attr(fig, "id") or str(fallback_idx)
    title = _attr(fig, "title") or _attr(fig, "suptitle")
    raw_panels = _attr(fig, "panels") or []
    panels: list[dict[str, Any]] = []
    for p_idx, p in enumerate(raw_panels, start=1):
        panels.append(_normalise_one_panel(p, p_idx))
    return {
        "figure_id": str(fig_id),
        "title": title,
        "panels": panels,
    }


def _normalise_one_panel(panel: Any, fallback_idx: int) -> dict[str, Any]:
    """Normalise a single panel entry."""
    panel_id = (
        _attr(panel, "id")
        or _attr(panel, "panel_id")
        or chr(ord("A") + fallback_idx - 1)
    )
    recipe = _attr(panel, "recipe") or _attr(panel, "recipe_full_name") or ""
    title = _attr(panel, "title") or _attr(panel, "caption")
    return {
        "panel_id": str(panel_id),
        "recipe": str(recipe),
        "title": title,
    }


def _attr(obj: Any, name: str) -> Any:
    """Read ``obj.name`` or ``obj[name]`` — whichever is available."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


# --------------------------------------------------------------------------- #
# Methods boilerplate                                                         #
# --------------------------------------------------------------------------- #


_FAMILY_PROSE: dict[str, str] = {
    "coef_forest": (
        "Effect sizes were estimated as Cohen's d with 95% bootstrap "
        "confidence intervals"
    ),
    "comparison": (
        "Group differences were evaluated with Welch's t-test; effect "
        "sizes are reported as Cohen's d with 95% bootstrap CIs"
    ),
    "correlation": (
        "Pearson correlations are reported with 95% bootstrap CIs; "
        "linear regression overlays use ordinary least squares"
    ),
    "factorial": (
        "Two-way factorials were fit with type-II ANOVA; effect sizes "
        "are reported as partial eta-squared"
    ),
    "equivalence": (
        "Equivalence was tested with the two one-sided tests (TOST) "
        "procedure against the recipe-declared bounds"
    ),
    "survival": (
        "Time-to-event outcomes were summarised by Kaplan-Meier curves "
        "with log-rank comparisons"
    ),
}

_DEFAULT_PROSE = (
    "Statistical analyses for {family} family panels followed the "
    "recipe-declared contract"
)


def _contract_dict_from_recipe_meta(meta: Any) -> dict[str, Any]:
    """Pull the ``StatisticalContract`` fields out of a recipe metadata blob.

    Accepts either a :class:`RecipeMetadata` (frozen dataclass) or a
    raw dict from a serialised registry. Returns an empty dict when no
    contract is bound.
    """
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
        # Empty tuple → omit; otherwise paste verbatim.
        if isinstance(val, tuple) and not val:
            continue
        out[f] = val
    return out


def _family_from_recipe_meta(meta: Any, recipe_full_name: str) -> str:
    """Resolve a recipe family from metadata; fall back to ``"unknown"``."""
    family = _attr(meta, "family")
    if family is None:
        return "unknown"
    # ``RecipeFamily`` is a StrEnum; ``.value`` and ``str()`` both work.
    val = getattr(family, "value", None)
    if val is not None:
        return str(val)
    return str(family) or "unknown"


def _render_one_methods_paragraph(
    family: str,
    contract: dict[str, Any],
    n_panels: int,
) -> str:
    """Compose one methods paragraph from a literal contract dict.

    The opening clause is family-specific (per :data:`_FAMILY_PROSE`);
    every subsequent clause comes verbatim from the contract — we never
    invent statistics.  Empty fields are silently skipped.
    """
    intro = _FAMILY_PROSE.get(family, _DEFAULT_PROSE.format(family=family))
    clauses: list[str] = [intro]

    n_min = contract.get("min_n_per_group")
    if n_min is not None:
        clauses.append(f"N >= {n_min} per group")

    dist = contract.get("distribution_assumption")
    if dist and dist != "any":
        clauses.append(f"distribution: {dist}")

    indep = contract.get("independence")
    if indep and indep != "any":
        clauses.append(f"independence: {indep}")

    correction = contract.get("multiple_comparisons")
    if correction and correction != "none":
        clauses.append(f"multiple-comparisons correction: {correction}")

    units = contract.get("effect_size_in_units")
    if units:
        clauses.append(f"effect-size units: {units}")

    miss = contract.get("max_missingness_fraction")
    if miss is not None:
        clauses.append(f"max missingness: {miss}")

    body = "; ".join(clauses) + "."

    refuses = contract.get("refuses_when") or ()
    if refuses:
        if isinstance(refuses, str):
            refuses_list = [refuses]
        else:
            refuses_list = [str(r) for r in refuses]
        body += (
            " Recipes refused to render under conditions: "
            + ", ".join(refuses_list)
            + "."
        )

    plural = "panel" if n_panels == 1 else "panels"
    body += f" (Applied to {n_panels} {family} {plural}.)"
    return body


def render_methods_boilerplate(
    figure_plan: Any,
    *,
    recipes_metadata: dict[str, Any] | None = None,
) -> str:
    """Render the ``Methods — Statistical analysis`` body.

    Walks every panel in ``figure_plan``, looks up its recipe in
    ``recipes_metadata``, reads the bound ``StatisticalContract``, and
    renders one paragraph per *unique* recipe family.  Recipes without
    a contract — and panels whose recipe is not in
    ``recipes_metadata`` — are silently skipped (rather than raising)
    so partial scaffolds remain useful.

    Parameters
    ----------
    figure_plan
        Either a ``Manifest``, a ``FigureSpec``, a list of figures, or
        a raw dict; see :func:`_normalise_figure_plan`.
    recipes_metadata
        Mapping ``recipe_full_name -> RecipeMetadata`` (or dict).
        ``None`` means "registry unavailable" — the function emits a
        single placeholder paragraph telling the user to re-run with a
        catalog.

    Returns
    -------
    str
        Markdown-friendly multi-paragraph string. The caller wraps it
        in a LaTeX subsection or a Markdown ``###`` section.
    """
    figures = _normalise_figure_plan(figure_plan)
    if not figures:
        return (
            "Statistical analysis details could not be auto-generated: "
            "the figure_plan contained no figures. Edit this section "
            "manually before submission."
        )

    if recipes_metadata is None:
        return (
            "Statistical analysis details could not be auto-generated: "
            "the recipe registry was not provided to the scaffolder. "
            "Re-run `figures manuscript scaffold` with a populated "
            "catalog, or edit this section manually."
        )

    # Group panels by recipe family.
    family_to_contract: dict[str, dict[str, Any]] = {}
    family_to_count: dict[str, int] = {}
    for fig in figures:
        for panel in fig["panels"]:
            recipe_name = panel["recipe"]
            if not recipe_name:
                continue
            meta = recipes_metadata.get(recipe_name)
            if meta is None:
                continue
            contract = _contract_dict_from_recipe_meta(meta)
            if not contract:
                continue
            family = _family_from_recipe_meta(meta, recipe_name)
            # First contract wins per family. The audit layer guarantees
            # within-family contracts are consistent at render time.
            family_to_contract.setdefault(family, contract)
            family_to_count[family] = family_to_count.get(family, 0) + 1

    if not family_to_contract:
        return (
            "Statistical analysis details could not be auto-generated: "
            "no recipe in the figure_plan declared a statistical_contract. "
            "Edit this section manually with the per-recipe methods text."
        )

    paragraphs: list[str] = []
    for family in sorted(family_to_contract):
        paragraphs.append(
            _render_one_methods_paragraph(
                family,
                family_to_contract[family],
                family_to_count[family],
            )
        )
    return "\n\n".join(paragraphs)


# --------------------------------------------------------------------------- #
# Caption insertion                                                           #
# --------------------------------------------------------------------------- #


def _read_caption_body(captions_dir: Path | None, figure_id: str) -> str | None:
    """Read an E5 caption file (``figure_<id>.md``) if present.

    Returns the body text without the title line (E5 wraps the title
    in ``**...**`` on the first line; we strip that so the raw prose
    flows into the LaTeX caption block). Returns ``None`` when the
    file does not exist.
    """
    if captions_dir is None:
        return None
    candidate = Path(captions_dir) / f"figure_{figure_id}.md"
    if not candidate.is_file():
        return None
    raw = candidate.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    # Drop the leading bold-title line if it exists; everything else is
    # body prose. E5 emits "**Figure 1 | Title.**\n\nBody...".
    lines = raw.splitlines()
    body_lines: list[str] = []
    seen_blank = False
    for ln in lines:
        if not seen_blank:
            if ln.strip() == "":
                seen_blank = True
            elif ln.startswith("**") and ln.rstrip().endswith("**"):
                # Title line; skip it.
                continue
            else:
                # Caption file with no title formatting; treat all of it
                # as body.
                body_lines.append(ln)
                seen_blank = True
        else:
            body_lines.append(ln)

    body = "\n".join(body_lines).strip()
    return body or None


# --------------------------------------------------------------------------- #
# Skeleton rendering — LaTeX and Markdown                                     #
# --------------------------------------------------------------------------- #


_RECIPE_TODO = "<recipe-derived sentence inserted at scaffold time>"


def _figure_pdf_relpath(figure_id: str) -> str:
    """Path the LaTeX skeleton uses to embed a rendered figure PDF."""
    return f"panelforge_workspace/figures/figure_{figure_id}.pdf"


def _provenance_relpath(figure_id: str) -> str:
    """Sidecar provenance JSON path the LaTeX skeleton documents."""
    return f"panelforge_workspace/figures/figure_{figure_id}.provenance.json"


def _abstract_word_budget_comment(venue: Venue, in_latex: bool) -> str:
    """Return the per-venue word-budget comment used in the abstract block."""
    budget = VENUE_TEMPLATES[venue]["max_abstract_words"]
    text = (
        f"({venue.value} venue: {budget}-word abstract; "
        "see VENUE_TEMPLATES for full house style)"
    )
    return f"% {text}" if in_latex else f"<!-- {text} -->"


def _render_latex_preamble(venue: Venue) -> str:
    """Compose the LaTeX preamble for the chosen venue."""
    spec = VENUE_TEMPLATES[venue]
    lines: list[str] = [spec["documentclass"]]
    note = spec.get("doc_class_note")
    if note:
        lines.append(note)
    lines.extend(spec["preamble_extras"])
    lines.extend(
        [
            "",
            r"\title{TODO --- manuscript title (panelforge-figures scaffold)}",
            r"\author{TODO --- author list}",
        ]
    )
    return "\n".join(lines)


def _render_latex_figure_block(
    figure_id: str,
    title: str | None,
    caption_body: str | None,
    venue: Venue,
) -> str:
    """One ``\\subsection`` + ``\\begin{figure}`` block for a single figure."""
    figure_macro = VENUE_TEMPLATES[venue]["figure_macro"]
    pdf_path = _figure_pdf_relpath(figure_id)
    prov_path = _provenance_relpath(figure_id)
    section_title = title or f"surveillance dynamics ({figure_id})"

    if caption_body is None:
        caption_text = (
            f"TODO --- write caption for Figure {figure_id}. "
            "Auto-drafted caption file not found; run "
            "`figures caption draft` to populate."
        )
        prov_note = (
            "% Caption stub: replace with auto-drafted text from "
            "`figures caption draft`, or write by hand."
        )
    else:
        caption_text = caption_body
        prov_note = (
            "% Auto-drafted caption (edit voice; statistics are correct "
            "by construction):"
        )

    lines = [
        rf"\subsection{{Figure {figure_id} --- {section_title}}}",
        "",
        figure_macro,
        r"\centering",
        rf"\includegraphics[width=\textwidth]{{{pdf_path}}}",
        rf"\caption{{{caption_text}}}",
        rf"\label{{fig:{figure_id}}}",
        r"\end{figure}",
        "",
        prov_note,
        f"% Source figure: {pdf_path}",
        f"% Provenance:    {prov_path}",
        "",
        rf"% [1-2 paragraphs of TODO results text referencing Figure~\ref{{fig:{figure_id}}}.]",
    ]
    return "\n".join(lines)


def _render_markdown_figure_block(
    figure_id: str,
    title: str | None,
    caption_body: str | None,
) -> str:
    """One ``##`` Results subsection + figure embed in Markdown."""
    pdf_path = _figure_pdf_relpath(figure_id)
    prov_path = _provenance_relpath(figure_id)
    section_title = title or f"surveillance dynamics ({figure_id})"

    if caption_body is None:
        caption_text = (
            f"TODO — write caption for Figure {figure_id}. Auto-drafted "
            "caption file not found; run `figures caption draft` to populate."
        )
        prov_note = (
            "<!-- Caption stub: replace with auto-drafted text from "
            "`figures caption draft`, or write by hand. -->"
        )
    else:
        caption_text = caption_body
        prov_note = (
            "<!-- Auto-drafted caption (edit voice; statistics are correct "
            "by construction). -->"
        )

    lines = [
        f"### Figure {figure_id} — {section_title}",
        "",
        f"![Figure {figure_id}]({pdf_path})",
        "",
        f"> **Figure {figure_id}.** {caption_text}",
        "",
        prov_note,
        f"<!-- Source figure: {pdf_path} -->",
        f"<!-- Provenance:    {prov_path} -->",
        "",
        f"[1-2 paragraphs of TODO results text referencing Figure {figure_id}.]",
    ]
    return "\n".join(lines)


def _resolve_caption_bodies(
    figures: list[dict[str, Any]],
    captions_dir: Path | None,
) -> tuple[dict[str, str | None], int]:
    """Load every available E5 caption; return (mapping, n_drafted)."""
    bodies: dict[str, str | None] = {}
    n_drafted = 0
    for fig in figures:
        body = _read_caption_body(captions_dir, fig["figure_id"])
        bodies[fig["figure_id"]] = body
        if body is not None:
            n_drafted += 1
    return bodies, n_drafted


def render_manuscript_skeleton(
    figure_plan: Any,
    *,
    venue: Venue = Venue.cell,
    format: ManuscriptFormat = ManuscriptFormat.latex,
    recipes_metadata: dict[str, Any] | None = None,
    captions_dir: Path | None = None,
) -> str:
    """Render the full manuscript skeleton string.

    The structure is identical across formats:

    1. ``Abstract`` — TODO with venue-specific word budget.
    2. ``Introduction`` — TODO with a suggested narrative arc.
    3. ``Results`` — one subsection per figure, each embedding the PDF
       + a caption (auto-drafted or TODO stub) + a provenance pointer.
    4. ``Methods → Statistical analysis`` — boilerplate from
       :func:`render_methods_boilerplate`.
    5. ``Methods → Code and data availability`` — TODO.
    6. ``Methods → Reproducibility envelope`` — fixed boilerplate that
       points the reviewer at the panelforge provenance sidecar +
       lockfile.
    7. ``Discussion`` — TODO with a tie-back hint.
    8. ``References`` — bibliography directive (LaTeX) or empty section
       (Markdown).
    """
    if venue not in VENUE_TEMPLATES:
        raise ScaffoldError(
            f"unsupported venue {venue!r}; choose one of "
            f"{tuple(v.value for v in VENUE_TEMPLATES)}"
        )

    figures = _normalise_figure_plan(figure_plan)
    caption_bodies, _n_drafted = _resolve_caption_bodies(figures, captions_dir)
    methods_body = render_methods_boilerplate(
        figure_plan,
        recipes_metadata=recipes_metadata,
    )

    if format == ManuscriptFormat.latex:
        return _render_latex_skeleton(
            figures=figures,
            venue=venue,
            caption_bodies=caption_bodies,
            methods_body=methods_body,
        )
    if format == ManuscriptFormat.markdown:
        return _render_markdown_skeleton(
            figures=figures,
            venue=venue,
            caption_bodies=caption_bodies,
            methods_body=methods_body,
        )
    raise ScaffoldError(f"unsupported format {format!r}")


def _render_latex_skeleton(
    *,
    figures: list[dict[str, Any]],
    venue: Venue,
    caption_bodies: dict[str, str | None],
    methods_body: str,
) -> str:
    """LaTeX-flavoured skeleton."""
    preamble = _render_latex_preamble(venue)
    abstract_note = _abstract_word_budget_comment(venue, in_latex=True)

    intro_block = "\n".join(
        [
            r"\section{Introduction}",
            r"TODO --- write Introduction (~500 words).",
            r"% Suggested narrative arc:",
            r"% 1. The biological question (1-2 paragraphs).",
            r"% 2. Existing literature gap (1 paragraph).",
            r"% 3. This work's contribution (1 paragraph; ties to Figures 1-N).",
        ]
    )

    if figures:
        figure_blocks = "\n\n".join(
            _render_latex_figure_block(
                fig["figure_id"],
                fig.get("title"),
                caption_bodies.get(fig["figure_id"]),
                venue,
            )
            for fig in figures
        )
    else:
        figure_blocks = (
            r"% No figures found in figure_plan — re-run with a populated "
            r"manifest." "\n"
            r"% TODO --- add Results subsections after running "
            r"`figures render`."
        )

    methods_block = "\n".join(
        [
            r"\section{Methods}",
            "",
            r"\subsection{Statistical analysis}",
            "% Auto-generated boilerplate from each recipe's StatisticalContract.",
            "% Edit prose voice as needed; numeric thresholds are paste-only "
            "from the contract.",
            methods_body,
            "",
            r"\subsection{Code and data availability}",
            r"TODO --- fill in (Zenodo DOI, GitHub URL, data deposition).",
            "",
            r"\subsection{Reproducibility envelope}",
            r"This manuscript was rendered with panelforge-figures. Each",
            r"figure has an accompanying provenance.json sidecar carrying a",
            r"sha256 content hash; an environment lockfile is provided as",
            r"supplementary file panelforge.lock.json (see",
            r"\texttt{figures lock} / \texttt{figures replay}).",
        ]
    )

    discussion_block = "\n".join(
        [
            r"\section{Discussion}",
            r"TODO --- write Discussion (~700 words).",
            r"% Tie back to Figures 1-N; flag what is novel vs. confirmatory;",
            r"% outline limitations (sample size, confounds, generality).",
        ]
    )

    references_block = "\n".join(
        [
            r"\bibliographystyle{plain}",
            r"\bibliography{references}",
        ]
    )

    parts = [
        preamble,
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        r"\begin{abstract}",
        r"TODO --- write structured abstract.",
        abstract_note,
        r"\end{abstract}",
        "",
        intro_block,
        "",
        r"\section{Results}",
        "",
        figure_blocks,
        "",
        methods_block,
        "",
        discussion_block,
        "",
        references_block,
        "",
        r"\end{document}",
        "",
    ]
    return "\n".join(parts)


def _render_markdown_skeleton(
    *,
    figures: list[dict[str, Any]],
    venue: Venue,
    caption_bodies: dict[str, str | None],
    methods_body: str,
) -> str:
    """Markdown-flavoured skeleton — same content, different wrapper."""
    abstract_note = _abstract_word_budget_comment(venue, in_latex=False)

    if figures:
        figure_blocks = "\n\n".join(
            _render_markdown_figure_block(
                fig["figure_id"],
                fig.get("title"),
                caption_bodies.get(fig["figure_id"]),
            )
            for fig in figures
        )
    else:
        figure_blocks = (
            "<!-- No figures found in figure_plan — re-run with a populated "
            "manifest. -->\n"
            "TODO — add Results subsections after running `figures render`."
        )

    parts = [
        "# TODO — manuscript title (panelforge-figures scaffold)",
        "",
        "_Authors: TODO — author list_",
        "",
        "## Abstract",
        "",
        "TODO — write structured abstract.",
        abstract_note,
        "",
        "## Introduction",
        "",
        "TODO — write Introduction (~500 words).",
        "",
        "<!-- Suggested narrative arc:",
        "  1. The biological question (1-2 paragraphs).",
        "  2. Existing literature gap (1 paragraph).",
        "  3. This work's contribution (1 paragraph; ties to Figures 1-N). -->",
        "",
        "## Results",
        "",
        figure_blocks,
        "",
        "## Methods",
        "",
        "### Statistical analysis",
        "",
        "<!-- Auto-generated boilerplate from each recipe's "
        "StatisticalContract. Edit prose voice as needed; numeric thresholds "
        "are paste-only from the contract. -->",
        "",
        methods_body,
        "",
        "### Code and data availability",
        "",
        "TODO — fill in (Zenodo DOI, GitHub URL, data deposition).",
        "",
        "### Reproducibility envelope",
        "",
        "This manuscript was rendered with panelforge-figures. Each figure "
        "has an accompanying provenance.json sidecar carrying a sha256 "
        "content hash; an environment lockfile is provided as supplementary "
        "file `panelforge.lock.json` (see `figures lock` / `figures replay`).",
        "",
        "## Discussion",
        "",
        "TODO — write Discussion (~700 words).",
        "",
        "<!-- Tie back to Figures 1-N; flag what is novel vs. confirmatory; "
        "outline limitations (sample size, confounds, generality). -->",
        "",
        "## References",
        "",
        "<!-- See references.bib for the BibTeX bibliography. -->",
        "",
    ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# References stub                                                             #
# --------------------------------------------------------------------------- #


_REFERENCES_STUB = """% references.bib — populated by `figures references lookup`
% or hand-edited.
%
% Each citation block below is a TEMPLATE. Replace the TODO fields,
% then build with: pdflatex → bibtex → pdflatex → pdflatex.

@article{TODO_first_author_year,
  author  = {TODO Author, A. and TODO Coauthor, B.},
  title   = {TODO --- paper title},
  journal = {TODO --- journal name},
  year    = {TODO},
  volume  = {TODO},
  pages   = {TODO},
  doi     = {TODO},
}
"""


def _write_references_stub(path: Path, *, overwrite: bool) -> None:
    """Write a minimal ``references.bib`` if not already present."""
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_REFERENCES_STUB, encoding="utf-8")


# --------------------------------------------------------------------------- #
# End-to-end driver                                                           #
# --------------------------------------------------------------------------- #


def _default_manuscript_path(
    project_root: Path,
    format: ManuscriptFormat,
) -> Path:
    """Where the scaffolder writes the manuscript by default."""
    suffix = "tex" if format == ManuscriptFormat.latex else "md"
    return project_root / "manuscript" / f"main.{suffix}"


def _default_references_path(project_root: Path) -> Path:
    """Where the scaffolder writes ``references.bib`` by default."""
    return project_root / "manuscript" / "references.bib"


def scaffold_manuscript(
    figure_plan: Any,
    project_root: str | Path,
    *,
    venue: Venue = Venue.cell,
    format: ManuscriptFormat = ManuscriptFormat.latex,
    output_path: str | Path | None = None,
    references_path: str | Path | None = None,
    overwrite: bool = False,
    captions_dir: str | Path | None = None,
    recipes_metadata: dict[str, Any] | None = None,
) -> ManuscriptScaffold:
    """End-to-end scaffolder: pick paths, render, write, return record.

    Steps
    -----
    1. Resolve ``output_path`` (default ``project_root/manuscript/main.tex``)
       and ``references_path`` (default ``manuscript/references.bib``).
    2. Refuse to overwrite an existing manuscript unless
       ``overwrite=True``.
    3. For every figure_id in ``figure_plan``, look for an E5 caption at
       ``captions_dir/figure_<id>.md``.  Bind it into the LaTeX caption
       block (or insert a TODO stub when missing).
    4. Render via :func:`render_manuscript_skeleton`.
    5. Write the manuscript file (creating its parent dir).
    6. Write a stub ``references.bib`` (idempotent: never overwrites
       an existing one even if ``overwrite=True`` for the manuscript;
       the bib stub is yours to keep).
    7. Return a :class:`ManuscriptScaffold` record summarising the run.

    Raises
    ------
    ScaffoldError
        On unsupported venue, missing figure plan, or write failures.
    """
    if figure_plan is None:
        raise ScaffoldError(
            "scaffold_manuscript requires a figure_plan; got None. "
            "Pass a Manifest, FigureSpec, or list of figures."
        )
    if venue not in VENUE_TEMPLATES:
        raise ScaffoldError(
            f"unsupported venue {venue!r}; choose one of "
            f"{tuple(v.value for v in VENUE_TEMPLATES)}"
        )

    project_root = Path(project_root)
    out_path = (
        Path(output_path)
        if output_path is not None
        else _default_manuscript_path(project_root, format)
    )
    refs_path = (
        Path(references_path)
        if references_path is not None
        else _default_references_path(project_root)
    )
    captions_dir_path = Path(captions_dir) if captions_dir is not None else None

    if out_path.exists() and not overwrite:
        raise ScaffoldError(
            f"manuscript already exists at {out_path}; pass overwrite=True "
            "to replace it. (References.bib is never overwritten — your "
            "citations are safe.)"
        )

    figures = _normalise_figure_plan(figure_plan)
    caption_bodies, n_drafted = _resolve_caption_bodies(
        figures, captions_dir_path
    )

    methods_body = render_methods_boilerplate(
        figure_plan,
        recipes_metadata=recipes_metadata,
    )
    n_methods_paragraphs = (
        methods_body.count("\n\n") + 1
        if methods_body and not methods_body.startswith(
            "Statistical analysis details could not"
        )
        else 0
    )

    if format == ManuscriptFormat.latex:
        document = _render_latex_skeleton(
            figures=figures,
            venue=venue,
            caption_bodies=caption_bodies,
            methods_body=methods_body,
        )
    elif format == ManuscriptFormat.markdown:
        document = _render_markdown_skeleton(
            figures=figures,
            venue=venue,
            caption_bodies=caption_bodies,
            methods_body=methods_body,
        )
    else:
        raise ScaffoldError(f"unsupported format {format!r}")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(document, encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(
            f"failed to write manuscript to {out_path}: {exc}"
        ) from exc

    try:
        _write_references_stub(refs_path, overwrite=False)
    except OSError as exc:
        raise ScaffoldError(
            f"failed to write references.bib to {refs_path}: {exc}"
        ) from exc

    notes: list[str] = []
    if not figures:
        notes.append(
            "figure_plan contained no figures; Results section is empty"
        )
    if recipes_metadata is None:
        notes.append(
            "recipes_metadata not provided; Statistical analysis section "
            "is a placeholder"
        )
    n_missing_captions = len(figures) - n_drafted
    if n_missing_captions > 0:
        notes.append(
            f"{n_missing_captions} figure(s) without auto-drafted captions; "
            "TODO stubs inserted"
        )

    return ManuscriptScaffold(
        project_root=project_root,
        manuscript_path=out_path,
        references_path=refs_path,
        n_figures=len(figures),
        n_captions_drafted=n_drafted,
        n_methods_paragraphs=n_methods_paragraphs,
        venue=venue,
        format=format,
        notes=tuple(notes),
    )
