"""8-question interactive intake for the recipe-discovery system.

Wave 2 — see ``RECIPE_DISCOVERY_SYSTEM.md`` §4.

The intake walks 8 fixed-order questions (most discriminating first) and
emits a :class:`ProjectProfile` written to ``panelforge_workspace/profile.json``.

Design notes
------------
* The question definitions live in :data:`INTAKE_QUESTIONS`, a tuple of
  :class:`IntakeQuestion`.  These are pure data so that Wave 3's
  ``project_scan.py`` can pre-fill answers without prompting and
  ``recipes_index.json`` can embed the question list.
* The interactive driver :func:`run_intake_interactive` is a thin Click
  prompt loop that delegates to :func:`_apply_answer` per question.
  All non-Click work happens in helpers so the logic is reusable.
* Pre-filled answers with ``confidence >= 0.7`` skip the prompt and
  echo a short ``[auto]`` line so the user can see what was inferred.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click

# ProjectProfile lives in the sibling scoring module (W2-Agent-B).  If that
# module has not landed yet we fall back to a local copy with the exact
# same field signature so this module remains importable on its own.
try:
    from .scoring import ProjectProfile  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover — exercised only before scoring lands
    @dataclass(frozen=True)
    class ProjectProfile:  # type: ignore[no-redef]
        manuscript_anchor: str
        factorial_design: bool
        equivalence_claims: bool
        dynamics_needed: str
        dimensionality: str
        modalities_in_scope: tuple[str, ...]
        hard_filters: dict[str, bool]
        shortlist_size: int = 12


# ───────────────────────────── data classes ─────────────────────────────


@dataclass(frozen=True)
class IntakeAnswer:
    """A single answer collected (or pre-filled) for one intake question."""

    question_id: int
    field_name: str
    value: Any
    source: str = "user"            # "user" | "default" | "inferred"
    confidence: float = 1.0


@dataclass(frozen=True)
class IntakeQuestion:
    """Static specification of one intake question.

    These are serialisable (see :func:`intake_questions_for_index`) so
    Wave 3 agents can read them out of ``recipes_index.json`` without
    importing this module.
    """

    id: int
    field_name: str
    prompt: str
    type: str                       # "bool" | "choice" | "multi_choice" | "int"
    choices: tuple[str, ...] = ()
    default: Any = None
    description: str = ""


# Hard-filter slugs accepted in question 7.  Kept in sync with the spec.
HARD_FILTER_KEYS: tuple[str, ...] = (
    "compartment_aware",
    "scale_aware",
    "factorial_only",
)


# Order matches the scoring weight order — most discriminating first.
INTAKE_QUESTIONS: tuple[IntakeQuestion, ...] = (
    IntakeQuestion(
        id=1,
        field_name="factorial_design",
        prompt="Is your project a factorial design (e.g. 2x2 sex x genotype)?",
        type="bool",
        default=False,
        description=(
            "Factorial designs unlock interaction-aware recipes "
            "(forest plots with interaction terms, ANOVA layouts)."
        ),
    ),
    IntakeQuestion(
        id=2,
        field_name="equivalence_claims",
        prompt="Will you make equivalence / null-accepting claims (TOST-style)?",
        type="bool",
        default=False,
        description=(
            "Toggles TOST bound recipes and equivalence-band overlays "
            "instead of plain difference-from-zero plots."
        ),
    ),
    IntakeQuestion(
        id=3,
        field_name="manuscript_anchor",
        prompt="Is the project anchored to a specific manuscript?",
        type="choice",
        choices=("CDC42", "DISC1", "both", "none"),
        default="none",
        description=(
            "Anchoring biases shortlists toward the named manuscript's "
            "companion pack; 'both' interleaves and 'none' uses generic priors."
        ),
    ),
    IntakeQuestion(
        id=4,
        field_name="dynamics_needed",
        prompt="What time treatment do you need?",
        type="choice",
        choices=("static", "kymograph", "live", "ordered_pseudotime", "mixed"),
        default="static",
        description=(
            "Drives whether kymograph, live-imaging, or pseudotime "
            "recipes are eligible at all."
        ),
    ),
    IntakeQuestion(
        id=5,
        field_name="dimensionality",
        prompt="Spatial dimensionality?",
        type="choice",
        choices=("2D", "3D", "mixed"),
        default="2D",
        description="Toggles z-stack / volumetric recipes.",
    ),
    IntakeQuestion(
        id=6,
        field_name="modalities_in_scope",
        prompt="Which modalities are in scope?",
        type="multi_choice",
        choices=(),                  # filled in at runtime from the registry
        default=None,                # None means "all available"
        description=(
            "Comma-separated subset of the registry's modality names; "
            "empty answer = include all."
        ),
    ),
    IntakeQuestion(
        id=7,
        field_name="hard_filters",
        prompt="Hard filters — any required?",
        type="multi_choice",
        choices=HARD_FILTER_KEYS,
        default=(),
        description=(
            "Comma-separated subset of "
            f"{', '.join(HARD_FILTER_KEYS)}; "
            "empty answer = no hard filters."
        ),
    ),
    IntakeQuestion(
        id=8,
        field_name="shortlist_size",
        prompt="Shortlist size?",
        type="int",
        default=12,
        description="Number of recipes the scorer will return.",
    ),
)


# ─────────────────────────── pure helpers ───────────────────────────────


def _parse_multi_choice(raw: str, valid: tuple[str, ...]) -> tuple[str, ...]:
    """Parse a comma/space separated answer; validate against ``valid``.

    An empty string maps to an empty tuple.  Caller decides whether
    that means "all" or "none".
    """
    if not raw or not raw.strip():
        return ()
    tokens = [t.strip() for t in raw.replace(",", " ").split() if t.strip()]
    bad = [t for t in tokens if t not in valid]
    if bad:
        raise click.BadParameter(
            f"unknown values: {', '.join(bad)} (valid: {', '.join(valid)})"
        )
    # de-duplicate while preserving order
    seen: dict[str, None] = {}
    for t in tokens:
        seen.setdefault(t, None)
    return tuple(seen.keys())


def _hard_filters_from_tokens(tokens: tuple[str, ...]) -> dict[str, bool]:
    """Build the ``hard_filters`` mapping from a list of selected slugs."""
    return {k: (k in tokens) for k in HARD_FILTER_KEYS}


def _profile_from_answers(
    answers: dict[str, IntakeAnswer],
    *,
    available_modalities: tuple[str, ...],
) -> ProjectProfile:
    """Assemble a :class:`ProjectProfile` from the answer dict."""
    # modalities_in_scope: None / empty tuple → include all
    modalities_value = answers["modalities_in_scope"].value
    if modalities_value is None or len(modalities_value) == 0:
        modalities = tuple(available_modalities)
    else:
        modalities = tuple(modalities_value)

    hf_value = answers["hard_filters"].value
    if isinstance(hf_value, dict):
        hard_filters = {k: bool(hf_value.get(k, False)) for k in HARD_FILTER_KEYS}
    else:
        hard_filters = _hard_filters_from_tokens(tuple(hf_value or ()))

    return ProjectProfile(
        manuscript_anchor=str(answers["manuscript_anchor"].value),
        factorial_design=bool(answers["factorial_design"].value),
        equivalence_claims=bool(answers["equivalence_claims"].value),
        dynamics_needed=str(answers["dynamics_needed"].value),
        dimensionality=str(answers["dimensionality"].value),
        modalities_in_scope=modalities,
        hard_filters=hard_filters,
        shortlist_size=int(answers["shortlist_size"].value),
    )


def _profile_to_yaml_block(profile: ProjectProfile) -> str:
    """Render a tiny human-readable YAML-ish summary for the confirm step.

    Intentionally hand-rolled: avoids pulling pyyaml just for one block
    and keeps the order stable / readable for the user.
    """
    lines = [
        "project_profile:",
        f"  manuscript_anchor:  {profile.manuscript_anchor}",
        f"  factorial_design:   {str(profile.factorial_design).lower()}",
        f"  equivalence_claims: {str(profile.equivalence_claims).lower()}",
        f"  dynamics_needed:    {profile.dynamics_needed}",
        f"  dimensionality:     {profile.dimensionality}",
        f"  shortlist_size:     {profile.shortlist_size}",
        "  modalities_in_scope:",
    ]
    for m in profile.modalities_in_scope:
        lines.append(f"    - {m}")
    lines.append("  hard_filters:")
    for k in HARD_FILTER_KEYS:
        lines.append(f"    {k}: {str(profile.hard_filters.get(k, False)).lower()}")
    return "\n".join(lines)


# ─────────────────────────── prompt I/O ─────────────────────────────────


def _prompt_one(q: IntakeQuestion, *, available_modalities: tuple[str, ...]) -> Any:
    """Render the appropriate Click prompt for ``q`` and return the value."""
    if q.type == "bool":
        return click.confirm(q.prompt, default=bool(q.default))

    if q.type == "choice":
        # Click's Choice handles validation + case-insensitive default.
        return click.prompt(
            q.prompt,
            type=click.Choice(q.choices, case_sensitive=False),
            default=q.default,
            show_choices=True,
        )

    if q.type == "int":
        return click.prompt(q.prompt, type=int, default=int(q.default))

    if q.type == "multi_choice":
        valid = q.choices or available_modalities
        default_display = (
            "(all)" if q.field_name == "modalities_in_scope" else "(none)"
        )
        click.echo(f"  available: {', '.join(valid)}")
        raw = click.prompt(
            f"{q.prompt} [comma-separated, blank = {default_display}]",
            default="",
            show_default=False,
        )
        return _parse_multi_choice(raw, tuple(valid))

    raise ValueError(f"unknown question type: {q.type}")


def _apply_answer(
    q: IntakeQuestion,
    pre_filled: dict[str, IntakeAnswer] | None,
    *,
    available_modalities: tuple[str, ...],
) -> IntakeAnswer:
    """Resolve answer for ``q``: honour pre-fill (conf >= 0.7) else prompt."""
    pf = (pre_filled or {}).get(q.field_name)
    if pf is not None and pf.confidence >= 0.7:
        click.echo(f"  [auto] {q.field_name} = {pf.value!r}  (conf={pf.confidence:.2f})")
        return pf

    value = _prompt_one(q, available_modalities=available_modalities)
    return IntakeAnswer(
        question_id=q.id,
        field_name=q.field_name,
        value=value,
        source="user",
    )


# ─────────────────────────── public API ─────────────────────────────────


def run_intake_interactive(
    *,
    available_modalities: tuple[str, ...],
    pre_filled: dict[str, IntakeAnswer] | None = None,
    out_path: Path = Path("panelforge_workspace/profile.json"),
) -> ProjectProfile:
    """Walk the 8-question intake and write ``profile.json``.

    Parameters
    ----------
    available_modalities
        Modalities visible to question 6.  Wave 3 supplies the registry list.
    pre_filled
        Optional ``{field_name: IntakeAnswer}`` map.  Answers with
        ``confidence >= 0.7`` skip the prompt; lower-confidence entries
        are ignored (the user is asked instead).
    out_path
        Where to write the assembled :class:`ProjectProfile` JSON.

    Returns
    -------
    ProjectProfile
        The confirmed profile.  If the user rejects at the confirm step,
        :class:`click.Abort` is raised.
    """
    click.echo("panelforge-figures intake — 8 questions")
    click.echo("(press Enter to accept the default shown in [brackets])")
    click.echo("")

    answers: dict[str, IntakeAnswer] = {}
    for q in INTAKE_QUESTIONS:
        click.echo(f"[{q.id}/8] {q.description}" if q.description else f"[{q.id}/8]")
        ans = _apply_answer(q, pre_filled, available_modalities=available_modalities)
        answers[q.field_name] = ans
        click.echo("")

    profile = _profile_from_answers(answers, available_modalities=available_modalities)

    click.echo("Assembled profile:")
    click.echo("")
    click.echo(_profile_to_yaml_block(profile))
    click.echo("")
    if not click.confirm("Confirm?", default=True):
        raise click.Abort()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(_profile_to_dict(profile), indent=2, sort_keys=True) + "\n"
    )
    click.echo(f"wrote {out_path}")
    return profile


def _profile_to_dict(profile: ProjectProfile) -> dict[str, Any]:
    """Stable JSON-serialisable representation of :class:`ProjectProfile`."""
    return {
        "manuscript_anchor": profile.manuscript_anchor,
        "factorial_design": profile.factorial_design,
        "equivalence_claims": profile.equivalence_claims,
        "dynamics_needed": profile.dynamics_needed,
        "dimensionality": profile.dimensionality,
        "modalities_in_scope": list(profile.modalities_in_scope),
        "hard_filters": dict(profile.hard_filters),
        "shortlist_size": profile.shortlist_size,
    }


def intake_questions_for_index() -> list[dict[str, Any]]:
    """Serialise :data:`INTAKE_QUESTIONS` for embedding in ``recipes_index.json``.

    The output is JSON-safe (tuples → lists, no None defaults stripped)
    and includes every field of :class:`IntakeQuestion`.  The dataclass
    field-name order is preserved.
    """
    out: list[dict[str, Any]] = []
    for q in INTAKE_QUESTIONS:
        d = asdict(q)
        d["choices"] = list(d["choices"])
        out.append(d)
    return out


__all__ = [
    "HARD_FILTER_KEYS",
    "INTAKE_QUESTIONS",
    "IntakeAnswer",
    "IntakeQuestion",
    "ProjectProfile",
    "intake_questions_for_index",
    "run_intake_interactive",
]
