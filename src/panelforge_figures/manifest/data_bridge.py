"""Data-bridge: bind user data files to recipe Pydantic contract fields.

Wave 3 — see ``CLAUDE_CODE_AUTONOMOUS.md`` §5.

The data bridge is a 3-pass mapper. Given a recipe's Pydantic contract
and a pool of data files (CSV / parquet / npz / etc.), it tries to
bind each contract field to a column / array key:

1. **Pass 1 — exact name match**: case-insensitive equality between
   the contract field name and a column name. Confidence 1.0.
2. **Pass 2 — fuzzy match**: ``difflib.get_close_matches`` with
   ``cutoff=0.8``. Confidence in ``[0.7, 0.95]`` based on the ratio.
3. **Pass 3 — LLM fallback**: lazy-import ``anthropic`` and ask
   Claude which column is the best match. Gated on the
   ``ANTHROPIC_API_KEY`` environment variable. If no key (or no
   ``anthropic`` package), Pass 3 returns cleanly with no binding —
   the field is reported as ``unbound``.

The lazy-import is critical: importing this module must NOT pull in
``anthropic`` so that downstream callers (e.g. CLI on machines
without the optional dep) keep working. The import lives inside
:func:`_llm_pass`.
"""

from __future__ import annotations

import csv
import difflib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataFile:
    """One discovered data file with a sample-read schema."""

    path: Path
    format: str                          # "csv" | "tsv" | "parquet" | "npz" | "tif" | "npy" | "json"
    columns: tuple[str, ...]             # column names (tabular) or array keys (npz/json)
    n_rows: int | None                   # None for non-tabular


@dataclass(frozen=True)
class FieldBinding:
    """One contract field's binding decision."""

    contract_field: str
    field_type: str                      # str-repr of the Pydantic type
    is_required: bool
    data_source: Path | None
    column_name: str | None
    pass_used: str                       # "exact" | "fuzzy" | "llm" | "unbound"
    confidence: float                    # 0.0 if unbound


@dataclass(frozen=True)
class RecipeBinding:
    """The full binding result for one recipe."""

    full_name: str
    bindings: tuple[FieldBinding, ...]
    fully_bound: bool
    skipped_reason: str | None


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


_KNOWN_EXTS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".npz": "npz",
    ".npy": "npy",
    ".tif": "tif",
    ".tiff": "tif",
    ".json": "json",
}

_SAMPLE_ROWS = 100  # cap on rows scanned during discovery


def _read_csv_schema(path: Path, delimiter: str) -> tuple[tuple[str, ...], int]:
    """Return ``(columns, n_rows)`` after reading at most _SAMPLE_ROWS rows."""
    with path.open("r", newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return ((), 0)
        n = 0
        for n, _row in enumerate(reader, start=1):
            if n >= _SAMPLE_ROWS:
                break
        return (tuple(c.strip() for c in header), n)


def _read_parquet_schema(path: Path) -> tuple[tuple[str, ...], int | None]:
    """Read parquet header without loading the whole file."""
    try:
        import pyarrow.parquet as pq
    except ImportError:                  # pragma: no cover — pyarrow is a hard dep
        return ((), None)
    pf = pq.ParquetFile(str(path))
    cols = tuple(pf.schema_arrow.names)
    n_rows = pf.metadata.num_rows if pf.metadata is not None else None
    return (cols, n_rows)


def _read_npz_schema(path: Path) -> tuple[tuple[str, ...], int | None]:
    """``np.load`` lazily — keys only, no array reads."""
    try:
        import numpy as np
    except ImportError:                  # pragma: no cover
        return ((), None)
    with np.load(str(path), allow_pickle=False) as arch:
        keys = tuple(sorted(arch.files))
    return (keys, None)


def _read_npy_schema(path: Path) -> tuple[tuple[str, ...], int | None]:
    """Single-array .npy — expose the file stem as the only "column"."""
    return ((path.stem,), None)


def _read_json_schema(path: Path) -> tuple[tuple[str, ...], int | None]:
    """Top-level keys (object) or stem (array)."""
    try:
        with path.open("r") as fh:
            obj = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return ((), None)
    if isinstance(obj, dict):
        return (tuple(obj.keys()), None)
    if isinstance(obj, list):
        return ((path.stem,), len(obj))
    return ((path.stem,), None)


def _read_tif_schema(path: Path) -> tuple[tuple[str, ...], int | None]:
    """Image — single virtual "column" named after the file stem."""
    return ((path.stem,), None)


def _schema_for(path: Path) -> tuple[str, tuple[str, ...], int | None] | None:
    """Dispatch on extension; return ``(format, columns, n_rows)`` or None."""
    fmt = _KNOWN_EXTS.get(path.suffix.lower())
    if fmt is None:
        return None
    try:
        if fmt == "csv":
            cols, n = _read_csv_schema(path, ",")
            return (fmt, cols, n)
        if fmt == "tsv":
            cols, n = _read_csv_schema(path, "\t")
            return (fmt, cols, n)
        if fmt == "parquet":
            cols, n = _read_parquet_schema(path)
            return (fmt, cols, n)
        if fmt == "npz":
            cols, n = _read_npz_schema(path)
            return (fmt, cols, n)
        if fmt == "npy":
            cols, n = _read_npy_schema(path)
            return (fmt, cols, n)
        if fmt == "json":
            cols, n = _read_json_schema(path)
            return (fmt, cols, n)
        if fmt == "tif":
            cols, n = _read_tif_schema(path)
            return (fmt, cols, n)
    except Exception:                    # degrade gracefully on bad files
        return None
    return None


def discover_data_files(data_dir: Path = Path("data")) -> list[DataFile]:
    """Walk ``data_dir`` recursively; sample-read schemas for known formats.

    Files with unknown extensions or unreadable contents are skipped.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        return []
    out: list[DataFile] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        result = _schema_for(path)
        if result is None:
            continue
        fmt, cols, n_rows = result
        out.append(DataFile(path=path, format=fmt, columns=cols, n_rows=n_rows))
    return out


# ---------------------------------------------------------------------------
# Pass 1 — exact match
# ---------------------------------------------------------------------------


def _exact_pass(field_name: str, columns: Iterable[str]) -> str | None:
    """Case-insensitive equality. Returns the matched column or None."""
    target = field_name.lower()
    for col in columns:
        if col.lower() == target:
            return col
    return None


# ---------------------------------------------------------------------------
# Pass 2 — fuzzy match
# ---------------------------------------------------------------------------


def _fuzzy_pass(
    field_name: str, columns: list[str]
) -> tuple[str | None, float]:
    """``difflib.get_close_matches`` with cutoff 0.8.

    Returns ``(column_name, confidence)``. Confidence is the SequenceMatcher
    ratio clamped to ``[0.7, 0.95]``.
    """
    if not columns:
        return None, 0.0
    matches = difflib.get_close_matches(
        field_name.lower(),
        [c.lower() for c in columns],
        n=1,
        cutoff=0.8,
    )
    if not matches:
        return None, 0.0
    matched_lower = matches[0]
    # Recover original-case column.
    original = next((c for c in columns if c.lower() == matched_lower), matched_lower)
    ratio = difflib.SequenceMatcher(
        None, field_name.lower(), matched_lower
    ).ratio()
    confidence = max(0.7, min(0.95, ratio))
    return original, confidence


# ---------------------------------------------------------------------------
# Pass 3 — LLM fallback (lazy import)
# ---------------------------------------------------------------------------


def _llm_pass(
    field_name: str,
    field_type: str,
    field_description: str,
    candidate_columns: list[str],
    samples: dict[str, list],
) -> tuple[str | None, float, str]:
    """Ask Claude which candidate column best matches the contract field.

    Lazy-imports ``anthropic`` so that callers without the optional
    package can still import this module. Returns ``(column, conf, reason)``;
    ``column`` is None on any failure path.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, 0.0, "no API key"
    try:
        import anthropic  # lazy by design — optional dep, gated above
    except ImportError:
        return None, 0.0, "anthropic package not installed"
    if not candidate_columns:
        return None, 0.0, "no candidate columns"

    client = anthropic.Anthropic()
    sample_lines = "\n".join(
        f"  {c}: sample={samples.get(c, [])[:3]}" for c in candidate_columns
    )
    prompt = (
        "Given a recipe contract field:\n"
        f"  name: {field_name}\n"
        f"  type: {field_type}\n"
        f"  description: {field_description}\n\n"
        "And these candidate data columns:\n"
        f"{sample_lines}\n\n"
        "Which single column is the best match? Return null if no column matches.\n"
        "Reason briefly, then output: BEST_MATCH: <column_name or null>"
    )
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
    except Exception as exc:                                  # network / API errors
        return None, 0.0, f"anthropic error: {exc}"

    match = re.search(r"BEST_MATCH:\s*(\S+)", text, re.IGNORECASE)
    if not match or match.group(1).lower() in ("null", "none"):
        return None, 0.0, text
    column = match.group(1).strip().rstrip(".,")
    if column not in candidate_columns:                       # hallucination guard
        return None, 0.0, f"hallucinated column '{column}'"
    confidence = 0.7 if "BEST_MATCH:" in text.upper() else 0.5
    return column, confidence, text


# ---------------------------------------------------------------------------
# Per-recipe binding
# ---------------------------------------------------------------------------


def _field_type_str(annotation: Any) -> str:
    """String representation of a Pydantic field's annotation."""
    if annotation is None:
        return "Any"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation)


def _field_description(field_info: Any) -> str:
    """Best-effort description for the LLM prompt."""
    desc = getattr(field_info, "description", None)
    return desc or ""


def _all_columns_pool(
    data_files: list[DataFile],
) -> list[tuple[Path, str]]:
    """Flatten ``(path, column)`` pairs for the candidate pool."""
    return [(df.path, c) for df in data_files for c in df.columns]


def _bind_one_field(
    field_name: str,
    field_type: str,
    is_required: bool,
    field_description: str,
    data_files: list[DataFile],
    use_llm: bool,
    llm_call_cache: dict[tuple[str, str], tuple[str | None, float, str]] | None = None,
) -> FieldBinding:
    """Run the 3 passes for one contract field."""
    # Pass 1 — exact, per-file.
    for df in data_files:
        match = _exact_pass(field_name, df.columns)
        if match is not None:
            return FieldBinding(
                contract_field=field_name,
                field_type=field_type,
                is_required=is_required,
                data_source=df.path,
                column_name=match,
                pass_used="exact",
                confidence=1.0,
            )

    # Pass 2 — fuzzy, per-file (highest score wins).
    best_fuzzy: tuple[Path | None, str | None, float] = (None, None, 0.0)
    for df in data_files:
        col, conf = _fuzzy_pass(field_name, list(df.columns))
        if col is not None and conf > best_fuzzy[2]:
            best_fuzzy = (df.path, col, conf)
    if best_fuzzy[1] is not None:
        return FieldBinding(
            contract_field=field_name,
            field_type=field_type,
            is_required=is_required,
            data_source=best_fuzzy[0],
            column_name=best_fuzzy[1],
            pass_used="fuzzy",
            confidence=best_fuzzy[2],
        )

    # Pass 3 — LLM, on the union of all columns.
    if use_llm and data_files:
        candidates = _all_columns_pool(data_files)
        candidate_cols = [c for _p, c in candidates]
        # cache key — by field + sorted candidate list — so we don't re-ask.
        cache_key = (field_name, "|".join(sorted(set(candidate_cols))))
        if llm_call_cache is not None and cache_key in llm_call_cache:
            llm_result = llm_call_cache[cache_key]
        else:
            llm_result = _llm_pass(
                field_name=field_name,
                field_type=field_type,
                field_description=field_description,
                candidate_columns=candidate_cols,
                samples={},
            )
            if llm_call_cache is not None:
                llm_call_cache[cache_key] = llm_result
        col, conf, _reason = llm_result
        if col is not None:
            # Find which file the chosen column belongs to.
            source_path = next(
                (p for p, c in candidates if c == col),
                None,
            )
            if source_path is not None:
                return FieldBinding(
                    contract_field=field_name,
                    field_type=field_type,
                    is_required=is_required,
                    data_source=source_path,
                    column_name=col,
                    pass_used="llm",
                    confidence=conf,
                )

    return FieldBinding(
        contract_field=field_name,
        field_type=field_type,
        is_required=is_required,
        data_source=None,
        column_name=None,
        pass_used="unbound",
        confidence=0.0,
    )


def bind_recipe_to_data(
    *,
    recipe_full_name: str,
    data_files: list[DataFile],
    use_llm: bool = True,
    _llm_call_cache: dict[tuple[str, str], tuple[str | None, float, str]] | None = None,
) -> RecipeBinding:
    """Run the 3-pass mapping for one recipe.

    Returns a :class:`RecipeBinding` even if not fully bound — callers
    decide whether to skip downstream rendering.
    """
    from ..core.contract import ensure_all_imported, get_recipe  # local import — keeps module light
    ensure_all_imported()
    try:
        entry = get_recipe(recipe_full_name)
    except KeyError:
        return RecipeBinding(
            full_name=recipe_full_name,
            bindings=(),
            fully_bound=False,
            skipped_reason=f"unknown recipe: {recipe_full_name}",
        )

    schema = entry.contract.model_json_schema()
    schema_props = schema.get("properties", {}) if isinstance(schema, dict) else {}

    bindings: list[FieldBinding] = []
    for fname, finfo in entry.contract.model_fields.items():
        ftype = _field_type_str(finfo.annotation)
        required = finfo.is_required()
        prop_block = schema_props.get(fname, {})
        if isinstance(prop_block, dict):
            fdesc = prop_block.get("description") or _field_description(finfo)
        else:
            fdesc = _field_description(finfo)
        binding = _bind_one_field(
            field_name=fname,
            field_type=ftype,
            is_required=required,
            field_description=fdesc,
            data_files=data_files,
            use_llm=use_llm,
            llm_call_cache=_llm_call_cache,
        )
        bindings.append(binding)

    fully_bound = compute_fully_bound(bindings)
    return RecipeBinding(
        full_name=recipe_full_name,
        bindings=tuple(bindings),
        fully_bound=fully_bound,
        skipped_reason=None if fully_bound else "missing required fields",
    )


def compute_fully_bound(bindings: Iterable[FieldBinding]) -> bool:
    """Return ``True`` iff every required field has a non-None data source.

    Single source of truth for the ``fully_bound`` predicate — both
    :func:`bind_recipe_to_data` and CLI consumers reading from the
    on-disk cache call into this helper so they cannot diverge.
    """
    return all(b.data_source is not None for b in bindings if b.is_required)


def bind_shortlist_to_data(
    *,
    shortlist: list[str],
    data_files: list[DataFile],
    use_llm: bool = True,
) -> list[RecipeBinding]:
    """Bind a shortlist of recipes to the same data pool.

    Caches per-(field_name, candidate_columns) LLM calls so the LLM is
    invoked at most once per (field, column-pool) pair across the shortlist.
    """
    cache: dict[tuple[str, str], tuple[str | None, float, str]] = {}
    return [
        bind_recipe_to_data(
            recipe_full_name=name,
            data_files=data_files,
            use_llm=use_llm,
            _llm_call_cache=cache,
        )
        for name in shortlist
    ]


# ---------------------------------------------------------------------------
# Cache persistence
# ---------------------------------------------------------------------------


def _binding_to_dict(b: FieldBinding) -> dict[str, Any]:
    d = asdict(b)
    if d["data_source"] is not None:
        d["data_source"] = str(d["data_source"])
    return d


def _binding_from_dict(d: dict[str, Any]) -> FieldBinding:
    src = d.get("data_source")
    return FieldBinding(
        contract_field=d["contract_field"],
        field_type=d["field_type"],
        is_required=bool(d["is_required"]),
        data_source=Path(src) if src else None,
        column_name=d.get("column_name"),
        pass_used=d["pass_used"],
        confidence=float(d["confidence"]),
    )


def write_bindings_cache(
    bindings: list[RecipeBinding],
    cache_path: Path = Path("panelforge_workspace/data_bridge_cache.json"),
) -> Path:
    """Persist confirmed bindings as JSON. Creates parent dirs as needed."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "recipes": [
            {
                "full_name": rb.full_name,
                "fully_bound": rb.fully_bound,
                "skipped_reason": rb.skipped_reason,
                "bindings": [_binding_to_dict(b) for b in rb.bindings],
            }
            for rb in bindings
        ],
    }
    cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return cache_path


def load_bindings_cache(
    cache_path: Path = Path("panelforge_workspace/data_bridge_cache.json"),
) -> dict[tuple[str, str], FieldBinding]:
    """Load cache keyed by ``(recipe_full_name, contract_field)``.

    Returns an empty dict if the cache is missing or malformed.
    """
    cache_path = Path(cache_path)
    if not cache_path.exists():
        return {}
    try:
        payload = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[tuple[str, str], FieldBinding] = {}
    for rb in payload.get("recipes", []):
        full = rb.get("full_name", "")
        for bd in rb.get("bindings", []):
            try:
                fb = _binding_from_dict(bd)
            except (KeyError, TypeError):
                continue
            out[(full, fb.contract_field)] = fb
    return out


# ─────────────────────────── render_loop adapter ───────────────────────


def to_render_binding(binding: RecipeBinding) -> Any:
    """Convert canonical ``data_bridge.RecipeBinding`` to the flat-shape
    ``render_loop.RenderBinding`` consumed by the render loop.

    Populates ``data_file_per_field`` so multi-source bindings (a recipe
    whose fields draw from two or more files) are preserved end-to-end.
    ``data_file_id`` is also set when every field happens to share a
    single source — kept for back-compat with callers that still read
    that attribute.

    Lazily imports ``render_loop`` to avoid an import cycle.
    """
    from .render_loop import RenderBinding
    column_mapping = {
        fb.contract_field: fb.column_name
        for fb in binding.bindings
        if fb.column_name is not None
    }
    data_file_per_field = {
        fb.contract_field: fb.data_source
        for fb in binding.bindings
        if fb.data_source is not None
    }
    sources = set(data_file_per_field.values())
    data_file_id = str(next(iter(sources))) if len(sources) == 1 else None
    return RenderBinding(
        full_name=binding.full_name,
        fully_bound=binding.fully_bound,
        column_mapping=column_mapping,
        data_file_per_field=data_file_per_field,
        data_file_id=data_file_id,
        unbound_reason=binding.skipped_reason,
    )


def to_render_data_files(files: list[DataFile]) -> list[Any]:
    """Convert ``data_bridge.DataFile`` objects to the simpler
    ``render_loop.RenderDataFile`` shape (file_id keyed by str(path))."""
    from .render_loop import RenderDataFile
    return [
        RenderDataFile(file_id=str(f.path), path=f.path) for f in files
    ]


__all__ = [
    "DataFile",
    "FieldBinding",
    "RecipeBinding",
    "bind_recipe_to_data",
    "bind_shortlist_to_data",
    "compute_fully_bound",
    "discover_data_files",
    "load_bindings_cache",
    "to_render_binding",
    "to_render_data_files",
    "write_bindings_cache",
]
