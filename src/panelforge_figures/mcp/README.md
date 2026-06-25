# `panelforge_figures.mcp` — package map

`mcp/` exposes panelforge-figures over the **Model Context Protocol** so an agent
client (e.g. Claude) can call the recipe registry, scorer, cross-project index,
provenance helpers, and project surface as tools. It is a thin transport/content
layer on top of `core/`, `manifest/`, `projects/`, and `safety/`; it registers no
recipes of its own.

The `mcp` SDK is an **optional** dependency. The package imports cleanly without
it — the SDK is lazy-imported only when a server is actually constructed, and an
`ImportError` surfaces as `MCPUnavailableError` pointing users at the `[mcp]`
extra (`pip install panelforge-figures[mcp]`).

For the design rationale, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.9,
§4.6.

---

## Two modules: transport vs content

| Module | Layer | Role |
|---|---|---|
| `server.py` | transport | Lifecycle, configuration, error handling, the stdio adapter. |
| `tools.py` | content | Enumerates the tools and wires each to its panelforge subsystem. |

`__init__.py` re-exports the public surface: `MCPServerConfig`,
`MCPUnavailableError`, `create_server`, `serve_stdio` (and `serve_stdio_sync`).

### `server.py`

- `MCPServerConfig` — frozen dataclass of `expose_*` flags (recipes, scorer,
  index, provenance, projects, telemetry) plus `server_name`/`server_version`/
  `project_root`.
- `create_server(config)` — lazy-imports the SDK and `tools`, then registers the
  enabled tool groups.
- `serve_stdio()` / `serve_stdio_sync()` — async + sync entrypoints; the CLI
  `figures mcp serve` verb calls the sync wrapper.

### `tools.py`

`register_recipe_tools` / `register_scorer_tools` / `register_index_tools` /
`register_provenance_tools` / `register_project_tools` / `register_telemetry_tools`.
Each off-package surface (`mcp.types`, `manifest.provenance`, `projects`,
`manifest.telemetry`) is imported *inside* these functions, never at module load.

---

## Design rules (v2.1.0 spec §4)

1. **No stdout writes.** The stdio transport multiplexes JSON-RPC frames over
   stdin/stdout; any stray `print` corrupts the framing. All diagnostics go
   through `logging` (stderr).
2. **Errors never escape a handler.** Every tool callback returns a JSON
   `{"success": bool, ...}` envelope — an uncaught exception would crash the
   JSON-RPC framing and disconnect the client.
3. **Auto-generated schemas.** A recipe tool's `inputSchema` comes from its
   pydantic `RecipeContract` via `model_json_schema()`, so client and server
   validation never drift.
4. **Dotted tool names.** `recipe.<modality>.<recipe>`, `scorer.*`, `index.*`,
   `provenance.*`, `projects.*`, `telemetry.*`; `server.py` dispatches by prefix.
5. **Telemetry is double-gated.** Even with `expose_telemetry=True`,
   `safety.is_telemetry_allowed()` is consulted at construction time and the
   telemetry tools are silently dropped when it returns `False` (clinical class
   always disables them).

---

## Known gap (see §3.9, §7)

Today only `register_recipe_tools` actually wires the SDK's `list_tools` /
`call_tool` decorators; the scorer/index/provenance/project tools are added
unconditionally and the matching `expose_*` flags do **not** gate registration.
Treat those flags as aspirational until the gap is closed.
