"""Figure-bias auditor (Elevation 17).

Audits *rendered* figures for visualization-honesty defects:

* truncated y-axes that exaggerate effects
* dual-y-axes that imply spurious relationships
* log scales applied to linear data (or vice-versa)
* missing CIs when the contract requires them
* sample-size annotations missing on underpowered figures
* underpowered findings not flagged in the caption
* 3D embellishments on inherently 2D data
* non-monotonic categorical orderings
* p-values without effect sizes
* color-blind-unsafe colormaps (``jet`` / ``rainbow`` family)

The auditor is **purely metadata-driven** — it never inspects pixels.
Every check reads the figure's ``<figure>.provenance.json`` sidecar
(see :mod:`panelforge_figures.manifest.provenance`) which carries the
recipe contract, the audit findings, and the data references.  When
the contract or audit dict is silent on a dimension, the check
gracefully skips rather than guessing.

The public API mirrors the venue-auditor (E16):

* :func:`audit_bias_for_figure` — audit a single sidecar.
* :func:`audit_bias_across_directory` — walk a directory of figures.
* :func:`render_bias_audit_markdown` — pretty-print a report.

Each individual check is also exposed so callers can run a tailored
subset (used by tests and by the CLI's ``--only`` flag).

Findings are emitted as :class:`BiasFinding` records, severity is one
of :class:`BiasSeverity` (``error`` / ``warning`` / ``info``), and the
overall verdict is one of ``"honest"`` / ``"needs_review"`` /
``"concerning"`` — exactly the trichotomy the CI runner exposes to the
PR comment.

See ``docs/spec_figure_bias_auditor.md`` for the design notes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "BiasFindingKind",
    "BiasSeverity",
    "BiasFinding",
    "BiasAuditReport",
    "BiasAuditorError",
    "audit_bias_for_figure",
    "audit_bias_across_directory",
    "render_bias_audit_markdown",
    "check_axis_truncation",
    "check_dual_axes",
    "check_scale_distribution_mismatch",
    "check_ci_omission_when_contract_requires",
    "check_sample_size_missing_when_under_min_n",
    "check_underpowered_unflagged",
    "check_color_encoding_without_colorbar",
    "check_3d_on_2d_data",
    "check_non_monotonic_ordinal_ordering",
    "check_p_value_threshold_only",
    "check_color_blind_unsafe",
]


# --------------------------------------------------------------------------- #
# Enums                                                                        #
# --------------------------------------------------------------------------- #


class BiasSeverity(StrEnum):
    """Triage band for a finding.

    * ``error`` — honest-reporting violation; figure should not ship.
    * ``warning`` — likely-misleading pattern; reviewer should look.
    * ``info`` — advisory only; non-blocking.
    """

    error = "error"
    warning = "warning"
    info = "info"


class BiasFindingKind(StrEnum):
    """Closed taxonomy of bias-finding kinds.

    Adding a new kind requires a new check function + entry in this enum;
    we deliberately do not accept free-form strings so reports stay
    consistent across runs.
    """

    truncated_y_axis = "truncated_y_axis"
    dual_y_axis = "dual_y_axis"
    log_on_linear_data = "log_on_linear_data"
    linear_on_log_data = "linear_on_log_data"
    ci_omitted = "ci_omitted"
    sample_size_missing = "sample_size_missing"
    underpowered_unflagged = "underpowered_unflagged"
    colorbar_missing = "colorbar_missing"
    three_d_effects = "three_d_effects"
    non_monotonic_categorical = "non_monotonic_categorical"
    p_value_threshold_only = "p_value_threshold_only"
    color_blind_unsafe = "color_blind_unsafe"


# --------------------------------------------------------------------------- #
# Dataclasses                                                                  #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BiasFinding:
    """A single finding about a figure (or one of its panels).

    Attributes
    ----------
    kind
        Discriminator from :class:`BiasFindingKind`.
    severity
        Triage band (:class:`BiasSeverity`).
    figure_id
        Canonical id of the figure, e.g. ``"Figure 1"``.  Derived from the
        provenance ``figure_path`` stem when possible.
    panel_id
        Sub-panel id (e.g. ``"Figure 1, panel A"``) or ``None`` when the
        finding applies to the whole figure.
    message
        Single human-readable sentence.  Suitable for both CLI stdout and
        the Markdown report.
    evidence
        Structured key/value bag of the values that triggered the check —
        useful for debugging or for re-checking outside the auditor.
    remediation
        Optional suggested fix.  Empty string when no canonical fix exists.
    location
        Optional provenance file path or recipe ``full_name`` — provides
        clickable context in the Markdown report.
    """

    kind: BiasFindingKind
    severity: BiasSeverity
    figure_id: str
    panel_id: str | None
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "figure_id": self.figure_id,
            "panel_id": self.panel_id,
            "message": self.message,
            "evidence": dict(self.evidence),
            "remediation": self.remediation,
            "location": self.location,
        }


@dataclass(frozen=True)
class BiasAuditReport:
    """End-to-end report for a directory walk.

    Attributes
    ----------
    audited_figures
        Tuple of figure_ids actually inspected (skipped ones are not
        included).
    findings
        Every :class:`BiasFinding` emitted by every check, in the order
        figures were encountered, then check order.
    n_errors, n_warnings, n_info
        Pre-computed counters so the PR-comment renderer doesn't have
        to re-scan.
    n_figures_inspected, n_figures_skipped
        Useful for "we audited X of Y figures" summary lines.
    overall_verdict
        Trichotomy:

        * ``"honest"`` — zero errors **and** zero warnings.
        * ``"needs_review"`` — warnings but no errors.
        * ``"concerning"`` — at least one error.
    """

    audited_figures: tuple[str, ...]
    findings: tuple[BiasFinding, ...]
    n_errors: int
    n_warnings: int
    n_info: int
    n_figures_inspected: int
    n_figures_skipped: int
    overall_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "audited_figures": list(self.audited_figures),
            "findings": [f.to_dict() for f in self.findings],
            "n_errors": self.n_errors,
            "n_warnings": self.n_warnings,
            "n_info": self.n_info,
            "n_figures_inspected": self.n_figures_inspected,
            "n_figures_skipped": self.n_figures_skipped,
            "overall_verdict": self.overall_verdict,
        }


class BiasAuditorError(RuntimeError):
    """Raised on auditor-level configuration problems (bad path, etc.)."""


# --------------------------------------------------------------------------- #
# Module-level constants                                                       #
# --------------------------------------------------------------------------- #


# Families where magnitude visualisations are common and a truncated
# axis materially distorts perception.  Free-form strings to keep us
# decoupled from the closed RecipeFamily enum.
_MAGNITUDE_FAMILIES: frozenset[str] = frozenset({
    "comparison",
    "factorial",
    "coef_forest",
    "sobol_bar",
    "split_violin",
})

# Families that strongly expect confidence-interval reporting when the
# explicit ``requires_ci`` flag is absent.
_CI_EXPECTED_FAMILIES: frozenset[str] = frozenset({
    "comparison",
    "coef_forest",
    "factorial",
    "equivalence",
    "split_violin",
})

# Families where CIs are optional (descriptive / curve-shape figures).
_CI_OPTIONAL_FAMILIES: frozenset[str] = frozenset({
    "descriptive",
    "diagnostic_curve",
    "heatmap",
    "phase_portrait",
    "ridge_by_group",
    "contour",
    "flow",
    "matrix",
    "radar",
    "gantt",
    "conceptual",
    "scatter_collapse",
    "ladder",
    "bifurcation",
    "hysteresis_loop",
    "timecourse_hierarchical_ci",
    "volcano",
})

# Known colour-blind-unsafe colormap names (matplotlib + numpy + some
# legacy R defaults).  Source: matplotlib v3.7 docs §"Choosing Colormaps".
_COLOR_BLIND_UNSAFE: frozenset[str] = frozenset({
    "jet",
    "rainbow",
    "hsv",
    "gist_rainbow",
    "ncar",
    "gist_ncar",
    "nipy_spectral",
})

# Known colour-blind-safe colormaps (perceptually uniform from viridis
# family + colour-blind-friendly qualitative palettes).
_COLOR_BLIND_SAFE: frozenset[str] = frozenset({
    "viridis",
    "cividis",
    "magma",
    "plasma",
    "inferno",
    "colorblind_friendly_palettes",
})

# Caption keywords that indicate the author acknowledged the
# underpowered status of the figure.  Matched case-insensitively against
# the rendered caption (if available).
_UNDERPOWERED_CAPTION_HINTS: tuple[str, ...] = (
    "underpowered",
    "preliminary",
    "limited sample size",
    "limited sample",
    "small sample",
    "exploratory",
    "tentative",
)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _figure_id_from_path(figure_path: str | Path) -> str:
    """Best-effort derivation of a "Figure N" id from a file path.

    Looks for the conventional ``figure_<n>[<sub>]`` stem; falls back to
    the path stem when no match.  Idempotent for paths produced by the
    rest of panelforge-figures.
    """
    stem = Path(figure_path).stem
    # Strip trailing ``.png``/``.pdf`` and the like if the caller passed
    # ``figure_1.png.provenance.json``.
    if stem.endswith(".png") or stem.endswith(".pdf"):
        stem = Path(stem).stem
    import re

    m = re.match(r"figure[_\-\s]*(\d+)([a-z]?)", stem.lower())
    if m:
        n = m.group(1)
        sub = m.group(2)
        return f"Figure {n}{sub.upper()}".strip()
    return stem


def _load_provenance(provenance_path: Path) -> dict[str, Any]:
    """Load and minimally validate a provenance.json sidecar."""
    if not provenance_path.is_file():
        raise BiasAuditorError(f"provenance file not found: {provenance_path}")
    try:
        data = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BiasAuditorError(
            f"provenance file is not valid JSON: {provenance_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise BiasAuditorError(
            f"provenance must be a JSON object: {provenance_path}"
        )
    return data


def _get_contract(provenance: dict[str, Any]) -> dict[str, Any]:
    """Extract the recipe contract dict from a provenance record.

    The contract may live at one of two locations (the sidecar evolved
    between schema 1.0 and 1.1):

    * ``recipe.contract`` (older sidecars)
    * top-level ``contract`` (newer sidecars from E17+)

    Returns an empty dict when neither is present.
    """
    recipe = provenance.get("recipe") or {}
    if isinstance(recipe, dict) and isinstance(recipe.get("contract"), dict):
        return recipe["contract"]
    top = provenance.get("contract")
    if isinstance(top, dict):
        return top
    return {}


def _get_statistical_contract(provenance: dict[str, Any]) -> dict[str, Any]:
    """Extract the statistical_contract dict from a provenance record."""
    recipe = provenance.get("recipe") or {}
    if isinstance(recipe, dict):
        sc = recipe.get("statistical_contract")
        if isinstance(sc, dict):
            return sc
    sc = provenance.get("statistical_contract")
    if isinstance(sc, dict):
        return sc
    return {}


def _get_audit_findings(provenance: dict[str, Any]) -> dict[str, Any]:
    """Extract audit_findings (key ``audit`` in the sidecar)."""
    audit = provenance.get("audit")
    if isinstance(audit, dict):
        return audit
    af = provenance.get("audit_findings")
    if isinstance(af, dict):
        return af
    return {}


def _get_family(provenance: dict[str, Any]) -> str:
    """Best-effort family extraction from contract / recipe metadata.

    Returns the empty string when no family signal is found — checks
    that depend on family then short-circuit to a safe no-op.
    """
    contract = _get_contract(provenance)
    fam = contract.get("family")
    if isinstance(fam, str) and fam:
        return fam.lower()
    recipe = provenance.get("recipe") or {}
    if isinstance(recipe, dict):
        fam = recipe.get("family")
        if isinstance(fam, str) and fam:
            return fam.lower()
        # Some sidecars stuff metadata under recipe.metadata
        meta = recipe.get("metadata")
        if isinstance(meta, dict):
            fam = meta.get("family")
            if isinstance(fam, str) and fam:
                return fam.lower()
    return ""


def _get_recipe_full_name(provenance: dict[str, Any]) -> str:
    recipe = provenance.get("recipe") or {}
    if isinstance(recipe, dict):
        fn = recipe.get("full_name")
        if isinstance(fn, str):
            return fn
    return ""


def _get_caption_text(provenance: dict[str, Any]) -> str:
    """Pull a caption string out of the sidecar if available.

    Looks at common keys (sidecar's metadata block, top-level ``caption``,
    rendered fields).  Lower-cased for case-insensitive matching.
    """
    for key in ("caption", "rendered_caption", "caption_text"):
        v = provenance.get(key)
        if isinstance(v, str):
            return v.lower()
    meta = provenance.get("metadata")
    if isinstance(meta, dict):
        for key in ("caption", "rendered_caption", "caption_text"):
            v = meta.get(key)
            if isinstance(v, str):
                return v.lower()
    return ""


# --------------------------------------------------------------------------- #
# Individual checks                                                            #
# --------------------------------------------------------------------------- #


def check_axis_truncation(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Flag y-axes that start above zero when data are strictly positive.

    Triggers only for magnitude-style families (bars, forests, sobol) —
    on time-series or scatter plots a non-zero baseline is normal.

    Emits a single :class:`BiasFinding` with severity ``warning`` when:

    * ``contract.y_axis_range`` (or ``y_axis_min``) is set and > 0;
    * the data minimum (from ``audit_findings.y_min`` or
      ``data_distribution_shape.y_min``) is strictly > 0;
    * the family is in :data:`_MAGNITUDE_FAMILIES`.
    """
    family = _get_family(provenance)
    if family and family not in _MAGNITUDE_FAMILIES:
        return []

    contract = _get_contract(provenance)
    audit = _get_audit_findings(provenance)

    # Axis min may live at a few canonical keys.
    axis_min: float | None = None
    yrange = contract.get("y_axis_range")
    if isinstance(yrange, (list, tuple)) and len(yrange) == 2:
        try:
            axis_min = float(yrange[0])
        except (TypeError, ValueError):
            axis_min = None
    if axis_min is None:
        v = contract.get("y_axis_min")
        if v is not None:
            try:
                axis_min = float(v)
            except (TypeError, ValueError):
                axis_min = None

    if axis_min is None or axis_min <= 0:
        return []

    # Data min may live under audit, or in a data_distribution_shape block.
    data_min: float | None = None
    for key in ("y_min", "data_min"):
        v = audit.get(key)
        if v is not None:
            try:
                data_min = float(v)
                break
            except (TypeError, ValueError):
                continue
    if data_min is None:
        shape = audit.get("data_distribution_shape")
        if isinstance(shape, dict):
            v = shape.get("y_min") or shape.get("min")
            if v is not None:
                try:
                    data_min = float(v)
                except (TypeError, ValueError):
                    data_min = None

    if data_min is None or data_min <= 0:
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.truncated_y_axis,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                f"y-axis starts at {axis_min} but data minimum is "
                f"{data_min} > 0 — visual exaggeration risk"
            ),
            evidence={
                "axis_min": axis_min,
                "data_min": data_min,
                "family": family,
            },
            remediation=(
                "Set the y-axis to start at 0 for magnitude comparisons, "
                "or break the axis explicitly with a zigzag marker."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_dual_axes(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Flag dual-y-axis figures pairing incompatible metrics.

    A dual-axis figure pairing (say) concentration on the left and time
    on the right invites visual correlation between two unrelated
    series; emit a warning unless both axes belong to the same
    measurement family (``concentration``, ``rate``, ``flux``, etc.).

    The compatibility check is conservative — when either axis lacks a
    declared family, the check skips.
    """
    contract = _get_contract(provenance)
    if not contract.get("dual_axes") and not contract.get("secondary_y_axis_label"):
        return []

    left_family = contract.get("y_axis_family") or contract.get("primary_y_axis_family")
    right_family = (
        contract.get("secondary_y_axis_family") or contract.get("right_y_axis_family")
    )

    if not left_family or not right_family:
        # Default permissive: dual axes alone aren't an automatic warning,
        # only when we can prove the families differ.
        if contract.get("dual_axes") or contract.get("secondary_y_axis_label"):
            return [
                BiasFinding(
                    kind=BiasFindingKind.dual_y_axis,
                    severity=BiasSeverity.warning,
                    figure_id=figure_id,
                    panel_id=None,
                    message=(
                        "dual y-axis present but axis families are not declared — "
                        "readers may infer a spurious relationship"
                    ),
                    evidence={
                        "secondary_y_axis_label": contract.get(
                            "secondary_y_axis_label"
                        ),
                        "dual_axes": bool(contract.get("dual_axes")),
                    },
                    remediation=(
                        "Either annotate both axes with their measurement "
                        "family or split the figure into two panels."
                    ),
                    location=_get_recipe_full_name(provenance),
                )
            ]
        return []

    if str(left_family).lower() == str(right_family).lower():
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.dual_y_axis,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                f"dual y-axis pairs incompatible metric families "
                f"({left_family!s} vs {right_family!s}) — readers may infer "
                f"a spurious relationship"
            ),
            evidence={
                "left_family": left_family,
                "right_family": right_family,
            },
            remediation=(
                "Split the two series into separate panels, or use "
                "small multiples sharing a single y-axis family."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_scale_distribution_mismatch(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Flag log/linear scale mismatched against the data's actual shape.

    Requires ``audit_findings.data_distribution_shape`` to be present;
    skips gracefully when missing (the field is new in this elevation
    and may be absent from older sidecars).

    Heuristic:

    * ``shape == "log_distributed"`` (or ``max/min > 100``) with a
      ``y_scale == "linear"`` axis → warning ``linear_on_log_data``.
    * ``shape == "linear_distributed"`` with a ``y_scale == "log"``
      axis → warning ``log_on_linear_data``.
    """
    audit = _get_audit_findings(provenance)
    shape = audit.get("data_distribution_shape")
    if not shape:
        return []

    contract = _get_contract(provenance)
    y_scale = (contract.get("y_scale") or "linear").lower()

    # Normalise both string shapes and dict shapes ({"max_over_min": 250.0}).
    shape_kind: str | None
    ratio: float | None = None
    if isinstance(shape, str):
        shape_kind = shape.lower()
    elif isinstance(shape, dict):
        shape_kind = (
            shape.get("kind")
            or shape.get("shape")
            or shape.get("distribution")
            or ""
        ).lower()
        for key in ("max_over_min", "ratio", "dynamic_range"):
            v = shape.get(key)
            if v is not None:
                try:
                    ratio = float(v)
                    break
                except (TypeError, ValueError):
                    continue
    else:
        return []

    is_log_distributed = shape_kind in ("log_distributed", "log", "heavy_tail") or (
        ratio is not None and ratio > 100.0
    )
    is_linear_distributed = shape_kind in ("linear_distributed", "linear", "uniform")

    findings: list[BiasFinding] = []
    if is_log_distributed and y_scale == "linear":
        findings.append(
            BiasFinding(
                kind=BiasFindingKind.linear_on_log_data,
                severity=BiasSeverity.warning,
                figure_id=figure_id,
                panel_id=None,
                message=(
                    "data span >2 decades but y-axis is linear — small "
                    "values are visually crushed against the baseline"
                ),
                evidence={
                    "shape": shape_kind,
                    "ratio": ratio,
                    "y_scale": y_scale,
                },
                remediation="Switch the y-axis to log scale.",
                location=_get_recipe_full_name(provenance),
            )
        )
    if is_linear_distributed and y_scale == "log":
        findings.append(
            BiasFinding(
                kind=BiasFindingKind.log_on_linear_data,
                severity=BiasSeverity.warning,
                figure_id=figure_id,
                panel_id=None,
                message=(
                    "data are linearly distributed but y-axis is log — "
                    "differences in the upper range are visually compressed"
                ),
                evidence={
                    "shape": shape_kind,
                    "y_scale": y_scale,
                },
                remediation="Switch the y-axis to linear scale.",
                location=_get_recipe_full_name(provenance),
            )
        )
    return findings


def check_ci_omission_when_contract_requires(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Flag missing CIs when the contract (explicitly or by family) needs them.

    Two paths:

    1. ``statistical_contract.requires_ci == True`` and no ``ci_lo`` /
       ``ci_hi`` / ``effect_size_ci`` key in audit_findings → severity
       ``error``.
    2. The recipe family is in :data:`_CI_EXPECTED_FAMILIES` and CI
       fields are missing → severity ``warning`` (inferred requirement).
    """
    audit = _get_audit_findings(provenance)
    sc = _get_statistical_contract(provenance)
    family = _get_family(provenance)

    def _has_ci() -> bool:
        for key in ("ci_lo", "ci_hi", "effect_size_ci", "ci", "ci_low", "ci_high"):
            if key in audit and audit[key] is not None:
                return True
        return False

    if sc.get("requires_ci") is True:
        if _has_ci():
            return []
        return [
            BiasFinding(
                kind=BiasFindingKind.ci_omitted,
                severity=BiasSeverity.error,
                figure_id=figure_id,
                panel_id=None,
                message=(
                    "statistical contract requires CI but audit findings "
                    "do not include ci_lo / ci_hi / effect_size_ci"
                ),
                evidence={"requires_ci": True, "family": family},
                remediation=(
                    "Bootstrap or analytic CIs are required by the "
                    "contract; emit them in audit_findings before render."
                ),
                location=_get_recipe_full_name(provenance),
            )
        ]

    # Inferred from family
    if family in _CI_EXPECTED_FAMILIES and not _has_ci():
        return [
            BiasFinding(
                kind=BiasFindingKind.ci_omitted,
                severity=BiasSeverity.warning,
                figure_id=figure_id,
                panel_id=None,
                message=(
                    f"family {family!r} strongly expects CIs but audit "
                    f"findings do not include ci_lo / ci_hi / effect_size_ci"
                ),
                evidence={"family": family, "requires_ci": False},
                remediation=(
                    "Either set ``requires_ci=True`` in the recipe's "
                    "statistical contract and emit CIs, or downgrade the "
                    "figure to a descriptive family."
                ),
                location=_get_recipe_full_name(provenance),
            )
        ]

    return []


def check_sample_size_missing_when_under_min_n(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Flag underpowered figures missing an explicit sample-size annotation.

    Triggers when:

    * ``statistical_contract.min_n_per_group`` is set,
    * ``audit_findings.n_per_group`` (or ``n_per_cell`` / ``n``) is
      strictly less than that minimum, AND
    * ``contract.sample_size_annotation`` is not ``True``.

    Severity ``error`` — both underpowered *and* unlabelled.
    """
    sc = _get_statistical_contract(provenance)
    audit = _get_audit_findings(provenance)
    contract = _get_contract(provenance)

    min_n = sc.get("min_n_per_group")
    if min_n is None:
        return []
    try:
        min_n_v = int(min_n)
    except (TypeError, ValueError):
        return []

    n: int | None = None
    for key in ("n_per_group", "n_per_cell", "n", "sample_size"):
        v = audit.get(key)
        if v is None:
            continue
        try:
            n = int(v)
            break
        except (TypeError, ValueError):
            continue
    if n is None or n >= min_n_v:
        return []

    if contract.get("sample_size_annotation") is True:
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.sample_size_missing,
            severity=BiasSeverity.error,
            figure_id=figure_id,
            panel_id=None,
            message=(
                f"sample size n={n} is below contract minimum "
                f"({min_n_v}) and no explicit sample-size annotation "
                "is declared"
            ),
            evidence={
                "n": n,
                "min_n_per_group": min_n_v,
                "sample_size_annotation": bool(
                    contract.get("sample_size_annotation")
                ),
            },
            remediation=(
                "Add ``sample_size_annotation: True`` to the recipe "
                "contract and overlay n-per-group labels on the panel."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_underpowered_unflagged(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Warn when an underpowered figure has no caption acknowledgement.

    Triggers when ``audit_findings.underpowered`` is truthy and none of
    the keywords in :data:`_UNDERPOWERED_CAPTION_HINTS` appear in the
    figure's caption text (read from provenance metadata when present).
    """
    audit = _get_audit_findings(provenance)
    if not audit.get("underpowered"):
        return []
    caption = _get_caption_text(provenance)
    if any(hint in caption for hint in _UNDERPOWERED_CAPTION_HINTS):
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.underpowered_unflagged,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                "audit flagged the figure as underpowered but the caption "
                "does not mention 'underpowered', 'preliminary', or "
                "'limited sample size'"
            ),
            evidence={
                "underpowered": True,
                "caption_present": bool(caption),
            },
            remediation=(
                "Add explicit language to the caption — e.g. "
                "'these results are preliminary owing to limited sample size'."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_color_encoding_without_colorbar(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Warn when a colormap-based panel lacks a colorbar.

    A heatmap / volcano / dot plot that encodes magnitude in colour
    without a colorbar makes the figure unreadable.  Triggers when:

    * the recipe family is in a colormap-using set, AND
    * ``contract.colorbar_present`` is explicitly ``False`` (we don't
      assume absence-means-missing — many recipes emit colorbars by
      default; only an explicit "off" should warn).
    """
    contract = _get_contract(provenance)
    family = _get_family(provenance)
    family_uses_colormap = family in {"heatmap", "volcano", "matrix", "contour"}
    recipe_full = _get_recipe_full_name(provenance).lower()
    if (
        not family_uses_colormap
        and "_heatmap" not in recipe_full
        and "_dot" not in recipe_full
        and "_volcano" not in recipe_full
    ):
        return []

    if contract.get("colorbar_present") is False:
        return [
            BiasFinding(
                kind=BiasFindingKind.colorbar_missing,
                severity=BiasSeverity.warning,
                figure_id=figure_id,
                panel_id=None,
                message=(
                    "panel encodes magnitude in colour but colorbar is "
                    "explicitly disabled — reader cannot decode values"
                ),
                evidence={
                    "family": family,
                    "colorbar_present": False,
                },
                remediation="Set ``colorbar_present=True`` in the recipe contract.",
                location=_get_recipe_full_name(provenance),
            )
        ]
    return []


def check_3d_on_2d_data(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Warn when 3D embellishments are used on inherently 2D data.

    Three-dimensional bars / pies / scatter on intrinsically 2D data
    distort perception (foreshortening, occlusion).  Triggers when:

    * ``contract.style_3d_effects == True`` OR the recipe ``full_name``
      contains ``3d_bar`` / ``pseudo3d`` / ``three_d_bar``;
    * the data are 2D — no ``z`` dimension in audit findings.
    """
    contract = _get_contract(provenance)
    audit = _get_audit_findings(provenance)
    recipe_full = _get_recipe_full_name(provenance).lower()

    is_3d_styled = (
        contract.get("style_3d_effects") is True
        or "3d_bar" in recipe_full
        or "pseudo3d" in recipe_full
        or "three_d_bar" in recipe_full
    )
    if not is_3d_styled:
        return []

    has_z_dim = (
        audit.get("z_dim_present") is True
        or "z_min" in audit
        or "z_max" in audit
        or audit.get("n_dimensions") == 3
    )
    if has_z_dim:
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.three_d_effects,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                "3D-styled rendering applied to 2D data — foreshortening "
                "and occlusion will distort perceived magnitudes"
            ),
            evidence={
                "style_3d_effects": bool(contract.get("style_3d_effects")),
                "recipe": recipe_full,
            },
            remediation="Render the same data in 2D (e.g. flat bar / scatter).",
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_non_monotonic_ordinal_ordering(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Inform when a categorical x-axis order is non-monotonic.

    Triggers (severity ``info``) when:

    * ``contract.x_categorical == True``,
    * ``contract.x_categorical_order`` is set, AND
    * the order does not match an alphabetical, numerical, or declared
      semantic ordering.
    """
    contract = _get_contract(provenance)
    if not contract.get("x_categorical"):
        return []

    order = contract.get("x_categorical_order")
    if not isinstance(order, (list, tuple)) or len(order) < 2:
        return []
    order_list = [str(x) for x in order]

    semantic = contract.get("semantic_ordering")
    if isinstance(semantic, (list, tuple)) and list(map(str, semantic)) == order_list:
        return []

    # Alphabetical?
    if order_list == sorted(order_list):
        return []
    if order_list == sorted(order_list, reverse=True):
        return []

    # Numerical?
    try:
        numeric = [float(x) for x in order_list]
        if numeric == sorted(numeric) or numeric == sorted(numeric, reverse=True):
            return []
    except (TypeError, ValueError):
        pass

    return [
        BiasFinding(
            kind=BiasFindingKind.non_monotonic_categorical,
            severity=BiasSeverity.info,
            figure_id=figure_id,
            panel_id=None,
            message=(
                "categorical x-axis ordering is neither alphabetical, "
                "numerical, nor semantic — readers may misread comparisons"
            ),
            evidence={"x_categorical_order": order_list},
            remediation=(
                "Either sort categories alphabetically/numerically or "
                "declare a semantic order via ``contract.semantic_ordering``."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_p_value_threshold_only(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Warn when a significant p-value is reported without an effect size.

    Honest-reporting guidance: every p < alpha should be accompanied by
    an effect-size estimate (Cohen's d, Hedges' g, odds ratio, etc.).
    Triggers when:

    * ``audit_findings.p_value < 0.05`` (or ``min_p_value``), AND
    * ``audit_findings.effect_size`` is missing / ``None``.
    """
    audit = _get_audit_findings(provenance)
    p: float | None = None
    for key in ("p_value", "min_p_value", "p"):
        v = audit.get(key)
        if v is None:
            continue
        try:
            p = float(v)
            break
        except (TypeError, ValueError):
            continue
    if p is None or p >= 0.05:
        return []

    es: Any | None = None
    for key in ("effect_size", "cohens_d", "hedges_g", "odds_ratio", "effect_d"):
        v = audit.get(key)
        if v is not None:
            es = v
            break
    if es is not None:
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.p_value_threshold_only,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                f"reported p={p:.4g} < 0.05 without an effect-size estimate "
                "— honest reporting requires effect size alongside p-values"
            ),
            evidence={"p_value": p, "effect_size": None},
            remediation=(
                "Emit ``effect_size`` (Cohen's d / Hedges' g / odds ratio) "
                "in audit_findings, and overlay it on the panel."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


def check_color_blind_unsafe(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Warn when the colormap is in the known-unsafe set.

    Triggers (severity ``warning``) when ``contract.colormap`` is in
    :data:`_COLOR_BLIND_UNSAFE`.  A figure on a colormap-using family
    with no colormap declared is silently skipped — we don't assume the
    default.
    """
    contract = _get_contract(provenance)
    cmap_raw = contract.get("colormap") or contract.get("cmap")
    if not isinstance(cmap_raw, str) or not cmap_raw:
        return []
    cmap = cmap_raw.lower()
    if cmap not in _COLOR_BLIND_UNSAFE:
        return []

    return [
        BiasFinding(
            kind=BiasFindingKind.color_blind_unsafe,
            severity=BiasSeverity.warning,
            figure_id=figure_id,
            panel_id=None,
            message=(
                f"colormap {cmap_raw!r} is not perceptually uniform and is "
                "unsafe for ~8% of male readers (red-green color-vision deficiency)"
            ),
            evidence={
                "colormap": cmap_raw,
                "safe_alternatives": sorted(_COLOR_BLIND_SAFE),
            },
            remediation=(
                f"Replace {cmap_raw!r} with a perceptually uniform map "
                "(viridis / cividis / magma / plasma / inferno)."
            ),
            location=_get_recipe_full_name(provenance),
        )
    ]


# --------------------------------------------------------------------------- #
# Aliases (spec-named entry points used in __all__)                           #
# --------------------------------------------------------------------------- #


# Spec uses a slightly different name for one check; provide an alias so
# both callers work.
def check_non_monotonic_categorical(
    provenance: dict[str, Any], figure_id: str
) -> list[BiasFinding]:
    """Alias for :func:`check_non_monotonic_ordinal_ordering`."""
    return check_non_monotonic_ordinal_ordering(provenance, figure_id)


# --------------------------------------------------------------------------- #
# Top-level pipeline                                                           #
# --------------------------------------------------------------------------- #


_CHECKS: tuple[Any, ...] = (
    check_axis_truncation,
    check_dual_axes,
    check_scale_distribution_mismatch,
    check_ci_omission_when_contract_requires,
    check_sample_size_missing_when_under_min_n,
    check_underpowered_unflagged,
    check_color_encoding_without_colorbar,
    check_3d_on_2d_data,
    check_non_monotonic_ordinal_ordering,
    check_p_value_threshold_only,
    check_color_blind_unsafe,
)


def audit_bias_for_figure(provenance_path: Path) -> tuple[BiasFinding, ...]:
    """Audit one figure given its provenance.json sidecar.

    Parameters
    ----------
    provenance_path
        Path to a ``<figure>.provenance.json`` sidecar.

    Returns
    -------
    tuple[BiasFinding, ...]
        Every finding emitted by every check, in deterministic order
        (check declaration order).

    Raises
    ------
    BiasAuditorError
        If the sidecar is missing or malformed.
    """
    provenance = _load_provenance(provenance_path)
    figure_id = _figure_id_from_path(
        provenance.get("figure_path") or provenance_path
    )
    out: list[BiasFinding] = []
    for check in _CHECKS:
        try:
            out.extend(check(provenance, figure_id))
        except Exception as exc:  # noqa: BLE001 — never abort the run
            out.append(
                BiasFinding(
                    kind=BiasFindingKind.truncated_y_axis,  # generic
                    severity=BiasSeverity.info,
                    figure_id=figure_id,
                    panel_id=None,
                    message=f"bias check {check.__name__} raised {type(exc).__name__}: {exc}",
                    evidence={"check": check.__name__, "exception": str(exc)},
                    remediation="",
                    location=str(provenance_path),
                )
            )
    return tuple(out)


def audit_bias_across_directory(figures_dir: Path) -> BiasAuditReport:
    """Walk ``figures_dir`` for ``*.provenance.json`` sidecars, audit each.

    The verdict triage is:

    * ``"honest"`` — zero errors and zero warnings across every audited
      figure.
    * ``"needs_review"`` — at least one warning, but no errors.
    * ``"concerning"`` — at least one error.

    Parameters
    ----------
    figures_dir
        Directory containing rendered figures and their sidecars.

    Returns
    -------
    BiasAuditReport
        Aggregate report.

    Raises
    ------
    BiasAuditorError
        If ``figures_dir`` does not exist.
    """
    figures_dir = Path(figures_dir)
    if not figures_dir.exists():
        raise BiasAuditorError(f"figures directory not found: {figures_dir}")
    if not figures_dir.is_dir():
        raise BiasAuditorError(f"figures path is not a directory: {figures_dir}")

    findings: list[BiasFinding] = []
    audited: list[str] = []
    n_skipped = 0

    sidecars = sorted(figures_dir.rglob("*.provenance.json"))
    for path in sidecars:
        try:
            provenance = _load_provenance(path)
        except BiasAuditorError:
            n_skipped += 1
            continue
        figure_id = _figure_id_from_path(
            provenance.get("figure_path") or path
        )
        audited.append(figure_id)
        try:
            findings.extend(audit_bias_for_figure(path))
        except BiasAuditorError:
            n_skipped += 1
            continue

    n_errors = sum(1 for f in findings if f.severity == BiasSeverity.error)
    n_warnings = sum(1 for f in findings if f.severity == BiasSeverity.warning)
    n_info = sum(1 for f in findings if f.severity == BiasSeverity.info)

    if n_errors > 0:
        verdict = "concerning"
    elif n_warnings > 0:
        verdict = "needs_review"
    else:
        verdict = "honest"

    return BiasAuditReport(
        audited_figures=tuple(audited),
        findings=tuple(findings),
        n_errors=n_errors,
        n_warnings=n_warnings,
        n_info=n_info,
        n_figures_inspected=len(audited),
        n_figures_skipped=n_skipped,
        overall_verdict=verdict,
    )


# --------------------------------------------------------------------------- #
# Markdown renderer                                                            #
# --------------------------------------------------------------------------- #


def render_bias_audit_markdown(report: BiasAuditReport) -> str:
    """Render a :class:`BiasAuditReport` as Markdown grouped by severity.

    Each severity bucket starts with a header and counts; findings are
    rendered as bullet points with the figure id, message, and (when
    present) remediation indented underneath.
    """
    lines: list[str] = []
    lines.append("# Figure-bias audit")
    lines.append("")
    lines.append(f"- **Verdict**: `{report.overall_verdict}`")
    lines.append(
        f"- **Inspected**: {report.n_figures_inspected} figure(s), "
        f"{report.n_figures_skipped} skipped"
    )
    lines.append(
        f"- **Findings**: {report.n_errors} error(s), "
        f"{report.n_warnings} warning(s), {report.n_info} info"
    )
    lines.append("")

    if report.n_figures_inspected == 0:
        lines.append("_No figures with provenance sidecars found._")
        lines.append("")
        return "\n".join(lines)

    by_sev: dict[BiasSeverity, list[BiasFinding]] = {
        BiasSeverity.error: [],
        BiasSeverity.warning: [],
        BiasSeverity.info: [],
    }
    for f in report.findings:
        by_sev[f.severity].append(f)

    sev_titles = {
        BiasSeverity.error: "## Errors",
        BiasSeverity.warning: "## Warnings",
        BiasSeverity.info: "## Info",
    }

    for sev in (BiasSeverity.error, BiasSeverity.warning, BiasSeverity.info):
        bucket = by_sev[sev]
        if not bucket:
            continue
        lines.append(sev_titles[sev])
        lines.append("")
        for f in bucket:
            panel = f" (panel {f.panel_id})" if f.panel_id else ""
            lines.append(
                f"- **{f.figure_id}{panel}** — `{f.kind.value}` — {f.message}"
            )
            if f.remediation:
                lines.append(f"  - _Fix_: {f.remediation}")
            if f.location:
                lines.append(f"  - _Location_: `{f.location}`")
        lines.append("")

    if not any(by_sev.values()):
        lines.append("_No bias-related findings detected — every audited figure is structurally honest._")
        lines.append("")

    return "\n".join(lines)
