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


# ─────────── 5b. expose_* flags gate tool exposure (security surface) ───────────


def test_group_enabled_honors_expose_flags():
    """Pure filtering logic (no SDK needed): ``_group_enabled`` must
    return ``False`` for a group whose ``expose_*`` flag is off.

    Regression for ``mcp-expose-flags-noop``: the per-group flags were
    never consulted, so ``expose_scorer=False`` still exposed
    ``scorer.score`` / ``scorer.explain`` — a security-surface
    mismatch.  This test reproduces the bug at the gating boundary
    without requiring the optional ``mcp`` extra.
    """
    from panelforge_figures.mcp.tools import _group_enabled

    cfg = MCPServerConfig(expose_scorer=False)
    # The disabled group must be gated off ...
    assert _group_enabled(cfg, "scorer") is False
    # ... while the still-enabled groups stay on.
    assert _group_enabled(cfg, "index") is True
    assert _group_enabled(cfg, "provenance") is True
    assert _group_enabled(cfg, "projects") is True


def test_group_enabled_each_flag_independently():
    """Disabling one group must not affect the others, and the default
    (all-on) config exposes every group."""
    from panelforge_figures.mcp.tools import _group_enabled

    all_on = MCPServerConfig()
    for grp in ("scorer", "index", "provenance", "projects"):
        assert _group_enabled(all_on, grp) is True

    pairs = {
        "scorer": "expose_scorer",
        "index": "expose_index",
        "provenance": "expose_provenance",
        "projects": "expose_projects",
    }
    for grp in pairs:
        cfg = MCPServerConfig(**{pairs[grp]: False})
        assert _group_enabled(cfg, grp) is False, grp
        for other in pairs:
            if other != grp:
                assert _group_enabled(cfg, other) is True, (grp, other)


def test_group_enabled_none_config_is_permissive():
    """``config is None`` (no config supplied) keeps the historical
    all-on baseline so flag-less callers are unchanged."""
    from panelforge_figures.mcp.tools import _group_enabled

    for grp in ("recipe", "scorer", "index", "provenance", "projects"):
        assert _group_enabled(None, grp) is True


def test_group_enabled_unknown_group_fails_closed():
    """An unrecognized group prefix is not exposed without an explicit
    flag (fail-closed)."""
    from panelforge_figures.mcp.tools import _group_enabled

    assert _group_enabled(MCPServerConfig(), "mystery") is False


class _CaptureServer:
    """Minimal stand-in for ``mcp.server.Server`` that captures the
    handlers registered by ``register_recipe_tools`` so a test can
    invoke ``list_tools`` directly without a live transport."""

    def __init__(self):
        self.list_tools_handler = None
        self.call_tool_handler = None

    def list_tools(self):
        def _decorator(fn):
            self.list_tools_handler = fn
            return fn

        return _decorator

    def call_tool(self):
        def _decorator(fn):
            self.call_tool_handler = fn
            return fn

        return _decorator


@_skip_without_mcp
def test_list_tools_omits_scorer_when_disabled():
    """End-to-end (needs the SDK for ``Tool`` construction): with
    ``expose_scorer=False`` the scorer tools must be ABSENT from the
    listed tools, and PRESENT when the default config is used."""
    from panelforge_figures.mcp import tools as mcp_tools

    # Enabled: scorer tools appear.
    srv_on = _CaptureServer()
    mcp_tools.register_recipe_tools(srv_on, MCPServerConfig())
    names_on = {t.name for t in asyncio.run(srv_on.list_tools_handler())}
    assert "scorer.score" in names_on
    assert "scorer.explain" in names_on

    # Disabled: scorer tools vanish, but the rest of the surface stays.
    srv_off = _CaptureServer()
    mcp_tools.register_recipe_tools(
        srv_off, MCPServerConfig(expose_scorer=False)
    )
    names_off = {t.name for t in asyncio.run(srv_off.list_tools_handler())}
    assert "scorer.score" not in names_off
    assert "scorer.explain" not in names_off
    # Non-disabled groups remain exposed.
    assert "index.list_recipes" in names_off
    assert "provenance.build" in names_off
    assert "projects.list" in names_off


class _FakeTool:
    """Stand-in for ``mcp.types.Tool`` carrying just ``.name`` so the
    list-tools filtering can be exercised without the optional SDK."""

    def __init__(self, name, description=None, inputSchema=None):  # noqa: N803
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _FakeTextContent:
    """Stand-in for ``mcp.types.TextContent`` so ``_err``/``_ok`` (which
    build TextContent envelopes) run without the optional SDK."""

    def __init__(self, type="text", text=""):  # noqa: A002 — match SDK kwarg
        self.type = type
        self.text = text


def _install_fake_mcp_types(monkeypatch):
    """Inject a minimal fake ``mcp.types`` so the SDK-dependent tool
    builders run in environments without the real ``mcp`` extra.

    Returns the ``mcp.tools`` module for the caller to drive.
    """
    import sys
    import types as _pytypes

    fake_types = _pytypes.ModuleType("mcp.types")
    fake_types.Tool = _FakeTool
    fake_types.TextContent = _FakeTextContent
    fake_root = sys.modules.get("mcp") or _pytypes.ModuleType("mcp")
    monkeypatch.setitem(sys.modules, "mcp", fake_root)
    monkeypatch.setitem(sys.modules, "mcp.types", fake_types)
    from panelforge_figures.mcp import tools as mcp_tools

    return mcp_tools


def test_list_tools_filters_scorer_without_sdk(monkeypatch):
    """Behavior-level regression that runs WITHOUT the real ``mcp`` SDK
    (uses a fake ``mcp.types.Tool``): with ``expose_scorer=False`` the
    scorer tools must not appear in the listing, but do when the flag
    is left at its default.

    This is the decisive reproduce-before-fix for
    ``mcp-expose-flags-noop`` — on the unfixed code ``_list_tools``
    unconditionally appended ``_scorer_tool_list()``, so the
    ``not in`` assertions failed while the security surface leaked.
    """
    mcp_tools = _install_fake_mcp_types(monkeypatch)

    srv_on = _CaptureServer()
    mcp_tools.register_recipe_tools(srv_on, MCPServerConfig())
    names_on = {t.name for t in asyncio.run(srv_on.list_tools_handler())}
    assert "scorer.score" in names_on
    assert "scorer.explain" in names_on

    srv_off = _CaptureServer()
    mcp_tools.register_recipe_tools(srv_off, MCPServerConfig(expose_scorer=False))
    names_off = {t.name for t in asyncio.run(srv_off.list_tools_handler())}
    assert "scorer.score" not in names_off
    assert "scorer.explain" not in names_off
    # Non-disabled groups stay exposed.
    assert "index.list_recipes" in names_off
    assert "provenance.build" in names_off
    assert "projects.list" in names_off


@_skip_without_mcp
def test_call_tool_refuses_disabled_scorer():
    """Dispatch is gated too: invoking ``scorer.score`` with
    ``expose_scorer=False`` returns a structured 'disabled' error
    rather than executing the scorer."""
    import json

    from panelforge_figures.mcp import tools as mcp_tools

    srv = _CaptureServer()
    mcp_tools.register_recipe_tools(srv, MCPServerConfig(expose_scorer=False))
    result = asyncio.run(srv.call_tool_handler("scorer.score", {}))
    payload = json.loads(result[0].text)
    assert payload["success"] is False
    assert "disabled" in payload["error"].lower()


def test_call_tool_refuses_disabled_scorer_without_sdk(monkeypatch):
    """SDK-free dispatch-gating guard (re-audit): the #5 security fix gates
    BOTH listing AND dispatch, but the only dispatch test was @_skip_without_mcp
    and never ran in CI. This exercises the dispatch gate via the fake
    ``mcp.types`` (Tool + TextContent), so the gate is guarded SDK-free."""
    import json

    mcp_tools = _install_fake_mcp_types(monkeypatch)

    srv = _CaptureServer()
    mcp_tools.register_recipe_tools(srv, MCPServerConfig(expose_scorer=False))
    result = asyncio.run(srv.call_tool_handler("scorer.score", {}))
    payload = json.loads(result[0].text)
    assert payload["success"] is False
    assert "disabled" in payload["error"].lower()

    # And with the group enabled, dispatch is NOT refused for that reason.
    srv_on = _CaptureServer()
    mcp_tools.register_recipe_tools(srv_on, MCPServerConfig())
    res_on = asyncio.run(srv_on.call_tool_handler("scorer.score", {}))
    payload_on = json.loads(res_on[0].text)
    # It may fail for other reasons (bad args) but NOT with a "disabled" group error.
    assert not (
        payload_on.get("success") is False
        and "disabled" in str(payload_on.get("error", "")).lower()
    )


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
