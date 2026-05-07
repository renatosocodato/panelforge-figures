"""Data-class safety mode — Sprint 2B (PR #65 — v1.11.0).

See ``docs/spec_data_class_safety.md`` for the full design.

Three classes — ``clinical | research | public`` — gate every elevation
that touches the network or persists derived state:

* ``clinical`` — LLM Pass-3 disabled, vision disabled, telemetry off,
  provenance hashes redacted, plugins requiring network refused.
* ``research`` (default when no class declared) — every off-host
  capability is opt-in via env var or project flag; provenance is
  recorded in full.
* ``public`` — LLM and vision are default-on; telemetry remains
  opt-in; provenance is recorded in full.

Public API consumed by gate sites
---------------------------------

::

    from panelforge_figures.safety import (
        DataClass,
        DataClassPolicy,
        get_data_class,
        get_policy,
        set_data_class,
        is_llm_allowed,
        is_telemetry_allowed,
        is_vision_allowed,
        is_plugin_network_allowed,
        should_redact_provenance_hashes,
    )

The module-level ``_CURRENT_DATA_CLASS`` is the single source of truth
for the runtime mode; it is set via :func:`set_data_class` (CLI verb
``figures config set data_class``) or by future load-time wiring from
``panelforge.project.yaml``.  All ``is_*_allowed`` predicates are
pure functions of the resolved policy, so gate sites are unit-testable
in isolation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class DataClass(StrEnum):
    """Three data-class modes locked by spec §2."""

    CLINICAL = "clinical"
    RESEARCH = "research"
    PUBLIC = "public"


class DataClassError(Exception):
    """Raised on schema errors or non-relaxable clinical overrides."""


@dataclass(frozen=True)
class DataClassPolicy:
    """Resolved per-mode behaviour policy.

    Cell values are deliberately documented strings rather than booleans
    because the spec distinguishes ``opt_in`` (default OFF, user can
    enable) from ``disabled`` (forced OFF, no override possible).

    Fields
    ------
    llm_pass3
        ``"enabled"`` — runs whenever ``ANTHROPIC_API_KEY`` is set.
        ``"opt_in"`` — runs only when the API key is set (treated as
        an explicit opt-in for the research class).
        ``"disabled"`` — refuses to invoke regardless of env state.
    telemetry
        ``"opt_in"`` — record_event no-ops until project explicitly
        enables.  ``"off"`` — record_event always no-ops (clinical).
    vision
        Same shape as ``llm_pass3``.
    provenance_hashes
        ``"full"`` — record sha256 for every data source.
        ``"redacted"`` — replace sha256 with ``"[redacted]"`` (clinical).
    plugin_network_required
        ``"allowed"`` — plugins declaring ``network_required: true`` may
        load.  ``"disallowed"`` — they are refused at load (clinical).
    """

    llm_pass3: str
    telemetry: str
    vision: str
    provenance_hashes: str
    plugin_network_required: str


# Locked policy table per spec §2.  Keys MUST stay aligned with
# DataClass enum members; the table is exhaustive — a runtime lookup
# miss is a programming error rather than a recoverable state.
_POLICIES: dict[DataClass, DataClassPolicy] = {
    DataClass.CLINICAL: DataClassPolicy(
        llm_pass3="disabled",
        telemetry="off",
        vision="disabled",
        provenance_hashes="redacted",
        plugin_network_required="disallowed",
    ),
    DataClass.RESEARCH: DataClassPolicy(
        llm_pass3="opt_in",
        telemetry="opt_in",
        vision="opt_in",
        provenance_hashes="full",
        plugin_network_required="allowed",
    ),
    DataClass.PUBLIC: DataClassPolicy(
        llm_pass3="enabled",
        telemetry="opt_in",
        vision="enabled",
        provenance_hashes="full",
        plugin_network_required="allowed",
    ),
}


# Module-level current data class — set by ``set_data_class`` or read
# from ``panelforge.project.yaml`` at project load.  Default is
# RESEARCH per spec §2: defaulting to clinical would silently break
# demo users; defaulting to public would silently expose regulated
# users.
_CURRENT_DATA_CLASS: DataClass = DataClass.RESEARCH


def get_data_class() -> DataClass:
    """Return the runtime data class."""
    return _CURRENT_DATA_CLASS


def set_data_class(value: DataClass | str) -> None:
    """Set the runtime data class.

    Accepts a :class:`DataClass` member or a string from
    ``{"clinical", "research", "public"}``.  Raises :class:`DataClassError`
    if the string is not one of the three.

    Note: Spec §11 risk-row 4 — ``data_class`` cannot be set via env
    var.  The only paths into this setter are the CLI ``figures config
    set`` verb and the project-YAML loader (Sprint 3+).
    """
    global _CURRENT_DATA_CLASS
    if isinstance(value, str):
        try:
            value = DataClass(value)
        except ValueError as exc:
            raise DataClassError(
                f"invalid data_class: {value!r}; "
                "valid values: clinical / research / public"
            ) from exc
    _CURRENT_DATA_CLASS = value


def get_policy() -> DataClassPolicy:
    """Return the resolved :class:`DataClassPolicy` for the current mode."""
    return _POLICIES[_CURRENT_DATA_CLASS]


def is_llm_allowed() -> bool:
    """LLM Pass-3 gate.

    * ``clinical`` → always False — bridge returns UNBOUND.
    * ``research`` → True iff ``ANTHROPIC_API_KEY`` is set (the env-var
      presence is the explicit opt-in for this class).
    * ``public`` → True (defaults to running whenever extras are
      installed; Pass-3 itself still checks for the key/package).
    """
    policy = get_policy().llm_pass3
    if policy == "disabled":
        return False
    if policy == "enabled":
        return True
    # opt_in: requires explicit ANTHROPIC_API_KEY in env
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def is_telemetry_allowed() -> bool:
    """Telemetry gate (W6 — wired in Sprint 3B).

    Clinical is forced off.  Research and public are opt-in; we never
    silently collect telemetry, so the default for opt-in is **OFF**
    until an explicit project-config flag (Sprint 3B) flips it on.
    """
    policy = get_policy().telemetry
    if policy in ("off", "disabled"):
        return False
    if policy == "enabled":
        return True
    # opt_in: default OFF until Sprint 3B's enable_telemetry flag wires in
    return False


def is_vision_allowed() -> bool:
    """Vision API gate (W5 — wired in Sprint 3A).

    Same logic as :func:`is_llm_allowed` — clinical refuses, public is
    default-on, research uses ``ANTHROPIC_API_KEY`` as the opt-in
    signal.
    """
    policy = get_policy().vision
    if policy == "disabled":
        return False
    if policy == "enabled":
        return True
    # opt_in: requires explicit ANTHROPIC_API_KEY in env
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def should_redact_provenance_hashes() -> bool:
    """Whether to redact ``data_sha256`` values in provenance sidecars."""
    return get_policy().provenance_hashes == "redacted"


def is_plugin_network_allowed() -> bool:
    """Whether the plugin loader may accept plugins declaring
    ``network_required: true``.

    Used by the plugin loader (Sprint 2A) to refuse network-touching
    plugins under clinical class.
    """
    return get_policy().plugin_network_required == "allowed"


__all__ = [
    "DataClass",
    "DataClassError",
    "DataClassPolicy",
    "get_data_class",
    "get_policy",
    "is_llm_allowed",
    "is_plugin_network_allowed",
    "is_telemetry_allowed",
    "is_vision_allowed",
    "set_data_class",
    "should_redact_provenance_hashes",
]
