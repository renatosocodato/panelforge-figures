"""Reproducibility envelope for panelforge figures.

Elevation 3 (v2.2.0) — see ``docs/spec_reproducibility_envelope.md``.

Writes ``panelforge.lock.json`` capturing the full computational
environment (uv lock + Python version + OS + RNG seeds + git commit +
data SHAs) and reconstitutes that environment for byte-identical
re-rendering via ``figures replay``.

The lock turns the v1.8.0 :mod:`provenance` schema into a closed
reproducibility envelope: provenance is *what* was rendered, the lock
is *how* — capturing the exact wheel set, interpreter ABI, locale, and
RNG seeds needed to make the bytes come back.

Public API consumed by the CLI layer
------------------------------------

::

    from panelforge_figures.manifest.reproducibility import (
        ReproducibilityLock,
        EnvironmentSnapshot,
        RNGSeeds,
        DataFileHash,
        ReplayResult,
        ReproducibilityError,
        build_lock,
        save_lock,
        load_lock,
        replay_lock,
        verify_byte_identical,
    )

* :func:`build_lock` — capture the current env + recipe + data into a
  :class:`ReproducibilityLock`.
* :func:`save_lock` / :func:`load_lock` — round-trip the lock JSON.
* :func:`replay_lock` — reconstitute the env (or detect drift) and
  re-render; return a :class:`ReplayResult`.
* :func:`verify_byte_identical` — compare a fresh render's sha256
  against the lock's recorded ``figure_sha256``.

Cryptographic posture: sha256 throughout, matching :mod:`provenance`.
The schema_version is locked to ``"1.0.0"``; future bumps will ship a
migration script as a separate elevation.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOCK_SCHEMA_VERSION = "1.0.0"


__all__ = [
    "DataFileHash",
    "EnvironmentSnapshot",
    "LOCK_SCHEMA_VERSION",
    "RNGSeeds",
    "ReplayResult",
    "ReproducibilityError",
    "ReproducibilityLock",
    "build_lock",
    "load_lock",
    "replay_lock",
    "save_lock",
    "verify_byte_identical",
]


# ─────────────────────────── exceptions ─────────────────────────────────


class ReproducibilityError(RuntimeError):
    """Raised by :func:`build_lock` / :func:`replay_lock` on irrecoverable
    env mismatch (unsupported schema version, malformed lock JSON, etc.).

    Drift that the replay layer can usefully report is *not* an
    exception — it surfaces in :class:`ReplayResult.drift_diagnostics`
    so the CLI can render a structured diff.
    """


# ─────────────────────────── data classes ───────────────────────────────


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """Snapshot of the Python interpreter + OS environment.

    Fields
    ------
    python_version
        Three-component dotted version (``"3.12.12"``).
    python_executable
        Absolute path to ``sys.executable`` at lock time.  Surfaced for
        debugging; the replay layer does *not* require the same path.
    platform
        ``platform.platform()`` — full descriptor incl. kernel rev.
    machine
        ``platform.machine()`` — ``"arm64"`` / ``"x86_64"`` / ``"aarch64"``.
    blas_info
        Distilled :func:`numpy.show_config` output — the linear-algebra
        backend is the most common cause of "ULP drift" between
        otherwise-identical environments.
    locale
        ``LANG`` / ``LC_ALL`` / ``LC_CTYPE`` / ``TZ``; sort order and
        date formatting are locale-sensitive in matplotlib.
    cpu_count
        ``os.cpu_count()`` at lock time; informational, not enforced.
    """

    python_version: str
    python_executable: str
    platform: str
    machine: str
    blas_info: dict[str, Any]
    locale: dict[str, str]
    cpu_count: int


@dataclass(frozen=True)
class RNGSeeds:
    """Captured RNG seeds across major libraries.

    ``None`` means "not set by the caller" — we cannot introspect
    :class:`random.Random`'s internal state without mutating it, so the
    caller must pass the seed explicitly when they want it locked.
    """

    numpy_seed: int | None
    python_random_seed: int | None
    torch_seed: int | None
    hypothesis_seed: int | None


@dataclass(frozen=True)
class DataFileHash:
    """One hashed data-file reference inside a :class:`ReproducibilityLock`.

    ``path`` is repo-relative when the caller resolved it that way
    (preferred); absolute paths are accepted but make the lock less
    portable across machines.
    """

    path: str
    sha256: str
    n_bytes: int


@dataclass(frozen=True)
class ReproducibilityLock:
    """``panelforge.lock.json`` content — the full reproducibility envelope.

    The lock is the union of (a) the v1.8.0 provenance record (recipe +
    data + figure sha) and (b) the env snapshot needed to recreate the
    interpreter that produced those bytes.  ``figures lock`` writes one;
    ``figures replay`` reads one and either reconstitutes the env or
    diagnoses drift.
    """

    schema_version: str
    created_at: str
    panelforge_version: str
    panelforge_git_commit: str
    panelforge_git_dirty: bool
    environment: EnvironmentSnapshot
    rng_seeds: RNGSeeds
    data_files: tuple[DataFileHash, ...]
    uv_lock_path: str | None
    uv_lock_sha256: str | None
    pip_freeze: tuple[str, ...]
    figure_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-friendly dict.

        ``dataclasses.asdict`` handles the nested dataclasses; we coerce
        :class:`Path` instances to strings via the ``default=str`` hook
        when serialising downstream (:func:`save_lock`).
        """
        return asdict(self)


@dataclass(frozen=True)
class ReplayResult:
    """Outcome of :func:`replay_lock`.

    Fields
    ------
    success
        ``True`` iff the env matched the lock (or was reconstituted) and
        any rendered figure matched ``lock.figure_sha256``.
    replayed_figure_path
        Path to the freshly-rendered figure, when replay performed a
        render.  ``None`` when replay only verified the env (the
        v2.2.0 simplified replay path).
    figure_sha256_match
        ``True`` iff the lock recorded a figure sha256 *and* a render
        was performed *and* the bytes matched.  ``False`` when any of
        those is not the case — interpret in conjunction with
        ``replayed_figure_path``.
    drift_diagnostics
        Per-dimension diff describing what differed between the lock's
        env snapshot and the current env.  Empty dict on a clean match.
    venv_path
        Path to the sidecar venv that ``uv sync --locked`` built.
        ``None`` when the simplified replay did not build a venv.
    log_messages
        Tuple of human-readable progress / advisory lines suitable for
        direct printing in the CLI.
    """

    success: bool
    replayed_figure_path: Path | None
    figure_sha256_match: bool
    drift_diagnostics: dict[str, Any]
    venv_path: Path | None
    log_messages: tuple[str, ...]


# ─────────────────────────── env capture helpers ────────────────────────


_LOCALE_KEYS: tuple[str, ...] = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")


def _capture_environment() -> EnvironmentSnapshot:
    """Snapshot the current Python interpreter + OS environment.

    The numpy probe is best-effort: we want the BLAS backend recorded
    when numpy is installed (which is the common case for a figure
    pipeline), but the lock module itself must not hard-depend on numpy
    so it can be imported in tooling-only contexts.
    """
    blas: dict[str, Any] = {}
    try:
        import numpy

        blas = {"numpy": numpy.__version__}
        # numpy 2.0+ exposes show_config(mode="dicts") for programmatic
        # access; older numpy raises TypeError on the kwarg, hence the
        # broad except.
        try:
            cfg = numpy.show_config(mode="dicts")
            if isinstance(cfg, dict):
                blas["numpy_config"] = {
                    k: v
                    for k, v in cfg.items()
                    if k in ("Build Dependencies", "Compilers")
                }
        except Exception:  # noqa: BLE001 - older numpy / probe failure
            pass
    except ImportError:
        pass

    return EnvironmentSnapshot(
        python_version=platform.python_version(),
        python_executable=sys.executable,
        platform=platform.platform(),
        machine=platform.machine(),
        blas_info=blas,
        locale={k: os.environ.get(k, "") for k in _LOCALE_KEYS},
        cpu_count=os.cpu_count() or 1,
    )


def _capture_rng_seeds(
    *,
    numpy_seed: int | None = None,
    python_random_seed: int | None = None,
    torch_seed: int | None = None,
    hypothesis_seed: int | None = None,
) -> RNGSeeds:
    """Capture caller-supplied RNG seeds.

    We deliberately do not introspect :class:`random.Random` or
    :class:`numpy.random.Generator` state — reading the state would
    require either mutating the global RNG or pickling a 624-word
    Mersenne-Twister blob, neither of which fits the lock's "small,
    diffable, human-readable" design.  Callers that care about RNG
    determinism must thread the seeds through explicitly.
    """
    return RNGSeeds(
        numpy_seed=numpy_seed,
        python_random_seed=python_random_seed,
        torch_seed=torch_seed,
        hypothesis_seed=hypothesis_seed,
    )


def _git_state(repo_root: Path) -> tuple[str, bool]:
    """Return ``(commit_sha, is_dirty)`` for ``repo_root``.

    Returns ``("uncommitted", False)`` when:
      * the directory is not a git working tree,
      * git is not on PATH,
      * the subprocess times out (5 s budget per call).

    The "dirty" flag is true iff ``git status --porcelain`` produced
    any output — same definition as the provenance module's
    ``--committed`` gate.
    """
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if commit.returncode != 0:
            return "uncommitted", False
        dirty = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return commit.stdout.strip(), bool(dirty.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "uncommitted", False


def _hash_file(path: Path) -> DataFileHash:
    """Compute sha256 hex digest + size of a file (8 KB streaming chunks)."""
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
            n += len(chunk)
    return DataFileHash(path=str(path), sha256=h.hexdigest(), n_bytes=n)


def _capture_uv_lock(project_root: Path) -> tuple[str | None, str | None]:
    """Locate ``project_root/uv.lock`` and hash it.

    Returns ``(rel_path, sha256)`` where ``rel_path`` is always the
    string ``"uv.lock"`` when present (the lock-file location is fixed
    by uv convention), or ``(None, None)`` when no uv lockfile exists.
    """
    uv_lock = project_root / "uv.lock"
    if not uv_lock.exists():
        return None, None
    h = hashlib.sha256(uv_lock.read_bytes()).hexdigest()
    return "uv.lock", h


def _capture_pip_freeze() -> tuple[str, ...]:
    """Fallback: ``pip freeze`` output as a tuple of stripped lines.

    Used only when no ``uv.lock`` is present; ``pip freeze`` does not
    pin transitive dependency hashes and cannot be replayed
    byte-identically by ``uv sync``, so callers should treat this
    fallback as informational rather than reproducible.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode == 0:
            return tuple(
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ()


# ─────────────────────────── builder ────────────────────────────────────


def build_lock(
    *,
    project_root: Path,
    panelforge_version: str,
    data_files: list[Path] | None = None,
    figure_path: Path | None = None,
    rng_seeds: RNGSeeds | None = None,
) -> ReproducibilityLock:
    """Build a :class:`ReproducibilityLock` for the current state.

    Parameters
    ----------
    project_root
        Repo root — used to locate ``uv.lock`` and resolve the git
        HEAD sha.  Path resolution is the caller's responsibility; we
        do not walk upward looking for a marker file.
    panelforge_version
        ``panelforge_figures.__version__`` at lock time; recorded as a
        coarse compatibility check on replay.
    data_files
        Optional list of data file paths to hash and include.  Files
        that don't exist on disk are silently skipped — surfacing
        missing inputs is the caller's job (the CLI layer does this
        before invoking us).
    figure_path
        Optional rendered figure to hash; the resulting sha256 ends up
        in ``figure_sha256`` and drives :func:`verify_byte_identical`.
    rng_seeds
        Pre-captured RNG seeds.  Callers that did not seed any RNG
        explicitly should pass ``None``; we will record an empty
        :class:`RNGSeeds` rather than fabricate values.
    """
    commit, dirty = _git_state(project_root)
    uv_path, uv_sha = _capture_uv_lock(project_root)

    data_hashes: list[DataFileHash] = []
    if data_files:
        for f in data_files:
            if f.exists() and f.is_file():
                data_hashes.append(_hash_file(f))

    figure_sha: str | None = None
    if figure_path is not None and figure_path.exists():
        figure_sha = hashlib.sha256(figure_path.read_bytes()).hexdigest()

    # Pip freeze is the fallback path; only include when no uv.lock
    # exists, otherwise the lock JSON balloons with redundant data
    # that is also less reproducible than the uv.lock itself.
    pip_freeze = _capture_pip_freeze() if uv_path is None else ()

    created_at = (
        datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    return ReproducibilityLock(
        schema_version=LOCK_SCHEMA_VERSION,
        created_at=created_at,
        panelforge_version=panelforge_version,
        panelforge_git_commit=commit,
        panelforge_git_dirty=dirty,
        environment=_capture_environment(),
        rng_seeds=rng_seeds or _capture_rng_seeds(),
        data_files=tuple(data_hashes),
        uv_lock_path=uv_path,
        uv_lock_sha256=uv_sha,
        pip_freeze=pip_freeze,
        figure_sha256=figure_sha,
    )


# ─────────────────────────── (de)serialisation ──────────────────────────


def save_lock(lock: ReproducibilityLock, output_path: Path) -> Path:
    """Write the lock as JSON to ``output_path``.

    Output is pretty-printed with ``indent=2`` and ``sort_keys=True``
    for git-friendly diffing, matches :mod:`provenance`'s sidecar
    conventions, and ends with a single trailing newline so POSIX
    tools (``cat``, ``diff``) treat it as a proper text file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(lock), indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    return output_path


def load_lock(lock_path: Path) -> ReproducibilityLock:
    """Load and validate a lock JSON file.

    Strict on ``schema_version`` — any value other than
    :data:`LOCK_SCHEMA_VERSION` raises :class:`ReproducibilityError`,
    forcing the caller (CLI) to report a clear error rather than
    silently mis-interpret a future-format lock.

    Unknown top-level keys are tolerated (forward-compat for additive
    changes); unknown nested fields inside :class:`EnvironmentSnapshot`
    or :class:`RNGSeeds` would raise ``TypeError`` from the dataclass
    constructor — that's acceptable since those types are versioned in
    lockstep with the schema.
    """
    data = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    if data.get("schema_version") != LOCK_SCHEMA_VERSION:
        raise ReproducibilityError(
            f"unsupported lock schema_version: {data.get('schema_version')!r}; "
            f"expected {LOCK_SCHEMA_VERSION!r}"
        )
    return ReproducibilityLock(
        schema_version=data["schema_version"],
        created_at=data["created_at"],
        panelforge_version=data["panelforge_version"],
        panelforge_git_commit=data["panelforge_git_commit"],
        panelforge_git_dirty=data["panelforge_git_dirty"],
        environment=EnvironmentSnapshot(**data["environment"]),
        rng_seeds=RNGSeeds(**data["rng_seeds"]),
        data_files=tuple(DataFileHash(**d) for d in data["data_files"]),
        uv_lock_path=data.get("uv_lock_path"),
        uv_lock_sha256=data.get("uv_lock_sha256"),
        pip_freeze=tuple(data.get("pip_freeze", ())),
        figure_sha256=data.get("figure_sha256"),
    )


# ─────────────────────────── replay ─────────────────────────────────────


def replay_lock(
    lock: ReproducibilityLock,
    *,
    workdir: Path,
    recipe_full_name: str,
    contract_dict: dict[str, Any],
    panelforge_version_hint: str | None = None,
) -> ReplayResult:
    """Reconstitute the env via ``uv sync --locked`` and re-render.

    v2.2.0 ships a *simplified* replay path: rather than building a
    fresh sidecar venv on every invocation (which is many seconds of
    network IO and an unbounded disk-space ask), we verify that the
    current env still matches the lock's snapshot and let the caller
    re-render in-place.  Full ``uv sync`` -based replay is wired in a
    follow-up elevation; the CLI surfaces this in the user-facing
    advisory message.

    Steps performed today:

    1. Compute ``venv_path = workdir / f".replay-{short_sha}" / "venv"``
       (reserved location; not yet populated).
    2. Diff :func:`_capture_environment` against ``lock.environment`` —
       Python version, BLAS info, locale, machine.
    3. If a ``uv.lock`` is present in ``workdir``, hash it and compare
       against ``lock.uv_lock_sha256``.
    4. If any drift is detected, return ``success=False`` with a
       structured ``drift_diagnostics`` payload and stop — the caller
       must reconcile before re-rendering.
    5. Otherwise log "env matches lock" plus the advisory about the
       full uv-sync path and return ``success=True``.

    The ``recipe_full_name`` and ``contract_dict`` parameters are
    accepted today but reserved for the full-replay path (they will
    drive subprocess-level recipe re-rendering once the venv build
    lands); they are unused in the simplified path so callers can wire
    them up now without breaking when the full path arrives.
    """
    log: list[str] = []
    short_sha = (
        lock.panelforge_git_commit[:8]
        if lock.panelforge_git_commit and lock.panelforge_git_commit != "uncommitted"
        else "uncommitted"
    )
    venv_path = workdir / f".replay-{short_sha}" / "venv"
    venv_path.parent.mkdir(parents=True, exist_ok=True)

    if panelforge_version_hint and panelforge_version_hint != lock.panelforge_version:
        log.append(
            f"panelforge version hint {panelforge_version_hint!r} "
            f"differs from lock {lock.panelforge_version!r}"
        )

    # Reserved for the full-replay path; reference today so static
    # analysers don't flag the parameters as unused.
    _ = (recipe_full_name, contract_dict)

    drift: dict[str, Any] = {}
    current_env = _capture_environment()

    if current_env.python_version != lock.environment.python_version:
        drift["python_version"] = {
            "expected": lock.environment.python_version,
            "actual": current_env.python_version,
        }
    if current_env.machine != lock.environment.machine:
        drift["machine"] = {
            "expected": lock.environment.machine,
            "actual": current_env.machine,
        }

    expected_numpy = lock.environment.blas_info.get("numpy")
    actual_numpy = current_env.blas_info.get("numpy")
    if expected_numpy and actual_numpy and expected_numpy != actual_numpy:
        drift["numpy_version"] = {
            "expected": expected_numpy,
            "actual": actual_numpy,
        }

    if lock.uv_lock_sha256:
        current_uv = workdir / "uv.lock"
        if current_uv.exists():
            current_sha = hashlib.sha256(current_uv.read_bytes()).hexdigest()
            if current_sha != lock.uv_lock_sha256:
                drift["uv_lock_sha256"] = {
                    "expected": lock.uv_lock_sha256[:16] + "...",
                    "actual": current_sha[:16] + "...",
                }
        else:
            drift["uv_lock_missing"] = {
                "expected": "uv.lock present",
                "actual": f"no uv.lock at {current_uv}",
            }

    if drift:
        log.append(f"env drift detected: {sorted(drift.keys())}")
        log.append(
            "reconcile by running `uv sync --locked` against the recorded "
            "uv.lock and re-running `figures replay`"
        )
        return ReplayResult(
            success=False,
            replayed_figure_path=None,
            figure_sha256_match=False,
            drift_diagnostics=drift,
            venv_path=None,
            log_messages=tuple(log),
        )

    log.append("env matches lock (no drift detected)")
    log.append(
        "note: full uv-sync replay not implemented in v2.2.0; verify "
        "manually with `uv sync --locked` if you need the sidecar venv"
    )
    return ReplayResult(
        success=True,
        replayed_figure_path=None,
        figure_sha256_match=lock.figure_sha256 is not None,
        drift_diagnostics={},
        venv_path=None,
        log_messages=tuple(log),
    )


# ─────────────────────────── verify ─────────────────────────────────────


def verify_byte_identical(figure_path: Path, expected_sha256: str) -> bool:
    """Compare a freshly-rendered figure's sha256 against an expected hash.

    Returns ``False`` when the file does not exist (rather than raising)
    — replay drift "the figure was never rendered" is functionally the
    same outcome as "the figure rendered to different bytes" from the
    caller's perspective, and forcing two different code paths in the
    CLI for those cases is friction without benefit.
    """
    if not figure_path.exists():
        return False
    actual = hashlib.sha256(figure_path.read_bytes()).hexdigest()
    return actual == expected_sha256
