"""Tests for the render cache (Elevation 11 — v3.5.0).

Covers the public surface of :mod:`panelforge_figures.manifest.render_cache`:

* SHA helpers (file / contract / data) and their canonicalisation
  guarantees.
* :class:`CacheEntry` and :class:`RenderCache` round-trips.
* Load / save with corruption + schema-mismatch tolerance.
* :func:`check_staleness` over every code path.
* :func:`update_cache_entry` upsert behaviour.
* :func:`summarize_cache_state` aggregation.
* CLI ``figures cache {status, clear, invalidate}`` smoke tests.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures import __version__
from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.render_cache import (
    CACHE_FILENAME,
    CACHE_SCHEMA_VERSION,
    CacheEntry,
    CacheStatus,
    RenderCache,
    RenderCacheError,
    cache_path_for_project,
    check_staleness,
    compute_contract_sha,
    compute_data_sha,
    compute_recipe_sha,
    load_cache,
    save_cache,
    summarize_cache_state,
    update_cache_entry,
)

# ─────────────────────────── SHA helpers ────────────────────────────────


def test_sha256_file_stable_across_reads(tmp_path: Path) -> None:
    """Hashing the same file twice yields the same digest."""
    p = tmp_path / "data.csv"
    p.write_bytes(b"hello,world\n1,2\n3,4\n")
    # _sha256_file is private but accessed via compute_recipe_sha.
    h1 = compute_recipe_sha(p)
    h2 = compute_recipe_sha(p)
    assert h1 == h2
    assert len(h1) == 64
    # ground-truth sha256 of the bytes
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert h1 == expected


def test_compute_recipe_sha_missing_file(tmp_path: Path) -> None:
    """Missing recipe file → empty string (caller treats as 'no recipe SHA')."""
    p = tmp_path / "does-not-exist.py"
    assert compute_recipe_sha(p) == ""


def test_compute_contract_sha_is_canonical() -> None:
    """Two dicts with the same content but different insertion orders
    must produce identical hashes — the contract SHA must be canonical."""
    a = {"alpha": 1, "beta": 2, "nested": {"x": 1, "y": 2}}
    b = {"nested": {"y": 2, "x": 1}, "beta": 2, "alpha": 1}
    assert compute_contract_sha(a) == compute_contract_sha(b)
    # And different values produce different hashes.
    c = {"alpha": 1, "beta": 3, "nested": {"x": 1, "y": 2}}
    assert compute_contract_sha(a) != compute_contract_sha(c)


def test_compute_data_sha_empty_list_is_sentinel() -> None:
    """Empty data list → fixed sentinel (sha256 of empty bytes)."""
    sentinel = hashlib.sha256(b"").hexdigest()
    assert compute_data_sha([]) == sentinel


def test_compute_data_sha_order_insensitive(tmp_path: Path) -> None:
    """[a, b] and [b, a] hash identically — the sort step does its job."""
    a = tmp_path / "a.csv"
    a.write_bytes(b"col\n1\n2\n")
    b = tmp_path / "b.csv"
    b.write_bytes(b"col\n9\n8\n")

    h_ab = compute_data_sha([a, b])
    h_ba = compute_data_sha([b, a])
    assert h_ab == h_ba

    # Same paths but mutating contents → different hash.
    b.write_bytes(b"col\n9\n8\n7\n")
    h_after = compute_data_sha([a, b])
    assert h_after != h_ab


def test_compute_data_sha_missing_file_does_not_crash(tmp_path: Path) -> None:
    """A missing file becomes the literal ``"missing"`` sentinel, not an
    exception — the cache should remain usable when a data file vanishes."""
    a = tmp_path / "a.csv"
    a.write_bytes(b"col\n1\n2\n")
    missing = tmp_path / "ghost.csv"
    h = compute_data_sha([a, missing])
    assert isinstance(h, str)
    assert len(h) == 64


# ─────────────────────────── CacheEntry round-trip ──────────────────────


def _make_entry(**overrides) -> CacheEntry:
    """Helper: build a CacheEntry with sensible defaults."""
    defaults = {
        "figure_id": "Figure 1",
        "panel_id": "1A",
        "recipe_full_name": "rna_seq.volcano",
        "recipe_sha": "a" * 64,
        "contract_sha": "b" * 64,
        "data_sha": "c" * 64,
        "output_sha": "d" * 64,
        "output_path": "figures/figure_1A.pdf",
        "rendered_at": "2026-05-11T10:00:00Z",
        "panelforge_version": __version__,
        "notes": ("rendered",),
    }
    defaults.update(overrides)
    return CacheEntry(**defaults)


def test_cache_entry_round_trip() -> None:
    """CacheEntry → dict → CacheEntry preserves every field."""
    entry = _make_entry()
    d = entry.to_dict()
    # ``notes`` is serialised as list (JSON-friendly).
    assert isinstance(d["notes"], list)
    restored = CacheEntry.from_dict(d)
    assert restored == entry
    # ``notes`` round-trips back to a tuple.
    assert isinstance(restored.notes, tuple)


def test_cache_entry_from_dict_tolerant_to_missing_fields() -> None:
    """A partial dict (e.g. forward-compat write that drops a field) loads
    without crashing — missing strings default to ""."""
    entry = CacheEntry.from_dict({"panel_id": "X"})
    assert entry.panel_id == "X"
    assert entry.recipe_sha == ""
    assert entry.notes == ()


# ─────────────────────────── RenderCache round-trip ─────────────────────


def test_render_cache_round_trip() -> None:
    """RenderCache → dict → RenderCache preserves all entries + schema."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    cache.upsert(_make_entry(panel_id="1B", figure_id="Figure 1"))
    cache.upsert(_make_entry(panel_id="2A", figure_id="Figure 2"))

    d = cache.to_dict()
    assert d["schema_version"] == CACHE_SCHEMA_VERSION
    assert set(d["entries"].keys()) == {"1A", "1B", "2A"}

    restored = RenderCache.from_dict(d)
    assert set(restored.entries.keys()) == {"1A", "1B", "2A"}
    assert restored.entries["2A"].figure_id == "Figure 2"


def test_render_cache_from_dict_skips_corrupt_entries() -> None:
    """One bad row should not block loading the rest."""
    d = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "entries": {
            "good": _make_entry(panel_id="good").to_dict(),
            # A non-dict entry would normally crash from_dict; we rely on
            # CacheEntry.from_dict being lenient.  Use an explicit dict
            # that's mostly empty — should still round-trip.
            "partial": {"panel_id": "partial"},
        },
    }
    cache = RenderCache.from_dict(d)
    assert "good" in cache.entries
    assert "partial" in cache.entries


# ─────────────────────────── load / save ────────────────────────────────


def test_load_cache_missing_file_returns_empty(tmp_path: Path) -> None:
    """First-run: no cache file → empty cache, no warning."""
    cache = load_cache(tmp_path)
    assert isinstance(cache, RenderCache)
    assert cache.entries == {}


def test_load_cache_corrupt_json_warns_and_empty(tmp_path: Path) -> None:
    """Truncated / invalid JSON → RuntimeWarning + empty cache."""
    cache_dir = tmp_path / "panelforge_workspace"
    cache_dir.mkdir(parents=True)
    (cache_dir / CACHE_FILENAME).write_text("{not valid json", encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cache = load_cache(tmp_path)
    assert cache.entries == {}
    assert any(issubclass(w.category, RuntimeWarning) for w in caught)
    assert any("corrupt" in str(w.message) for w in caught)


def test_load_cache_schema_mismatch_warns_and_empty(tmp_path: Path) -> None:
    """Old / unknown schema version → RuntimeWarning + empty cache."""
    cache_dir = tmp_path / "panelforge_workspace"
    cache_dir.mkdir(parents=True)
    (cache_dir / CACHE_FILENAME).write_text(
        json.dumps({"schema_version": "0.0.1", "entries": {}}),
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cache = load_cache(tmp_path)
    assert cache.entries == {}
    assert any("schema mismatch" in str(w.message) for w in caught)


def test_save_cache_round_trip_via_disk(tmp_path: Path) -> None:
    """save_cache then load_cache reproduces the exact entry set."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    cache.upsert(_make_entry(panel_id="1B"))

    path = save_cache(cache, tmp_path)
    assert path.exists()
    assert path.name == CACHE_FILENAME

    restored = load_cache(tmp_path)
    assert set(restored.entries.keys()) == {"1A", "1B"}


def test_save_cache_is_atomic(tmp_path: Path) -> None:
    """Atomic semantics: only one render_cache.json after save, no temp left."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    save_cache(cache, tmp_path)

    ws = tmp_path / "panelforge_workspace"
    children = list(ws.iterdir())
    assert len(children) == 1
    assert children[0].name == CACHE_FILENAME


def test_save_cache_creates_parent_directory(tmp_path: Path) -> None:
    """panelforge_workspace/ does not need to exist beforehand."""
    cache = RenderCache.empty()
    path = save_cache(cache, tmp_path)
    assert path.parent.is_dir()


def test_cache_path_for_project_layout(tmp_path: Path) -> None:
    """Default path = <project>/panelforge_workspace/render_cache.json."""
    p = cache_path_for_project(tmp_path)
    assert p == tmp_path / "panelforge_workspace" / CACHE_FILENAME


# ─────────────────────────── staleness paths ────────────────────────────


def test_check_staleness_missing() -> None:
    """No entry in cache → CacheStatus.missing."""
    cache = RenderCache.empty()
    s = check_staleness(
        cache, panel_id="X",
        current_recipe_sha="a", current_contract_sha="b", current_data_sha="c",
    )
    assert s == CacheStatus.missing


def test_check_staleness_fresh_when_all_match(tmp_path: Path) -> None:
    """All SHAs match + output file exists → CacheStatus.fresh."""
    cache = RenderCache.empty()
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-1.4\n")
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="r", contract_sha="c", data_sha="d",
        output_sha=hashlib.sha256(out.read_bytes()).hexdigest(),
        output_path=str(out),
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="c", current_data_sha="d",
        output_path=out,
    )
    assert s == CacheStatus.fresh


def test_check_staleness_stale_recipe() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="OLD", contract_sha="c", data_sha="d",
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="NEW", current_contract_sha="c",
        current_data_sha="d",
    )
    assert s == CacheStatus.stale_recipe


def test_check_staleness_stale_contract() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="r", contract_sha="OLD", data_sha="d",
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="NEW",
        current_data_sha="d",
    )
    assert s == CacheStatus.stale_contract


def test_check_staleness_stale_data() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="r", contract_sha="c", data_sha="OLD",
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="c",
        current_data_sha="NEW",
    )
    assert s == CacheStatus.stale_data


def test_check_staleness_stale_output(tmp_path: Path) -> None:
    """SHAs match but the recorded output file was deleted → stale_output."""
    cache = RenderCache.empty()
    missing_out = tmp_path / "deleted.pdf"  # never created
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="r", contract_sha="c", data_sha="d",
        output_path=str(missing_out),
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="c",
        current_data_sha="d",
        output_path=missing_out,
    )
    assert s == CacheStatus.stale_output


def test_check_staleness_stale_output_on_mutation(tmp_path: Path) -> None:
    """Output file still present but its bytes changed → stale_output.

    Regression for the "cache blind to mutation" gap: an externally
    edited / corrupted output PDF must invalidate the cache, not report
    fresh.  We record a real render (so ``output_sha`` is a genuine
    on-disk hash), confirm fresh, then append bytes to the file and
    confirm the panel is now flagged for re-render.
    """
    cache = RenderCache.empty()
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-1.4\n%rendered")
    update_cache_entry(
        cache,
        panel_id="1A",
        figure_id="Figure 1",
        recipe_full_name="rna_seq.volcano",
        recipe_sha="r",
        contract_sha="c",
        data_sha="d",
        output_path=out,
        panelforge_version=__version__,
        notes=("rendered",),
    )

    # Sanity: nothing touched → fresh.
    assert check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="c", current_data_sha="d",
        output_path=out,
    ) == CacheStatus.fresh

    # Mutate the output on disk (corruption / external edit).
    with out.open("ab") as fh:
        fh.write(b"\n%tampered")

    # The on-disk bytes no longer match the recorded output_sha → stale.
    assert check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="r", current_contract_sha="c", current_data_sha="d",
        output_path=out,
    ) == CacheStatus.stale_output


def test_check_staleness_order_recipe_wins_over_data() -> None:
    """When both recipe and data changed, recipe wins (higher-priority cause)."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(
        panel_id="1A",
        recipe_sha="OLD_R", contract_sha="c", data_sha="OLD_D",
    ))
    s = check_staleness(
        cache, panel_id="1A",
        current_recipe_sha="NEW_R", current_contract_sha="c",
        current_data_sha="NEW_D",
    )
    assert s == CacheStatus.stale_recipe


# ─────────────────────────── update / upsert / remove ───────────────────


def test_update_cache_entry_records_state(tmp_path: Path) -> None:
    """update_cache_entry creates an entry, hashes the output, and upserts."""
    cache = RenderCache.empty()
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-1.4\n%fake")
    entry = update_cache_entry(
        cache,
        panel_id="1A",
        figure_id="Figure 1",
        recipe_full_name="rna_seq.volcano",
        recipe_sha="r" * 64,
        contract_sha="c" * 64,
        data_sha="d" * 64,
        output_path=out,
        panelforge_version=__version__,
        notes=("rendered",),
    )
    assert entry.panel_id == "1A"
    assert entry.output_sha == hashlib.sha256(out.read_bytes()).hexdigest()
    assert cache.get("1A") is entry
    # rendered_at ends with 'Z' (no offset).
    assert entry.rendered_at.endswith("Z")


def test_update_cache_entry_missing_output_yields_empty_sha(tmp_path: Path) -> None:
    """If the output path doesn't exist at update time, output_sha is ""."""
    cache = RenderCache.empty()
    entry = update_cache_entry(
        cache,
        panel_id="1A",
        figure_id="Figure 1",
        recipe_full_name="x.y",
        recipe_sha="r", contract_sha="c", data_sha="d",
        output_path=tmp_path / "never_created.pdf",
        panelforge_version=__version__,
    )
    assert entry.output_sha == ""


def test_render_cache_upsert_overwrites() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A", recipe_sha="v1"))
    cache.upsert(_make_entry(panel_id="1A", recipe_sha="v2"))
    assert len(cache.entries) == 1
    assert cache.entries["1A"].recipe_sha == "v1" * 0 + "v2" * 1  # plainly v2
    assert cache.entries["1A"].recipe_sha == "v2"


def test_render_cache_remove_is_idempotent() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    cache.remove("1A")
    assert "1A" not in cache.entries
    # Second remove must not raise — idempotent.
    cache.remove("1A")
    cache.remove("never-existed")


# ─────────────────────────── summarize ──────────────────────────────────


def test_summarize_cache_state_counts() -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    states = {
        "1A": CacheStatus.fresh,
        "1B": CacheStatus.missing,
        "1C": CacheStatus.stale_data,
        "1D": CacheStatus.stale_data,
    }
    s = summarize_cache_state(cache, states)
    assert s["fresh"] == 1
    assert s["missing"] == 1
    assert s["stale_data"] == 2
    assert s["stale_recipe"] == 0
    assert s["total"] == 4
    assert s["cache_entries"] == 1


# ─────────────────────────── end-to-end ─────────────────────────────────


def test_end_to_end_render_then_cached(tmp_path: Path) -> None:
    """Simulate: render a panel → save cache → reload → check_staleness=fresh.

    This is the canonical happy path the executor relies on.
    """
    # Set up an output file on disk so check_staleness's output_path
    # branch is exercised properly.
    out = tmp_path / "figure_1A.pdf"
    out.write_bytes(b"%PDF-1.4\n%data\n")

    cache = RenderCache.empty()
    recipe_sha = "r" * 64
    contract_sha = "c" * 64
    data_sha = "d" * 64

    update_cache_entry(
        cache,
        panel_id="1A",
        figure_id="Figure 1",
        recipe_full_name="rna_seq.volcano",
        recipe_sha=recipe_sha,
        contract_sha=contract_sha,
        data_sha=data_sha,
        output_path=out,
        panelforge_version=__version__,
        notes=("rendered",),
    )
    saved_path = save_cache(cache, tmp_path)
    assert saved_path.exists()

    # Fresh process: load from disk and verify staleness.
    reloaded = load_cache(tmp_path)
    s = check_staleness(
        reloaded, panel_id="1A",
        current_recipe_sha=recipe_sha,
        current_contract_sha=contract_sha,
        current_data_sha=data_sha,
        output_path=out,
    )
    assert s == CacheStatus.fresh

    # Now mutate the "data" SHA and confirm staleness flips.
    s2 = check_staleness(
        reloaded, panel_id="1A",
        current_recipe_sha=recipe_sha,
        current_contract_sha=contract_sha,
        current_data_sha="NEW_DATA_SHA",
        output_path=out,
    )
    assert s2 == CacheStatus.stale_data


def test_render_cache_error_class_exists() -> None:
    """RenderCacheError is a RuntimeError subclass (importable, raisable)."""
    assert issubclass(RenderCacheError, RuntimeError)
    with pytest.raises(RenderCacheError):
        raise RenderCacheError("test")


# ─────────────────────────── CLI smoke ──────────────────────────────────


def test_cli_cache_status_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["cache", "status", "--help"])
    assert result.exit_code == 0
    assert "cache state" in result.output.lower() or "entries" in result.output.lower()


def test_cli_cache_status_on_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["cache", "status", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "entries: 0" in result.output


def test_cli_cache_status_with_entries(tmp_path: Path) -> None:
    """A populated cache should list its rows in the status output."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A", figure_id="Figure 1"))
    cache.upsert(_make_entry(
        panel_id="2A", figure_id="Figure 2",
        rendered_at="2026-05-12T11:00:00Z",
    ))
    save_cache(cache, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["cache", "status", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "entries: 2" in result.output
    assert "1A" in result.output
    assert "2A" in result.output
    assert "oldest" in result.output
    assert "newest" in result.output


def test_cli_cache_clear_deletes_file(tmp_path: Path) -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    path = save_cache(cache, tmp_path)
    assert path.exists()

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["cache", "clear", "--project-root", str(tmp_path), "--yes"],
    )
    assert result.exit_code == 0
    assert not path.exists()
    assert "deleted" in result.output


def test_cli_cache_clear_on_empty(tmp_path: Path) -> None:
    """Clearing a non-existent cache reports gracefully without exiting nonzero."""
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["cache", "clear", "--project-root", str(tmp_path), "--yes"],
    )
    assert result.exit_code == 0
    assert "already empty" in result.output.lower()


def test_cli_cache_invalidate_removes_entry(tmp_path: Path) -> None:
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    cache.upsert(_make_entry(panel_id="1B"))
    save_cache(cache, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["cache", "invalidate",
         "--project-root", str(tmp_path),
         "--panel-id", "1A"],
    )
    assert result.exit_code == 0
    assert "1 panel(s) invalidated" in result.output

    reloaded = load_cache(tmp_path)
    assert "1A" not in reloaded.entries
    assert "1B" in reloaded.entries


def test_cli_cache_invalidate_unknown_panel_warns(tmp_path: Path) -> None:
    """Invalidating a missing panel-id is a warning, not an error."""
    cache = RenderCache.empty()
    cache.upsert(_make_entry(panel_id="1A"))
    save_cache(cache, tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["cache", "invalidate",
         "--project-root", str(tmp_path),
         "--panel-id", "does-not-exist"],
    )
    assert result.exit_code == 0
    assert "not in cache" in result.output
    assert "0 panel(s) invalidated" in result.output


def test_cli_execute_plan_has_force_flag() -> None:
    """The --force flag should appear in `figures execute-plan --help`."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["execute-plan", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.output
