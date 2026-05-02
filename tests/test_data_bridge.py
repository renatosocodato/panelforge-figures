"""Tests for the data-bridge 3-pass mapper (Wave 3)."""

from __future__ import annotations

import csv
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import Field

from panelforge_figures.core.contract import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    _RegistryEntry,
)
from panelforge_figures.manifest import data_bridge as db

# ---------------------------------------------------------------------------
# Synthetic recipes — added to the registry per-test and torn down so the
# global recipe-registry pollution does not leak into test_recipes_smoke etc.
# ---------------------------------------------------------------------------


class _EstimatesInput(RecipeContract):
    estimates: list[float] = Field(..., description="point estimates")
    title: str = "demo"


class _EstimatesAndCounts(RecipeContract):
    estimates: list[float] = Field(..., description="point estimates")
    counts: list[int] = Field(..., description="row counts")


def _demo_estimates() -> _EstimatesInput:
    return _EstimatesInput(estimates=[0.1, 0.2, 0.3])


def _demo_two() -> _EstimatesAndCounts:
    return _EstimatesAndCounts(estimates=[0.1], counts=[1])


def _render_noop(contract, ax=None, **_):
    return ax


def _make_entry(
    name: str,
    contract: type[RecipeContract],
    demo,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
) -> _RegistryEntry:
    md = RecipeMetadata(
        name=name,
        modality="_test_db_modality",
        family=RecipeFamily.coef_forest,
        answers_question=f"does the binder bind {name}?",
        required_fields=required,
        optional_fields=optional,
    )
    return _RegistryEntry(
        metadata=md,
        dotted_path=f"tests.test_data_bridge._render_noop_{name}",
        render=_render_noop,
        contract=contract,
        demo_contract=demo,
    )


@pytest.fixture(autouse=True)
def _scoped_test_registry() -> Iterator[None]:
    """Add synthetic test recipes to ``_REGISTRY`` for this test only.

    Function-scoped + autouse so every test starts with a clean registry
    extension and ends with the entries removed — preventing pollution
    of session-scoped registry consumers like ``test_recipes_smoke``.
    """
    from panelforge_figures.core.contract import _REGISTRY

    estimates_entry = _make_entry(
        "estimates_recipe", _EstimatesInput, _demo_estimates,
        required=("estimates",), optional=("title",),
    )
    two_entry = _make_entry(
        "two_field_recipe", _EstimatesAndCounts, _demo_two,
        required=("estimates", "counts"),
    )
    keys = [estimates_entry.full_name, two_entry.full_name]
    _REGISTRY[estimates_entry.full_name] = estimates_entry
    _REGISTRY[two_entry.full_name] = two_entry
    try:
        yield
    finally:
        for k in keys:
            _REGISTRY.pop(k, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, columns: list[str], rows: int = 3) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for i in range(rows):
            writer.writerow([float(i)] * len(columns))
    return path


def _write_parquet(path: Path, columns: list[str], rows: int = 3) -> Path:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({c: [float(i) for i in range(rows)] for c in columns})
    pq.write_table(table, str(path))
    return path


# ---------------------------------------------------------------------------
# Test 1 — Pass 1 exact match
# ---------------------------------------------------------------------------


def test_pass1_exact_match(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "d.csv", ["estimates", "counts"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("estimates", "counts"), n_rows=3,
    )
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=False,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "exact"
    assert estimates.confidence == 1.0
    assert estimates.column_name == "estimates"
    assert estimates.data_source == csv_path
    assert rb.fully_bound is True


def test_pass1_exact_match_case_insensitive(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "d.csv", ["Estimates"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("Estimates",), n_rows=3,
    )
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=False,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "exact"


# ---------------------------------------------------------------------------
# Test 2 — Pass 2 fuzzy match
# ---------------------------------------------------------------------------


def test_pass2_fuzzy_match(tmp_path: Path) -> None:
    # "estimates" vs "estimates_col" — clearly within difflib's 0.8 cutoff:
    # SequenceMatcher.ratio() ~ 0.818 for this pair.
    csv_path = _write_csv(tmp_path / "d.csv", ["estimates_col"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("estimates_col",), n_rows=3,
    )
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=False,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "fuzzy"
    assert 0.7 <= estimates.confidence <= 0.95
    assert estimates.column_name == "estimates_col"


# ---------------------------------------------------------------------------
# Test 3 — Pass 3 LLM (mocked)
# ---------------------------------------------------------------------------


def test_pass3_llm_with_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    csv_path = _write_csv(tmp_path / "d.csv", ["col_xyz", "other"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("col_xyz", "other"), n_rows=3,
    )

    def fake_llm(field_name, field_type, field_description, candidate_columns, samples):
        return ("col_xyz", 0.7, "test reason")

    monkeypatch.setattr(db, "_llm_pass", fake_llm)
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=True,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "llm"
    assert estimates.column_name == "col_xyz"
    assert estimates.confidence == 0.7


def test_pass3_unbound_when_no_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    csv_path = _write_csv(tmp_path / "d.csv", ["col_xyz"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("col_xyz",), n_rows=3,
    )
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=True,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "unbound"
    assert estimates.confidence == 0.0
    assert rb.fully_bound is False


# ---------------------------------------------------------------------------
# Test 4 — Cache round-trip
# ---------------------------------------------------------------------------


def test_cache_round_trip(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "d.csv", ["estimates"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("estimates",), n_rows=3,
    )
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=False,
    )
    cache_path = tmp_path / "cache.json"
    written = db.write_bindings_cache([rb], cache_path=cache_path)
    assert written == cache_path
    assert cache_path.exists()

    loaded = db.load_bindings_cache(cache_path=cache_path)
    key = ("_test_db_modality.estimates_recipe", "estimates")
    assert key in loaded
    fb = loaded[key]
    assert fb.column_name == "estimates"
    assert fb.pass_used == "exact"
    assert fb.confidence == 1.0
    assert fb.data_source == csv_path


def test_cache_load_missing_returns_empty(tmp_path: Path) -> None:
    loaded = db.load_bindings_cache(cache_path=tmp_path / "does_not_exist.json")
    assert loaded == {}


# ---------------------------------------------------------------------------
# Test 5 — Discovery
# ---------------------------------------------------------------------------


def test_discover_data_files_csv_and_parquet(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    _write_csv(tmp_path / "a.csv", ["x", "y"])
    _write_parquet(tmp_path / "b.parquet", ["alpha", "beta"])
    files = db.discover_data_files(data_dir=tmp_path)
    assert len(files) == 2
    fmts = {f.format for f in files}
    assert fmts == {"csv", "parquet"}
    by_fmt = {f.format: f for f in files}
    assert set(by_fmt["csv"].columns) == {"x", "y"}
    assert set(by_fmt["parquet"].columns) == {"alpha", "beta"}


def test_discover_data_files_missing_dir(tmp_path: Path) -> None:
    files = db.discover_data_files(data_dir=tmp_path / "absent")
    assert files == []


# ---------------------------------------------------------------------------
# Test 6 — Pydantic introspection on a real recipe
# ---------------------------------------------------------------------------


def test_real_recipe_unbound_with_no_data() -> None:
    rb = db.bind_recipe_to_data(
        recipe_full_name="meta_and_diagnostic.bayes_factor_arrow_plot",
        data_files=[],
        use_llm=False,
    )
    assert rb.full_name == "meta_and_diagnostic.bayes_factor_arrow_plot"
    assert rb.fully_bound is False
    # Every required binding is unbound.
    for b in rb.bindings:
        if b.is_required:
            assert b.pass_used == "unbound"
            assert b.data_source is None
            assert b.confidence == 0.0
    # We saw at least one required field.
    assert any(b.is_required for b in rb.bindings)


# ---------------------------------------------------------------------------
# Test 7 — Hallucination guard
# ---------------------------------------------------------------------------


def test_pass3_hallucination_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    csv_path = _write_csv(tmp_path / "d.csv", ["legit_col"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("legit_col",), n_rows=3,
    )
    # Returning a column the data files do not contain — must be ignored.
    def fake_llm(field_name, field_type, field_description, candidate_columns, samples):
        # Simulate the hallucination guard inside _llm_pass: return None.
        # (The real _llm_pass already does this; we simulate post-guard output here.)
        return (None, 0.0, "hallucinated column 'made_up'")

    monkeypatch.setattr(db, "_llm_pass", fake_llm)
    rb = db.bind_recipe_to_data(
        recipe_full_name="_test_db_modality.estimates_recipe",
        data_files=[df],
        use_llm=True,
    )
    estimates = next(b for b in rb.bindings if b.contract_field == "estimates")
    assert estimates.pass_used == "unbound"
    assert estimates.column_name is None


def test_pass3_real_llm_function_rejects_hallucination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The internal _llm_pass should reject hallucinated columns."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Build a fake `anthropic` module with a stub Anthropic client.
    class _FakeContent:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeMessage:
        def __init__(self, text: str) -> None:
            self.content = [_FakeContent(text)]

    class _FakeMessages:
        def create(self, **_kw):
            return _FakeMessage("Reasoning... BEST_MATCH: made_up_column")

    class _FakeAnthropic:
        def __init__(self) -> None:
            self.messages = _FakeMessages()

    fake_mod = type(sys)("anthropic")
    fake_mod.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)

    col, conf, _reason = db._llm_pass(
        field_name="estimates",
        field_type="list[float]",
        field_description="",
        candidate_columns=["real_a", "real_b"],
        samples={},
    )
    assert col is None
    assert conf == 0.0


# ---------------------------------------------------------------------------
# Test 8 — Cross-recipe LLM cache
# ---------------------------------------------------------------------------


def test_cross_recipe_cache_reuses_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    csv_path = _write_csv(tmp_path / "d.csv", ["zzz_pure_noise", "qqq_other"])
    df = db.DataFile(
        path=csv_path, format="csv",
        columns=("zzz_pure_noise", "qqq_other"), n_rows=3,
    )

    call_log: list[tuple[str, tuple[str, ...]]] = []

    def fake_llm(field_name, field_type, field_description, candidate_columns, samples):
        call_log.append((field_name, tuple(candidate_columns)))
        if field_name == "estimates":
            return ("zzz_pure_noise", 0.7, "ok")
        if field_name == "counts":
            return ("qqq_other", 0.7, "ok")
        return (None, 0.0, "")

    monkeypatch.setattr(db, "_llm_pass", fake_llm)
    results = db.bind_shortlist_to_data(
        shortlist=[
            "_test_db_modality.estimates_recipe",
            "_test_db_modality.two_field_recipe",
        ],
        data_files=[df],
        use_llm=True,
    )
    assert len(results) == 2
    # "estimates" appears in BOTH recipes; the LLM should be called once for it
    # because the candidate-column pool is identical.
    estimates_calls = [c for c in call_log if c[0] == "estimates"]
    assert len(estimates_calls) == 1


# ---------------------------------------------------------------------------
# Test 9 — Lazy import of anthropic
# ---------------------------------------------------------------------------


def test_data_bridge_import_does_not_pull_anthropic() -> None:
    """Importing the module must not trigger an import of `anthropic`.

    Run in a subprocess so we are not contaminated by other tests'
    monkeypatches that may have inserted a stub `anthropic` into
    ``sys.modules``.
    """
    import subprocess

    cwd = Path(__file__).resolve().parents[1]
    code = (
        "import sys\n"
        "from panelforge_figures.manifest.data_bridge import bind_recipe_to_data\n"
        "assert 'anthropic' not in sys.modules, "
        "'anthropic was eagerly imported (sys.modules check failed)'\n"
        "print('OK')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd=cwd,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "OK" in proc.stdout


# ---------------------------------------------------------------------------
# Test 10 — Unknown recipe handling
# ---------------------------------------------------------------------------


def test_unknown_recipe_returns_skipped() -> None:
    rb = db.bind_recipe_to_data(
        recipe_full_name="no_such_modality.nope",
        data_files=[],
        use_llm=False,
    )
    assert rb.fully_bound is False
    assert rb.bindings == ()
    assert rb.skipped_reason and "unknown recipe" in rb.skipped_reason
