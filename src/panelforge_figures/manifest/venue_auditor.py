"""Elevation 16 — pre-submission journal-fit auditor.

Audits a manuscript + figures package against a target venue's locked rules
(sourced from each journal's "Instructions to Authors") and emits a structured
Pass/Warn/Fail report.

The locked rule table :data:`VENUE_RULES` covers nine venues:

    - nature, cell, nejm, science, biorxiv, elife, plos_one, jama, plain

Each venue's :class:`VenueRules` record captures: maximum main figures /
tables, abstract format (free vs structured), word count caps, color mode
(rgb/cmyk/any), color-blind safety requirement, reference style, mandatory
statements (data availability, code availability, IRB/IACUC), and reporting-
checklist requirements (CONSORT for trials, ARRIVE for animals, STARD for
diagnostics).

The top-level entry point is :func:`audit_venue`, which:

    1. Parses the manuscript via :mod:`manuscript_parse` (E10)
    2. Looks up the rule set from :data:`VENUE_RULES`
    3. Applies each ``check_*`` function in turn
    4. Aggregates violations and emits an overall verdict
       (``ready_to_submit`` / ``needs_revision`` / ``blocked``)

The CLI wrapper (``figures audit-venue``) and CI runner integration
(``ci-audit --steps audit-venue``) round-trip through this same pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "Venue",
    "VenueRules",
    "RuleViolation",
    "RuleSeverity",
    "VenueAuditReport",
    "VenueAuditorError",
    "VENUE_RULES",
    "audit_venue",
    "render_venue_audit_markdown",
    "check_color_blind_safety",
    "check_figure_count",
    "check_word_counts",
    "check_abstract_structure",
    "check_data_availability_statement",
    "check_reference_style",
    "check_figure_extensions",
]


# --------------------------------------------------------------------------- #
# Enums                                                                       #
# --------------------------------------------------------------------------- #


class Venue(StrEnum):
    """Supported submission venues.

    ``plain`` is a no-op pseudo-venue used when the manuscript has no
    target journal yet (rules are universally ``None`` so every check
    short-circuits to ``info`` or passes silently).
    """

    plain = "plain"
    nature = "nature"
    cell = "cell"
    nejm = "nejm"
    biorxiv = "biorxiv"
    science = "science"
    elife = "elife"
    plos_one = "plos_one"
    jama = "jama"


class RuleSeverity(StrEnum):
    """Severity tier of a single :class:`RuleViolation`.

    ``error`` blocks submission, ``warning`` will be flagged by the journal
    but typically accepted, and ``info`` is purely advisory.
    """

    error = "error"
    warning = "warning"
    info = "info"


# --------------------------------------------------------------------------- #
# Dataclasses                                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class VenueRules:
    """Locked rules per venue. Sourced from the journal's 'Instructions to Authors'.

    ``None`` fields mean "no cap / no requirement"; the corresponding check
    is silently skipped.  Strings use the venue's own vocabulary ("vancouver",
    "harvard", "cell", "numbered") so downstream code can branch on style
    without re-encoding journal-specific quirks.
    """

    venue: Venue
    max_main_figures: int | None
    max_main_tables: int | None
    max_display_items: int | None      # combined figures+tables
    max_abstract_words: int | None
    abstract_format: str               # "free" / "structured" / "two-paragraph"
    abstract_structured_sections: tuple[str, ...] = ()
    max_intro_words: int | None = None
    max_discussion_words: int | None = None
    max_total_words: int | None = None
    color_mode: str = "any"            # "rgb" / "cmyk" / "any"
    figure_extensions_allowed: tuple[str, ...] = (".pdf", ".eps", ".tiff", ".png")
    min_figure_dpi: int = 300
    color_blind_safe_required: bool = False
    reference_style: str = "any"
    consort_required_for_trials: bool = False
    arrive_required_for_animals: bool = False
    stard_required_for_diagnostics: bool = False
    data_availability_required: bool = False
    code_availability_required: bool = False
    irb_statement_required: bool = False
    iacuc_statement_required: bool = False
    star_methods_required: bool = False
    supplementary_separate_required: bool = False
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleViolation:
    """A single rule failure / advisory.

    Attributes
    ----------
    rule_id
        Stable identifier, e.g. ``"max_main_figures"``.
    severity
        :class:`RuleSeverity` tier.
    actual_value
        What the audit observed in the manuscript.
    expected_value
        What the venue requires.
    location
        Human-readable pointer (``"manuscript / Abstract"`` /
        ``"Figure 5"`` / ``"panelforge_workspace/figures/figure_3.pdf"``).
    message
        One-line human description.
    remediation
        Optional suggested fix.
    """

    rule_id: str
    severity: RuleSeverity
    actual_value: Any
    expected_value: Any
    location: str
    message: str
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "location": self.location,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class VenueAuditReport:
    """End-to-end venue audit report.

    ``overall_verdict`` is computed from the worst severity in
    ``violations``:

      - ``"blocked"``         if any ``error``
      - ``"needs_revision"``  if any ``warning`` (no errors)
      - ``"ready_to_submit"`` if zero errors and zero warnings
    """

    venue: Venue
    manuscript_path: Path
    figures_dir: Path | None
    violations: tuple[RuleViolation, ...]
    n_errors: int
    n_warnings: int
    n_info: int
    rules_applied: int
    rules_passed: int
    rules_skipped: int
    overall_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue.value,
            "manuscript_path": str(self.manuscript_path),
            "figures_dir": str(self.figures_dir) if self.figures_dir is not None else None,
            "violations": [v.to_dict() for v in self.violations],
            "n_errors": self.n_errors,
            "n_warnings": self.n_warnings,
            "n_info": self.n_info,
            "rules_applied": self.rules_applied,
            "rules_passed": self.rules_passed,
            "rules_skipped": self.rules_skipped,
            "overall_verdict": self.overall_verdict,
        }


class VenueAuditorError(RuntimeError):
    """Raised on configuration errors before any check runs."""


# --------------------------------------------------------------------------- #
# Locked venue rules tables                                                    #
# --------------------------------------------------------------------------- #


VENUE_RULES: dict[Venue, VenueRules] = {
    Venue.nature: VenueRules(
        venue=Venue.nature,
        max_main_figures=5,
        max_main_tables=4,
        max_display_items=None,
        max_abstract_words=200,
        abstract_format="free",
        max_total_words=4500,
        color_mode="any",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="numbered",
        data_availability_required=True,
        code_availability_required=True,
        notes=(
            "Nature limits main figures to 5 + 4 tables (combined max may "
            "vary by article type). Abstract: 200 words, no structured sections. "
            "Reference style: numbered, in order of appearance.",
        ),
    ),
    Venue.cell: VenueRules(
        venue=Venue.cell,
        max_main_figures=7,
        max_main_tables=None,
        max_display_items=7,
        max_abstract_words=150,
        abstract_format="free",
        max_total_words=8000,
        color_mode="any",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="cell",
        star_methods_required=True,
        data_availability_required=True,
        code_availability_required=True,
        notes=(
            "Cell requires STAR Methods + Key Resources Table. Display items "
            "capped at 7. Abstract: 150 words.",
        ),
    ),
    Venue.nejm: VenueRules(
        venue=Venue.nejm,
        max_main_figures=6,
        max_main_tables=6,
        max_display_items=6,
        max_abstract_words=250,
        abstract_format="structured",
        abstract_structured_sections=("Background", "Methods", "Results", "Conclusions"),
        color_mode="cmyk",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="vancouver",
        consort_required_for_trials=True,
        irb_statement_required=True,
        data_availability_required=True,
        notes=(
            "NEJM requires structured abstract (Background/Methods/Results/"
            "Conclusions, 250 words total). CONSORT diagram required for "
            "clinical trials. CMYK color mode for print.",
        ),
    ),
    Venue.science: VenueRules(
        venue=Venue.science,
        max_main_figures=6,
        max_main_tables=None,
        max_display_items=6,
        max_abstract_words=125,
        abstract_format="free",
        max_total_words=2500,
        color_mode="any",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="numbered",
        data_availability_required=True,
        code_availability_required=True,
        notes=(
            "Science: 125-word abstract; 4-6 display items; single Materials "
            "and Methods section.",
        ),
    ),
    Venue.biorxiv: VenueRules(
        venue=Venue.biorxiv,
        max_main_figures=None,
        max_main_tables=None,
        max_display_items=None,
        max_abstract_words=300,
        abstract_format="free",
        max_total_words=None,
        color_mode="any",
        min_figure_dpi=150,
        color_blind_safe_required=False,
        reference_style="any",
        notes=("biorxiv preprint server: no hard caps. Recommended <= 300-word abstract.",),
    ),
    Venue.elife: VenueRules(
        venue=Venue.elife,
        max_main_figures=8,
        max_main_tables=None,
        max_display_items=None,
        max_abstract_words=150,
        abstract_format="free",
        max_total_words=None,
        color_mode="any",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="harvard",
        data_availability_required=True,
        code_availability_required=True,
        notes=("eLife: open code + data required. Up to 8 main figures.",),
    ),
    Venue.plos_one: VenueRules(
        venue=Venue.plos_one,
        max_main_figures=None,
        max_main_tables=None,
        max_display_items=None,
        max_abstract_words=300,
        abstract_format="free",
        color_mode="rgb",
        min_figure_dpi=300,
        color_blind_safe_required=False,
        reference_style="vancouver",
        data_availability_required=True,
        code_availability_required=True,
        notes=("PLOS ONE: data availability + code availability mandatory.",),
    ),
    Venue.jama: VenueRules(
        venue=Venue.jama,
        max_main_figures=6,
        max_main_tables=6,
        max_display_items=6,
        max_abstract_words=350,
        abstract_format="structured",
        abstract_structured_sections=(
            "Importance",
            "Objective",
            "Design, Setting, and Participants",
            "Main Outcomes and Measures",
            "Results",
            "Conclusions and Relevance",
        ),
        color_mode="cmyk",
        min_figure_dpi=300,
        color_blind_safe_required=True,
        reference_style="vancouver",
        consort_required_for_trials=True,
        stard_required_for_diagnostics=True,
        irb_statement_required=True,
        data_availability_required=True,
        notes=("JAMA: 6-section structured abstract (350 words).",),
    ),
    Venue.plain: VenueRules(
        venue=Venue.plain,
        max_main_figures=None,
        max_main_tables=None,
        max_display_items=None,
        max_abstract_words=None,
        abstract_format="free",
        notes=("Plain article: no venue-specific rules.",),
    ),
}


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _word_count(text: str) -> int:
    """Count non-whitespace tokens.  Strips LaTeX command tokens crudely."""
    cleaned = re.sub(r"\\[A-Za-z]+\*?(?:\{[^}]*\})?", " ", text)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    return len([t for t in cleaned.split() if t.strip()])


def _extract_abstract(manuscript_text: str) -> str | None:
    """Extract abstract body from LaTeX or markdown source.

    Looks for ``\\begin{abstract}...\\end{abstract}`` (LaTeX) or a
    section heading named "Abstract" (markdown / generic) — robust to
    case and missing punctuation.  Returns ``None`` when no abstract
    can be located.
    """
    m = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
        manuscript_text,
        re.DOTALL,
    )
    if m is not None:
        return m.group(1).strip()

    lines = manuscript_text.splitlines()
    n = len(lines)
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue
        if re.match(r"^#{1,6}\s+abstract\s*$", stripped, re.IGNORECASE) or \
                re.match(r"^abstract\s*$", stripped, re.IGNORECASE):
            body: list[str] = []
            for j in range(i + 1, n):
                if re.match(r"^#{1,6}\s+\S", lines[j].strip()):
                    break
                if re.match(r"^\\section\b", lines[j].strip()):
                    break
                body.append(lines[j])
            text = "\n".join(body).strip()
            if text:
                return text
    return None


# --------------------------------------------------------------------------- #
# Individual checks                                                            #
# --------------------------------------------------------------------------- #


def check_figure_count(
    rules: VenueRules,
    *,
    n_main_figures: int,
    n_main_tables: int,
) -> tuple[RuleViolation, ...]:
    """Cap figures/tables/display items per venue.

    Emits ``error`` violations for any cap that is exceeded.  Skips
    silently for caps set to ``None`` (e.g. biorxiv).
    """
    violations: list[RuleViolation] = []
    if rules.max_main_figures is not None and n_main_figures > rules.max_main_figures:
        violations.append(
            RuleViolation(
                rule_id="max_main_figures",
                severity=RuleSeverity.error,
                actual_value=n_main_figures,
                expected_value=f"<= {rules.max_main_figures}",
                location="manuscript / figure blocks",
                message=(
                    f"{rules.venue.value} caps main figures at {rules.max_main_figures}; "
                    f"manuscript has {n_main_figures}."
                ),
                remediation=(
                    f"Move {n_main_figures - rules.max_main_figures} figure(s) "
                    "to Extended Data / Supplementary Information."
                ),
            )
        )
    if rules.max_main_tables is not None and n_main_tables > rules.max_main_tables:
        violations.append(
            RuleViolation(
                rule_id="max_main_tables",
                severity=RuleSeverity.error,
                actual_value=n_main_tables,
                expected_value=f"<= {rules.max_main_tables}",
                location="manuscript / table blocks",
                message=(
                    f"{rules.venue.value} caps main tables at {rules.max_main_tables}; "
                    f"manuscript has {n_main_tables}."
                ),
                remediation=(
                    f"Move {n_main_tables - rules.max_main_tables} table(s) "
                    "to Supplementary Information."
                ),
            )
        )
    if rules.max_display_items is not None:
        total = n_main_figures + n_main_tables
        if total > rules.max_display_items:
            violations.append(
                RuleViolation(
                    rule_id="max_display_items",
                    severity=RuleSeverity.error,
                    actual_value=total,
                    expected_value=f"<= {rules.max_display_items}",
                    location="manuscript / display items",
                    message=(
                        f"{rules.venue.value} caps display items (figures+tables) "
                        f"at {rules.max_display_items}; manuscript has {total}."
                    ),
                    remediation=(
                        "Combine related panels into multi-panel figures or "
                        "demote items to supplementary."
                    ),
                )
            )
    return tuple(violations)


def check_word_counts(
    rules: VenueRules,
    *,
    abstract_words: int | None,
    total_words: int | None = None,
) -> tuple[RuleViolation, ...]:
    """Abstract word count + total word count.

    ``abstract_words=None`` means "no abstract found" — emits a warning
    when the venue requires one (i.e. ``max_abstract_words`` is set).
    """
    violations: list[RuleViolation] = []

    if rules.max_abstract_words is not None:
        if abstract_words is None:
            violations.append(
                RuleViolation(
                    rule_id="abstract_missing",
                    severity=RuleSeverity.warning,
                    actual_value=None,
                    expected_value=f"<= {rules.max_abstract_words} words",
                    location="manuscript / Abstract",
                    message=(
                        f"{rules.venue.value} requires an abstract "
                        f"(<= {rules.max_abstract_words} words); none detected."
                    ),
                    remediation="Add a \\begin{abstract}...\\end{abstract} block.",
                )
            )
        elif abstract_words > rules.max_abstract_words:
            violations.append(
                RuleViolation(
                    rule_id="max_abstract_words",
                    severity=RuleSeverity.error,
                    actual_value=abstract_words,
                    expected_value=f"<= {rules.max_abstract_words}",
                    location="manuscript / Abstract",
                    message=(
                        f"Abstract has {abstract_words} words; "
                        f"{rules.venue.value} caps at {rules.max_abstract_words}."
                    ),
                    remediation=(
                        f"Trim {abstract_words - rules.max_abstract_words} word(s) "
                        "from the abstract."
                    ),
                )
            )

    if rules.max_total_words is not None and total_words is not None:
        if total_words > rules.max_total_words:
            violations.append(
                RuleViolation(
                    rule_id="max_total_words",
                    severity=RuleSeverity.warning,
                    actual_value=total_words,
                    expected_value=f"<= {rules.max_total_words}",
                    location="manuscript / total body",
                    message=(
                        f"Manuscript body is {total_words} words; "
                        f"{rules.venue.value} target is <= {rules.max_total_words}."
                    ),
                    remediation=(
                        f"Trim approximately {total_words - rules.max_total_words} "
                        "words from the body."
                    ),
                )
            )

    return tuple(violations)


def check_abstract_structure(
    rules: VenueRules,
    abstract_text: str,
) -> tuple[RuleViolation, ...]:
    """For structured-abstract venues, verify required subsections exist.

    Looks for each required section name as a case-insensitive substring
    of the abstract text (so ``Background:``, ``Background.``, and
    ``\\textbf{Background}`` all match).  Returns empty for free-format
    venues.
    """
    if rules.abstract_format != "structured":
        return ()
    if not rules.abstract_structured_sections:
        return ()
    if not abstract_text:
        return (
            RuleViolation(
                rule_id="abstract_structure_missing",
                severity=RuleSeverity.error,
                actual_value=None,
                expected_value=list(rules.abstract_structured_sections),
                location="manuscript / Abstract",
                message=(
                    f"{rules.venue.value} requires a structured abstract; "
                    "no abstract text found."
                ),
                remediation=(
                    f"Add a structured abstract with sections: "
                    f"{', '.join(rules.abstract_structured_sections)}."
                ),
            ),
        )

    body_lower = abstract_text.lower()
    missing: list[str] = []
    for section in rules.abstract_structured_sections:
        if section.lower() not in body_lower:
            missing.append(section)

    if not missing:
        return ()

    return (
        RuleViolation(
            rule_id="abstract_structure_incomplete",
            severity=RuleSeverity.error,
            actual_value=list(missing),
            expected_value=list(rules.abstract_structured_sections),
            location="manuscript / Abstract",
            message=(
                f"{rules.venue.value} requires structured-abstract sections "
                f"({', '.join(rules.abstract_structured_sections)}); "
                f"missing: {', '.join(missing)}."
            ),
            remediation=(
                "Add the missing section header(s) to the abstract body "
                "(e.g. '\\textbf{Background:}' or 'Background:')."
            ),
        ),
    )


# Heuristic Brettel/Vienot 1999 simplified deuteranopia simulator + Delta-E.
# We avoid taking PIL as a hard dependency; the check is best-effort.
def _simulate_deuteranopia_delta(image_rgb: Any) -> float:
    """Estimate mean RGB delta between original and deuteranopia simulation.

    Returns the mean per-pixel L1 delta divided by 255 (normalised 0..1).
    A low value (< 0.04) suggests the figure relies heavily on red-green
    channels that are confused under deuteranopia.

    ``image_rgb`` is an ``(H, W, 3)`` numpy array; ``numpy`` is assumed
    available (it is a hard dependency of panelforge-figures).
    """
    import numpy as np

    rgb = np.asarray(image_rgb, dtype=np.float32) / 255.0
    # Brettel/Vienot 1999 simplified deuteranope projection in LMS.
    rgb_to_lms = np.array(
        [
            [17.8824, 43.5161, 4.11935],
            [3.45565, 27.1554, 3.86714],
            [0.0299566, 0.184309, 1.46709],
        ],
        dtype=np.float32,
    )
    lms_to_rgb = np.linalg.inv(rgb_to_lms)
    deuteranope = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.494207, 0.0, 1.24827],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    lms = rgb @ rgb_to_lms.T
    lms_sim = lms @ deuteranope.T
    rgb_sim = lms_sim @ lms_to_rgb.T
    rgb_sim = np.clip(rgb_sim, 0.0, 1.0)
    delta = np.mean(np.abs(rgb - rgb_sim))
    return float(delta)


def check_color_blind_safety(
    figures_dir: Path,
    *,
    extensions: tuple[str, ...] = (".pdf", ".png", ".svg"),
) -> tuple[RuleViolation, ...]:
    """Scan rendered figure files for color-blind-unsafe palettes.

    Heuristic:

    - For ``.png`` figures: load via PIL, simulate deuteranopia per the
      Brettel/Vienot 1999 model, compute mean RGB delta. Figures with
      delta below 0.02 are flagged as potentially relying on red-green
      contrast.
    - For ``.pdf`` / ``.svg``: emit an ``info``-level violation noting
      that the check could not be performed (no rasterisation here).

    This is intentionally conservative — the check only fires when the
    figure is *very* close to its deuteranope projection, indicating
    near-monochrome red-green dominance.  False negatives are expected.
    """
    if not figures_dir.exists() or not figures_dir.is_dir():
        return (
            RuleViolation(
                rule_id="color_blind_check_skipped",
                severity=RuleSeverity.info,
                actual_value=str(figures_dir),
                expected_value="existing directory",
                location=str(figures_dir),
                message=f"figures directory does not exist: {figures_dir}",
                remediation="",
            ),
        )

    violations: list[RuleViolation] = []
    try:
        from PIL import Image  # type: ignore[import-not-found]

        _have_pil = True
    except ImportError:
        Image = None  # type: ignore[assignment]
        _have_pil = False

    files = sorted(figures_dir.rglob("*"))
    for fp in files:
        if not fp.is_file():
            continue
        ext = fp.suffix.lower()
        if ext not in extensions:
            continue
        if ext == ".png":
            if not _have_pil:
                violations.append(
                    RuleViolation(
                        rule_id="color_blind_check_skipped",
                        severity=RuleSeverity.info,
                        actual_value="no-PIL",
                        expected_value="pillow installed",
                        location=str(fp),
                        message=(
                            "Pillow not installed; cannot assess color-blind safety "
                            f"of {fp.name}."
                        ),
                        remediation="pip install pillow",
                    )
                )
                continue
            try:
                import numpy as np

                with Image.open(fp) as im:
                    rgb = im.convert("RGB")
                    arr = np.asarray(rgb)
                delta = _simulate_deuteranopia_delta(arr)
            except Exception as exc:  # noqa: BLE001 — per-file sandbox
                violations.append(
                    RuleViolation(
                        rule_id="color_blind_check_skipped",
                        severity=RuleSeverity.info,
                        actual_value=str(exc),
                        expected_value="readable PNG",
                        location=str(fp),
                        message=f"could not read {fp.name}: {exc}",
                        remediation="",
                    )
                )
                continue
            if delta < 0.02:
                violations.append(
                    RuleViolation(
                        rule_id="color_blind_unsafe",
                        severity=RuleSeverity.warning,
                        actual_value=round(delta, 4),
                        expected_value=">= 0.02",
                        location=str(fp),
                        message=(
                            f"{fp.name} may rely on red-green contrast "
                            f"(deuteranope delta = {delta:.4f})."
                        ),
                        remediation=(
                            "Switch to a color-blind-safe palette "
                            "(viridis / cividis / Wong 2011)."
                        ),
                    )
                )
        else:
            violations.append(
                RuleViolation(
                    rule_id="color_blind_check_skipped",
                    severity=RuleSeverity.info,
                    actual_value=ext,
                    expected_value=".png (for rasterised check)",
                    location=str(fp),
                    message=(
                        f"cannot assess color-blind safety for {fp.suffix} files "
                        "(vector input; render to PNG first)."
                    ),
                    remediation="",
                )
            )
    return tuple(violations)


_DATA_AVAILABILITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdata\s+availability\b", re.IGNORECASE),
    re.compile(r"\bavailability\s+of\s+data\b", re.IGNORECASE),
    re.compile(r"\bdata\s+are\s+available\b", re.IGNORECASE),
    re.compile(r"\bdata\s+have\s+been\s+deposited\b", re.IGNORECASE),
)
_CODE_AVAILABILITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bcode\s+availability\b", re.IGNORECASE),
    re.compile(r"\bavailability\s+of\s+code\b", re.IGNORECASE),
    re.compile(r"\bsource\s+code\s+(?:is|are|has\s+been)\s+available\b", re.IGNORECASE),
)
_IRB_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bIRB\b"),
    re.compile(r"\binstitutional\s+review\s+board\b", re.IGNORECASE),
    re.compile(r"\bethics\s+committee\b", re.IGNORECASE),
    re.compile(r"\bapproved\s+by\s+the\s+ethics\b", re.IGNORECASE),
)
_IACUC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bIACUC\b"),
    re.compile(r"\banimal\s+care\s+and\s+use\s+committee\b", re.IGNORECASE),
    re.compile(r"\banimal\s+ethics\b", re.IGNORECASE),
)


def check_data_availability_statement(
    rules: VenueRules,
    manuscript_text: str,
) -> tuple[RuleViolation, ...]:
    """Scan manuscript for required statements.

    Looks for data availability, code availability, IRB approval, and
    IACUC approval keywords.  Each missing statement that the venue
    requires becomes an ``error``.
    """
    violations: list[RuleViolation] = []

    if rules.data_availability_required:
        if not any(p.search(manuscript_text) for p in _DATA_AVAILABILITY_PATTERNS):
            violations.append(
                RuleViolation(
                    rule_id="data_availability_missing",
                    severity=RuleSeverity.error,
                    actual_value="absent",
                    expected_value="present",
                    location="manuscript / Data Availability",
                    message=(
                        f"{rules.venue.value} requires a Data Availability statement; "
                        "none detected."
                    ),
                    remediation=(
                        "Add a 'Data Availability' section/paragraph identifying "
                        "where the underlying data are deposited."
                    ),
                )
            )
    if rules.code_availability_required:
        if not any(p.search(manuscript_text) for p in _CODE_AVAILABILITY_PATTERNS):
            violations.append(
                RuleViolation(
                    rule_id="code_availability_missing",
                    severity=RuleSeverity.error,
                    actual_value="absent",
                    expected_value="present",
                    location="manuscript / Code Availability",
                    message=(
                        f"{rules.venue.value} requires a Code Availability statement; "
                        "none detected."
                    ),
                    remediation=(
                        "Add a 'Code Availability' section/paragraph with a URL / DOI "
                        "to the analysis code."
                    ),
                )
            )
    if rules.irb_statement_required:
        if not any(p.search(manuscript_text) for p in _IRB_PATTERNS):
            violations.append(
                RuleViolation(
                    rule_id="irb_statement_missing",
                    severity=RuleSeverity.error,
                    actual_value="absent",
                    expected_value="present",
                    location="manuscript / Methods",
                    message=(
                        f"{rules.venue.value} requires an IRB / ethics-committee "
                        "approval statement; none detected."
                    ),
                    remediation=(
                        "Add IRB / ethics-committee approval information to the "
                        "Methods section."
                    ),
                )
            )
    if rules.iacuc_statement_required:
        if not any(p.search(manuscript_text) for p in _IACUC_PATTERNS):
            violations.append(
                RuleViolation(
                    rule_id="iacuc_statement_missing",
                    severity=RuleSeverity.error,
                    actual_value="absent",
                    expected_value="present",
                    location="manuscript / Methods",
                    message=(
                        f"{rules.venue.value} requires an IACUC / animal-ethics "
                        "approval statement; none detected."
                    ),
                    remediation=(
                        "Add IACUC / animal-ethics approval information to the "
                        "Methods section."
                    ),
                )
            )
    return tuple(violations)


_NUMBERED_CITATION = re.compile(r"\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]")
_AUTHOR_YEAR_CITATION = re.compile(
    r"\(\s*(?:[A-Z][a-zA-Z'\-]+(?:\s+et\s+al\.?)?|[A-Z][a-zA-Z'\-]+\s+(?:and|&)\s+"
    r"[A-Z][a-zA-Z'\-]+)\s*,?\s*(?:19|20)\d{2}[a-z]?\s*\)"
)
_LATEX_CITE = re.compile(r"\\cite[a-zA-Z]*\b")


def check_reference_style(
    rules: VenueRules,
    manuscript_text: str,
    *,
    bib_path: Path | None = None,
) -> tuple[RuleViolation, ...]:
    """Detect citation style and compare against the venue's expectation.

    Heuristic detection:
      - ``numbered``      : presence of ``[1]``, ``[2]``, ``[3-5]`` etc.
      - ``author-year``   : presence of ``(Smith, 2020)`` /
                            ``(Smith and Jones, 2020)`` patterns
      - LaTeX ``\\cite``  : style is determined by the bibliography style
                            (we cannot fully resolve it here; emit info)

    When the manuscript's detected style does not match the venue's
    ``reference_style``, emit a ``warning``.  Style ``any`` always passes.
    """
    # ``bib_path`` is accepted for forward compatibility (full .bib parsing
    # is out of scope for v1).  It is intentionally unused here.
    del bib_path

    if rules.reference_style == "any":
        return ()

    n_numbered = len(_NUMBERED_CITATION.findall(manuscript_text))
    n_authoryear = len(_AUTHOR_YEAR_CITATION.findall(manuscript_text))
    n_latex_cite = len(_LATEX_CITE.findall(manuscript_text))

    if n_numbered == 0 and n_authoryear == 0 and n_latex_cite == 0:
        return (
            RuleViolation(
                rule_id="reference_style_unknown",
                severity=RuleSeverity.info,
                actual_value="no citations detected",
                expected_value=rules.reference_style,
                location="manuscript / citations",
                message="no citations detected; cannot verify reference style.",
                remediation="",
            ),
        )

    detected: str
    if n_numbered > n_authoryear:
        detected = "numbered"
    elif n_authoryear > n_numbered:
        detected = "author-year"
    else:
        detected = "latex-cite"

    expected = rules.reference_style
    # cell, harvard, vancouver: map onto numbered / author-year for comparison.
    expected_kind: str
    if expected in ("numbered", "vancouver"):
        expected_kind = "numbered"
    elif expected in ("harvard", "cell"):
        expected_kind = "author-year"
    else:
        expected_kind = expected

    if detected == "latex-cite":
        return (
            RuleViolation(
                rule_id="reference_style_latex",
                severity=RuleSeverity.info,
                actual_value="latex \\cite{...}",
                expected_value=expected,
                location="manuscript / citations",
                message=(
                    "Manuscript uses \\cite{...}; final rendered style depends on "
                    "the bibliography style — cannot fully verify here."
                ),
                remediation=(
                    f"Ensure your .bst / biblatex style produces {expected} citations."
                ),
            ),
        )

    if detected != expected_kind:
        return (
            RuleViolation(
                rule_id="reference_style_mismatch",
                severity=RuleSeverity.warning,
                actual_value=detected,
                expected_value=expected,
                location="manuscript / citations",
                message=(
                    f"Citations look like '{detected}' but {rules.venue.value} "
                    f"expects '{expected}'."
                ),
                remediation=(
                    f"Switch to a {expected} citation style "
                    "(adjust \\bibliographystyle or rewrite inline citations)."
                ),
            ),
        )

    return ()


def check_figure_extensions(
    rules: VenueRules,
    figures_dir: Path,
) -> tuple[RuleViolation, ...]:
    """All rendered figures use allowed extensions for the venue.

    Files outside ``figure_extensions_allowed`` become ``error``
    violations.  Hidden files (dotfiles) and non-figure asset directories
    (e.g. ``.cache/``) are ignored.
    """
    if not figures_dir.exists() or not figures_dir.is_dir():
        return ()
    allowed = {e.lower() for e in rules.figure_extensions_allowed}
    # Common non-figure extensions we always permit at the file level
    # (these are likely captions, metadata, intermediate artifacts).
    benign = {".txt", ".md", ".yaml", ".yml", ".json", ".log"}

    violations: list[RuleViolation] = []
    for fp in sorted(figures_dir.rglob("*")):
        if not fp.is_file():
            continue
        if fp.name.startswith("."):
            continue
        ext = fp.suffix.lower()
        if ext in allowed or ext in benign:
            continue
        if ext == "":
            continue
        violations.append(
            RuleViolation(
                rule_id="figure_extension_disallowed",
                severity=RuleSeverity.error,
                actual_value=ext,
                expected_value=sorted(allowed),
                location=str(fp),
                message=(
                    f"{fp.name} has extension '{ext}' which is not in "
                    f"{rules.venue.value}'s allowed list: "
                    f"{sorted(allowed)}."
                ),
                remediation=(
                    f"Re-export {fp.name} as one of {sorted(allowed)}."
                ),
            )
        )
    return tuple(violations)


# --------------------------------------------------------------------------- #
# Top-level pipeline                                                           #
# --------------------------------------------------------------------------- #


def _coerce_venue(venue: Venue | str) -> Venue:
    if isinstance(venue, Venue):
        return venue
    try:
        return Venue(venue)
    except ValueError as exc:
        raise VenueAuditorError(
            f"unknown venue: {venue!r}; expected one of "
            f"{[v.value for v in Venue]}"
        ) from exc


def _count_figures_from_manuscript(manuscript) -> tuple[int, int]:
    """Return (n_main_figures, n_main_tables) inferred from the parser.

    The parser populates ``figure_blocks``; we treat each entry as a main
    figure unless its ``figure_id`` starts with ``"supp"`` / ``"sup"`` /
    ``"ext"`` (Extended Data) / ``"s"`` followed by a digit.
    """
    n_fig = 0
    for b in manuscript.figure_blocks:
        fid = (b.figure_id or "").lower()
        # Strip a "fig:" prefix if present.
        if fid.startswith("fig:"):
            fid = fid[4:]
        if fid.startswith(("supp", "sup", "ext", "extdata", "extended")):
            continue
        if re.match(r"^s\d", fid):
            continue
        n_fig += 1
    # Table detection: not currently exposed by the parser; we count
    # \begin{table} occurrences directly from the raw text.
    n_tab = 0
    try:
        text = Path(manuscript.path).read_text(encoding="utf-8")
        n_tab = len(re.findall(r"\\begin\{table\*?\}", text))
        n_tab += len(re.findall(r"^\|.*\|\s*$", text, re.MULTILINE)) // 4
    except OSError:
        n_tab = 0
    return n_fig, n_tab


def audit_venue(
    manuscript_path: Path,
    *,
    venue: Venue | str,
    figures_dir: Path | None = None,
    bib_path: Path | None = None,
    n_main_figures: int | None = None,
    n_main_tables: int | None = None,
) -> VenueAuditReport:
    """End-to-end venue audit.

    1. Parses ``manuscript_path`` via :mod:`manuscript_parse` (E10).
    2. Looks up the rule set from :data:`VENUE_RULES`.
    3. Applies each ``check_*`` function in turn, sandboxing each
       behind a per-check try/except so one failure does not abort
       the chain.
    4. Aggregates the resulting violations into a
       :class:`VenueAuditReport` and computes ``overall_verdict``.

    Parameters
    ----------
    manuscript_path
        Path to the manuscript (.tex / .md).
    venue
        :class:`Venue` value or its string name.
    figures_dir
        Optional path to the rendered figures directory.  When
        ``None``, figure-related checks are skipped silently.
    bib_path
        Optional path to a BibTeX file.  Reserved for future use.
    n_main_figures
        Override the auto-counted main-figure count.
    n_main_tables
        Override the auto-counted main-table count.

    Returns
    -------
    VenueAuditReport
    """
    from panelforge_figures.manifest.manuscript_parse import (
        ManuscriptParseError,
        parse_manuscript,
    )

    venue_enum = _coerce_venue(venue)
    rules = VENUE_RULES[venue_enum]

    if not manuscript_path.exists():
        raise VenueAuditorError(f"manuscript not found: {manuscript_path}")

    try:
        manuscript = parse_manuscript(manuscript_path)
    except ManuscriptParseError as exc:
        raise VenueAuditorError(f"failed to parse manuscript: {exc}") from exc

    manuscript_text = manuscript_path.read_text(encoding="utf-8")

    if n_main_figures is None:
        n_fig, n_tab_auto = _count_figures_from_manuscript(manuscript)
        n_main_figures = n_fig
        if n_main_tables is None:
            n_main_tables = n_tab_auto
    if n_main_tables is None:
        n_main_tables = 0

    abstract_text = _extract_abstract(manuscript_text) or ""
    abstract_words = _word_count(abstract_text) if abstract_text else None
    total_words = manuscript.n_words

    all_violations: list[RuleViolation] = []
    rules_applied = 0
    rules_skipped = 0

    # ── check_figure_count ────────────────────────────────────────────
    if (
        rules.max_main_figures is not None
        or rules.max_main_tables is not None
        or rules.max_display_items is not None
    ):
        rules_applied += 1
        all_violations.extend(
            check_figure_count(
                rules,
                n_main_figures=n_main_figures,
                n_main_tables=n_main_tables,
            )
        )
    else:
        rules_skipped += 1

    # ── check_word_counts ─────────────────────────────────────────────
    if rules.max_abstract_words is not None or rules.max_total_words is not None:
        rules_applied += 1
        all_violations.extend(
            check_word_counts(
                rules,
                abstract_words=abstract_words,
                total_words=total_words,
            )
        )
    else:
        rules_skipped += 1

    # ── check_abstract_structure ──────────────────────────────────────
    if rules.abstract_format == "structured":
        rules_applied += 1
        all_violations.extend(check_abstract_structure(rules, abstract_text))
    else:
        rules_skipped += 1

    # ── check_data_availability_statement ────────────────────────────
    if (
        rules.data_availability_required
        or rules.code_availability_required
        or rules.irb_statement_required
        or rules.iacuc_statement_required
    ):
        rules_applied += 1
        all_violations.extend(
            check_data_availability_statement(rules, manuscript_text)
        )
    else:
        rules_skipped += 1

    # ── check_reference_style ─────────────────────────────────────────
    if rules.reference_style != "any":
        rules_applied += 1
        all_violations.extend(
            check_reference_style(rules, manuscript_text, bib_path=bib_path)
        )
    else:
        rules_skipped += 1

    # ── check_figure_extensions ───────────────────────────────────────
    if figures_dir is not None:
        rules_applied += 1
        all_violations.extend(check_figure_extensions(rules, figures_dir))
    else:
        rules_skipped += 1

    # ── check_color_blind_safety ──────────────────────────────────────
    if rules.color_blind_safe_required and figures_dir is not None:
        rules_applied += 1
        all_violations.extend(
            check_color_blind_safety(figures_dir, extensions=(".pdf", ".png", ".svg"))
        )
    else:
        rules_skipped += 1

    # ── STAR Methods (Cell-specific) ──────────────────────────────────
    if rules.star_methods_required:
        rules_applied += 1
        if not manuscript.has_star_methods:
            all_violations.append(
                RuleViolation(
                    rule_id="star_methods_missing",
                    severity=RuleSeverity.error,
                    actual_value=False,
                    expected_value=True,
                    location="manuscript / STAR Methods",
                    message=(
                        f"{rules.venue.value} requires STAR Methods "
                        "(no 'STAR Methods' section detected)."
                    ),
                    remediation=(
                        "Add a 'STAR Methods' section with a Key Resources Table."
                    ),
                )
            )
    else:
        rules_skipped += 1

    # ── Tally + verdict ───────────────────────────────────────────────
    n_errors = sum(1 for v in all_violations if v.severity == RuleSeverity.error)
    n_warnings = sum(1 for v in all_violations if v.severity == RuleSeverity.warning)
    n_info = sum(1 for v in all_violations if v.severity == RuleSeverity.info)
    rules_passed = max(rules_applied - n_errors - n_warnings, 0)

    if n_errors > 0:
        verdict = "blocked"
    elif n_warnings > 0:
        verdict = "needs_revision"
    else:
        verdict = "ready_to_submit"

    return VenueAuditReport(
        venue=venue_enum,
        manuscript_path=manuscript_path,
        figures_dir=figures_dir,
        violations=tuple(all_violations),
        n_errors=n_errors,
        n_warnings=n_warnings,
        n_info=n_info,
        rules_applied=rules_applied,
        rules_passed=rules_passed,
        rules_skipped=rules_skipped,
        overall_verdict=verdict,
    )


# --------------------------------------------------------------------------- #
# Markdown renderer                                                            #
# --------------------------------------------------------------------------- #


_VERDICT_BADGE: dict[str, str] = {
    "ready_to_submit": "READY TO SUBMIT",
    "needs_revision": "NEEDS REVISION",
    "blocked": "BLOCKED",
}


def render_venue_audit_markdown(report: VenueAuditReport) -> str:
    """Human-readable markdown grouped by severity, with remediation hints."""
    lines: list[str] = []
    lines.append(f"# Venue Audit Report — {report.venue.value}")
    lines.append("")
    lines.append(f"- Manuscript: `{report.manuscript_path}`")
    if report.figures_dir is not None:
        lines.append(f"- Figures directory: `{report.figures_dir}`")
    lines.append(f"- Overall verdict: **{_VERDICT_BADGE.get(report.overall_verdict, report.overall_verdict)}**")
    lines.append(
        f"- Rules applied: {report.rules_applied} "
        f"(passed: {report.rules_passed}, skipped: {report.rules_skipped})"
    )
    lines.append(
        f"- Findings: {report.n_errors} error(s), "
        f"{report.n_warnings} warning(s), {report.n_info} info."
    )
    lines.append("")

    venue_rules = VENUE_RULES[report.venue]
    if venue_rules.notes:
        lines.append("## Venue notes")
        lines.append("")
        for n in venue_rules.notes:
            lines.append(f"> {n}")
        lines.append("")

    for sev_label, sev in (
        ("Errors", RuleSeverity.error),
        ("Warnings", RuleSeverity.warning),
        ("Info", RuleSeverity.info),
    ):
        items = [v for v in report.violations if v.severity == sev]
        if not items:
            continue
        lines.append(f"## {sev_label} ({len(items)})")
        lines.append("")
        for v in items:
            lines.append(f"### `{v.rule_id}` — {v.location}")
            lines.append("")
            lines.append(f"- {v.message}")
            lines.append(f"- Actual: `{v.actual_value}`")
            lines.append(f"- Expected: `{v.expected_value}`")
            if v.remediation:
                lines.append(f"- Remediation: {v.remediation}")
            lines.append("")

    if (
        report.n_errors == 0
        and report.n_warnings == 0
        and report.n_info == 0
    ):
        lines.append("All applicable venue rules passed.")
        lines.append("")
    return "\n".join(lines)
