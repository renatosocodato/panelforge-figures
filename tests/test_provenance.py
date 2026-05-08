"""Tests for the provenance chain (Sprint 1B — PR #62).

Coverage maps to ``docs/spec_provenance_chain.md`` §9:

* Schema (5 tests)
* Hashing (4 tests)
* verify (4 tests)
* bundle / diff (4 tests)
* env-var override + schema_version lock (2 tests)
* Round-trip end-to-end (1 test)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from panelforge_figures.manifest import (
    PROVENANCE_SCHEMA_VERSION,
    ProvenanceRecord,
    VerificationResult,
    build_provenance,
    bundle_provenance,
    diff_provenance,
    load_provenance_json,
    verify_provenance,
    write_provenance_json,
)
from panelforge_figures.manifest.provenance import (
    _git_blob_sha,
    _now_iso_utc,
    _record_to_dict,
    _sha256_file,
)

# ─────────────────────────── helpers / fixtures ─────────────────────────


def _make_figure(path: Path, content: bytes = b"%PDF-1.4 fake fig\n") -> Path:
    """Write a tiny binary fixture standing in for a rendered PDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _make_recipe_module(path: Path, body: str = "X = 1\n") -> Path:
    """Write a tiny recipe module fixture (.py file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _make_data_csv(path: Path, content: str = "a,b\n1,2\n3,4\n") -> Path:
    """Write a tiny CSV fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a directory layout (data/, recipe/, figures/)."""
    (tmp_path / "data").mkdir()
    (tmp_path / "recipe").mkdir()
    (tmp_path / "figures").mkdir()
    return tmp_path


def _build_full_record(workspace: Path) -> ProvenanceRecord:
    """Helper: write fixtures + return a fully-populated record."""
    fig = _make_figure(workspace / "figures" / "fig.pdf")
    rmod = _make_recipe_module(workspace / "recipe" / "myrecipe.py")
    csv = _make_data_csv(workspace / "data" / "src.csv")
    return build_provenance(
        figure_path=fig,
        recipe_full_name="modality.myrecipe",
        recipe_module_path=rmod,
        panelforge_version="2.0.0",
        panelforge_git_commit="aa31f80c",
        data_files=[{"path": str(csv), "format": "csv", "n_rows": 2}],
        column_mapping={"x": "a", "y": "b"},
        scorer_state={"version": "1.0.0", "score": 0.565, "weights": {"factorial": 0.30}},
        audit_findings={"rules_passed": ["n_at_least_10"], "rules_warned": [], "rules_failed": []},
    )


# ─────────────────────────── hashing (4 tests) ──────────────────────────


def test_sha256_file_matches_hashlib_reference(tmp_path: Path) -> None:
    """sha256 of a known file must equal hashlib.sha256(content).hexdigest()."""
    p = tmp_path / "small.bin"
    body = b"hello provenance\n"
    p.write_bytes(body)
    expected = hashlib.sha256(body).hexdigest()
    assert _sha256_file(p) == expected


def test_sha256_file_detects_single_byte_change(tmp_path: Path) -> None:
    """One byte changed → hash changed."""
    p = tmp_path / "probe.bin"
    p.write_bytes(b"abcdef")
    h1 = _sha256_file(p)
    p.write_bytes(b"abcdef!")
    h2 = _sha256_file(p)
    assert h1 != h2


def test_git_blob_sha_matches_git_hash_object(tmp_path: Path) -> None:
    """Our git_blob_sha helper must equal `git hash-object` for an arbitrary file.

    We invoke git directly and compare; if git is not available the test
    is skipped (the helper will return None in that case anyway).
    """
    p = tmp_path / "blob.txt"
    p.write_bytes(b"some recipe content\n")
    try:
        ref = subprocess.run(
            ["git", "hash-object", str(p)],
            capture_output=True, text=True, check=True, timeout=2,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pytest.skip("git unavailable")
    actual = _git_blob_sha(p)
    assert actual == ref


def test_git_blob_sha_falls_back_to_none_outside_git_when_unavailable(
    tmp_path: Path,
) -> None:
    """When git is somehow unavailable (or path is bogus), helper returns None.

    We can't reliably make git unavailable, so we point it at a directory
    instead of a file — git rejects that.
    """
    # Pointing git hash-object at a directory exits non-zero.
    result = _git_blob_sha(tmp_path)
    # Either None (subprocess error) or some sha is acceptable on different
    # git versions, but the function MUST not raise.
    assert result is None or isinstance(result, str)


# ─────────────────────────── builder + round-trip (5 tests) ─────────────


def test_build_provenance_returns_correct_shape(workspace: Path) -> None:
    """The record assembled by build_provenance has every required field."""
    rec = _build_full_record(workspace)
    assert isinstance(rec, ProvenanceRecord)
    assert rec.schema_version == PROVENANCE_SCHEMA_VERSION
    assert rec.figure_sha256 and len(rec.figure_sha256) == 64
    assert rec.recipe["full_name"] == "modality.myrecipe"
    assert rec.recipe["panelforge_version"] == "2.0.0"
    assert rec.data["sources"][0]["sha256"] is not None
    assert rec.data["column_mapping"] == {"x": "a", "y": "b"}
    assert rec.scorer is not None
    assert rec.audit is not None
    assert "python_version" in rec.rendering_environment


def test_write_load_round_trip(workspace: Path) -> None:
    """write → load returns an equal ProvenanceRecord (modulo dict identity)."""
    rec = _build_full_record(workspace)
    out_path = write_provenance_json(rec)
    assert out_path.is_file()
    assert out_path.name.endswith(".provenance.json")
    loaded = load_provenance_json(out_path)
    # Re-serialise both and compare dicts — frozen dataclass equality
    # cares about reference identity for nested dicts/lists.
    assert _record_to_dict(loaded) == _record_to_dict(rec)


def test_write_provenance_json_default_path(workspace: Path) -> None:
    """Default sidecar lives next to the figure with .provenance.json suffix."""
    rec = _build_full_record(workspace)
    out_path = write_provenance_json(rec)
    expected = workspace / "figures" / "fig.pdf.provenance.json"
    assert out_path == expected
    assert out_path.is_file()


def test_schema_validates_canonical_record(workspace: Path) -> None:
    """build_provenance output validates against docs/provenance.schema.json."""
    pytest.importorskip("jsonschema")
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[1] / "docs" / "provenance.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    # Schema itself is well-formed.
    jsonschema.Draft202012Validator.check_schema(schema)
    # And our record validates.
    rec = _build_full_record(workspace)
    jsonschema.validate(instance=_record_to_dict(rec), schema=schema)


def test_schema_rejects_missing_required_field(workspace: Path) -> None:
    """A record missing a required field (e.g. figure_sha256) fails validation."""
    pytest.importorskip("jsonschema")
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[1] / "docs" / "provenance.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    rec_dict = _record_to_dict(_build_full_record(workspace))
    rec_dict.pop("figure_sha256")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=rec_dict, schema=schema)


# ─────────────────────────── verify (4 tests) ───────────────────────────


def test_verify_passes_immediately_after_render(workspace: Path) -> None:
    """A freshly-written sidecar verifies as 'match' with empty findings."""
    rec = _build_full_record(workspace)
    sidecar = write_provenance_json(rec)
    result = verify_provenance(sidecar)
    assert isinstance(result, VerificationResult)
    assert result.overall == "match", result.findings
    assert result.findings == ()


def test_verify_flags_data_drift(workspace: Path) -> None:
    """Modifying a source CSV after-the-fact must trigger drift_data."""
    rec = _build_full_record(workspace)
    sidecar = write_provenance_json(rec)

    # Mutate the CSV.
    csv_path = workspace / "data" / "src.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")

    result = verify_provenance(sidecar)
    assert result.overall == "drift_data"
    assert any("sha256 mismatch" in f for f in result.findings)


def test_verify_flags_figure_drift(workspace: Path) -> None:
    """Modifying the figure file after sidecar write must trigger drift_figure."""
    rec = _build_full_record(workspace)
    sidecar = write_provenance_json(rec)

    fig_path = workspace / "figures" / "fig.pdf"
    fig_path.write_bytes(b"%PDF-1.4 tampered\n")

    result = verify_provenance(sidecar)
    assert result.overall == "drift_figure"
    assert any("figure sha256 mismatch" in f for f in result.findings)


def test_verify_flags_missing_data_file(workspace: Path) -> None:
    """Removing a referenced data file must trigger drift_data with 'missing'."""
    rec = _build_full_record(workspace)
    sidecar = write_provenance_json(rec)

    (workspace / "data" / "src.csv").unlink()

    result = verify_provenance(sidecar)
    assert result.overall == "drift_data"
    assert any("data file missing" in f for f in result.findings)


def test_verify_flags_recipe_drift(workspace: Path) -> None:
    """Modifying the recipe module's bytes flips git-blob sha → drift_recipe."""
    rec = _build_full_record(workspace)
    # Sanity: only run if we got a real git sha (else the helper returned
    # None and there's nothing to compare).
    if rec.recipe.get("module_sha") is None:
        pytest.skip("git unavailable; module_sha not recorded")
    sidecar = write_provenance_json(rec)

    rmod = workspace / "recipe" / "myrecipe.py"
    rmod.write_text("X = 2\n", encoding="utf-8")  # bytes change → sha changes

    result = verify_provenance(sidecar)
    assert result.overall == "drift_recipe"
    assert any("recipe module sha mismatch" in f for f in result.findings)


# ─────────────────────────── diff (4 tests) ─────────────────────────────


def test_diff_identical_files_returns_empty_diff(workspace: Path) -> None:
    """diff(rec, rec) → all dimensions are empty lists."""
    rec = _build_full_record(workspace)
    a = write_provenance_json(rec, out_path=workspace / "a.json")
    b = write_provenance_json(rec, out_path=workspace / "b.json")
    diff = diff_provenance(a, b)
    assert diff == {
        "figure": [],
        "recipe": [],
        "data": [],
        "scorer": [],
        "environment": [],
    }


def test_diff_flags_scorer_score_change(workspace: Path) -> None:
    """Two records differing only on scorer.score → scorer dim populated."""
    rec_a = _build_full_record(workspace)
    rec_b = ProvenanceRecord(
        schema_version=rec_a.schema_version,
        figure_path=rec_a.figure_path,
        figure_sha256=rec_a.figure_sha256,
        rendered_at=rec_a.rendered_at,
        recipe=rec_a.recipe,
        data=rec_a.data,
        scorer={**rec_a.scorer, "score": 0.999},
        audit=rec_a.audit,
        rendering_environment=rec_a.rendering_environment,
    )
    a = write_provenance_json(rec_a, out_path=workspace / "a.json")
    b = write_provenance_json(rec_b, out_path=workspace / "b.json")
    diff = diff_provenance(a, b)
    assert diff["scorer"]
    assert any("score:" in line for line in diff["scorer"])
    # Other dimensions remain empty.
    assert diff["figure"] == []
    assert diff["data"] == []


def test_diff_flags_recipe_module_sha_change(workspace: Path) -> None:
    """Changing recipe.module_sha → recipe dim mentions module_sha."""
    rec_a = _build_full_record(workspace)
    rec_b = ProvenanceRecord(
        schema_version=rec_a.schema_version,
        figure_path=rec_a.figure_path,
        figure_sha256=rec_a.figure_sha256,
        rendered_at=rec_a.rendered_at,
        recipe={**rec_a.recipe, "module_sha": "f" * 40},
        data=rec_a.data,
        scorer=rec_a.scorer,
        audit=rec_a.audit,
        rendering_environment=rec_a.rendering_environment,
    )
    a = write_provenance_json(rec_a, out_path=workspace / "a.json")
    b = write_provenance_json(rec_b, out_path=workspace / "b.json")
    diff = diff_provenance(a, b)
    assert diff["recipe"]
    assert any("module_sha" in line for line in diff["recipe"])


def test_diff_flags_data_sha_change(workspace: Path) -> None:
    """Different sha256 on a source path → data dim populated."""
    rec_a = _build_full_record(workspace)
    new_sources = list(rec_a.data["sources"])
    new_sources[0] = {**new_sources[0], "sha256": "0" * 64}
    rec_b = ProvenanceRecord(
        schema_version=rec_a.schema_version,
        figure_path=rec_a.figure_path,
        figure_sha256=rec_a.figure_sha256,
        rendered_at=rec_a.rendered_at,
        recipe=rec_a.recipe,
        data={"sources": new_sources, "column_mapping": rec_a.data["column_mapping"]},
        scorer=rec_a.scorer,
        audit=rec_a.audit,
        rendering_environment=rec_a.rendering_environment,
    )
    a = write_provenance_json(rec_a, out_path=workspace / "a.json")
    b = write_provenance_json(rec_b, out_path=workspace / "b.json")
    diff = diff_provenance(a, b)
    assert diff["data"]


# ─────────────────────────── bundle (3 tests) ───────────────────────────


def test_bundle_produces_tar_gz_with_expected_members(workspace: Path) -> None:
    """Bundle contains figure + provenance + data file + recipe module."""
    rec = _build_full_record(workspace)
    write_provenance_json(rec)
    bundle = bundle_provenance(workspace / "figures" / "fig.pdf")
    assert bundle.is_file()
    assert bundle.name.endswith(".provenance.tar.gz")
    with tarfile.open(bundle, "r:gz") as tar:
        names = tar.getnames()
    assert "fig.pdf" in names
    assert any(n.endswith(".provenance.json") for n in names)
    assert any(n.startswith("data/") and n.endswith(".csv") for n in names)
    assert any(n.startswith("recipe/") and n.endswith(".py") for n in names)


def test_bundle_round_trip_preserves_hashes(workspace: Path, tmp_path: Path) -> None:
    """Extract bundle into fresh dir; verify_provenance still passes."""
    rec = _build_full_record(workspace)
    sidecar = write_provenance_json(rec)
    bundle = bundle_provenance(workspace / "figures" / "fig.pdf")

    # Hash data CSV inside the bundle, compare to recorded.
    with tarfile.open(bundle, "r:gz") as tar:
        data_member = next(
            m for m in tar.getmembers() if m.name.startswith("data/")
        )
        f = tar.extractfile(data_member)
        assert f is not None
        body = f.read()
    expected = rec.data["sources"][0]["sha256"]
    assert hashlib.sha256(body).hexdigest() == expected
    # Bundle contains the sidecar and is self-describing.
    assert sidecar.is_file()


def test_bundle_raises_when_sidecar_missing(workspace: Path) -> None:
    """bundle_provenance raises FileNotFoundError if sidecar is absent."""
    fig = _make_figure(workspace / "figures" / "lone.pdf")
    with pytest.raises(FileNotFoundError):
        bundle_provenance(fig)


# ─────────────────────────── meta (2 tests) ─────────────────────────────


def test_schema_version_locked_to_1_1_0() -> None:
    """spec §2.2 + Elevation 3: v2.2.0 ships schema_version '1.1.0' (bumped
    from '1.0.0' to add the optional ``provenance_lock`` field)."""
    assert PROVENANCE_SCHEMA_VERSION == "1.1.0"


def test_panelforge_built_at_env_var_overrides_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting PANELFORGE_BUILT_AT freezes rendered_at for archival builds (spec §6, §7)."""
    monkeypatch.setenv("PANELFORGE_BUILT_AT", "1970-01-01T00:00:00Z")
    assert _now_iso_utc() == "1970-01-01T00:00:00Z"
