"""Tests for vision-driven recipe selection + iterative refinement.

Sprint 2C — v1.12.0.  See ``docs/spec_vision_input.md`` and
``src/panelforge_figures/manifest/vision_input.py``.

Coverage matrix
---------------

* Vision unavailable when ``ANTHROPIC_API_KEY`` is unset →
  :class:`VisionUnavailableError`.
* Vision unavailable when ``data_class=clinical`` →
  :class:`VisionUnavailableError`.
* :func:`_parse_vision_response` — valid JSON returns a list of
  :class:`VisionInference`.
* :func:`_parse_vision_response` — hallucinated family is filtered.
* :func:`_parse_vision_response` — malformed JSON returns an empty
  list.
* Cache round-trip: save + load.
* Cache miss → API is called once.
* Cache hit → API is NOT called (the second call short-circuits).
* SHA-256 of an image is deterministic.
* :func:`to_intake_pre_filled` filters by confidence threshold.
* Mocked anthropic client returns a stubbed response → parsed into
  :class:`VisionScanResult` correctly.
* CLI: ``figures vision-explain --help`` exits 0.
* CLI: ``figures refine --help`` exits 0.
* CLI: missing image causes Click to exit 2 (path-validation error).
* :func:`refine_figure` returns a parsed contract patch.

Fixtures restore the data class to RESEARCH after every test so we do
not leak clinical state into adjacent test modules (which would
silently disable LLM Pass-3 in their fixtures).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.vision_input import (
    VisionInference,
    VisionScanResult,
    VisionUnavailableError,
    _load_cache,
    _parse_vision_response,
    _save_cache,
    _sha256_file,
    refine_figure,
    to_intake_pre_filled,
    vision_scan_reference_figure,
)
from panelforge_figures.safety import DataClass, get_data_class, set_data_class

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_default_class() -> Iterator[None]:
    """Reset the module-level data class to RESEARCH after each test."""
    saved = get_data_class()
    try:
        yield
    finally:
        set_data_class(
            saved if saved == DataClass.RESEARCH else DataClass.RESEARCH
        )


@pytest.fixture
def _vision_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Run vision tests in a tmp dir so the cache lives under it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def _tiny_png(tmp_path: Path) -> Path:
    """Return a path to a 1-byte placeholder PNG (content is irrelevant
    because we always mock the anthropic client)."""
    p = tmp_path / "fig.png"
    # Real PNG file signature so _media_type_for resolves correctly;
    # contents past the signature are arbitrary because we mock the
    # vision call.
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    return p


def _install_fake_anthropic(
    monkeypatch: pytest.MonkeyPatch,
    response_text: str,
    counter: list[int] | None = None,
) -> None:
    """Stub out ``sys.modules['anthropic']`` with a canned response."""

    class _FakeContent:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeMessage:
        def __init__(self, text: str) -> None:
            self.content = [_FakeContent(text)]

    class _FakeMessages:
        def create(self, **_kw):
            if counter is not None:
                counter[0] += 1
            return _FakeMessage(response_text)

    class _FakeAnthropic:
        def __init__(self) -> None:
            self.messages = _FakeMessages()

    fake_mod = type(sys)("anthropic")
    fake_mod.Anthropic = _FakeAnthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)


# ---------------------------------------------------------------------------
# Gate behaviour
# ---------------------------------------------------------------------------


def test_vision_unavailable_without_api_key(
    monkeypatch: pytest.MonkeyPatch, _tiny_png: Path
) -> None:
    """No API key under research class → VisionUnavailableError."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    set_data_class(DataClass.RESEARCH)
    with pytest.raises(VisionUnavailableError):
        vision_scan_reference_figure(_tiny_png)


def test_vision_unavailable_under_clinical(
    monkeypatch: pytest.MonkeyPatch, _tiny_png: Path
) -> None:
    """Clinical data_class → VisionUnavailableError even with API key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)
    with pytest.raises(VisionUnavailableError):
        vision_scan_reference_figure(_tiny_png)


def test_refine_unavailable_under_clinical(
    monkeypatch: pytest.MonkeyPatch, _tiny_png: Path
) -> None:
    """``refine_figure`` is also gated under clinical."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)
    with pytest.raises(VisionUnavailableError):
        refine_figure(_tiny_png, "make it log-scale")


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def test_parse_vision_response_valid_json() -> None:
    """A well-formed JSON response yields the expected inferences."""
    raw = json.dumps(
        {
            "family": "coef_forest",
            "family_confidence": 0.92,
            "dimensionality": "2D",
            "dimensionality_confidence": 0.95,
            "has_error_bars": True,
            "has_error_bars_confidence": 0.88,
        }
    )
    result = _parse_vision_response(raw, threshold=0.7)
    keys = {i.field_name for i in result}
    assert "family" in keys
    assert "dimensionality" in keys
    assert "has_error_bars" in keys
    fam = next(i for i in result if i.field_name == "family")
    assert fam.value == "coef_forest"
    assert fam.confidence == pytest.approx(0.92)


def test_parse_vision_response_filters_hallucinated_family() -> None:
    """A family value outside the closed taxonomy is dropped silently."""
    raw = json.dumps(
        {
            "family": "totally_fabricated_family",
            "family_confidence": 0.99,
            "dimensionality": "2D",
            "dimensionality_confidence": 0.9,
        }
    )
    result = _parse_vision_response(raw, threshold=0.7)
    keys = {i.field_name for i in result}
    assert "family" not in keys, "hallucinated family must be filtered"
    assert "dimensionality" in keys


def test_parse_vision_response_malformed_json_returns_empty() -> None:
    """If the response has no ``{...}`` block, return an empty list."""
    raw = "I refuse to comply with structured output today."
    result = _parse_vision_response(raw, threshold=0.7)
    assert result == []


def test_parse_vision_response_invalid_json_returns_empty() -> None:
    """Truncated / invalid JSON inside the brace block returns []."""
    raw = "{ this is not valid JSON, missing quotes and braces"
    result = _parse_vision_response(raw, threshold=0.7)
    assert result == []


# ---------------------------------------------------------------------------
# Cache round-trip
# ---------------------------------------------------------------------------


def test_cache_round_trip(_vision_workspace: Path) -> None:
    """``_save_cache`` then ``_load_cache`` yields an equal envelope."""
    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    sha = _sha256_file(image_path)
    original = VisionScanResult(
        image_path=image_path,
        image_sha256=sha,
        model="claude-sonnet-4-5",
        cost_usd_estimate=0.012,
        inferences=(
            VisionInference("family", "coef_forest", 0.9, "looks like a forest"),
            VisionInference("dimensionality", "2D", 0.95),
        ),
        raw_response="canned",
    )
    _save_cache(original)
    loaded = _load_cache(sha)
    assert loaded is not None
    assert loaded.image_sha256 == original.image_sha256
    assert loaded.model == original.model
    assert loaded.cost_usd_estimate == pytest.approx(original.cost_usd_estimate)
    assert len(loaded.inferences) == 2
    assert loaded.inferences[0].field_name == "family"
    assert loaded.inferences[0].value == "coef_forest"


def test_sha256_is_deterministic(tmp_path: Path) -> None:
    """Same bytes → same SHA-256 hex digest."""
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"identical-content")
    p2.write_bytes(b"identical-content")
    assert _sha256_file(p1) == _sha256_file(p2)
    assert len(_sha256_file(p1)) == 64


def test_cache_miss_then_hit(
    monkeypatch: pytest.MonkeyPatch,
    _vision_workspace: Path,
) -> None:
    """First call invokes the mocked API; second call short-circuits."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.RESEARCH)

    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    canned = json.dumps(
        {
            "family": "coef_forest",
            "family_confidence": 0.9,
            "dimensionality": "2D",
            "dimensionality_confidence": 0.85,
        }
    )
    counter: list[int] = [0]
    _install_fake_anthropic(monkeypatch, canned, counter=counter)

    r1 = vision_scan_reference_figure(image_path)
    assert counter[0] == 1
    assert any(i.field_name == "family" for i in r1.inferences)

    # Second call should hit the cache and not invoke the API.
    r2 = vision_scan_reference_figure(image_path)
    assert counter[0] == 1, "second call must use cache"
    assert r2.image_sha256 == r1.image_sha256


# ---------------------------------------------------------------------------
# to_intake_pre_filled
# ---------------------------------------------------------------------------


def test_to_intake_pre_filled_filters_by_threshold() -> None:
    """Inferences below the threshold are dropped from the intake dict."""
    result = VisionScanResult(
        image_path=Path("/tmp/fig.png"),
        image_sha256="0" * 64,
        model="claude-sonnet-4-5",
        cost_usd_estimate=0.012,
        inferences=(
            # Above threshold: should be included
            VisionInference("dimensionality", "2D", 0.9),
            VisionInference("has_factorial_structure", True, 0.85),
            # Below threshold: should be dropped
            VisionInference("has_equivalence_bands", True, 0.5),
        ),
    )
    pre_fill = to_intake_pre_filled(result, confidence_threshold=0.7)
    assert pre_fill.get("dimensionality") == "2D"
    assert pre_fill.get("factorial_design") is True
    assert "equivalence_claims" not in pre_fill


def test_to_intake_pre_filled_maps_keys_correctly() -> None:
    """Vision keys are renamed to intake field names."""
    result = VisionScanResult(
        image_path=Path("/tmp/fig.png"),
        image_sha256="0" * 64,
        model="claude-sonnet-4-5",
        cost_usd_estimate=0.012,
        inferences=(
            VisionInference("has_factorial_structure", False, 0.9),
            VisionInference("has_equivalence_bands", True, 0.95),
        ),
    )
    pre_fill = to_intake_pre_filled(result)
    assert pre_fill["factorial_design"] is False
    assert pre_fill["equivalence_claims"] is True
    # `family` and `palette_hint` are NOT mapped to intake.
    assert "family" not in pre_fill


# ---------------------------------------------------------------------------
# Mocked end-to-end vision_scan_reference_figure
# ---------------------------------------------------------------------------


def test_vision_scan_with_mocked_anthropic(
    monkeypatch: pytest.MonkeyPatch, _vision_workspace: Path
) -> None:
    """Mocked anthropic client returns parsed inferences in the envelope."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.RESEARCH)

    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    canned = json.dumps(
        {
            "family": "split_violin",
            "family_confidence": 0.88,
            "dimensionality": "2D",
            "dimensionality_confidence": 0.9,
            "has_error_bars": True,
            "has_error_bars_confidence": 0.7,
            "n_panels": 1,
            "n_panels_confidence": 0.95,
        }
    )
    _install_fake_anthropic(monkeypatch, canned)

    result = vision_scan_reference_figure(image_path)
    assert result.model.startswith("claude-sonnet-4-5") or result.model.startswith("claude")
    fam = next(i for i in result.inferences if i.field_name == "family")
    assert fam.value == "split_violin"
    npanels = next(i for i in result.inferences if i.field_name == "n_panels")
    assert npanels.value == 1


# ---------------------------------------------------------------------------
# refine_figure happy path
# ---------------------------------------------------------------------------


def test_refine_figure_parses_contract_patch(
    monkeypatch: pytest.MonkeyPatch, _vision_workspace: Path
) -> None:
    """Mocked refinement returns the contract patch dict."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.RESEARCH)

    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    canned = json.dumps(
        {
            "contract_patch": {"y_log_scale": True},
            "suggested_alternatives": ["actin_mt.coef_forest_v3"],
            "rationale": "log-scale is a contract field on this family",
        }
    )
    _install_fake_anthropic(monkeypatch, canned)

    outcome = refine_figure(image_path, "make y-axis log-scale")
    assert outcome.contract_patch == {"y_log_scale": True}
    assert outcome.suggested_alternatives == ("actin_mt.coef_forest_v3",)


def test_refine_figure_missing_json_returns_empty_patch(
    monkeypatch: pytest.MonkeyPatch, _vision_workspace: Path
) -> None:
    """If the model output has no JSON block, we get an empty patch."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.RESEARCH)

    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    _install_fake_anthropic(monkeypatch, "no json here, sorry")
    outcome = refine_figure(image_path, "tweak it")
    assert outcome.contract_patch == {}
    assert outcome.suggested_alternatives == ()


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


def test_cli_vision_explain_help() -> None:
    """``figures vision-explain --help`` exits 0."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["vision-explain", "--help"])
    assert result.exit_code == 0
    assert "vision" in result.output.lower()


def test_cli_refine_help() -> None:
    """``figures refine --help`` exits 0."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["refine", "--help"])
    assert result.exit_code == 0
    # Click's --help should mention contract or instruction.
    assert "instruction" in result.output.lower() or "refine" in result.output.lower()


def test_cli_vision_explain_missing_image_exits_nonzero(
    tmp_path: Path,
) -> None:
    """A non-existent image path causes Click's path validator to exit 2."""
    runner = CliRunner()
    bogus = tmp_path / "does_not_exist.png"
    result = runner.invoke(cli_main, ["vision-explain", str(bogus)])
    # Click's path-exists validator exits with code 2.
    assert result.exit_code != 0


def test_cli_vision_explain_unavailable_under_clinical(
    monkeypatch: pytest.MonkeyPatch, _vision_workspace: Path
) -> None:
    """Under clinical class, the CLI reports unavailable and exits 1."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    set_data_class(DataClass.CLINICAL)

    image_path = _vision_workspace / "fig.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["vision-explain", str(image_path)])
    assert result.exit_code == 1
    assert "vision" in result.output.lower()
