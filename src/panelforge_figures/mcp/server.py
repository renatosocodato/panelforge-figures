"""MCP server lifecycle for panelforge-figures — Elevation 1 (v2.1.0).

This module wires the panelforge-figures recipe registry, scorer,
cross-project index, provenance helpers, project surface, and (optionally)
telemetry into a Model Context Protocol server.  It is the *transport
layer* — every recipe / scorer / index tool is registered by Build-B's
companion ``tools`` module; this file owns lifecycle, configuration,
error handling, and the stdio adapter that the CLI command spawns.

Design rules (v2.1.0 spec §4)
-----------------------------

1. **Lazy import of the ``mcp`` SDK** — panelforge-figures must import
   cleanly for the 95%+ of users who never spawn an MCP server.  The
   SDK is only imported inside :func:`create_server` and
   :func:`serve_stdio`.  An ``ImportError`` is re-raised as the public
   :class:`MCPUnavailableError` with an actionable hint pointing to
   the ``[mcp]`` extra.

2. **No stdout writes.** The stdio transport multiplexes JSON-RPC
   frames over stdin/stdout; *any* stray ``print`` or ``sys.stdout``
   write corrupts the framing and breaks the client handshake.  All
   diagnostics go through :mod:`logging` (which writes to stderr by
   default).

3. **Telemetry is double-gated.** A consumer may set
   ``expose_telemetry=True`` in the config, but the runtime safety
   policy still has the final say — :func:`panelforge_figures.safety
   .is_telemetry_allowed` is consulted at server-construction time and
   the telemetry tools are silently dropped when it returns ``False``.

4. **Per-tool exceptions are recoverable.** Tool callbacks registered
   by Build-B should raise to signal failure; the MCP SDK converts
   exceptions into the correct JSON-RPC error envelopes.  This module
   never wraps tools in catch-alls that would mask real errors — it
   only guards the *transport setup* path.

Public API
~~~~~~~~~~

* :class:`MCPServerConfig` — frozen dataclass capturing which tool
  groups to expose and where to anchor project / telemetry scopes.
* :class:`MCPUnavailableError` — single failure mode for "SDK missing
  or transport setup failed".
* :func:`create_server` — assembles a configured ``mcp.server.Server``
  with the chosen tool groups registered.
* :func:`serve_stdio` — async entrypoint used by the CLI; opens the
  stdio adapter and runs until the client closes.
* :func:`serve_stdio_sync` — thin synchronous wrapper for the CLI
  ``figures mcp serve`` verb.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Imported only for type-checking; avoids the runtime cost of
    # loading the SDK when callers merely import this module.
    from mcp.server import Server


logger = logging.getLogger(__name__)


class MCPUnavailableError(RuntimeError):
    """Raised when the ``mcp`` SDK is not installed or transport setup fails.

    The error message is intentionally verbose because users hitting
    this typically did ``pip install panelforge-figures`` without the
    optional ``[mcp]`` extra; the hint redirects them to the correct
    install command rather than searching the docs.
    """


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for the panelforge-figures MCP server.

    Each ``expose_*`` flag controls a *tool group* registered by
    Build-B's ``tools`` module.  Defaults match the v2.1.0 spec:
    everything is exposed *except* telemetry, which is gated behind
    both this flag and the runtime safety policy (see
    :func:`create_server`).

    Attributes
    ----------
    server_name
        Identifier reported during the MCP handshake.  Clients use it
        to disambiguate when multiple servers are connected.
    server_version
        Reported alongside ``server_name``; should match the package
        version so clients can detect mismatches.
    expose_recipes
        Register one MCP tool per recipe contract (~448 tools).  Each
        tool's input schema is auto-generated from the recipe's
        Pydantic model.
    expose_scorer
        Register the ``score_panel`` / ``score_figure`` tools that
        wrap the scoring engine.
    expose_index
        Register cross-project index tools (search, list).
    expose_provenance
        Register provenance read tools (sidecar inspection, delta
        between two outputs).
    expose_telemetry
        Register telemetry tools.  Even when ``True``, the runtime
        :func:`panelforge_figures.safety.is_telemetry_allowed` check
        gates registration — clinical class always disables them.
    expose_projects
        Register project surface tools (list projects, switch active
        project, read project YAML).
    project_root
        Optional anchor for project / telemetry tools.  When ``None``
        the tools fall back to discovering the current project from
        ``cwd`` at call time.
    """

    server_name: str = "panelforge-figures"
    server_version: str = "2.1.0"
    expose_recipes: bool = True
    expose_scorer: bool = True
    expose_index: bool = True
    expose_provenance: bool = True
    expose_telemetry: bool = False
    expose_projects: bool = True
    project_root: Path | None = None


def _load_sdk() -> Any:
    """Import the ``mcp.server`` module on demand.

    Centralised so both :func:`create_server` and :func:`serve_stdio`
    surface the same friendly error.  Returns the imported
    ``Server`` class — callers cast to ``Any`` because the SDK is
    not a typed dependency at import time.
    """
    try:
        from mcp.server import Server  # type: ignore[import-not-found]
    except ImportError as exc:
        raise MCPUnavailableError(
            "mcp SDK not installed. "
            "Install with `pip install panelforge-figures[mcp]`."
        ) from exc
    return Server


def _load_stdio_adapter() -> Any:
    """Import the stdio transport adapter on demand."""
    try:
        from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
    except ImportError as exc:
        raise MCPUnavailableError(
            "mcp SDK not installed. "
            "Install with `pip install panelforge-figures[mcp]`."
        ) from exc
    return stdio_server


def create_server(config: MCPServerConfig | None = None) -> Server:
    """Build an MCP ``Server`` instance with all enabled tools registered.

    The function lazy-imports the ``mcp`` SDK and Build-B's
    ``tools`` module, so callers that merely ``import panelforge_figures
    .mcp`` pay no SDK cost.  Each tool group is opt-out via the
    corresponding ``expose_*`` flag on :class:`MCPServerConfig`;
    telemetry is *additionally* gated by the runtime safety policy.

    Parameters
    ----------
    config
        Server configuration.  Defaults to ``MCPServerConfig()``.

    Returns
    -------
    mcp.server.Server
        A server with the configured tool groups registered, ready
        to be passed to :func:`serve_stdio` or another transport
        adapter.

    Raises
    ------
    MCPUnavailableError
        If the ``mcp`` SDK cannot be imported.  The error message
        points at the ``[mcp]`` extra.
    """
    config = config or MCPServerConfig()
    server_cls = _load_sdk()

    # Late import — avoids a circular import (tools imports server's
    # config dataclass) and keeps the module import cheap for users
    # who never call create_server.
    from . import tools  # noqa: PLC0415 — intentional lazy import

    server = server_cls(config.server_name)
    logger.info(
        "creating MCP server %s v%s",
        config.server_name,
        config.server_version,
    )

    if config.expose_recipes:
        logger.debug("registering recipe tools")
        tools.register_recipe_tools(server, config)
    if config.expose_scorer:
        logger.debug("registering scorer tools")
        tools.register_scorer_tools(server, config)
    if config.expose_index:
        logger.debug("registering index tools")
        tools.register_index_tools(server, config)
    if config.expose_provenance:
        logger.debug("registering provenance tools")
        tools.register_provenance_tools(server, config)
    if config.expose_projects:
        logger.debug("registering project tools")
        tools.register_project_tools(server, config)

    if config.expose_telemetry:
        # Double gate: the config flag is the *intent*; the runtime
        # safety policy is the *authority*.  Clinical class forces
        # telemetry off regardless of the flag, so we silently drop
        # the registration rather than raising — refusing to start
        # the server would be a worse failure mode than running
        # without telemetry.
        from panelforge_figures.safety import is_telemetry_allowed  # noqa: PLC0415

        if is_telemetry_allowed():
            logger.debug("registering telemetry tools")
            tools.register_telemetry_tools(server, config)
        else:
            logger.info(
                "telemetry tools requested but disabled by safety policy; skipping"
            )

    return server


async def serve_stdio(config: MCPServerConfig | None = None) -> None:
    """Run the MCP server on the stdio transport.

    Blocks until the connected client closes its end of the pipe.
    All diagnostic output goes through :mod:`logging`; the stdio
    streams are reserved exclusively for MCP JSON-RPC frames.

    Parameters
    ----------
    config
        Server configuration; passed to :func:`create_server`.

    Raises
    ------
    MCPUnavailableError
        If the SDK or its stdio adapter cannot be imported.
    """
    stdio_server = _load_stdio_adapter()
    server = create_server(config)

    logger.info("starting MCP server on stdio transport")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
    logger.info("MCP server stdio session closed")


def serve_stdio_sync(config: MCPServerConfig | None = None) -> None:
    """Synchronous wrapper around :func:`serve_stdio` for the CLI verb.

    The CLI ``figures mcp serve`` command invokes this directly; using
    :func:`asyncio.run` here keeps the CLI free of async knowledge.
    """
    asyncio.run(serve_stdio(config))


__all__ = [
    "MCPServerConfig",
    "MCPUnavailableError",
    "create_server",
    "serve_stdio",
    "serve_stdio_sync",
]
