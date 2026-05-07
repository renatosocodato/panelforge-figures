"""PHI/PII column-name scanner — Sprint 2B (PR #65).

See ``docs/spec_data_class_safety.md`` §4 for the full rationale.

The scanner is **pattern-based**.  It examines column NAMES only —
never cell values.  Names are normalised to lowercase with
non-alphanumerics replaced by spaces before regex matching, so
``Patient-DOB``, ``patient_dob``, and ``PatientDOB`` all match the
same patterns.  See ``_normalise()`` for why we use space (not
underscore) — Python regex word-boundaries do not fire across ``_``.

Three risk tiers (per spec §4):

* **High-risk** — definite PHI/PII (``mrn``, ``ssn``, ``patient_dob``,
  ``email``, ``phone``, etc.).  An ERROR-level finding when
  ``data_class != clinical``.
* **Medium-risk** — potential PHI when combined (``subject_id``,
  ``zip``, ``age_at_event``, etc.).  An INFO finding under research,
  WARN under public.
* **Low-risk** — no action; included as a positive control for tests
  (``cell_id``, ``area_um2``, ``feature``).

A column may match patterns at both tiers; the higher tier wins
(spec §4 last paragraph).  The scanner is deliberately
fail-conservative: false positives are silenced via the per-project
``data_class_overrides.allowed_columns`` allow-list (spec §3).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# High-risk patterns — definite PHI/PII (spec §4).  The patterns use
# ``[\W_]?`` between word fragments so the matcher tolerates separators
# (``patient_dob`` vs ``patient-dob`` vs ``patientdob``); we also strip
# all non-alphanumerics during normalisation for belt-and-braces
# coverage.
HIGH_RISK_PATTERNS: tuple[str, ...] = (
    r"\bpatient[\W_]?dob\b",
    r"\bdob\b",
    r"\bmrn\b",
    r"\bssn\b",
    r"\bphn\b",
    r"\bsubject[\W_]?id[\W_]?full\b",
    r"\baddress\b",
    r"\bstreet[\W_]?address\b",
    r"\bemail\b",
    r"\bemail[\W_]?addr\b",
    r"\bphone\b",
    r"\bphone[\W_]?number\b",
    r"\btelephone\b",
    r"\bdate[\W_]?of[\W_]?birth\b",
    r"\bbirth[\W_]?date\b",
    r"\bbirthday\b",
    r"\bmedical[\W_]?record\b",
    r"\bnpi\b",
)


# Medium-risk patterns — potential PHI when combined (spec §4).
MEDIUM_RISK_PATTERNS: tuple[str, ...] = (
    r"\bpatient[\W_]?id\b",
    r"\bsubject[\W_]?id\b",
    r"\bstudy[\W_]?id\b",
    r"\bencounter[\W_]?id\b",
    r"\bvisit[\W_]?id\b",
    r"\baccession\b",
    r"\bsample[\W_]?id[\W_]?full\b",
    r"\bzip\b",
    r"\bzipcode\b",
    r"\bpostal[\W_]?code\b",
    r"\bage[\W_]?at[\W_]?event\b",
    r"\bage[\W_]?yr\b",
    r"\bage[\W_]?years\b",
    r"\bsex\b",
    r"\bgender\b",
    r"\brace\b",
    r"\bethnicity\b",
)


@dataclass(frozen=True)
class PHIScanFinding:
    """One column → tier match.

    ``column`` is the original (un-normalised) column name from the
    file — what the user sees in their CSV.  ``risk_level`` is one of
    ``"high"`` or ``"medium"``.  ``matched_pattern`` is the regex that
    triggered, surfaced in the CLI output so users can map back to
    spec §4.
    """

    column: str
    risk_level: str
    matched_pattern: str


def _normalise(name: str) -> str:
    """Lowercase + replace any non-alphanumerics with `` `` (single space).

    This is the case- and separator-insensitive step that makes
    ``Patient-DOB`` and ``patient_dob`` match the same patterns.

    NOTE: we deliberately use *space* rather than ``_`` because Python
    regex word-boundaries (``\\b``) DO fire across spaces but DO NOT fire
    across underscores (which are word characters).  This lets the
    high-vs-medium overlap test (``patient_dob_age_yr`` matching both
    tiers per spec §4) work without rewriting every pattern.
    """
    return re.sub(r"[^a-z0-9]", " ", name.lower())


def match_column(name: str) -> str | None:
    """Return ``"high"``, ``"medium"``, or None for one column name.

    Higher tier wins when both match (spec §4).
    """
    normalised = _normalise(name)
    for pat in HIGH_RISK_PATTERNS:
        if re.search(pat, normalised, re.IGNORECASE):
            return "high"
    for pat in MEDIUM_RISK_PATTERNS:
        if re.search(pat, normalised, re.IGNORECASE):
            return "medium"
    return None


def scan_columns_for_phi(columns: Iterable[str]) -> list[PHIScanFinding]:
    """Scan a flat iterable of column names; emit at most one finding per column.

    The first matching pattern (high-risk first, then medium) wins —
    the scanner does not produce duplicate findings for a column whose
    name happens to match more than one regex within the same tier.
    """
    findings: list[PHIScanFinding] = []
    for col in columns:
        normalised = _normalise(col)
        matched = False
        for pat in HIGH_RISK_PATTERNS:
            if re.search(pat, normalised, re.IGNORECASE):
                findings.append(PHIScanFinding(col, "high", pat))
                matched = True
                break
        if matched:
            continue
        for pat in MEDIUM_RISK_PATTERNS:
            if re.search(pat, normalised, re.IGNORECASE):
                findings.append(PHIScanFinding(col, "medium", pat))
                break
    return findings


__all__ = [
    "HIGH_RISK_PATTERNS",
    "MEDIUM_RISK_PATTERNS",
    "PHIScanFinding",
    "match_column",
    "scan_columns_for_phi",
]
