"""MCP tool registry for panelforge-figures — Elevation 1 (v2.1.0).

This module is the *content layer* of the MCP server.  Build-A's
:mod:`panelforge_figures.mcp.server` owns lifecycle and transport;
this module enumerates the tools exposed to the agent client and wires
each to the corresponding panelforge subsystem (recipe registry,
scorer, cross-project index, provenance helpers, project surface,
telemetry).

Design rules (v2.1.0 spec §4)
-----------------------------

1. **Lazy import of every off-package surface.** ``mcp.types``,
   :mod:`panelforge_figures.manifest.provenance`, :mod:`panelforge_figures
   .projects`, and :mod:`panelforge_figures.manifest.telemetry` are
   imported *inside* the registration / handler functions, never at
   module import.  panelforge-figures must remain importable when the
   ``mcp`` extra is missing (the server module raises a friendly
   :class:`MCPUnavailableError` later); modules that merely call
   ``register_*_tools`` to wire flags must not trip an SDK import.

2. **Errors never escape a handler.** Every tool callback returns a
   JSON-encoded ``TextContent`` of shape ``{"success": bool, ...}``.
   Letting an exception bubble up crashes the JSON-RPC framing of the
   stdio transport and disconnects the client — far worse than a
   structured error payload.

3. **JSONSchema is auto-generated.** Recipe tool ``inputSchema`` blocks
   come from the Pydantic ``RecipeContract`` subclass via
   ``model_json_schema()``.  Hand-rolled schemas would diverge from
   the contracts the moment a recipe author renames a field.

4. **Tool naming is dotted.** ``recipe.<modality>.<recipe_name>`` for
   recipes; ``scorer.score`` / ``scorer.explain``; ``index.list_recipes``
   / ``index.get_recipe``; ``provenance.build`` / ``provenance.verify``;
   ``projects.<verb>``; ``telemetry.status`` / ``telemetry.pick``.
   Build-A's ``server.py`` dispatches by prefix.

5. **Single-pass registration.** :func:`register_recipe_tools` registers
   the SDK's ``list_tools`` and ``call_tool`` decorators *once* and
   enumerates every tool group (recipes + scorer + index + provenance
   + projects + telemetry) inside that one pass.  The other
   ``register_*_tools`` entry-points exist as no-ops so Build-A's
   modular ``expose_*`` flags read symmetrically; they are wired in to
   keep ``server.py`` simple and to leave room for future split.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Stable in-package surfaces — safe to import at module load.  Anything
# touching the optional ``mcp`` SDK or off-module subsystems with their
# own import surface (telemetry, projects, provenance) is deferred.
from panelforge_figures.core.contract import (
    ensure_all_imported,
    get_recipe,
    list_recipes,
)
from panelforge_figures.manifest.scoring import (
    SCORING_RUBRIC_VERSION,
    WEIGHTS_HISTORY,
    ProjectProfile,
    score_recipes,
)

if TYPE_CHECKING:
    # Type-checking only — the server module's ``Server`` is opaque
    # at runtime; passing it through ``Any`` keeps ruff happy and
    # avoids importing the SDK from a TYPE_CHECKING block.
    from panelforge_figures.mcp.server import MCPServerConfig


logger = logging.getLogger(__name__)


# Default location for rendered figures when the config does not supply
# a ``project_root``.  Mirrors the on-disk layout used elsewhere in the
# package (``panelforge_workspace/figures/``).
_DEFAULT_FIGURES_SUBDIR: tuple[str, str] = ("panelforge_workspace", "figures")


# ───────────────────────── helpers ─────────────────────────────────────


def _pydantic_model_to_json_schema(model_cls: type) -> dict[str, Any]:
    """Convert a Pydantic v2 :class:`RecipeContract` subclass to a tool schema.

    Pydantic emits a JSONSchema-compatible dict — we forward it verbatim
    so client-side validation matches server-side validation byte-for-
    byte.  Wrapping or trimming the schema would cause subtle drift the
    moment a recipe author adds a field.
    """
    return model_cls.model_json_schema()


def _figures_out_dir(config: MCPServerConfig | None) -> Path:
    """Resolve the directory to write rendered figures into.

    Falls back to ``./panelforge_workspace/figures`` (relative to the
    process CWD) when ``config.project_root`` is ``None`` — mirrors
    Build-A's "discover the project at call time" contract for tools
    that do not pin a root.
    """
    if config is not None and config.project_root is not None:
        base = Path(config.project_root)
    else:
        base = Path.cwd()
    return base.joinpath(*_DEFAULT_FIGURES_SUBDIR)


def _stable_arg_hash(arguments: dict[str, Any]) -> str:
    """Deterministic short hash of an arguments dict for filenames.

    JSON-encoded with ``sort_keys=True`` to make the digest stable
    across Python dict-ordering quirks; truncated to 12 chars to keep
    filenames manageable while remaining collision-resistant for any
    realistic agent workload.
    """
    body = json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:12]


def _ok(payload: dict[str, Any]) -> list[Any]:
    """Wrap a ``dict`` payload as a single ``TextContent`` success envelope.

    Lazy-imports :mod:`mcp.types` because this module loads under
    callers that never enabled the ``[mcp]`` extra (e.g. ``ruff`` /
    pytest collection on a clean install).
    """
    from mcp.types import TextContent  # noqa: PLC0415 — lazy SDK import

    body = {"success": True, **payload}
    return [TextContent(type="text", text=json.dumps(body, default=str))]


def _err(message: str, *, extra: dict[str, Any] | None = None) -> list[Any]:
    """Wrap an error message as a single ``TextContent`` failure envelope.

    The handler-level catch-alls in this module funnel every exception
    through this helper so the JSON-RPC reply is always well-formed —
    a raw raise would crash the stdio framer and disconnect the agent.
    """
    from mcp.types import TextContent  # noqa: PLC0415 — lazy SDK import

    body: dict[str, Any] = {"success": False, "error": message}
    if extra:
        body.update(extra)
    return [TextContent(type="text", text=json.dumps(body, default=str))]


def _scored_to_dict(scored: Any) -> dict[str, Any]:
    """Serialize a :class:`ScoredRecipe` (frozen dataclass) as a JSON dict."""
    return {
        "full_name": scored.full_name,
        "modality": scored.modality,
        "name": scored.name,
        "family": scored.family,
        "answers_question": scored.answers_question,
        "score": scored.score,
        "tags": dict(scored.tags),
    }


def _recipe_info_to_index(info: Any) -> dict[str, Any]:
    """Render a single registry entry as a catalog row.

    Used by both ``index.list_recipes`` (bulk) and ``index.get_recipe``
    (single).  We keep the shape compact — the agent-facing
    ``recipes_index.json`` (built elsewhere in the package) is the
    authoritative catalog; this is a fast in-process view.
    """
    md = info.metadata
    return {
        "full_name": info.full_name,
        "name": md.name,
        "modality": md.modality,
        "family": md.family.value,
        "answers_question": md.answers_question,
        "required_fields": list(md.required_fields),
        "optional_fields": list(md.optional_fields),
        "file_format_hints": list(md.file_format_hints),
        "n_points_typical": md.n_points_typical,
        "alternatives_in_modality": list(md.alternatives_in_modality),
        "tool_name": f"recipe.{md.modality}.{md.name}",
        "dotted_path": info.dotted_path,
    }


def _tag_recipe_for_scorer(info: Any) -> dict[str, Any]:
    """Build the row shape :func:`score_recipes` consumes from a registry entry.

    The auto-tagger is the source of truth for the categorical tags the
    scorer reads (factorial / equivalence / anchor / dynamics /
    dimensionality).  Importing it lazily keeps the module import cost
    flat for callers that never invoke the scorer tools.
    """
    from panelforge_figures.manifest.auto_tag import auto_tag_recipe  # noqa: PLC0415

    md = info.metadata
    tags = auto_tag_recipe(
        name=md.name,
        modality=md.modality,
        family=md.family.value,
        answers_question=md.answers_question,
        required_fields=tuple(md.required_fields),
        optional_fields=tuple(md.optional_fields),
    )
    return {
        "modality": md.modality,
        "name": md.name,
        "family": md.family.value,
        "answers_question": md.answers_question,
        "tags": dict(tags),
    }


# ───────────────────────── exposure gating ─────────────────────────────


def _group_enabled(config: MCPServerConfig | None, group: str) -> bool:
    """Return whether tool ``group`` should be exposed for ``config``.

    The single source of truth for honoring the ``expose_*`` flags
    inside :func:`register_recipe_tools`'s ``list_tools`` union *and*
    its ``call_tool`` dispatcher.  Because ``register_recipe_tools`` is
    the one real registration pass (the other ``register_*_tools`` are
    no-ops), the per-group flags would otherwise never be consulted —
    a security-surface mismatch where ``expose_scorer=False`` still
    exposed ``scorer.score`` / ``scorer.explain``.

    ``config is None`` means "no config supplied" — we default to the
    permissive baseline (everything on) to preserve the historical
    behavior of callers that registered tools without a config, and to
    match :class:`MCPServerConfig`'s own ``expose_* = True`` defaults.
    Telemetry is *not* handled here: it carries an extra runtime safety
    gate and is resolved separately at its call sites.

    Pure (no SDK import), so it is unit-testable without the optional
    ``mcp`` extra installed.
    """
    if config is None:
        return True
    flag_attr = {
        "recipe": "expose_recipes",
        "scorer": "expose_scorer",
        "index": "expose_index",
        "provenance": "expose_provenance",
        "projects": "expose_projects",
    }.get(group)
    if flag_attr is None:
        # Unknown group — fail closed so an accidental new prefix is
        # not exposed without an explicit flag.
        return False
    return bool(getattr(config, flag_attr))


# ───────────────────────── tool list builders ──────────────────────────


def _scorer_tool_list() -> list[Any]:
    """Two scorer-facing tools: ``scorer.score`` + ``scorer.explain``."""
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    profile_schema: dict[str, Any] = {
        "type": "object",
        "description": "ProjectProfile snapshot fed into the scorer.",
        "properties": {
            "manuscript_anchor": {
                "type": "string",
                "description": "DISC1 | CDC42 | both | none",
            },
            "factorial_design": {"type": "boolean"},
            "equivalence_claims": {"type": "boolean"},
            "dynamics_needed": {
                "type": "string",
                "description": "static | kymograph | live | ordered_pseudotime | mixed",
            },
            "dimensionality": {
                "type": "string",
                "description": "2D | 3D | mixed",
            },
            "modalities_in_scope": {
                "type": "array",
                "items": {"type": "string"},
            },
            "hard_filters": {
                "type": "object",
                "additionalProperties": {"type": "boolean"},
            },
            "shortlist_size": {"type": "integer", "minimum": 1},
        },
        "required": [
            "manuscript_anchor",
            "factorial_design",
            "equivalence_claims",
            "dynamics_needed",
            "dimensionality",
            "modalities_in_scope",
        ],
    }

    score_input = {
        "type": "object",
        "properties": {
            "profile": profile_schema,
            "weights_version": {
                "type": "string",
                "description": "Entry from WEIGHTS_HISTORY; default = current",
            },
            "top_n": {
                "type": "integer",
                "minimum": 1,
                "description": "Maximum recipes to return (default 12)",
            },
        },
        "required": ["profile"],
    }
    explain_input = {
        "type": "object",
        "properties": {
            "profile": profile_schema,
            "full_name": {
                "type": "string",
                "description": "Recipe full_name '{modality}.{recipe}' to explain.",
            },
            "weights_version": {"type": "string"},
        },
        "required": ["profile", "full_name"],
    }

    return [
        Tool(
            name="scorer.score",
            description=(
                "Rank recipes against a ProjectProfile using the v"
                f"{SCORING_RUBRIC_VERSION} scoring rubric.  Returns the "
                "shortlisted top-N with score, modality, and tags."
            ),
            inputSchema=score_input,
        ),
        Tool(
            name="scorer.explain",
            description=(
                "Break a single recipe's score into per-tag contributions "
                "for a given ProjectProfile.  Helps agents debug why a "
                "recipe ranked where it did."
            ),
            inputSchema=explain_input,
        ),
    ]


def _index_tool_list() -> list[Any]:
    """Two catalog tools: ``index.list_recipes`` + ``index.get_recipe``."""
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    return [
        Tool(
            name="index.list_recipes",
            description=(
                "Return the panelforge-figures recipe catalog: every "
                "registered recipe's metadata + the MCP tool name to "
                "invoke for rendering."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="index.get_recipe",
            description=(
                "Return one recipe's metadata + Pydantic input schema "
                "for the supplied full_name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "{modality}.{recipe} dotted name",
                    },
                },
                "required": ["full_name"],
            },
        ),
    ]


def _provenance_tool_list() -> list[Any]:
    """Two provenance tools: ``provenance.build`` + ``provenance.verify``."""
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    build_input = {
        "type": "object",
        "properties": {
            "figure_path": {"type": "string"},
            "recipe_full_name": {"type": "string"},
            "recipe_module_path": {"type": "string"},
            "panelforge_version": {"type": "string"},
            "panelforge_git_commit": {"type": "string"},
            "data_files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "format": {"type": "string"},
                        "n_rows": {"type": "integer"},
                    },
                    "required": ["path"],
                },
            },
            "column_mapping": {"type": "object"},
            "scorer_state": {"type": "object"},
            "audit_findings": {"type": "object"},
            "write_sidecar": {
                "type": "boolean",
                "description": "Persist as <figure>.provenance.json (default true).",
            },
        },
        "required": [
            "figure_path",
            "recipe_full_name",
            "recipe_module_path",
            "panelforge_version",
            "panelforge_git_commit",
            "data_files",
        ],
    }
    verify_input = {
        "type": "object",
        "properties": {
            "provenance_path": {"type": "string"},
        },
        "required": ["provenance_path"],
    }

    return [
        Tool(
            name="provenance.build",
            description=(
                "Compute a content-addressed ProvenanceRecord for a "
                "rendered figure (sha256 of figure + data + recipe "
                "module).  Optionally persists the sidecar JSON."
            ),
            inputSchema=build_input,
        ),
        Tool(
            name="provenance.verify",
            description=(
                "Recompute every hash in a provenance.json sidecar and "
                "report drift by dimension (figure / data / recipe)."
            ),
            inputSchema=verify_input,
        ),
    ]


def _project_tool_list() -> list[Any]:
    """Six project-surface tools mirroring ``figures projects ...`` CLI verbs."""
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    return [
        Tool(
            name="projects.list",
            description=(
                "List every panelforge project registered for this user "
                "(per-user YAML at $XDG_CONFIG_HOME/panelforge/projects.yaml)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="projects.register",
            description=(
                "Register a project path + id (idempotent; refreshes "
                "last-used / status fields when re-registering)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "project_id": {"type": "string"},
                    "active_profile": {"type": "string", "default": ""},
                    "n_recipes": {"type": "integer", "default": 0},
                    "status": {"type": "string", "default": "n/a"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "set_default": {"type": "boolean", "default": False},
                },
                "required": ["path", "project_id"],
            },
        ),
        Tool(
            name="projects.switch",
            description=(
                "Set the registry default to ``project_id`` and refresh "
                "its last-used timestamp."
            ),
            inputSchema={
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        ),
        Tool(
            name="projects.current",
            description=(
                "Return the registry's default project id (or null if "
                "no projects are registered)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="projects.diff",
            description=(
                "Compute the recipe-overlap diff between two registered "
                "projects' manifests (a_only / b_only / shared)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "a_id": {"type": "string"},
                    "b_id": {"type": "string"},
                },
                "required": ["a_id", "b_id"],
            },
        ),
        Tool(
            name="projects.portfolio",
            description=(
                "Aggregate the recipe-usage view across every registered "
                "project (forward map + inverted index + top-N recipes)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "minimum": 1, "default": 10},
                },
            },
        ),
    ]


def _telemetry_tool_list() -> list[Any]:
    """Two telemetry tools: ``telemetry.status`` + ``telemetry.pick``."""
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    return [
        Tool(
            name="telemetry.status",
            description=(
                "Return the active telemetry posture: data_class gate, "
                "project opt-in flag, and log path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                },
            },
        ),
        Tool(
            name="telemetry.pick",
            description=(
                "Record the user's recipe pick into ``usage.jsonl`` "
                "(updates the row in place; appends rejected_higher_scored)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "full_name": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                "required": ["full_name"],
            },
        ),
    ]


# ───────────────────────── handlers ────────────────────────────────────


async def _handle_recipe_call(
    name: str,
    arguments: dict[str, Any],
    config: MCPServerConfig | None,
) -> list[Any]:
    """Dispatch a ``recipe.*`` tool call: render the figure to PNG.

    The tool name carries the full recipe identity
    (``recipe.<modality>.<recipe_name>``); we strip the prefix and look
    the recipe up in the registry rather than scanning the supplied
    list — that keeps the lookup O(1) and survives recipe registry
    updates between server start and tool invocation.
    """
    # Configure matplotlib for headless rendering once per call.  The
    # ``force=False`` form is a no-op when an Agg backend is already
    # active (e.g. inside the test runner), avoiding spurious warnings.
    import matplotlib  # noqa: PLC0415 — lazy import; large dep
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt  # noqa: PLC0415

    full_name = name[len("recipe.") :]
    try:
        info = get_recipe(full_name)
    except KeyError:
        return _err(f"unknown recipe: {full_name}")

    # Instantiate the contract — Pydantic raises ValidationError on
    # type / shape mismatch; we surface the message but never re-raise.
    try:
        contract = info.contract(**arguments)
    except Exception as exc:  # pydantic.ValidationError or TypeError
        return _err(f"contract validation failed: {exc}")

    out_dir = _figures_out_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = _stable_arg_hash(arguments)
    out_path = out_dir / f"{info.metadata.modality}.{info.metadata.name}.{digest}.png"

    fig = None
    try:
        fig, ax = plt.subplots()
        info.render(contract, ax=ax)
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
    except Exception as exc:
        return _err(f"render failed: {exc}", extra={"recipe": full_name})
    finally:
        # Always close the figure to free memory — matplotlib leaks
        # large array buffers per-figure that the GC alone won't reap
        # promptly inside an MCP server's long-running event loop.
        if fig is not None:
            plt.close(fig)

    return _ok(
        {
            "figure_path": str(out_path),
            "recipe": full_name,
            "args_digest": digest,
        }
    )


async def _handle_scorer_call(
    name: str,
    arguments: dict[str, Any],
) -> list[Any]:
    """Dispatch ``scorer.score`` / ``scorer.explain``.

    Both operate on the in-process recipe registry (after
    ``ensure_all_imported``), augmented with the auto-tagger's
    categorical tags so the scorer's hard filters / soft weights have
    something to read.
    """
    try:
        profile_kwargs = dict(arguments.get("profile") or {})
        weights_version = arguments.get("weights_version", SCORING_RUBRIC_VERSION)
        if weights_version not in WEIGHTS_HISTORY:
            return _err(
                f"unknown weights_version: {weights_version!r}; "
                f"available: {sorted(WEIGHTS_HISTORY)}"
            )

        # Coerce the loose-typed arguments into the frozen dataclass —
        # tuple/dict/list shapes get tightened; missing fields raise
        # TypeError which we catch below.
        modalities = tuple(profile_kwargs.pop("modalities_in_scope", ()))
        hard_filters = dict(profile_kwargs.pop("hard_filters", {}) or {})
        profile = ProjectProfile(
            modalities_in_scope=modalities,
            hard_filters=hard_filters,
            **profile_kwargs,
        )
    except (TypeError, ValueError) as exc:
        return _err(f"profile parse failed: {exc}")

    ensure_all_imported()
    tagged = [_tag_recipe_for_scorer(info) for info in list_recipes()]

    if name == "scorer.score":
        try:
            scored = score_recipes(
                profile,
                tagged,
                weights_version=weights_version,
            )
        except Exception as exc:
            return _err(f"score_recipes failed: {exc}")
        top_n = int(arguments.get("top_n") or profile.shortlist_size)
        rows = [_scored_to_dict(s) for s in scored[:top_n]]
        return _ok(
            {
                "weights_version": weights_version,
                "top_n": top_n,
                "results": rows,
            }
        )

    if name == "scorer.explain":
        full_name = arguments.get("full_name", "")
        # Find the row for this recipe in the tagged list (the scorer's
        # input shape) so the per-tag contribution breakdown matches
        # what scorer.score sees.
        target = next((r for r in tagged if f"{r['modality']}.{r['name']}" == full_name), None)
        if target is None:
            return _err(f"unknown recipe: {full_name}")

        from panelforge_figures.manifest.scoring import (  # noqa: PLC0415 — lazy
            match_anchor,
            match_bool,
            match_dim,
            match_dynamics,
        )

        weights = WEIGHTS_HISTORY[weights_version]
        tags = target["tags"] or {}
        contributions: dict[str, dict[str, float]] = {
            "factorial": {
                "weight": float(weights["factorial"]),
                "match": float(match_bool(tags.get("factorial"), profile.factorial_design)),
            },
            "equivalence": {
                "weight": float(weights["equivalence"]),
                "match": float(
                    match_bool(tags.get("equivalence"), profile.equivalence_claims)
                ),
            },
            "anchor": {
                "weight": float(weights["anchor"]),
                "match": float(match_anchor(tags.get("anchor"), profile.manuscript_anchor)),
            },
            "dynamics": {
                "weight": float(weights["dynamics"]),
                "match": float(match_dynamics(tags.get("dynamics"), profile.dynamics_needed)),
            },
            "dimensionality": {
                "weight": float(weights["dimensionality"]),
                "match": float(match_dim(tags.get("dimensionality"), profile.dimensionality)),
            },
        }
        for k, v in contributions.items():
            v["score"] = round(v["weight"] * v["match"], 4)
        total = round(sum(v["score"] for v in contributions.values()), 4)
        return _ok(
            {
                "full_name": full_name,
                "weights_version": weights_version,
                "tags": dict(tags),
                "contributions": contributions,
                "score": total,
            }
        )

    return _err(f"unknown scorer tool: {name}")


async def _handle_index_call(name: str, arguments: dict[str, Any]) -> list[Any]:
    """Dispatch ``index.list_recipes`` / ``index.get_recipe``."""
    ensure_all_imported()
    if name == "index.list_recipes":
        rows = [_recipe_info_to_index(info) for info in list_recipes()]
        return _ok({"n_recipes": len(rows), "recipes": rows})

    if name == "index.get_recipe":
        full_name = arguments.get("full_name", "")
        try:
            info = get_recipe(full_name)
        except KeyError:
            return _err(f"unknown recipe: {full_name}")
        record = _recipe_info_to_index(info)
        record["input_schema"] = _pydantic_model_to_json_schema(info.contract)
        return _ok({"recipe": record})

    return _err(f"unknown index tool: {name}")


async def _handle_provenance_call(name: str, arguments: dict[str, Any]) -> list[Any]:
    """Dispatch ``provenance.build`` / ``provenance.verify`` (lazy import)."""
    from panelforge_figures.manifest.provenance import (  # noqa: PLC0415 — lazy
        build_provenance,
        verify_provenance,
        write_provenance_json,
    )

    if name == "provenance.build":
        try:
            record = build_provenance(
                figure_path=Path(arguments["figure_path"]),
                recipe_full_name=str(arguments["recipe_full_name"]),
                recipe_module_path=Path(arguments["recipe_module_path"]),
                panelforge_version=str(arguments["panelforge_version"]),
                panelforge_git_commit=str(arguments["panelforge_git_commit"]),
                data_files=list(arguments["data_files"]),
                column_mapping=dict(arguments.get("column_mapping") or {}),
                scorer_state=arguments.get("scorer_state"),
                audit_findings=arguments.get("audit_findings"),
            )
        except (KeyError, TypeError, FileNotFoundError, OSError) as exc:
            return _err(f"build_provenance failed: {exc}")

        sidecar_path: str | None = None
        if arguments.get("write_sidecar", True):
            try:
                sidecar_path = str(write_provenance_json(record))
            except OSError as exc:
                return _err(f"write_provenance_json failed: {exc}")

        return _ok(
            {
                "schema_version": record.schema_version,
                "figure_path": record.figure_path,
                "figure_sha256": record.figure_sha256,
                "rendered_at": record.rendered_at,
                "recipe": record.recipe,
                "data": record.data,
                "scorer": record.scorer,
                "audit": record.audit,
                "rendering_environment": record.rendering_environment,
                "sidecar_path": sidecar_path,
            }
        )

    if name == "provenance.verify":
        try:
            result = verify_provenance(Path(arguments["provenance_path"]))
        except (KeyError, FileNotFoundError, OSError) as exc:
            return _err(f"verify_provenance failed: {exc}")
        return _ok(
            {
                "figure_path": str(result.figure_path),
                "overall": result.overall,
                "findings": list(result.findings),
            }
        )

    return _err(f"unknown provenance tool: {name}")


async def _handle_project_call(
    name: str,
    arguments: dict[str, Any],
    config: MCPServerConfig | None,
) -> list[Any]:
    """Dispatch ``projects.*`` (lazy-imports the projects subpackage)."""
    from panelforge_figures.projects import (  # noqa: PLC0415 — lazy
        ProjectIdCollision,
        ProjectPathMissing,
        load_registry,
        register_if_absent,
        switch_default,
    )
    from panelforge_figures.projects.portfolio import (  # noqa: PLC0415 — lazy
        aggregate_portfolio,
        diff_projects,
        top_n_recipes,
    )

    config_path = (
        Path(config.project_root) / ".panelforge_projects.yaml"
        if config is not None and config.project_root is not None
        else None
    )
    # The registry's "real" path is XDG_CONFIG_HOME by default; only
    # use the per-config override when the caller actually supplied
    # one — stay conservative and let the package default win otherwise.
    config_path = None if config_path is None or not config_path.exists() else config_path

    try:
        if name == "projects.list":
            registry = load_registry(config_path)
            entries = []
            for pid, e in registry.projects.items():
                entries.append(
                    {
                        "id": pid,
                        "path": str(e.path),
                        "last_used": e.last_used.isoformat(),
                        "active_profile": e.active_profile,
                        "n_recipes_picked": e.n_recipes_picked,
                        "last_render_status": e.last_render_status,
                        "tags": list(e.tags),
                        "is_default": pid == registry.default_project,
                    }
                )
            return _ok(
                {
                    "default_project": registry.default_project,
                    "n_projects": len(entries),
                    "projects": entries,
                }
            )

        if name == "projects.register":
            try:
                entry = register_if_absent(
                    Path(arguments["path"]),
                    project_id=str(arguments["project_id"]),
                    profile=str(arguments.get("active_profile", "") or ""),
                    n_recipes=int(arguments.get("n_recipes", 0) or 0),
                    status=str(arguments.get("status", "n/a") or "n/a"),
                    tags=tuple(arguments.get("tags") or ()),
                    config_path=config_path,
                    set_default=bool(arguments.get("set_default", False)),
                )
            except (ProjectIdCollision, ProjectPathMissing) as exc:
                return _err(str(exc))
            return _ok(
                {
                    "id": entry.id,
                    "path": str(entry.path),
                    "last_used": entry.last_used.isoformat(),
                    "active_profile": entry.active_profile,
                    "n_recipes_picked": entry.n_recipes_picked,
                    "last_render_status": entry.last_render_status,
                    "tags": list(entry.tags),
                }
            )

        if name == "projects.switch":
            try:
                entry = switch_default(
                    str(arguments["project_id"]),
                    config_path=config_path,
                )
            except (KeyError, ProjectPathMissing) as exc:
                return _err(str(exc))
            return _ok(
                {
                    "id": entry.id,
                    "path": str(entry.path),
                    "active_profile": entry.active_profile,
                }
            )

        if name == "projects.current":
            registry = load_registry(config_path)
            return _ok({"default_project": registry.default_project})

        if name == "projects.diff":
            registry = load_registry(config_path)
            try:
                report = diff_projects(
                    registry,
                    str(arguments["a_id"]),
                    str(arguments["b_id"]),
                )
            except KeyError as exc:
                return _err(f"unknown project id: {exc}")
            return _ok(
                {
                    "project_a_id": report.project_a_id,
                    "project_b_id": report.project_b_id,
                    "a_only": list(report.a_only),
                    "b_only": list(report.b_only),
                    "shared": list(report.shared),
                    "suggestion": report.suggestion,
                }
            )

        if name == "projects.portfolio":
            registry = load_registry(config_path)
            summary = aggregate_portfolio(registry)
            top = top_n_recipes(summary, n=int(arguments.get("top_n", 10) or 10))
            return _ok(
                {
                    "n_projects": summary.n_projects,
                    "n_distinct_recipes": summary.n_distinct_recipes,
                    "project_ids": list(summary.project_ids),
                    "recipes_by_project": {
                        pid: sorted(recipes)
                        for pid, recipes in summary.recipes_by_project.items()
                    },
                    "recipe_to_projects": {
                        recipe: sorted(pids)
                        for recipe, pids in summary.recipe_to_projects.items()
                    },
                    "top": [
                        {
                            "recipe_full_name": row.recipe_full_name,
                            "project_count": row.project_count,
                            "project_ids": list(row.project_ids),
                        }
                        for row in top
                    ],
                }
            )
    except Exception as exc:  # noqa: BLE001 — final safety net
        return _err(f"{name} failed: {exc}")

    return _err(f"unknown project tool: {name}")


async def _handle_telemetry_call(
    name: str,
    arguments: dict[str, Any],
    config: MCPServerConfig | None,
) -> list[Any]:
    """Dispatch ``telemetry.status`` / ``telemetry.pick`` (double-gated)."""
    # Double-gate: ``register_telemetry_tools`` already checked the
    # safety policy at server-start; we re-check here so a runtime
    # data_class change (e.g. CLI flips to clinical mid-session) does
    # not silently expose a previously-allowed surface.
    from panelforge_figures.safety import is_telemetry_allowed  # noqa: PLC0415

    if not is_telemetry_allowed():
        return _err(
            "telemetry disabled by data_class policy",
            extra={"reason": "policy_gate"},
        )

    from panelforge_figures.manifest.telemetry import (  # noqa: PLC0415 — lazy
        TelemetryError,
        is_telemetry_enabled,
        set_user_pick,
        telemetry_log_path,
    )

    project_root = (
        Path(arguments.get("project_root"))
        if arguments.get("project_root")
        else (Path(config.project_root) if config and config.project_root else Path.cwd())
    )

    if name == "telemetry.status":
        log_path = telemetry_log_path(project_root)
        return _ok(
            {
                "data_class_allows_telemetry": True,
                "project_opt_in": is_telemetry_enabled(project_root),
                "project_root": str(project_root),
                "log_path": str(log_path),
                "log_exists": log_path.is_file(),
            }
        )

    if name == "telemetry.pick":
        try:
            row = set_user_pick(
                project_root,
                str(arguments["full_name"]),
                session_id=arguments.get("session_id") or None,
            )
        except TelemetryError as exc:
            return _err(str(exc))
        except KeyError as exc:
            return _err(f"missing argument: {exc}")
        return _ok(
            {
                "session_id": row.session_id,
                "timestamp": row.timestamp,
                "user_picked": row.user_picked,
                "rejected_higher_scored": list(row.rejected_higher_scored),
            }
        )

    return _err(f"unknown telemetry tool: {name}")


# ───────────────────────── public registration ─────────────────────────


def register_recipe_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """Register the SDK's ``list_tools`` + ``call_tool`` decorators.

    This is the *single* registration entry point — the other
    ``register_*_tools`` functions are no-ops kept for symmetry with
    Build-A's modular ``expose_*`` config flags.  Doing it in one pass
    means the ``list_tools`` handler returns the union of every group
    in deterministic order and ``call_tool`` dispatches on tool-name
    prefix without per-group re-wiring.

    Per Build-A's contract the ``server`` object exposes
    ``list_tools()`` and ``call_tool()`` as decorator factories — we
    apply each once and store the resulting handlers on the closure
    for ``call_tool`` to find via the recipe / scorer / index /
    provenance / projects / telemetry prefix.
    """
    from mcp.types import Tool  # noqa: PLC0415 — lazy SDK import

    ensure_all_imported()
    recipes = list_recipes()

    # Snapshot the recipe metadata + lazy module docstring lookup so
    # we don't pay the import cost on every list_tools roundtrip.
    recipe_tools: list[Tool] = []
    for info in recipes:
        md = info.metadata
        tool_name = f"recipe.{md.modality}.{md.name}"
        # Module docstring is a richer narrative than ``answers_question``
        # alone — but we keep ``answers_question`` first because that's
        # the agent-facing summary line.
        try:
            mod = __import__(info.render.__module__, fromlist=["__doc__"])
            mod_doc = (mod.__doc__ or "").strip()
        except Exception:  # noqa: BLE001 — module import failure is non-fatal here
            mod_doc = ""
        description = (
            f"{md.answers_question}\n\n"
            f"Family: {md.family.value}.  Modality: {md.modality}."
        )
        if mod_doc:
            description = f"{description}\n\n{mod_doc}"

        recipe_tools.append(
            Tool(
                name=tool_name,
                description=description,
                inputSchema=_pydantic_model_to_json_schema(info.contract),
            )
        )

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        # Build the union freshly each call so a future hot-reload of
        # any tool group is visible without a server restart.  The
        # recipe list is captured in the closure (~448 entries; cheap
        # to enumerate) but the helper-tool lists are rebuilt because
        # they're a few entries each and they capture small SDK-typed
        # objects we'd rather not stash globally.
        # Each non-telemetry group is gated by its ``expose_*`` flag —
        # skipping a group's *tools* here keeps its surface off the
        # listing (its dispatch branch in ``_call_tool`` is gated the
        # same way, so a stale call returns a structured error).
        out: list[Tool] = list(recipe_tools)
        if _group_enabled(config, "scorer"):
            out.extend(_scorer_tool_list())
        if _group_enabled(config, "index"):
            out.extend(_index_tool_list())
        if _group_enabled(config, "provenance"):
            out.extend(_provenance_tool_list())
        if _group_enabled(config, "projects"):
            out.extend(_project_tool_list())

        # Telemetry tools are conditionally exposed: the server config
        # plus the runtime safety policy together decide visibility.
        # Even when ``expose_telemetry=False`` we keep the dispatch
        # branch alive (so a tool *call* with a stale name returns a
        # structured error rather than crashing the dispatcher).
        if config is not None and config.expose_telemetry:
            from panelforge_figures.safety import is_telemetry_allowed  # noqa: PLC0415
            if is_telemetry_allowed():
                out.extend(_telemetry_tool_list())
        return out

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        # Outermost catch-all: under no circumstance should an
        # exception escape this handler — the stdio JSON-RPC framer
        # would reject a non-conforming reply and disconnect the
        # client.  Returning a structured error envelope keeps the
        # session healthy and gives the agent something to act on.
        try:
            args = dict(arguments or {})
            # Dispatch is gated by the same ``expose_*`` flags that gate
            # the listing: a call into a disabled group returns a
            # structured "not exposed" error rather than silently
            # executing — closing the security-surface mismatch where a
            # client could invoke ``scorer.score`` despite
            # ``expose_scorer=False``.
            if name.startswith("recipe."):
                if not _group_enabled(config, "recipe"):
                    return _err(f"tool group disabled: {name}")
                return await _handle_recipe_call(name, args, config)
            if name.startswith("scorer."):
                if not _group_enabled(config, "scorer"):
                    return _err(f"tool group disabled: {name}")
                return await _handle_scorer_call(name, args)
            if name.startswith("index."):
                if not _group_enabled(config, "index"):
                    return _err(f"tool group disabled: {name}")
                return await _handle_index_call(name, args)
            if name.startswith("provenance."):
                if not _group_enabled(config, "provenance"):
                    return _err(f"tool group disabled: {name}")
                return await _handle_provenance_call(name, args)
            if name.startswith("projects."):
                if not _group_enabled(config, "projects"):
                    return _err(f"tool group disabled: {name}")
                return await _handle_project_call(name, args, config)
            if name.startswith("telemetry."):
                return await _handle_telemetry_call(name, args, config)
            return _err(f"unknown tool: {name}")
        except Exception as exc:  # noqa: BLE001 — final transport-level guard
            logger.exception("unhandled error in tool %s", name)
            return _err(f"unhandled error: {exc}", extra={"tool": name})


def register_scorer_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """No-op — scorer tools register inside :func:`register_recipe_tools`.

    Build-A's ``expose_scorer`` flag still gates this entry point so
    the ``server.py`` flow reads symmetrically; the actual list_tools
    union and call_tool dispatcher are registered exactly once by
    :func:`register_recipe_tools` to avoid SDK double-registration.
    """
    return None


def register_index_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """No-op — index tools register inside :func:`register_recipe_tools`."""
    return None


def register_provenance_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """No-op — provenance tools register inside :func:`register_recipe_tools`."""
    return None


def register_project_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """No-op — project tools register inside :func:`register_recipe_tools`."""
    return None


def register_telemetry_tools(server: Any, config: MCPServerConfig | None = None) -> None:
    """No-op — telemetry tools register inside :func:`register_recipe_tools`.

    The safety-policy gate runs there too, so server.py's
    ``is_telemetry_allowed`` check is the *intent* signal and the
    in-handler re-check is the *authority*.  This split mirrors the
    safety-mode design in :mod:`panelforge_figures.safety`.
    """
    return None


__all__ = [
    "register_index_tools",
    "register_project_tools",
    "register_provenance_tools",
    "register_recipe_tools",
    "register_scorer_tools",
    "register_telemetry_tools",
]
