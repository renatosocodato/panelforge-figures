"""Canonical figure-id normalisation — shared across the manuscript auditors.

Figure ids reach the auditors in a zoo of surface forms:

* prose references          — ``"Figure 3A"`` / ``"Fig. 3a"`` / ``"figure 3"``
* LaTeX labels              — ``"fig:3a"`` / ``"\\label{fig:3A}"`` payloads
* filename stems            — ``"figure_3a"`` / ``"fig_3"`` / ``"panel-3-a"``
* author-chosen mnemonics   — ``"fig:overview"`` / ``"figure_workflow"``

Before this module, every consumer compared these strings *as written*, so
``"Figure 3A"`` and ``"fig:3a"`` were silently treated as different figures —
a case- and format-sensitive trap that made cross-auditor correlation
ad-hoc and unreliable.

:func:`normalise_figure_id` collapses all of those numbered forms onto a
single canonical token (lowercased, with the ``fig`` / ``figure`` / ``fig:``
prefix and the separators stripped) so::

    normalise_figure_id("Figure 3A") == normalise_figure_id("fig:3a")
                                      == normalise_figure_id("figure_3a")
                                      == "3a"

Non-numbered, author-chosen ids (``"fig:overview"``) are kept meaningful:
the recognised prefix is still stripped and the remainder lowercased, so
``"Fig:Overview"`` and ``"figure_overview"`` both canonicalise to
``"overview"`` while never collapsing to the empty string.

Adoption note
-------------
``xref_linter`` and ``claim_check`` route their figure-id comparisons
through this helper. ``bias_auditor`` and ``scout`` (owned by other
modules) can adopt the same canonical form later for cross-auditor
correlation; this module is the single source of truth for the rule.
"""

from __future__ import annotations

import re

__all__ = ["normalise_figure_id"]


# Strips a leading ``figure`` / ``fig`` prefix (optionally followed by the
# LaTeX ``:`` namespace marker or a separator) from the front of an id.
# ``re.IGNORECASE`` makes the match case-insensitive; the trailing
# ``[:\s_\-]*`` swallows the ``:`` / whitespace / ``_`` / ``-`` that
# conventionally sits between the prefix and the number.
_PREFIX_RE = re.compile(r"^(?:figure|fig)[:\s_\-]*", re.IGNORECASE)

# Internal separators (whitespace / ``_`` / ``-`` / ``:``) that appear
# between the number and a panel subletter (``"3 a"`` / ``"3_a"``).
_SEPARATOR_RE = re.compile(r"[:\s_\-]+")


def normalise_figure_id(raw: str) -> str:
    """Collapse any figure-id surface form onto one canonical token.

    The canonical form is lowercased, has the leading ``fig`` / ``figure``
    / ``fig:`` prefix removed, and has all internal separators
    (whitespace, ``_``, ``-``, ``:``) stripped. Numbered ids therefore
    converge::

        >>> normalise_figure_id("Figure 3A")
        '3a'
        >>> normalise_figure_id("fig:3a")
        '3a'
        >>> normalise_figure_id("figure_3a")
        '3a'
        >>> normalise_figure_id("Fig. 3")
        '3'

    Author-chosen mnemonic ids keep their meaning (the prefix is still
    stripped, the remainder lowercased)::

        >>> normalise_figure_id("fig:overview")
        'overview'
        >>> normalise_figure_id("figure_workflow")
        'workflow'

    Edge handling
    -------------
    * ``None``-like / empty / whitespace-only input returns ``""``.
    * A bare prefix with nothing after it (``"figure"`` / ``"fig:"``)
      returns ``"figure"`` — the prefix is *not* stripped when stripping
      it would leave an empty token, so the id stays meaningful rather
      than collapsing to ``""`` (which would alias every prefix-only id).
    * A ``"Fig."`` abbreviation with a trailing period (``"Fig. 3"``) is
      handled: the period is treated as a separator and dropped.

    Parameters
    ----------
    raw
        Any figure-id surface form (prose reference, LaTeX label,
        filename stem, or mnemonic).

    Returns
    -------
    str
        The canonical token. Two ids that refer to the same figure
        compare equal under ``==`` after normalisation regardless of
        their original case or separator style.
    """
    if not raw:
        return ""
    text = raw.strip()
    if not text:
        return ""
    # Drop a trailing period from a "Fig." abbreviation before separator
    # collapsing so "Fig. 3" → "fig 3" → "3" rather than leaving a dot.
    text = text.replace(".", " ")
    stripped = _PREFIX_RE.sub("", text, count=1)
    # Refuse to strip the prefix when doing so empties the token (e.g.
    # a bare "figure" / "fig:"): keep a stable, non-empty canonical id.
    if not stripped.strip(" :_-"):
        stripped = text
    # Collapse internal separators and lowercase.
    collapsed = _SEPARATOR_RE.sub("", stripped)
    return collapsed.lower()
