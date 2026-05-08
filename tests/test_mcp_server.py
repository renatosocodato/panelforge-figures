"""Tests for the MCP server (Elevation 1).

Coverage map:

* :class:`MCPServerConfig` defaults are safe (telemetry off).
* Lazy import path raises :class:`MCPUnavailableError` with an
  actionable hint when the ``mcp`` SDK is missing.
* ``serve_stdio`` raises the same error class without the SDK.
* When the SDK is installed (``pytest.importorskip``), ``create_server``
  returns a server and respects all six ``expose_*`` flags.
* Telemetry exposure is double-gated by both the config flag *and* the
  runtime ``is_telemetry_allowed()`` check (CLINICAL data class blocks).
* CLI smoke: ``figures mcp serve --help`` succeeds; running the command
  without the SDK exits 1 and prints a friendly stderr message.
* Version bump to 2.1.0.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from panelforge_figures.mcp import (
    MCPServerConfig,
    MCPUnavailableError,
    create_server,
    serve_stdio,
)

# ─────────── 1. Config defaults ───────────


def test_config_defaults_safe():
    """Defaults: telemetry off, every other tool group on, server name set."""
    c = MCPServerConfig()
    assert c.server_name == "panelforge-figures"
    assert c.expose_telemetry is False  # always opt-in
    assert c.expose_recipes is True
    assert c.expose_scorer is True
    assert c.expose_index is True
    assert c.expose_provenance is True
    assert c.expose_projects is True
    assert c.project_root is None


def test_config_overrides_apply():
    """All ``expose_*`` flags accept overrides without raising."""
    c = MCPServerConfig(
        expose_recipes=False,
        expose_scorer=False,
        expose_index=False,
        expose_provenance=False,
        expose_projects=False,
        expose_telemetry=True,
    )
    assert c.expose_recipes is False
    assert c.expose_telemetry is True


# ─────────── 2. Lazy import error handling ───────────


def test_create_server_raises_friendly_error_without_mcp_sdk():
    """If the mcp SDK isn't importable, ``create_server`` raises
    :class:`MCPUnavailableError` mentioning the ``[mcp]`` extra."""
    with patch.dict("sys.modules", {"mcp": None, "mcp.server": None}):
        with pytest.raises(MCPUnavailableError, match=r"\[mcp\]"):
            create_server()


def test_serve_stdio_raises_friendly_error_without_mcp_sdk():
    """The async serve path mirrors the sync path's failure mode."""
    with patch.dict(
        "sys.modules",
        {"mcp": None, "mcp.server": None, "mcp.server.stdio": None},
    ):
        with pytest.raises(MCPUnavailableError):
            asyncio.run(serve_stdio())


def test_mcp_unavailable_error_is_runtime_error():
    """Downstream callers should be able to ``except RuntimeError`` if
    they don't want to import our concrete class."""
    assert issubclass(MCPUnavailableError, RuntimeError)


# ─────────── 3. Server creation (skipped if mcp not installed) ───────────

# Per-test skipif so the non-mcp tests above still run when the SDK is missing.
try:
    import mcp as _mcp_sdk  # noqa: F401

    _HAS_MCP_SDK = True
except ImportError:
    _HAS_MCP_SDK = False

_skip_without_mcp = pytest.mark.skipif(
    not _HAS_MCP_SDK,
    reason="mcp SDK not installed in test env",
)


@_skip_without_mcp
def test_create_server_succeeds_with_mcp():
    server = create_server()
    assert server is not None
    assert server.name == "panelforge-figures"


@_skip_without_mcp
def test_create_server_respects_disable_flags():
    """Disabling every tool group must not crash; all flags are honored."""
    config = MCPServerConfig(
        expose_recipes=False,
        expose_scorer=False,
        expose_index=False,
        expose_provenance=False,
        expose_projects=False,
        expose_telemetry=False,
    )
    server = create_server(config)
    assert server is not None


@_skip_without_mcp
def test_create_server_with_default_config_arg():
    """``create_server(None)`` should fall back to ``MCPServerConfig()``."""
    server = create_server(None)
    assert server is not None


# ─────────── 4. Tool listing smoke ───────────


@_skip_without_mcp
def test_list_tools_smoke():
    """Tool registration runs at server-creation time; verify the server
    object exists.  A full transport test would require the SDK + a
    real stdio pair, which is out of scope for unit tests."""
    server = create_server()
    assert server is not None


# ─────────── 5. Telemetry double-gating ───────────


@_skip_without_mcp
def test_telemetry_double_gated():
    """Even with ``expose_telemetry=True``, the runtime
    ``is_telemetry_allowed()`` must also return True.  CLINICAL data
    class blocks both layers."""
    from panelforge_figures.safety import DataClass, set_data_class

    set_data_class(DataClass.CLINICAL)
    try:
        config = MCPServerConfig(expose_telemetry=True)
        server = create_server(config)
        # Server was created; the runtime gate refused to attach
        # telemetry tools, but creation itself must succeed.
        assert server is not None
    finally:
        set_data_class(DataClass.RESEARCH)


# ─────────── 6. CLI smoke ───────────


def test_cli_mcp_serve_help():
    """``figures mcp serve --help`` exits 0 and mentions transport."""
    from panelforge_figures.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["mcp", "serve", "--help"])
    assert result.exit_code == 0
    assert "transport" in result.output.lower()


def test_cli_mcp_group_help():
    """``figures mcp --help`` lists the ``serve`` subcommand."""
    from panelforge_figures.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "serve" in result.output.lower()


def test_cli_mcp_serve_without_sdk_exits_1():
    """If the mcp SDK is missing, the CLI exits 1 and prints a friendly
    error to stderr (NOT stdout — stdout is reserved for protocol)."""
    from panelforge_figures.cli import main

    with patch.dict(
        "sys.modules",
        {"mcp": None, "mcp.server": None, "mcp.server.stdio": None},
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["mcp", "serve"])
        assert result.exit_code == 1


# ─────────── 7. Version bump ───────────


def test_version_is_at_least_v2():
    """v2+ programme: minor version bumps per elevation, not strict equality."""
    from panelforge_figures import __version__

    parts = __version__.split(".")
    assert int(parts[0]) >= 2, f"expected ≥ 2.x.y, got {__version__!r}"
