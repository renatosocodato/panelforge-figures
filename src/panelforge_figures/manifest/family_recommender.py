"""Data-driven figure family recommender (Elevation 8).

Analyses raw data structure (CSV / DataFrame / Parquet / Excel / JSON) and
recommends ranked figure families with confidence scores and rationale.

Surfaces "recipe gaps" — combinations of (family, data shape) for which no
existing recipe is a good fit; the user can opt to scaffold a tailored recipe
via the E6 author-recipe infrastructure (``manifest.recipe_authoring``).

Design principles
-----------------
* The principled stance is preserved: *the human chooses the figure family*.
  This module only **informs** the user of the best candidates plus the
  matching recipes; nothing is auto-selected, nothing is auto-scaffolded.
* Scoring is heuristic — confidence is in [0, 1] and combines additive
  evidence rules. The rationale string explains *why* each family scored.
* ``pandas`` is lazy-imported inside :func:`profile_data`. The module is
  importable without pandas; only the actual profiling needs it.

Public surface
--------------
:class:`DataProfile` — coarse profile of a tabular data source.
:class:`FamilyRecommendation` — ranked recommendation with rationale.
:class:`RecipeGap` — a high-confidence family with no matching recipe.
:func:`profile_data` — read a data source and emit a profile.
:func:`recommend_families` — score and rank figure families against a profile.
:func:`find_matching_recipes` — look up registry entries that fit a family.
:func:`detect_recipe_gaps` — identify gaps the author-recipe pipeline can fill.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "DataKind",
    "DataProfile",
    "FamilyRecommendation",
    "GroupingStructure",
    "RecipeGap",
    "RecommenderError",
    "detect_recipe_gaps",
    "find_matching_recipes",
    "profile_data",
    "recommend_families",
]


# ──────────────────────── enums and dataclasses ──────────────────────────


class DataKind(StrEnum):
    """Coarse classification of a data column."""

    numeric = "numeric"
    categorical = "categorical"
    binary = "binary"  # 0/1 or True/False
    ordinal = "ordinal"
    datetime = "datetime"
    text = "text"
    unknown = "unknown"


class GroupingStructure(StrEnum):
    """How observations relate to one another."""

    independent = "independent"  # iid samples
    paired = "paired"  # same subjects measured twice
    repeated_measures = "repeated_measures"  # same subjects, ≥3 timepoints
    factorial = "factorial"  # 2x2 / 2x3 etc.
    nested = "nested"  # cells within tissues within mice
    unknown = "unknown"


@dataclass(frozen=True)
class DataProfile:
    """Result of profiling a raw data table."""

    n_rows: int
    n_cols: int
    column_kinds: dict[str, DataKind]
    n_numeric: int
    n_categorical: int
    n_binary: int
    n_missing_total: int
    fraction_missing: float
    grouping_structure: GroupingStructure
    n_groups: int  # if categorical, number of distinct groups
    n_per_group: dict[str, int]  # counts per group (per first factor column)
    has_paired_id: bool  # True if a 'subject_id' or 'cell_id' column exists
    has_time_column: bool  # True if a datetime column exists
    candidate_factor_columns: tuple[str, ...]  # categorical with ≤6 levels
    candidate_response_columns: tuple[str, ...]  # numeric with full data
    detected_2x2: bool  # has 2 factors with 2 levels each
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of the profile."""
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "column_kinds": {k: v.value for k, v in self.column_kinds.items()},
            "n_numeric": self.n_numeric,
            "n_categorical": self.n_categorical,
            "n_binary": self.n_binary,
            "n_missing_total": self.n_missing_total,
            "fraction_missing": self.fraction_missing,
            "grouping_structure": self.grouping_structure.value,
            "n_groups": self.n_groups,
            "n_per_group": dict(self.n_per_group),
            "has_paired_id": self.has_paired_id,
            "has_time_column": self.has_time_column,
            "candidate_factor_columns": list(self.candidate_factor_columns),
            "candidate_response_columns": list(self.candidate_response_columns),
            "detected_2x2": self.detected_2x2,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FamilyRecommendation:
    """Recommendation for a single figure family."""

    family: str  # RecipeFamily.value or one of the supported author-recipe families
    confidence: float  # ∈ [0, 1]
    rationale: str  # why this family fits the data
    n_matching_recipes: int  # how many recipes in the registry match
    matching_recipe_names: tuple[str, ...] = ()  # full_names of top-N candidates


@dataclass(frozen=True)
class RecipeGap:
    """A gap: a recommended family with no matching recipe."""

    family: str
    data_profile_summary: str  # human-readable summary
    suggested_recipe_name: str  # auto-generated name suggestion
    suggested_modality: str  # auto-generated modality suggestion
    suggested_research_question: str  # auto-generated research question
    rationale: str  # why a recipe is needed


class RecommenderError(RuntimeError):
    """Raised on profile errors (unsupported format, missing file, etc.)."""


# ─────────────────────────── data profiling ──────────────────────────────


_DEFAULT_PAIRED_ID_COLUMNS: tuple[str, ...] = (
    "subject_id",
    "cell_id",
    "mouse_id",
    "id",
    "participant_id",
    "patient_id",
    "animal_id",
)
_DEFAULT_TIME_KEYWORDS: tuple[str, ...] = (
    "time",
    "date",
    "timestamp",
    "day",
    "minute",
    "second",
    "hour",
)


def profile_data(
    data_source: Any,  # Path | str | pandas.DataFrame
    *,
    paired_id_columns: tuple[str, ...] = _DEFAULT_PAIRED_ID_COLUMNS,
    time_column_keywords: tuple[str, ...] = _DEFAULT_TIME_KEYWORDS,
    max_categorical_levels: int = 50,
    factor_max_levels: int = 6,
) -> DataProfile:
    """Profile a raw data source.

    Supported sources: ``Path`` to ``.csv`` / ``.tsv`` / ``.parquet`` /
    ``.xlsx`` / ``.json`` files, or any ``pandas.DataFrame`` (duck-typed).

    Heuristics
    ----------
    * **kind detection** — try numeric coercion → ``numeric``; else ≤
      ``max_categorical_levels`` distinct values → ``categorical``; else
      ``text``.
    * **binary** — exactly 2 unique non-null values.
    * **paired_id** — any column whose name matches ``paired_id_columns``
      *and* has fewer distinct values than rows (i.e. each id repeats).
    * **factorial** — at least 2 categorical columns each with 2 levels →
      ``detected_2x2``; ``GroupingStructure.factorial`` is set when ≥ 2
      candidate factor columns are present.
    * **candidate_factor_columns** — categorical with ≤ ``factor_max_levels``
      levels (sorted by name for determinism).
    * **candidate_response_columns** — numeric with < 50% missing.
    """
    import pandas as pd  # heavy import: deferred until profiling is requested

    df = _load_dataframe(data_source, pd=pd)
    notes: list[str] = []

    n_rows = int(df.shape[0])
    n_cols = int(df.shape[1])
    if n_rows == 0:
        raise RecommenderError("data source has zero rows; cannot profile")
    if n_cols == 0:
        raise RecommenderError("data source has zero columns; cannot profile")

    column_kinds: dict[str, DataKind] = {}
    n_numeric = 0
    n_categorical = 0
    n_binary = 0
    n_missing_total = 0

    candidate_factor_columns: list[str] = []
    candidate_response_columns: list[str] = []

    # We gather (column, n_levels) for factorial detection.
    factor_levels: list[tuple[str, int]] = []

    has_time_column = False
    has_paired_id = False
    paired_id_match: str | None = None

    n_per_group: dict[str, int] = {}
    n_groups = 0
    grouping_structure = GroupingStructure.independent  # default until upgraded

    for col in df.columns:
        col_str = str(col)
        series = df[col]
        n_missing = int(series.isna().sum())
        n_missing_total += n_missing

        kind = _classify_column(
            series,
            pd=pd,
            max_categorical_levels=max_categorical_levels,
        )
        column_kinds[col_str] = kind

        if kind == DataKind.numeric:
            n_numeric += 1
            if (n_missing / max(n_rows, 1)) < 0.5:
                candidate_response_columns.append(col_str)
        elif kind == DataKind.binary:
            n_binary += 1
            n_categorical += 1
            factor_levels.append((col_str, 2))
            if 2 <= factor_max_levels:
                candidate_factor_columns.append(col_str)
        elif kind == DataKind.categorical:
            n_categorical += 1
            n_levels = int(series.nunique(dropna=True))
            factor_levels.append((col_str, n_levels))
            if n_levels <= factor_max_levels:
                candidate_factor_columns.append(col_str)
        elif kind == DataKind.datetime:
            has_time_column = True

        # paired-id detection (column-name match + repeats)
        lname = col_str.lower()
        if lname in {p.lower() for p in paired_id_columns}:
            try:
                n_distinct = int(series.nunique(dropna=True))
            except (TypeError, ValueError):
                n_distinct = n_rows
            if 0 < n_distinct < n_rows:
                has_paired_id = True
                paired_id_match = col_str

        # time-column keyword fallback (handles strings like "day_5")
        if not has_time_column and any(kw in lname for kw in time_column_keywords):
            if kind in (DataKind.numeric, DataKind.datetime):
                has_time_column = True

    # First categorical factor → group counts
    if candidate_factor_columns:
        first_factor = candidate_factor_columns[0]
        try:
            counts = df[first_factor].value_counts(dropna=True)
            n_per_group = {str(k): int(v) for k, v in counts.items()}
            n_groups = len(n_per_group)
        except Exception:  # pragma: no cover — defensive fallback
            n_per_group = {}
            n_groups = 0

    # Factorial / 2x2 detection: at least 2 factor columns each with 2 levels.
    factor_levels_two = [c for c, k in factor_levels if k == 2]
    detected_2x2 = len(factor_levels_two) >= 2

    if len(candidate_factor_columns) >= 2:
        grouping_structure = GroupingStructure.factorial
    elif has_paired_id and paired_id_match is not None:
        # Decide paired vs repeated_measures by counting per-id observations.
        try:
            per_id_counts = df[paired_id_match].value_counts(dropna=True)
            max_per_id = int(per_id_counts.max()) if len(per_id_counts) else 0
        except Exception:  # pragma: no cover
            max_per_id = 0
        if max_per_id >= 3:
            grouping_structure = GroupingStructure.repeated_measures
        elif max_per_id == 2:
            grouping_structure = GroupingStructure.paired
        else:
            grouping_structure = GroupingStructure.independent

    fraction_missing = (
        n_missing_total / (n_rows * n_cols) if (n_rows and n_cols) else 0.0
    )
    if fraction_missing > 0.20:
        notes.append(
            f"high missingness: {fraction_missing:.0%} of cells are NA"
        )
    if n_rows < 10:
        notes.append(f"very small sample (n_rows={n_rows}); estimates will be noisy")

    return DataProfile(
        n_rows=n_rows,
        n_cols=n_cols,
        column_kinds=column_kinds,
        n_numeric=n_numeric,
        n_categorical=n_categorical,
        n_binary=n_binary,
        n_missing_total=n_missing_total,
        fraction_missing=fraction_missing,
        grouping_structure=grouping_structure,
        n_groups=n_groups,
        n_per_group=n_per_group,
        has_paired_id=has_paired_id,
        has_time_column=has_time_column,
        candidate_factor_columns=tuple(candidate_factor_columns),
        candidate_response_columns=tuple(candidate_response_columns),
        detected_2x2=detected_2x2,
        notes=tuple(notes),
    )


def _load_dataframe(data_source: Any, *, pd: Any) -> Any:
    """Load a DataFrame from a Path / str / DataFrame-like."""
    if isinstance(data_source, pd.DataFrame):
        return data_source

    if isinstance(data_source, str):
        data_source = Path(data_source)

    if isinstance(data_source, Path):
        if not data_source.exists():
            raise RecommenderError(f"data file not found: {data_source}")
        suffix = data_source.suffix.lower()
        try:
            if suffix == ".csv":
                return pd.read_csv(data_source)
            if suffix == ".tsv":
                return pd.read_csv(data_source, sep="\t")
            if suffix in (".parquet", ".pq"):
                return pd.read_parquet(data_source)
            if suffix in (".xlsx", ".xls"):
                return pd.read_excel(data_source)
            if suffix == ".json":
                return pd.read_json(data_source)
        except Exception as exc:
            raise RecommenderError(
                f"failed to read {data_source}: {exc}"
            ) from exc
        raise RecommenderError(
            f"unsupported file format: {data_source.suffix!r} "
            "(supported: .csv .tsv .parquet .pq .xlsx .xls .json)"
        )

    # Duck-typing fallback for DataFrame-like objects from libraries that
    # mimic pandas (polars.to_pandas() etc.).
    if hasattr(data_source, "columns") and hasattr(data_source, "shape"):
        return data_source

    raise RecommenderError(
        f"unsupported data source type: {type(data_source).__name__}"
    )


def _classify_column(
    series: Any, *, pd: Any, max_categorical_levels: int
) -> DataKind:
    """Coarse type detection for a single column."""
    # Empty-after-dropna columns are unknown.
    non_null = series.dropna()
    if len(non_null) == 0:
        return DataKind.unknown

    # datetime detection
    if pd.api.types.is_datetime64_any_dtype(series):
        return DataKind.datetime

    # bool dtype
    if pd.api.types.is_bool_dtype(series):
        return DataKind.binary

    # numeric path (already a numeric dtype)
    if pd.api.types.is_numeric_dtype(series):
        unique = non_null.unique()
        if len(unique) == 2 and set(map(_to_int_or_none, unique)) <= {0, 1}:
            return DataKind.binary
        return DataKind.numeric

    # try to coerce object → numeric (e.g. CSVs that read as object)
    try:
        coerced = pd.to_numeric(non_null, errors="raise")
        unique = pd.Series(coerced).unique()
        if len(unique) == 2 and set(map(_to_int_or_none, unique)) <= {0, 1}:
            return DataKind.binary
        return DataKind.numeric
    except (ValueError, TypeError):
        pass

    # try datetime coerce — but only if values *look* like timestamps. We
    # don't want to fall through pd.to_datetime for arbitrary categorical
    # text, which emits UserWarning under the "infer format" code path
    # (pytest's filterwarnings = "error" turns these into hard failures).
    sample = str(next(iter(non_null), ""))
    looks_like_time = any(ch in sample for ch in (":", "-", "/")) and any(
        ch.isdigit() for ch in sample
    )
    if looks_like_time:
        import warnings

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                pd.to_datetime(non_null, errors="raise")
            return DataKind.datetime
        except (ValueError, TypeError, OverflowError, UserWarning, Warning):
            pass

    # boolean strings ("True"/"False", "yes"/"no")
    str_unique = {str(v).strip().lower() for v in non_null.unique()}
    if str_unique <= {"true", "false"} or str_unique <= {"yes", "no"}:
        return DataKind.binary

    # else: categorical or text
    n_unique = len(non_null.unique())
    if n_unique <= max_categorical_levels:
        return DataKind.categorical
    return DataKind.text


def _to_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ─────────────────────────── recommendations ─────────────────────────────


def recommend_families(
    profile: DataProfile,
    *,
    top_k: int = 5,
    confidence_floor: float = 0.05,
) -> list[FamilyRecommendation]:
    """Rank figure families by fit to the data profile.

    Heuristic rules combine additive evidence; each rule contributes to
    the family's score. Final scores are clipped to [0, 1] and sorted
    descending. The rationale string concatenates fired rules.

    The families considered are the five families supported by the
    author-recipe pipeline (``coef_forest``, ``comparison``,
    ``correlation``, ``factorial``, ``equivalence``) plus the registry
    families (``timecourse_hierarchical_ci``, ``diagnostic_curve``,
    ``volcano``, ``ridge_by_group``).
    """
    candidates: dict[str, dict[str, Any]] = {}

    def bump(family: str, weight: float, reason: str) -> None:
        slot = candidates.setdefault(
            family, {"score": 0.0, "reasons": []}
        )
        slot["score"] += weight
        slot["reasons"].append(reason)

    n_responses = len(profile.candidate_response_columns)
    n_factors = len(profile.candidate_factor_columns)
    n_per_group_min = (
        min(profile.n_per_group.values()) if profile.n_per_group else 0
    )
    n_per_group_min = int(n_per_group_min)

    # ── factorial ─────────────────────────────────────────────────────
    if profile.detected_2x2:
        bump(
            "factorial",
            0.50,
            "detected 2×2 factorial design (two binary factor columns)",
        )
        bump(
            "coef_forest",
            0.35,
            "factorial design supports a coefficient-forest summary",
        )
    elif n_factors >= 2:
        bump(
            "factorial",
            0.40,
            f"{n_factors} categorical factor columns suggest a factorial design",
        )
        bump(
            "coef_forest",
            0.30,
            "multi-factor design supports a coefficient-forest summary",
        )

    # ── comparison (two-group) ────────────────────────────────────────
    if profile.n_groups == 2 and n_responses >= 1:
        bump(
            "comparison",
            0.55,
            "exactly 2 groups with a numeric response → two-group comparison",
        )
    elif profile.n_groups == 2 and n_responses == 0:
        bump(
            "comparison",
            0.20,
            "exactly 2 groups but no clear numeric response — confidence reduced",
        )

    # ── one-way ANOVA / multi-group comparison ────────────────────────
    if profile.n_groups >= 3 and n_responses >= 1 and not profile.detected_2x2:
        bump(
            "coef_forest",
            0.40,
            f"{profile.n_groups} groups with a numeric response → multi-group "
            "comparison; coef_forest summarises term-level effects",
        )
        bump(
            "comparison",
            0.25,
            f"{profile.n_groups} groups → side-by-side group comparison",
        )

    # ── correlation: ≥2 numeric, ≤1 factor column ─────────────────────
    if n_responses >= 2 and n_factors <= 1:
        bump(
            "correlation",
            0.55,
            f"{n_responses} numeric response columns + ≤1 factor → "
            "correlation analysis",
        )

    # ── paired / repeated_measures ────────────────────────────────────
    if (
        profile.has_paired_id
        and profile.grouping_structure
        in (GroupingStructure.paired, GroupingStructure.repeated_measures)
    ):
        bump(
            "comparison",
            0.30,
            f"paired-id column detected ({profile.grouping_structure.value}) → "
            "paired comparison family is appropriate",
        )
        if profile.grouping_structure == GroupingStructure.repeated_measures:
            bump(
                "timecourse_hierarchical_ci",
                0.50,
                "repeated measures (≥3 timepoints per subject) → "
                "hierarchical timecourse CI ribbon",
            )

    # ── time-series ───────────────────────────────────────────────────
    if profile.has_time_column and n_responses >= 1:
        bump(
            "timecourse_hierarchical_ci",
            0.40,
            "time column present with a numeric response → timecourse family",
        )

    # ── binary outcome → diagnostic curve ─────────────────────────────
    if profile.n_binary >= 1 and n_responses >= 1:
        bump(
            "diagnostic_curve",
            0.45,
            "binary outcome plus a numeric predictor → ROC / diagnostic-curve "
            "family",
        )

    # ── volcano / ridge for many numeric columns ──────────────────────
    if n_responses >= 5 and profile.n_groups >= 2:
        bump(
            "volcano",
            0.40,
            f"{n_responses} numeric responses across {profile.n_groups} groups → "
            "volcano plot for differential statistics",
        )
    if n_responses >= 2 and profile.n_groups >= 3:
        bump(
            "ridge_by_group",
            0.30,
            f"{n_responses} numeric responses across {profile.n_groups} groups "
            "→ ridge plot per group",
        )

    # ── high missingness → diagnostic boost ───────────────────────────
    if profile.fraction_missing > 0.20:
        bump(
            "diagnostic_curve",
            0.15,
            f"high missingness ({profile.fraction_missing:.0%}) — diagnostic "
            "family helps surface gaps",
        )

    # ── small-n → equivalence (TOST) preferred ────────────────────────
    if 0 < n_per_group_min < 10 and n_responses >= 1:
        bump(
            "equivalence",
            0.40,
            f"smallest group has only {n_per_group_min} observations → "
            "TOST / equivalence family preferred over null-hypothesis tests",
        )

    # ── safety net: tiny dataset → no strong recommendation ───────────
    if profile.n_rows < 4:
        for slot in candidates.values():
            slot["score"] *= 0.5
        bump(
            "comparison",
            0.05,
            f"only {profile.n_rows} rows — every recommendation is tentative",
        )

    # Build ranked list, clipping confidence to [0, 1].
    ranked: list[FamilyRecommendation] = []
    for family, slot in candidates.items():
        confidence = max(0.0, min(1.0, float(slot["score"])))
        if confidence < confidence_floor:
            continue
        matches = find_matching_recipes(family, profile)
        rationale = "; ".join(slot["reasons"]) or "(no specific rule fired)"
        ranked.append(
            FamilyRecommendation(
                family=family,
                confidence=confidence,
                rationale=rationale,
                n_matching_recipes=len(matches),
                matching_recipe_names=tuple(matches[:5]),
            )
        )

    ranked.sort(key=lambda r: (-r.confidence, r.family))
    return ranked[:top_k]


# ─────────────────────── recipe registry matching ────────────────────────


def find_matching_recipes(
    family: str,
    profile: DataProfile,
    *,
    max_results: int = 10,
) -> list[str]:
    """Return registry recipe full_names that match family + data shape.

    Match rules
    -----------
    1. ``RecipeMetadata.family`` (string-equal) must equal ``family`` —
       this also accepts the five author-recipe families (``comparison``,
       ``equivalence``, ``factorial``) which are not present in the
       registry's ``RecipeFamily`` enum but may live as recipe metadata
       once the user scaffolds them.
    2. ``StatisticalContract.min_n_per_group`` must be satisfied if the
       profile has groups (``profile.n_groups`` ≥ 1) and per-group counts.
    3. ``max_missingness_fraction`` (if set) must be ≥ profile's missing
       fraction — recipes that would refuse to render are filtered out.

    The returned list is sorted by ``full_name`` for deterministic output;
    callers can choose top-N.
    """
    try:
        from ..core.contract import ensure_all_imported, list_recipes
    except Exception:  # pragma: no cover — circular-import safety
        return []

    try:
        ensure_all_imported()
    except Exception:  # pragma: no cover — missing optional modality
        pass

    matches: list[str] = []
    for entry in list_recipes():
        meta = entry.metadata
        meta_family = (
            meta.family.value if hasattr(meta.family, "value") else str(meta.family)
        )
        if meta_family != family:
            continue

        # statistical contract gates
        contract = getattr(meta, "statistical_contract", None)
        if contract is not None:
            min_n = getattr(contract, "min_n_per_group", None)
            if min_n is not None and profile.n_per_group:
                smallest = min(profile.n_per_group.values())
                if smallest < min_n:
                    continue
            max_missing = getattr(contract, "max_missingness_fraction", None)
            if max_missing is not None and profile.fraction_missing > max_missing:
                continue

        matches.append(entry.full_name)

    matches.sort()
    return matches[:max_results]


# ────────────────────────── recipe gap detection ─────────────────────────


def detect_recipe_gaps(
    profile: DataProfile,
    recommendations: list[FamilyRecommendation],
    *,
    confidence_threshold: float = 0.50,
) -> list[RecipeGap]:
    """For each high-confidence family with no matching recipes, emit a gap.

    A gap is reported when:

    * ``recommendation.confidence >= confidence_threshold``, **and**
    * ``recommendation.n_matching_recipes == 0``.

    The suggested recipe name is built from the family + data-shape hint
    (e.g. ``comparison_paired_with_outliers_v1``). The suggested modality
    is ``custom_lab`` by default — the CLI overrides this if a project
    YAML is available. The research question is auto-generated to match
    the family.
    """
    gaps: list[RecipeGap] = []
    for rec in recommendations:
        if rec.n_matching_recipes > 0:
            continue
        if rec.confidence < confidence_threshold:
            continue
        shape_hint = _data_shape_hint(profile, rec.family)
        suggested_name = f"{rec.family}_{shape_hint}_v1"
        suggested_q = _suggest_research_question(profile, rec.family)
        summary = _profile_summary(profile)
        rationale = (
            f"family {rec.family!r} scored {rec.confidence:.2f} for this data "
            f"shape, but no registered recipe matches the constraints "
            f"(grouping={profile.grouping_structure.value}, "
            f"n_per_group_min="
            f"{min(profile.n_per_group.values()) if profile.n_per_group else 0}, "
            f"missing={profile.fraction_missing:.0%})"
        )
        gaps.append(
            RecipeGap(
                family=rec.family,
                data_profile_summary=summary,
                suggested_recipe_name=suggested_name,
                suggested_modality="custom_lab",
                suggested_research_question=suggested_q,
                rationale=rationale,
            )
        )
    return gaps


def _data_shape_hint(profile: DataProfile, family: str) -> str:
    """Build a short, snake_case hint describing the data shape."""
    parts: list[str] = []
    if profile.detected_2x2:
        parts.append("2x2")
    if profile.has_paired_id:
        parts.append("paired")
    if profile.has_time_column:
        parts.append("time")
    if profile.fraction_missing > 0.20:
        parts.append("with_missing")
    n_per_group_min = (
        min(profile.n_per_group.values()) if profile.n_per_group else 0
    )
    if 0 < n_per_group_min < 10:
        parts.append("small_n")
    if not parts:
        parts.append(profile.grouping_structure.value)
    # Family-specific tweak
    if family == "correlation" and len(profile.candidate_response_columns) >= 2:
        parts.append(
            f"{len(profile.candidate_response_columns)}_numeric"
        )
    return "_".join(parts)


def _suggest_research_question(profile: DataProfile, family: str) -> str:
    """Generate a default research question stub for the family + profile."""
    response = (
        profile.candidate_response_columns[0]
        if profile.candidate_response_columns
        else "the response"
    )
    factors = (
        ", ".join(profile.candidate_factor_columns[:2])
        if profile.candidate_factor_columns
        else "groups"
    )
    if family == "comparison":
        return (
            f"Does {response} differ between {factors}?"
        )
    if family == "factorial":
        return (
            f"How do {factors} jointly affect {response}, and is there an "
            "interaction?"
        )
    if family == "coef_forest":
        return (
            f"Which terms in a model of {response} have non-zero effects, "
            "and how large are they?"
        )
    if family == "correlation":
        if len(profile.candidate_response_columns) >= 2:
            x, y = profile.candidate_response_columns[:2]
            return f"How are {x} and {y} associated?"
        return f"How is {response} associated with another numeric measure?"
    if family == "equivalence":
        return (
            f"Are the {factors} groups practically equivalent in {response} "
            "(within a pre-specified margin)?"
        )
    if family == "timecourse_hierarchical_ci":
        return (
            f"How does {response} evolve over time, and how variable is it "
            "across subjects?"
        )
    if family == "diagnostic_curve":
        return (
            f"How well does {response} discriminate between the binary "
            "outcome classes?"
        )
    if family == "volcano":
        return (
            f"Which features show the largest and most reliable differences "
            f"between {factors}?"
        )
    if family == "ridge_by_group":
        return (
            f"How do the distributions of {response} compare across "
            f"{factors}?"
        )
    return f"What does the data tell us about {response} via the {family} lens?"


def _profile_summary(profile: DataProfile) -> str:
    """One-line human-readable summary of a data profile."""
    return (
        f"{profile.n_rows} rows × {profile.n_cols} cols, "
        f"{profile.n_numeric} numeric / {profile.n_categorical} categorical, "
        f"grouping={profile.grouping_structure.value}, "
        f"n_groups={profile.n_groups}, "
        f"missing={profile.fraction_missing:.0%}"
    )
