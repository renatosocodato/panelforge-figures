"""Provenance chain — content-addressed sidecars for rendered figures.

Sprint 1B (PR #62) — see ``docs/spec_provenance_chain.md``.

Every rendered figure (PDF/PNG) gets a sidecar ``<figure>.provenance.json``
written next to it.  The sidecar content-addresses the figure back to (a)
its source data files, (b) the recipe module that produced it, (c) the
scorer state that selected it, and (d) the rendering environment.

The public API mirrors the spec §8 file plan:

* :func:`build_provenance` — assemble a :class:`ProvenanceRecord` from
  caller-supplied recipe + data + scorer + audit metadata.
* :func:`write_provenance_json` / :func:`load_provenance_json` —
  round-trip the sidecar to/from disk.
* :func:`verify_provenance` — recompute every hash from the sidecar's
  references and report drift by dimension.
* :func:`diff_provenance` — structurally diff two sidecars and report
  per-dimension changes.
* :func:`bundle_provenance` — produce a self-contained ``.tar.gz`` with
  figure + sidecar + referenced data files + recipe module.

Cryptographic posture: sha256 throughout, deliberately chosen over sha1
(broken collision resistance), sha512 (size, no security gain), and
BLAKE3 (third-party dep).  See spec §5.1 for rationale.

The schema_version is currently locked to ``"1.0.0"``; future bumps will
ship a migration script as a separate elevation (spec §12).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROVENANCE_SCHEMA_VERSION = "1.1.0"


# ─────────────────────────── data classes ───────────────────────────────


@dataclass(frozen=True)
class ProvenanceRecord:
    """Sidecar JSON content for one rendered figure.

    Mirrors the JSON-Schema in ``docs/provenance.schema.json``.

    Required fields:
      * ``schema_version`` — semver of the sidecar format (currently 1.0.0).
      * ``figure_path`` — repo-relative path to the figure file.
      * ``figure_sha256`` — sha256 hex digest of the figure's bytes.
      * ``rendered_at`` — ISO-8601 UTC timestamp.
      * ``recipe`` — ``{full_name, module_sha, module_path,
        panelforge_version, panelforge_git_commit}``.
      * ``data`` — ``{sources: [{path, sha256, format, n_rows}],
        column_mapping: {field: column}}``.

    Optional fields:
      * ``scorer`` — scorer state at the time of selection (None when
        rendered standalone; spec §2.2).
      * ``audit`` — ``{rules_passed, rules_warned, rules_failed}``
        (None if no audit ran).
      * ``rendering_environment`` — defaults to ``{}`` if empty.
    """

    schema_version: str
    figure_path: str
    figure_sha256: str
    rendered_at: str
    recipe: dict[str, Any]
    data: dict[str, Any]
    scorer: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    rendering_environment: dict[str, Any] = field(default_factory=dict)
    provenance_lock: dict[str, Any] | None = None
    """Optional reproducibility-envelope lock dict (Elevation 3, schema
    1.1.0). Embeds the contents of ``panelforge.lock.json`` (or a
    sub-dict thereof) so a sidecar carries enough environment+RNG+data
    state to attempt a byte-identical replay. Defaults to ``None`` for
    backwards compatibility — old (1.0.0) sidecars load cleanly with
    this field absent."""


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of :func:`verify_provenance`.

    ``overall`` is one of:

    * ``"match"`` — every recomputed hash matches the recorded value.
    * ``"drift_figure"`` — figure file missing or its sha256 has changed.
    * ``"drift_data"`` — at least one source data file is missing or
      its sha256 has changed.
    * ``"drift_recipe"`` — the recipe module's git-blob sha differs.
    * ``"drift_env"`` — environment drift detected (matplotlib version,
      platform); reserved for future strict-mode use.

    ``findings`` is a tuple of human-readable diff lines suitable for
    direct printing in the CLI.
    """

    figure_path: Path
    overall: str
    findings: tuple[str, ...]


# ─────────────────────────── hashing helpers ────────────────────────────


def _sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes (streaming, 64 KB chunks)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_blob_sha(path: Path) -> str | None:
    """git ``hash-object`` equivalent for ``path``.

    Returns the sha1 of git's blob format ("blob <size>\\0<content>"),
    which is what git uses to address blobs.  Falling back to a sha256
    of the raw bytes happens at the call-site when None is returned —
    the spec (§2.2) accepts either, and ``verify_provenance`` only
    compares values that were both produced by the same routine.

    Returns None if not in a git tree, git is unavailable, or the
    subprocess fails (e.g. permission denied).
    """
    try:
        result = subprocess.run(
            ["git", "hash-object", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _now_iso_utc() -> str:
    """ISO-8601 UTC timestamp truncated to seconds.

    The ``PANELFORGE_BUILT_AT`` environment variable, when set, overrides
    the wall-clock time — used by ``--committed`` (spec §7) for
    deterministic timestamps in archival renders.
    """
    env = os.environ.get("PANELFORGE_BUILT_AT")
    if env:
        return env.strip()
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _matplotlib_version() -> str:
    """Return the installed matplotlib version, or 'unknown' if missing."""
    try:
        import matplotlib

        return matplotlib.__version__
    except ImportError:
        return "unknown"


# ─────────────────────────── builder ────────────────────────────────────


def build_provenance(
    *,
    figure_path: Path,
    recipe_full_name: str,
    recipe_module_path: Path,
    panelforge_version: str,
    panelforge_git_commit: str,
    data_files: list[dict[str, Any]],
    column_mapping: dict[str, str] | None = None,
    scorer_state: dict[str, Any] | None = None,
    audit_findings: dict[str, Any] | None = None,
    provenance_lock: dict[str, Any] | None = None,
) -> ProvenanceRecord:
    """Compute the full provenance record for a rendered figure.

    Parameters
    ----------
    figure_path
        Path to the rendered PDF/PNG.  Hashed bytes of this file end up
        in ``figure_sha256``.
    recipe_full_name
        Dotted ``modality.recipe`` identifier.
    recipe_module_path
        Path to the recipe's ``.py`` file.  Hashed via ``git hash-object``
        when available so it matches the shas a reader would compute
        from a git checkout.
    panelforge_version
        ``panelforge_figures.__version__``; recorded for environment drift.
    panelforge_git_commit
        Full git HEAD sha at render time (or ``"uncommitted"`` if dirty).
    data_files
        List of ``{path, format?, n_rows?}`` dicts — one per source data
        file.  ``sha256`` is computed here from the file bytes; the
        caller does not need to pre-hash.
    column_mapping
        Verbatim binding from the intake step (contract field → column).
    scorer_state
        Whatever the scorer wants to record (weights, tied_with, etc.).
        Pass ``None`` if the recipe was rendered standalone.
    audit_findings
        Whatever the statistical audit wants to record (passed/warned/
        failed rule_ids).  Pass ``None`` if no audit ran.

    The function does not validate that referenced files exist beyond
    what's needed to compute hashes — for missing source files, the
    ``sha256`` value is set to ``None`` and surfaces in
    ``verify_provenance`` later.
    """
    # Hash source data files.
    # Sprint 2B (v1.11.0) — clinical class redacts the sha256 of data
    # files while preserving path/format/n_rows so the sidecar still
    # documents *which* files were used without leaking a hash that
    # might be used as a row-level fingerprint downstream.  See
    # ``docs/spec_data_class_safety.md`` §6 (Provenance hash row).
    from ..safety import should_redact_provenance_hashes
    redact_hashes = should_redact_provenance_hashes()

    data_records = []
    for df in data_files:
        df_path = Path(df["path"])
        if redact_hashes:
            sha = "[redacted]"
        elif df_path.is_file():
            sha = _sha256_file(df_path)
        else:
            sha = None
        rec = {
            "path": str(df_path),
            "sha256": sha,
            "format": df.get("format", df_path.suffix.lstrip(".")),
            "n_rows": df.get("n_rows"),
        }
        data_records.append(rec)

    return ProvenanceRecord(
        schema_version=PROVENANCE_SCHEMA_VERSION,
        figure_path=str(figure_path),
        figure_sha256=_sha256_file(figure_path),
        rendered_at=_now_iso_utc(),
        recipe={
            "full_name": recipe_full_name,
            "module_sha": _git_blob_sha(recipe_module_path),
            "module_path": str(recipe_module_path),
            "panelforge_version": panelforge_version,
            "panelforge_git_commit": panelforge_git_commit,
        },
        data={
            "sources": data_records,
            "column_mapping": column_mapping or {},
        },
        scorer=scorer_state,
        audit=audit_findings,
        rendering_environment={
            "python_version": ".".join(map(str, sys.version_info[:3])),
            "matplotlib_version": _matplotlib_version(),
            "platform": platform.system().lower(),
        },
        provenance_lock=provenance_lock,
    )


# ─────────────────────────── (de)serialisation ──────────────────────────


def _record_to_dict(record: ProvenanceRecord) -> dict[str, Any]:
    """Serialise a :class:`ProvenanceRecord` to a JSON-friendly dict.

    ``scorer`` and ``audit`` are dropped from the dict when ``None`` so
    sidecars stay minimal — they remain optional in the schema.
    """
    d: dict[str, Any] = {
        "schema_version": record.schema_version,
        "figure_path": record.figure_path,
        "figure_sha256": record.figure_sha256,
        "rendered_at": record.rendered_at,
        "recipe": record.recipe,
        "data": record.data,
        "rendering_environment": record.rendering_environment,
    }
    if record.scorer is not None:
        d["scorer"] = record.scorer
    if record.audit is not None:
        d["audit"] = record.audit
    if record.provenance_lock is not None:
        d["provenance_lock"] = record.provenance_lock
    return d


def write_provenance_json(
    record: ProvenanceRecord,
    *,
    out_path: Path | None = None,
) -> Path:
    """Write a provenance.json sidecar; default path is ``<figure>.provenance.json``.

    Output is pretty-printed with ``indent=2`` and ``sort_keys=True`` for
    git-friendly diffing.  A trailing newline is appended so POSIX tools
    (``cat``, ``diff``) treat the file as a proper text file.
    """
    fig_path = Path(record.figure_path)
    if out_path is None:
        out_path = fig_path.with_suffix(fig_path.suffix + ".provenance.json")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(_record_to_dict(record), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def load_provenance_json(path: Path) -> ProvenanceRecord:
    """Load a provenance.json sidecar and return its :class:`ProvenanceRecord`.

    Missing optional keys (``scorer``, ``audit``, ``rendering_environment``)
    fall back to ``None`` / empty dict, matching the dataclass defaults.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ProvenanceRecord(
        schema_version=data["schema_version"],
        figure_path=data["figure_path"],
        figure_sha256=data["figure_sha256"],
        rendered_at=data["rendered_at"],
        recipe=data["recipe"],
        data=data["data"],
        scorer=data.get("scorer"),
        audit=data.get("audit"),
        rendering_environment=data.get("rendering_environment", {}),
        provenance_lock=data.get("provenance_lock"),
    )


# ─────────────────────────── verify ─────────────────────────────────────


def verify_provenance(provenance_path: Path) -> VerificationResult:
    """Recompute every hash referenced by ``provenance_path`` and flag drift.

    Steps (subset of spec §3.2; full re-render lives in the CLI layer):

    1. Verify the figure file exists and its sha256 still matches.
    2. Verify each source data file exists and its sha256 still matches.
    3. Verify the recipe module's git-blob sha still matches.

    The first dimension that drifts wins the ``overall`` slot, but
    ``findings`` accumulates *every* divergence so the user sees the
    full diff in one pass.
    """
    record = load_provenance_json(provenance_path)
    findings: list[str] = []
    drift: str | None = None

    # Verify figure file.
    fig_path = Path(record.figure_path)
    if not fig_path.is_file():
        findings.append(f"figure missing: {fig_path}")
        return VerificationResult(fig_path, "drift_figure", tuple(findings))
    actual_fig_sha = _sha256_file(fig_path)
    if actual_fig_sha != record.figure_sha256:
        findings.append(
            f"figure sha256 mismatch: expected {record.figure_sha256[:8]}..., "
            f"got {actual_fig_sha[:8]}..."
        )
        drift = drift or "drift_figure"

    # Verify each source data file.
    for src in record.data.get("sources", []):
        src_path = Path(src["path"])
        if not src_path.is_file():
            findings.append(f"data file missing: {src_path}")
            drift = drift or "drift_data"
            continue
        actual_sha = _sha256_file(src_path)
        if src.get("sha256") and actual_sha != src["sha256"]:
            findings.append(
                f"data sha256 mismatch ({src_path.name}): "
                f"expected {src['sha256'][:8]}..., got {actual_sha[:8]}..."
            )
            drift = drift or "drift_data"

    # Verify recipe module.
    recipe_path = Path(record.recipe.get("module_path", ""))
    if recipe_path.is_file():
        actual_recipe_sha = _git_blob_sha(recipe_path)
        recorded = record.recipe.get("module_sha")
        if (
            recorded
            and actual_recipe_sha
            and actual_recipe_sha != recorded
        ):
            findings.append(
                f"recipe module sha mismatch: expected {recorded[:8]}..., "
                f"got {actual_recipe_sha[:8]}..."
            )
            drift = drift or "drift_recipe"

    return VerificationResult(
        figure_path=fig_path,
        overall=drift or "match",
        findings=tuple(findings),
    )


# ─────────────────────────── diff ───────────────────────────────────────


def _short(s: str | None, n: int = 8) -> str:
    """Truncate a hex hash to ``n`` characters with an ellipsis."""
    if not s:
        return "absent"
    return s[:n] + "..."


def diff_provenance(a_path: Path, b_path: Path) -> dict[str, list[str]]:
    """Compare two provenance.json sidecars and return per-dimension diff.

    Returned dict has fixed keys ``figure``, ``recipe``, ``data``,
    ``scorer``, ``environment``; values are lists of human-readable
    diff lines (empty when that dimension matches).

    Dimensions:
      * **figure** — ``figure_sha256`` change.
      * **recipe** — ``module_sha`` or ``panelforge_version`` change.
      * **data** — any source path's sha256 differs (or appears in only
        one side).
      * **scorer** — ``score`` field of ``scorer`` dict differs.
      * **environment** — ``matplotlib_version`` or ``platform`` differs.
    """
    a = load_provenance_json(a_path)
    b = load_provenance_json(b_path)
    diff: dict[str, list[str]] = {
        "figure": [],
        "recipe": [],
        "data": [],
        "scorer": [],
        "environment": [],
    }

    # Figure
    if a.figure_sha256 != b.figure_sha256:
        diff["figure"].append(
            f"sha256: {_short(a.figure_sha256)} → {_short(b.figure_sha256)}"
        )

    # Recipe
    if a.recipe.get("module_sha") != b.recipe.get("module_sha"):
        diff["recipe"].append(
            f"module_sha: {_short(a.recipe.get('module_sha'))} → "
            f"{_short(b.recipe.get('module_sha'))}"
        )
    if a.recipe.get("panelforge_version") != b.recipe.get("panelforge_version"):
        diff["recipe"].append(
            f"panelforge_version: {a.recipe.get('panelforge_version')} → "
            f"{b.recipe.get('panelforge_version')}"
        )

    # Data
    a_data = {s["path"]: s for s in a.data.get("sources", [])}
    b_data = {s["path"]: s for s in b.data.get("sources", [])}
    for path in sorted(set(a_data) | set(b_data)):
        a_sha = a_data.get(path, {}).get("sha256")
        b_sha = b_data.get(path, {}).get("sha256")
        if a_sha != b_sha:
            diff["data"].append(
                f"{path}: {_short(a_sha)} → {_short(b_sha)}"
            )

    # Scorer
    if a.scorer is not None and b.scorer is not None:
        a_score = a.scorer.get("score")
        b_score = b.scorer.get("score")
        if a_score != b_score:
            diff["scorer"].append(f"score: {a_score} → {b_score}")
        # Surface weight changes even if the resulting score happens to match.
        a_weights = a.scorer.get("weights") or {}
        b_weights = b.scorer.get("weights") or {}
        for k in sorted(set(a_weights) | set(b_weights)):
            if a_weights.get(k) != b_weights.get(k):
                diff["scorer"].append(
                    f"weights.{k}: {a_weights.get(k)} → {b_weights.get(k)}"
                )

    # Environment
    a_env = a.rendering_environment or {}
    b_env = b.rendering_environment or {}
    if a_env.get("matplotlib_version") != b_env.get("matplotlib_version"):
        diff["environment"].append(
            f"matplotlib_version: {a_env.get('matplotlib_version')} → "
            f"{b_env.get('matplotlib_version')}"
        )
    if a_env.get("platform") != b_env.get("platform"):
        diff["environment"].append(
            f"platform: {a_env.get('platform')} → {b_env.get('platform')}"
        )

    return diff


# ─────────────────────────── bundle ─────────────────────────────────────


def bundle_provenance(
    figure_path: Path,
    *,
    out_path: Path | None = None,
) -> Path:
    """Bundle a figure + provenance + referenced data + recipe into a tarball.

    Creates a self-contained ``.tar.gz`` (default
    ``<figure>.provenance.tar.gz``) with the layout from spec §3.3:

    ::

        <figure>.pdf
        <figure>.pdf.provenance.json
        data/<source.csv>
        data/<source2.parquet>
        recipe/<module.py>

    Files referenced by the sidecar that no longer exist on disk are
    silently skipped — the resulting bundle is then incomplete, but
    ``verify_provenance`` on the unpacked tarball will surface the
    missing pieces explicitly.

    Raises
    ------
    FileNotFoundError
        If the sidecar (``<figure>.provenance.json``) does not exist;
        we cannot bundle without the manifest of what to include.
    """
    fig = Path(figure_path)
    prov_path = fig.with_suffix(fig.suffix + ".provenance.json")
    if not prov_path.is_file():
        raise FileNotFoundError(f"provenance not found: {prov_path}")

    record = load_provenance_json(prov_path)
    if out_path is None:
        out_path = fig.with_suffix(fig.suffix + ".provenance.tar.gz")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(fig, arcname=fig.name)
        tar.add(prov_path, arcname=prov_path.name)
        for src in record.data.get("sources", []):
            src_path = Path(src["path"])
            if src_path.is_file():
                tar.add(src_path, arcname=f"data/{src_path.name}")
        recipe_path = Path(record.recipe.get("module_path", ""))
        if recipe_path.is_file():
            tar.add(recipe_path, arcname=f"recipe/{recipe_path.name}")

    return out_path


__all__ = [
    "PROVENANCE_SCHEMA_VERSION",
    "ProvenanceRecord",
    "VerificationResult",
    "build_provenance",
    "bundle_provenance",
    "diff_provenance",
    "load_provenance_json",
    "verify_provenance",
    "write_provenance_json",
]
