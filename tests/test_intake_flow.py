"""Tests for the 8-question intake module (Wave 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.manifest.intake import (
    HARD_FILTER_KEYS,
    INTAKE_QUESTIONS,
    IntakeAnswer,
    ProjectProfile,
    _profile_from_answers,
    _profile_to_dict,
    intake_questions_for_index,
    run_intake_interactive,
)

# ──────────────────────────── fixtures ───────────────────────────────────


AVAILABLE_MODALITIES = (
    "rhogtpase_dynamics",
    "sensitivity_analysis",
    "grant_and_conceptual",
    "meta_and_diagnostic",
)


def _all_defaults_pre_filled() -> dict[str, IntakeAnswer]:
    """Return a pre_filled dict where every answer is the spec default."""
    pf: dict[str, IntakeAnswer] = {}
    for q in INTAKE_QUESTIONS:
        if q.field_name == "modalities_in_scope":
            value: object = ()                                    # → all
        elif q.field_name == "hard_filters":
            value = ()                                            # → none set
        else:
            value = q.default
        pf[q.field_name] = IntakeAnswer(
            question_id=q.id,
            field_name=q.field_name,
            value=value,
            source="default",
            confidence=1.0,
        )
    return pf


# ─────────────────────────── structural tests ────────────────────────────


def test_intake_questions_has_exactly_eight_with_monotonic_ids() -> None:
    assert len(INTAKE_QUESTIONS) == 8
    ids = [q.id for q in INTAKE_QUESTIONS]
    assert ids == list(range(1, 9))


def test_intake_questions_field_names_match_spec() -> None:
    expected = [
        "factorial_design",
        "equivalence_claims",
        "manuscript_anchor",
        "dynamics_needed",
        "dimensionality",
        "modalities_in_scope",
        "hard_filters",
        "shortlist_size",
    ]
    assert [q.field_name for q in INTAKE_QUESTIONS] == expected


def test_intake_questions_for_index_serialises_to_json() -> None:
    serialised = intake_questions_for_index()
    assert len(serialised) == 8
    # round-trip through json to prove it's JSON-safe
    blob = json.dumps(serialised)
    loaded = json.loads(blob)
    assert len(loaded) == 8
    # required keys on every entry
    for entry in loaded:
        assert {"id", "field_name", "prompt", "type", "choices", "default", "description"} <= set(
            entry.keys()
        )
        assert isinstance(entry["choices"], list)


# ─────────────────────────── behaviour tests ─────────────────────────────


def test_pre_filled_path_skips_all_prompts(tmp_path: Path) -> None:
    """Smoke test via CliRunner: pre-filled answers + 'y' for the final confirm.

    Stricter behavioural checks live in the monkeypatch-based test below.
    """
    pre = _all_defaults_pre_filled()
    out = tmp_path / "profile.json"

    runner = CliRunner()
    result = runner.invoke(
        _intake_as_click_cmd(pre, AVAILABLE_MODALITIES, out),
        input="y\n",                             # only the final Confirm? needs input
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    assert "[auto] factorial_design" in result.output


def test_pre_filled_path_no_prompts_via_direct_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stronger version: monkeypatch click.prompt + click.confirm to fail fast.

    If any question prompt is reached (other than the final confirm) the
    test will explode.  The final confirm is patched to auto-yes.
    """
    from panelforge_figures.manifest import intake as mod

    prompt_calls: list[tuple] = []

    def _fake_prompt(*args: object, **kwargs: object) -> object:
        prompt_calls.append((args, kwargs))
        raise AssertionError("click.prompt should not be called when all answers are pre-filled")

    confirm_calls: list[tuple] = []

    def _fake_confirm(text: str, *args: object, **kwargs: object) -> bool:
        confirm_calls.append((text,))
        # Only the final "Confirm?" is allowed.  Any per-question bool prompt
        # would also land here, so fail unless this is the final confirm.
        if text != "Confirm?":
            raise AssertionError(
                f"click.confirm should not be called for questions; got {text!r}"
            )
        return True

    monkeypatch.setattr(mod.click, "prompt", _fake_prompt)
    monkeypatch.setattr(mod.click, "confirm", _fake_confirm)

    out = tmp_path / "profile.json"
    profile = run_intake_interactive(
        available_modalities=AVAILABLE_MODALITIES,
        pre_filled=_all_defaults_pre_filled(),
        out_path=out,
    )

    assert prompt_calls == []
    # Exactly one confirm — the final one.
    assert len(confirm_calls) == 1
    assert profile.manuscript_anchor == "none"
    assert profile.factorial_design is False
    assert out.exists()


def test_low_confidence_pre_fill_is_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Pre-filled answers with confidence < 0.7 should NOT skip the prompt."""
    from panelforge_figures.manifest import intake as mod

    pre = _all_defaults_pre_filled()
    # Drop confidence on factorial_design below threshold
    pre["factorial_design"] = IntakeAnswer(
        question_id=1,
        field_name="factorial_design",
        value=False,
        source="inferred",
        confidence=0.4,
    )

    confirm_seen: list[str] = []

    def _fake_confirm(text: str, *args: object, **kwargs: object) -> bool:
        confirm_seen.append(text)
        return True if text == "Confirm?" else False     # any other confirm = "no"

    monkeypatch.setattr(mod.click, "confirm", _fake_confirm)

    # Other prompts (none should fire because everything else is high-conf)
    def _fake_prompt(*a: object, **kw: object) -> object:
        raise AssertionError(f"unexpected click.prompt call: {a!r} {kw!r}")

    monkeypatch.setattr(mod.click, "prompt", _fake_prompt)

    profile = run_intake_interactive(
        available_modalities=AVAILABLE_MODALITIES,
        pre_filled=pre,
        out_path=tmp_path / "profile.json",
    )

    # The factorial_design confirm prompt must have been asked.
    assert any("factorial design" in c.lower() for c in confirm_seen)
    assert profile.factorial_design is False


def test_conservative_defaults_yield_spec_defaults(tmp_path: Path) -> None:
    """Pre-fill every answer with its default → resulting profile is all-defaults."""
    pre = _all_defaults_pre_filled()
    profile = _profile_from_answers(pre, available_modalities=AVAILABLE_MODALITIES)

    assert profile.manuscript_anchor == "none"
    assert profile.factorial_design is False
    assert profile.equivalence_claims is False
    assert profile.dynamics_needed == "static"
    assert profile.dimensionality == "2D"
    assert profile.shortlist_size == 12
    # Empty modalities answer → ALL available modalities included.
    assert profile.modalities_in_scope == AVAILABLE_MODALITIES
    # Empty hard_filters answer → all filter keys present and False.
    assert set(profile.hard_filters.keys()) == set(HARD_FILTER_KEYS)
    assert all(v is False for v in profile.hard_filters.values())


# ─────────────────────────── output file tests ───────────────────────────


def test_profile_json_written_to_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from panelforge_figures.manifest import intake as mod

    def _yes(*a: object, **kw: object) -> bool:
        return True

    def _no_prompt(*a: object, **kw: object) -> object:
        raise AssertionError("no prompts expected")

    monkeypatch.setattr(mod.click, "confirm", _yes)
    monkeypatch.setattr(mod.click, "prompt", _no_prompt)

    out = tmp_path / "panelforge_workspace" / "profile.json"
    profile = run_intake_interactive(
        available_modalities=AVAILABLE_MODALITIES,
        pre_filled=_all_defaults_pre_filled(),
        out_path=out,
    )

    assert out.is_file()
    data = json.loads(out.read_text())

    # Every ProjectProfile field round-trips
    expected = _profile_to_dict(profile)
    assert data == expected

    # Spot-check: defaults landed on disk
    assert data["manuscript_anchor"] == "none"
    assert data["shortlist_size"] == 12
    assert data["modalities_in_scope"] == list(AVAILABLE_MODALITIES)
    assert data["hard_filters"] == {k: False for k in HARD_FILTER_KEYS}


def test_project_profile_is_frozen_dataclass() -> None:
    """The fall-back ProjectProfile must be hashable/frozen like the real one."""
    p = ProjectProfile(
        manuscript_anchor="none",
        factorial_design=False,
        equivalence_claims=False,
        dynamics_needed="static",
        dimensionality="2D",
        modalities_in_scope=("a", "b"),
        hard_filters={k: False for k in HARD_FILTER_KEYS},
        shortlist_size=12,
    )
    # frozen → cannot mutate
    with pytest.raises(Exception):
        p.shortlist_size = 7  # type: ignore[misc]


# ──────────────────────── helper: Click smoke wrapper ────────────────────


def _intake_as_click_cmd(
    pre_filled: dict[str, IntakeAnswer],
    modalities: tuple[str, ...],
    out: Path,
):
    """Wrap :func:`run_intake_interactive` as a Click command for CliRunner."""
    import click as _click

    @_click.command()
    def _cmd() -> None:
        run_intake_interactive(
            available_modalities=modalities,
            pre_filled=pre_filled,
            out_path=out,
        )

    return _cmd
