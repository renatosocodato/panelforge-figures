"""Vision-driven recipe selection + iterative figure refinement.

Sprint 2C — v1.12.0.  See ``docs/spec_vision_input.md`` for the full
design rationale.

This module uses Claude Sonnet 4.5 vision to:

1. **Pre-fill the 8-question intake from a reference figure PNG** —
   :func:`vision_scan_reference_figure` sends the image to Anthropic
   and returns a list of :class:`VisionInference` records.
2. **Refine a rendered figure based on a natural-language instruction**
   — :func:`refine_figure` sends the rendered PNG plus the recipe
   Python source plus the instruction and returns a JSON-patch on the
   contract that the user reviews before re-render.
3. **Explain what's in a figure** (read-only) — implemented as a
   ``vision_scan_reference_figure`` call from the CLI ``vision-explain``
   verb, no contract change.

Privacy
-------
The image bytes ARE sent to Anthropic.  Data values are NOT (this
module never reads CSV/Parquet content; it reads images and recipe
Python only).  Vision is gated on:

* ``ANTHROPIC_API_KEY`` being set (the explicit opt-in for the
  ``research`` data class — see ``safety.is_vision_allowed``).
* The ``anthropic`` package being installed (the
  ``panelforge-figures[claude-autonomous]`` extra).
* The current data class allowing vision (clinical refuses
  unconditionally; research treats key-presence as opt-in; public is
  default-on).

Caching
-------
Vision results are cached by image SHA-256 in
``panelforge_workspace/vision_cache/<sha[:16]>.json`` so repeat calls
on the same image are free.  Cache miss → API call → cache write.
The cache file format is stable JSON with ``image_sha256`` as the
ground-truth key.

Lazy import
-----------
``anthropic`` is imported lazily inside :func:`vision_scan_reference_figure`
and :func:`refine_figure`, mirroring ``data_bridge._llm_pass``, so
callers without the optional dep can still import this module.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VISION_MODEL_DEFAULT = "claude-sonnet-4-5"
"""Locked default model.  Override via ``PANELFORGE_VISION_MODEL`` env
var if a future model needs to be pinned per-project (spec §15)."""

VISION_CACHE_DIR = Path("panelforge_workspace/vision_cache")
"""Cache directory.  Created lazily on first write."""

# Closed taxonomy pulled from recipes_index.json.  We hardcode the
# current set here so the prompt template is deterministic in tests
# and offline environments; :func:`_load_valid_families` will refresh
# this at runtime when the index is available, blocking hallucinated
# family names that drift past the recipe pack frontier.
_VALID_FAMILIES: tuple[str, ...] = (
    "bifurcation",
    "coef_forest",
    "conceptual",
    "contour",
    "diagnostic_curve",
    "flow",
    "gantt",
    "heatmap",
    "hysteresis_loop",
    "ladder",
    "matrix",
    "phase_portrait",
    "radar",
    "ridge_by_group",
    "scatter_collapse",
    "sobol_bar",
    "split_violin",
    "timecourse_hierarchical_ci",
    "volcano",
)


def _load_valid_families() -> tuple[str, ...]:
    """Return the closed-taxonomy family list.

    Tries to read ``recipes_index.json`` from the current working
    directory first (so plugin-extended families propagate); falls
    back to the hardcoded :data:`_VALID_FAMILIES` if the index is
    missing or malformed.  This keeps the prompt template in sync
    with whatever new families ship in recipe packs (spec §2.2).
    """
    index_path = Path("recipes_index.json")
    if not index_path.is_file():
        return _VALID_FAMILIES
    try:
        data = json.loads(index_path.read_text())
    except (json.JSONDecodeError, OSError):
        return _VALID_FAMILIES
    families: set[str] = set()
    for mod in data.get("modalities", []):
        for rec in mod.get("recipes", []):
            fam = rec.get("family")
            if fam:
                families.add(fam)
    if not families:
        return _VALID_FAMILIES
    return tuple(sorted(families))


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VisionInference:
    """One vision-derived inference about a reference figure.

    Mirrors :class:`manifest.project_scan.InferredAnswer` in shape so
    intake-pipeline code can consume both interchangeably.
    """

    field_name: str
    """One of ``family`` / ``dimensionality`` / ``has_error_bars`` /
    ``has_equivalence_bands`` / ``has_factorial_structure`` /
    ``n_panels`` / ``palette_hint``."""

    value: Any
    """The inferred value (str / bool / int)."""

    confidence: float
    """Self-rated confidence in ``[0.0, 1.0]``."""

    rationale: str = ""
    """Optional 1-line justification for downstream display."""


@dataclass(frozen=True)
class VisionScanResult:
    """Result envelope for one vision scan call."""

    image_path: Path
    image_sha256: str
    model: str
    cost_usd_estimate: float
    inferences: tuple[VisionInference, ...]
    raw_response: str = ""


@dataclass(frozen=True)
class RefinementOutcome:
    """Result envelope for one ``figures refine`` call."""

    figure_path: Path
    instruction: str
    contract_patch: dict[str, Any]
    suggested_alternatives: tuple[str, ...] = ()
    cost_usd_estimate: float = 0.025
    raw_response: str = ""


class VisionUnavailableError(RuntimeError):
    """Raised when the vision API gate is closed.

    Reasons: ``data_class=clinical``, ``ANTHROPIC_API_KEY`` not set, or
    ``anthropic`` package not installed.
    """


# ---------------------------------------------------------------------------
# Gate + cache helpers
# ---------------------------------------------------------------------------


def _check_vision_gate() -> None:
    """Raise :class:`VisionUnavailableError` if vision is disabled.

    Wraps ``safety.is_vision_allowed`` (Sprint 2B — v1.11.0) so all
    vision entry points fail-closed before any work.  The lazy import
    matches ``data_bridge._llm_pass`` so this module's import surface
    stays small for callers that bypass the safety module entirely.
    """
    from ..safety import is_vision_allowed
    if not is_vision_allowed():
        raise VisionUnavailableError(
            "Vision API disabled.  Possible reasons:\n"
            "  - data_class=clinical (clinical mode disables all vision)\n"
            "  - ANTHROPIC_API_KEY not set\n"
            "  - panelforge-figures[claude-autonomous] extra not installed\n"
            "Check `figures config show` for current data_class."
        )


def _sha256_file(path: Path) -> str:
    """Stream the file through SHA-256 in 64 KB chunks.

    Used both as the cache key and as the metadata field on
    :class:`VisionScanResult`.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path_for(image_sha: str) -> Path:
    """Cache file path for a given image SHA-256."""
    VISION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return VISION_CACHE_DIR / f"{image_sha[:16]}.json"


def _load_cache(image_sha: str) -> VisionScanResult | None:
    """Best-effort cache load; returns None on any failure."""
    path = _cache_path_for(image_sha)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return VisionScanResult(
            image_path=Path(data["image_path"]),
            image_sha256=data["image_sha256"],
            model=data["model"],
            cost_usd_estimate=data["cost_usd_estimate"],
            inferences=tuple(VisionInference(**i) for i in data["inferences"]),
            raw_response=data.get("raw_response", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        return None


def _save_cache(result: VisionScanResult) -> None:
    """Write the cache file as deterministic JSON."""
    path = _cache_path_for(result.image_sha256)
    payload = {
        "image_path": str(result.image_path),
        "image_sha256": result.image_sha256,
        "model": result.model,
        "cost_usd_estimate": result.cost_usd_estimate,
        "inferences": [
            {
                "field_name": i.field_name,
                "value": i.value,
                "confidence": i.confidence,
                "rationale": i.rationale,
            }
            for i in result.inferences
        ],
        "raw_response": result.raw_response,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _media_type_for(path: Path) -> str:
    """Map a file extension to a vision media type."""
    s = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(s, "image/png")


# ---------------------------------------------------------------------------
# Prompt template + response parsing
# ---------------------------------------------------------------------------


_SCAN_PROMPT = """You are analyzing a scientific figure PNG to identify its visual family + anchor signals.

Return a JSON object with these keys:
  - family: one of {valid_families} (the panel-rendering family)
  - dimensionality: "2D" | "3D" | "1D" | "scalar"
  - has_error_bars: true | false
  - has_equivalence_bands: true | false   (TOST-style bounds visible?)
  - has_factorial_structure: true | false   (multi-axis sex x genotype layout?)
  - n_panels: integer
  - palette_hint: "slate" | "teal" | "coral" | "purple" | "amber" | "mixed" | "unknown"

For each key, also include a `<key>_confidence` field in [0.0, 1.0]
(your self-rated confidence).

Output the JSON only, no prose.
"""


_PAIRED_KEYS: tuple[str, ...] = (
    "family",
    "dimensionality",
    "has_error_bars",
    "has_equivalence_bands",
    "has_factorial_structure",
    "n_panels",
    "palette_hint",
)


def _parse_vision_response(
    raw: str, threshold: float
) -> list[VisionInference]:
    """Parse the JSON block from a Claude response.

    The model may wrap its JSON in markdown fences; we extract the
    first ``{...}`` block.  Closed-taxonomy validation is applied to
    the ``family`` field — any hallucinated value outside
    :data:`_VALID_FAMILIES` is dropped silently rather than surfaced
    as a low-confidence inference.

    The ``threshold`` parameter is currently informational — filtering
    by confidence happens in :func:`to_intake_pre_filled` so callers
    can inspect the full inference list (e.g. ``vision-explain``
    shows everything regardless of threshold).
    """
    del threshold  # filtering lives downstream — keep the API symmetric

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return []
    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return []

    inferences: list[VisionInference] = []
    valid_families = _load_valid_families()
    for key in _PAIRED_KEYS:
        if key not in data:
            continue
        value = data[key]
        try:
            conf = float(data.get(f"{key}_confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        # Closed-taxonomy guard for `family`.
        if key == "family" and value not in valid_families:
            continue
        inferences.append(
            VisionInference(
                field_name=key,
                value=value,
                confidence=conf,
            )
        )
    return inferences


# ---------------------------------------------------------------------------
# Vision scan (intake pre-fill mode)
# ---------------------------------------------------------------------------


def vision_scan_reference_figure(
    image_path: Path,
    *,
    confidence_threshold: float = 0.7,
    use_cache: bool = True,
) -> VisionScanResult:
    """Send ``image_path`` to Claude Sonnet 4.5 vision; return inferences.

    Caches by image SHA-256 in
    ``panelforge_workspace/vision_cache/`` so repeat calls on the same
    image are free.  Raises :class:`VisionUnavailableError` if the
    gate is closed (clinical class, missing API key, or missing
    ``anthropic`` package).
    """
    _check_vision_gate()

    image_path = Path(image_path)
    image_sha = _sha256_file(image_path)
    if use_cache:
        cached = _load_cache(image_sha)
        if cached is not None:
            return cached

    try:
        import anthropic  # lazy by design — optional dep
    except ImportError as exc:
        raise VisionUnavailableError(
            "anthropic package not installed.  Run "
            "`pip install panelforge-figures[claude-autonomous]`."
        ) from exc

    model = os.environ.get("PANELFORGE_VISION_MODEL", VISION_MODEL_DEFAULT)
    client = anthropic.Anthropic()

    image_bytes = image_path.read_bytes()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = _SCAN_PROMPT.format(
        valid_families=", ".join(f"'{f}'" for f in _load_valid_families())
    )

    response = client.messages.create(
        model=model,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _media_type_for(image_path),
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    raw_text = response.content[0].text
    inferences = _parse_vision_response(raw_text, confidence_threshold)

    result = VisionScanResult(
        image_path=image_path,
        image_sha256=image_sha,
        model=model,
        cost_usd_estimate=0.012,  # spec §9 indicative
        inferences=tuple(inferences),
        raw_response=raw_text,
    )
    if use_cache:
        _save_cache(result)
    return result


def to_intake_pre_filled(
    result: VisionScanResult,
    *,
    confidence_threshold: float = 0.7,
) -> dict[str, Any]:
    """Convert a :class:`VisionScanResult` to an intake pre-fill dict.

    Maps vision keys to intake field names where the mapping is
    direct.  Inferences below ``confidence_threshold`` are dropped so
    the intake will prompt the user explicitly for those fields.

    Mapping
    -------
    * ``dimensionality`` → ``dimensionality`` (intake question 5)
    * ``has_factorial_structure`` → ``factorial_design`` (intake Q1)
    * ``has_equivalence_bands`` → ``equivalence_claims`` (intake Q2)

    The ``family``, ``n_panels``, and ``palette_hint`` inferences are
    NOT mapped to intake — they feed downstream scoring (Sprint 3+).
    """
    out: dict[str, Any] = {}
    for inf in result.inferences:
        if inf.confidence < confidence_threshold:
            continue
        if inf.field_name == "dimensionality":
            out["dimensionality"] = inf.value
        elif inf.field_name == "has_factorial_structure":
            out["factorial_design"] = bool(inf.value)
        elif inf.field_name == "has_equivalence_bands":
            out["equivalence_claims"] = bool(inf.value)
    return out


# ---------------------------------------------------------------------------
# Iterative refinement (figures refine)
# ---------------------------------------------------------------------------


_REFINE_PROMPT = """User wants to refine this figure with the instruction:
  {instruction}

The recipe source is:
```python
{recipe_source}
```

Return a JSON object with these keys:
  - contract_patch: dict of contract field changes (e.g. {{"y_log_scale": true}})
  - suggested_alternatives: list of alternative recipe full_names if a different recipe would be better
  - rationale: 1-2 sentence justification

Output the JSON only.
"""


def refine_figure(
    figure_path: Path,
    instruction: str,
    *,
    recipe_module_path: Path | None = None,
) -> RefinementOutcome:
    """Run the two-pass refinement loop and return a contract patch.

    Reads the rendered PNG (via Anthropic vision) and the source
    recipe Python (as text) and asks Claude for a JSON-patch on the
    contract.  The caller is responsible for showing the patch to the
    user, prompting for confirmation, and re-rendering on approval —
    see ``cli.refine_cmd`` for the wired CLI surface.

    Raises :class:`VisionUnavailableError` if the gate is closed.
    """
    _check_vision_gate()
    try:
        import anthropic  # lazy
    except ImportError as exc:
        raise VisionUnavailableError(
            "anthropic package not installed."
        ) from exc

    figure_path = Path(figure_path)
    model = os.environ.get("PANELFORGE_VISION_MODEL", VISION_MODEL_DEFAULT)
    client = anthropic.Anthropic()

    image_bytes = figure_path.read_bytes()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    recipe_source = ""
    if recipe_module_path is not None and recipe_module_path.is_file():
        recipe_source = recipe_module_path.read_text()

    prompt = _REFINE_PROMPT.format(
        instruction=instruction,
        recipe_source=recipe_source,
    )

    response = client.messages.create(
        model=model,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _media_type_for(figure_path),
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    raw = response.content[0].text
    return _parse_refine_response(figure_path, instruction, raw)


def _parse_refine_response(
    figure_path: Path, instruction: str, raw: str
) -> RefinementOutcome:
    """Parse the JSON block from a refinement response."""
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return RefinementOutcome(
            figure_path=figure_path,
            instruction=instruction,
            contract_patch={},
            raw_response=raw,
        )
    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return RefinementOutcome(
            figure_path=figure_path,
            instruction=instruction,
            contract_patch={},
            raw_response=raw,
        )

    contract_patch = data.get("contract_patch") or {}
    if not isinstance(contract_patch, dict):
        contract_patch = {}

    alts = data.get("suggested_alternatives") or []
    if not isinstance(alts, list):
        alts = []
    alt_tuple = tuple(str(a) for a in alts)

    return RefinementOutcome(
        figure_path=figure_path,
        instruction=instruction,
        contract_patch=contract_patch,
        suggested_alternatives=alt_tuple,
        raw_response=raw,
    )


__all__ = [
    "VISION_CACHE_DIR",
    "VISION_MODEL_DEFAULT",
    "RefinementOutcome",
    "VisionInference",
    "VisionScanResult",
    "VisionUnavailableError",
    "refine_figure",
    "to_intake_pre_filled",
    "vision_scan_reference_figure",
]
