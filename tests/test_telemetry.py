"""Telemetry-channel tests (Sprint 3B — v1.13.0).

Covers the opt-in usage-telemetry channel landed alongside
``manifest/telemetry.py``.  The module under test:

* ``is_telemetry_enabled`` — reads ``panelforge.project.yaml``.
* ``log_invocation`` — writes one JSONL row per ``figures generate`` call.
* ``set_user_pick`` — backfills ``user_picked`` and computes
  ``rejected_higher_scored`` on the most recent (or session-matched) row.
* ``export_telemetry`` — emits a sanitized aggregated artifact.
* ``telemetry_log_path`` — resolves ``<project>/panelforge_workspace/usage.jsonl``.

The CLI smoke tests at the bottom drive the new ``figures telemetry`` and
``figures pick`` subcommands via Click's ``CliRunner``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from panelforge_figures.manifest.telemetry import (
    TelemetryError,
    export_telemetry,
    is_telemetry_enabled,
    log_invocation,
    set_user_pick,
    telemetry_log_path,
)

# ──────────────────────────────────────────────────────────────────────────
# Cluster 1 — opt-out by default
# ──────────────────────────────────────────────────────────────────────────


def test_default_install_no_telemetry(tmp_path: Path) -> None:
    """Empty project (no ``panelforge.project.yaml``) → telemetry off."""
    assert is_telemetry_enabled(tmp_path) is False
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    assert not telemetry_log_path(tmp_path).exists()


def test_explicit_off_no_telemetry(tmp_path: Path) -> None:
    """``telemetry: off`` in YAML → ``is_telemetry_enabled`` is False."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: off\n")
    assert is_telemetry_enabled(tmp_path) is False
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    assert not telemetry_log_path(tmp_path).exists()


def test_yaml_without_telemetry_key_no_telemetry(tmp_path: Path) -> None:
    """A YAML present but lacking the ``telemetry`` key still defaults off."""
    (tmp_path / "panelforge.project.yaml").write_text(
        "anchor: DISC1\nfactorial: false\n"
    )
    assert is_telemetry_enabled(tmp_path) is False


# ──────────────────────────────────────────────────────────────────────────
# Cluster 2 — opt-in writes correct schema
# ──────────────────────────────────────────────────────────────────────────


def test_opt_in_writes_correct_row(tmp_path: Path) -> None:
    """``telemetry: opt-in`` → exactly one schema-valid row per call."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    assert is_telemetry_enabled(tmp_path) is True

    log_invocation(
        tmp_path,
        profile={
            "modality": "live_imaging_2d",
            "factorial_design": "2x2_factorial",
            "equivalence_present": True,
            "anchor_strength": "established",
            "dynamics_kind": "time_lapse",
            "dimensionality": "2d",
            "shortlist_size": 12,
        },
        scored_top_5=[
            {
                "full_name": "live_imaging_2d.factorial_anchor_v3",
                "score": 0.685,
                "tags": {
                    "factorial": 1.0,
                    "equivalence": 1.0,
                    "anchor": 0.5,
                    "dynamics": 0.5,
                    "dimensionality": 1.0,
                },
            }
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    log_path = telemetry_log_path(tmp_path)
    assert log_path.exists()
    rows = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    r = rows[0]
    assert r["panelforge_version"] == "1.13.0"
    assert r["scoring_rubric_version"] == "1.0.0"
    assert r["user_picked"] is None
    assert r["rejected_higher_scored"] == []
    assert r["timestamp"].endswith("Z")
    assert len(r["session_id"]) >= 16
    assert r["profile"]["modality"] == "live_imaging_2d"
    assert r["scored_top_5"][0]["full_name"] == "live_imaging_2d.factorial_anchor_v3"


def test_opt_in_appends_per_call(tmp_path: Path) -> None:
    """Each ``log_invocation`` call appends a new row, never overwrites."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    for _ in range(3):
        log_invocation(
            tmp_path,
            profile={"modality": "live_imaging_2d"},
            scored_top_5=[
                {"full_name": "x", "score": 0.5, "tags": {}},
            ],
            panelforge_version="1.13.0",
            scoring_rubric_version="1.0.0",
        )
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 3
    # session_ids must be distinct (UUIDv4 per call)
    assert len({r["session_id"] for r in rows}) == 3


def test_opt_in_truncates_to_top_5(tmp_path: Path) -> None:
    """``scored_top_5`` is truncated to at most five rows even on a long input."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    long_list = [
        {"full_name": f"r{i}", "score": 0.9 - 0.05 * i, "tags": {}}
        for i in range(12)
    ]
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=long_list,
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert len(rows[0]["scored_top_5"]) == 5


# ──────────────────────────────────────────────────────────────────────────
# Cluster 3 — pick semantics
# ──────────────────────────────────────────────────────────────────────────


def test_pick_sets_user_picked_and_rejected(tmp_path: Path) -> None:
    """``set_user_pick`` records the pick and computes ``rejected_higher_scored``."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "a", "score": 0.9, "tags": {}},
            {"full_name": "b", "score": 0.7, "tags": {}},
            {"full_name": "c", "score": 0.5, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "b", session_id=sid)
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["user_picked"] == "b"
    assert rows[0]["rejected_higher_scored"] == ["a"]


def test_pick_top_recipe_has_empty_rejected(tmp_path: Path) -> None:
    """Picking the highest-scored recipe leaves ``rejected_higher_scored`` empty."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "top", "score": 0.9, "tags": {}},
            {"full_name": "mid", "score": 0.7, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "top", session_id=sid)
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["user_picked"] == "top"
    assert rows[0]["rejected_higher_scored"] == []


def test_pick_with_no_candidate_raises(tmp_path: Path) -> None:
    """``set_user_pick`` against a fresh workspace raises a friendly error."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    with pytest.raises(TelemetryError):
        set_user_pick(tmp_path, "x")


def test_pick_uses_most_recent_when_unambiguous(tmp_path: Path) -> None:
    """With one un-picked row, ``set_user_pick`` updates it without ``--session-id``."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "a", "score": 0.9, "tags": {}},
            {"full_name": "b", "score": 0.7, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "b")
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["user_picked"] == "b"


# ──────────────────────────────────────────────────────────────────────────
# Cluster 4 — export sanitization
# ──────────────────────────────────────────────────────────────────────────


def test_export_anonymizes_session_id(tmp_path: Path) -> None:
    """``--anonymize`` replaces ``session_id`` with ``sha256(sid)[:16]``."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "a", session_id=sid)
    out = tmp_path / "out.jsonl"
    n = export_telemetry(tmp_path, out, anonymize=True, drop_unpicked=True)
    assert n == 1
    rows = [
        json.loads(line)
        for line in out.read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["session_id"] != sid
    assert len(rows[0]["session_id"]) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", rows[0]["session_id"])


def test_export_drops_unpicked(tmp_path: Path) -> None:
    """``drop_unpicked=True`` keeps only rows with a recorded pick."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    # Row 1: pick recorded.
    sid1 = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "a", "score": 0.9, "tags": {}},
            {"full_name": "b", "score": 0.7, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "b", session_id=sid1)
    # Row 2: no pick recorded — should be dropped.
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "x", "score": 0.9, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    out = tmp_path / "out.jsonl"
    n = export_telemetry(tmp_path, out, anonymize=True, drop_unpicked=True)
    assert n == 1
    rows = [
        json.loads(line)
        for line in out.read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["user_picked"] == "b"


def test_export_keeps_unpicked_when_requested(tmp_path: Path) -> None:
    """``drop_unpicked=False`` keeps every row including ``user_picked: null``."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    out = tmp_path / "out.jsonl"
    n = export_telemetry(tmp_path, out, anonymize=True, drop_unpicked=False)
    assert n == 1


def test_export_no_anonymize_keeps_session_id(tmp_path: Path) -> None:
    """``--no-anonymize`` preserves the raw ``session_id``."""
    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "a", session_id=sid)
    out = tmp_path / "out.jsonl"
    export_telemetry(tmp_path, out, anonymize=False, drop_unpicked=True)
    rows = [
        json.loads(line)
        for line in out.read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["session_id"] == sid


# ──────────────────────────────────────────────────────────────────────────
# Cluster 5 — CLI smoke
# ──────────────────────────────────────────────────────────────────────────


def test_cli_telemetry_status_off(tmp_path: Path) -> None:
    """``figures telemetry status`` reports off on a fresh project."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main, ["telemetry", "status", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "off" in result.output.lower()


def test_cli_telemetry_status_opt_in(tmp_path: Path) -> None:
    """``figures telemetry status`` reports opt-in once a row exists."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    runner = CliRunner()
    result = runner.invoke(
        main, ["telemetry", "status", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "opt-in" in result.output.lower()
    assert "1" in result.output  # 1 row


def test_cli_pick_no_row(tmp_path: Path) -> None:
    """``figures pick`` against an empty workspace exits non-zero."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    runner = CliRunner()
    result = runner.invoke(
        main, ["pick", "x", "--project-root", str(tmp_path)]
    )
    assert result.exit_code != 0


def test_cli_pick_records_user_pick(tmp_path: Path) -> None:
    """``figures pick <full_name>`` updates the most recent row."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[
            {"full_name": "a", "score": 0.9, "tags": {}},
            {"full_name": "b", "score": 0.7, "tags": {}},
        ],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    runner = CliRunner()
    result = runner.invoke(
        main, ["pick", "b", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert rows[0]["user_picked"] == "b"


def test_cli_telemetry_export_writes_jsonl(tmp_path: Path) -> None:
    """``figures telemetry export <path>`` writes a sanitized artifact."""
    from click.testing import CliRunner

    from panelforge_figures.cli import main

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "a", session_id=sid)
    out = tmp_path / "exported.jsonl"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "telemetry",
            "export",
            str(out),
            "--project-root",
            str(tmp_path),
            "--anonymize",
            "--drop-unpicked",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    rows = [
        json.loads(line)
        for line in out.read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["session_id"] != sid


# ──────────────────────────────────────────────────────────────────────────
# Cluster 6 — data-class second gate (privacy-by-construction)
# ──────────────────────────────────────────────────────────────────────────
#
# ``log_invocation`` must bridge BOTH gates: the project-yaml opt-in
# (``is_telemetry_enabled``) *and* the data-class policy
# (``safety.is_telemetry_allowed`` / the resolved policy).  A clinical
# project forces telemetry OFF regardless of ``telemetry: opt-in``, so no
# ``usage.jsonl`` may be written.  Research/public keep the opt-in path.


@pytest.fixture
def _restore_data_class() -> Iterator[None]:
    """Reset the module-level data class to RESEARCH after the test so
    clinical state cannot leak into adjacent test modules."""
    from panelforge_figures.safety import DataClass, set_data_class

    try:
        yield
    finally:
        set_data_class(DataClass.RESEARCH)


def test_clinical_data_class_blocks_opt_in_telemetry(
    tmp_path: Path, _restore_data_class: object
) -> None:
    """``data_class=clinical`` + ``telemetry: opt-in`` → NO ``usage.jsonl``.

    The clinical policy forces telemetry OFF by construction; the
    project-yaml opt-in must not be able to re-enable it.
    """
    from panelforge_figures.safety import DataClass, set_data_class

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    # YAML gate is open …
    assert is_telemetry_enabled(tmp_path) is True
    # … but the data-class gate is closed.
    set_data_class(DataClass.CLINICAL)

    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "x", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )

    assert sid == ""
    assert not telemetry_log_path(tmp_path).exists()


def test_research_data_class_still_writes_opt_in_telemetry(
    tmp_path: Path, _restore_data_class: object
) -> None:
    """``data_class=research`` + ``telemetry: opt-in`` → row is written.

    The data-class second gate must not regress the opt-in path for
    non-clinical classes: research keeps recording when the project
    explicitly opts in.
    """
    from panelforge_figures.safety import DataClass, set_data_class

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    set_data_class(DataClass.RESEARCH)

    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "x", "score": 0.5, "tags": {}}],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )

    assert sid != ""
    assert telemetry_log_path(tmp_path).exists()
    rows = [
        json.loads(line)
        for line in telemetry_log_path(tmp_path).read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1


def test_public_data_class_still_writes_opt_in_telemetry(
    tmp_path: Path, _restore_data_class: object
) -> None:
    """``data_class=public`` + ``telemetry: opt-in`` → row is written."""
    from panelforge_figures.safety import DataClass, set_data_class

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    set_data_class(DataClass.PUBLIC)

    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[],
        panelforge_version="1.13.0",
        scoring_rubric_version="1.0.0",
    )

    assert sid != ""
    assert telemetry_log_path(tmp_path).exists()


# ──────────────────────────────────────────────────────────────────────────
# Cluster 7 — clinical gate covers the WRITE/READ paths too (re-audit #2)
# ──────────────────────────────────────────────────────────────────────────
#
# log_invocation no-ops under clinical, but the gate must also cover
# set_user_pick (writes usage.jsonl) and export_telemetry (reads it +
# writes a derived artifact) — otherwise a project written under research
# and later reclassified clinical could still mutate/leak telemetry.


def test_clinical_blocks_set_user_pick_on_existing_rows(
    tmp_path: Path, _restore_data_class: object
) -> None:
    """A row written under research must NOT be mutable once reclassified
    clinical: set_user_pick refuses and usage.jsonl stays byte-identical."""
    from panelforge_figures.safety import DataClass, set_data_class

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.0.0",
        scoring_rubric_version="1.0.0",
    )
    assert sid != ""
    log_path = telemetry_log_path(tmp_path)
    before = log_path.read_bytes()

    set_data_class(DataClass.CLINICAL)
    with pytest.raises(TelemetryError):
        set_user_pick(tmp_path, "a", session_id=sid)
    # No write occurred — the file is unchanged.
    assert log_path.read_bytes() == before


def test_clinical_blocks_export_telemetry(
    tmp_path: Path, _restore_data_class: object
) -> None:
    """export_telemetry must refuse under clinical — no read, no artifact."""
    from panelforge_figures.safety import DataClass, set_data_class

    (tmp_path / "panelforge.project.yaml").write_text("telemetry: opt-in\n")
    sid = log_invocation(
        tmp_path,
        profile={"modality": "live_imaging_2d"},
        scored_top_5=[{"full_name": "a", "score": 0.5, "tags": {}}],
        panelforge_version="1.0.0",
        scoring_rubric_version="1.0.0",
    )
    set_user_pick(tmp_path, "a", session_id=sid)  # legitimate, still research
    out = tmp_path / "export.jsonl"

    set_data_class(DataClass.CLINICAL)
    with pytest.raises(TelemetryError):
        export_telemetry(tmp_path, out, anonymize=True, drop_unpicked=True)
    assert not out.exists()
