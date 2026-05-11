"""Tests for IPython magic integration (Elevation 19 — v3.13.0).

Covers :mod:`panelforge_figures.notebook.magic`:

1. ``load_ipython_extension(mock_ipython)`` registers magics.
2. ``_dispatch_line("profile", [...])`` delegates to :func:`api.profile`.
3. ``_dispatch_line("version", [])`` returns ``__version__``.
4. ``_dispatch_cell("recommend", [], "data/cells.csv")`` works.
5. ``_dispatch_cell("render", [recipe_name], json_dict)`` works.
6. ``_help()`` returns a docstring listing every subcommand.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

# Skip the entire module when IPython is not installed.
pytest.importorskip("IPython")
pd = pytest.importorskip("pandas")

from panelforge_figures import __version__  # noqa: E402
from panelforge_figures.notebook import api as notebook_api  # noqa: E402
from panelforge_figures.notebook import magic as notebook_magic  # noqa: E402

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


class _FakeIPython:
    """Minimal stand-in for an InteractiveShell.

    Records every ``register_magics`` call and exposes a ``user_ns``
    namespace so the magic's eval-fallback path can be exercised.
    """

    def __init__(self) -> None:
        self.registered: list[Any] = []
        self.user_ns: dict[str, Any] = {}

    def register_magics(self, magics: Any) -> None:
        self.registered.append(magics)


@pytest.fixture
def fake_ipython() -> _FakeIPython:
    return _FakeIPython()


@pytest.fixture
def magics(fake_ipython: _FakeIPython):
    """Construct the magics class + an instance bound to a fake shell."""
    cls = notebook_magic.build_magics_class()
    return cls(fake_ipython)


@pytest.fixture
def two_group_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "group": ["A"] * 5 + ["B"] * 5,
            "response": [1.0, 1.2, 1.4, 0.9, 1.1, 2.0, 2.2, 2.4, 2.1, 1.9],
            "covariate": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        }
    )
    out = tmp_path / "two_group.csv"
    df.to_csv(out, index=False)
    return out


# --------------------------------------------------------------------------- #
# 1. load_ipython_extension registers the magics                              #
# --------------------------------------------------------------------------- #


def test_load_ipython_extension_registers_magics(fake_ipython: _FakeIPython) -> None:
    notebook_magic.load_ipython_extension(fake_ipython)
    assert len(fake_ipython.registered) == 1
    instance = fake_ipython.registered[0]
    # The registered object is an instance of PanelforgeMagics.
    cls = notebook_magic.build_magics_class()
    assert isinstance(instance, cls)


def test_load_ipython_extension_via_package(fake_ipython: _FakeIPython) -> None:
    """The top-level notebook package re-exports load_ipython_extension."""
    import panelforge_figures.notebook as nb

    nb.load_ipython_extension(fake_ipython)
    assert len(fake_ipython.registered) == 1


# --------------------------------------------------------------------------- #
# 2. _dispatch_line("profile", [...])                                          #
# --------------------------------------------------------------------------- #


def test_dispatch_line_profile_returns_profile_report(
    magics: Any,
    two_group_csv: Path,
) -> None:
    result = magics._dispatch_line("profile", [str(two_group_csv)])
    assert isinstance(result, notebook_api.ProfileReport)
    assert result.profile_dict["n_rows"] == 10


def test_dispatch_line_profile_without_path_raises(magics: Any) -> None:
    with pytest.raises(ValueError, match="usage:"):
        magics._dispatch_line("profile", [])


# --------------------------------------------------------------------------- #
# 3. _dispatch_line("version", [])                                            #
# --------------------------------------------------------------------------- #


def test_dispatch_line_version_returns_version_string(magics: Any) -> None:
    result = magics._dispatch_line("version", [])
    assert isinstance(result, str)
    assert __version__ in result
    assert "panelforge-figures" in result


def test_dispatch_line_unknown_command_raises(magics: Any) -> None:
    with pytest.raises(ValueError, match="unknown subcommand"):
        magics._dispatch_line("totally-fake", [])


# --------------------------------------------------------------------------- #
# 4. _dispatch_cell("recommend", [], "data/cells.csv")                         #
# --------------------------------------------------------------------------- #


def test_dispatch_cell_recommend_with_body(
    magics: Any,
    two_group_csv: Path,
) -> None:
    result = magics._dispatch_cell("recommend", [], str(two_group_csv))
    assert isinstance(result, notebook_api.RecommendationReport)
    assert result.data_path == Path(str(two_group_csv))


def test_dispatch_cell_profile_with_body(
    magics: Any,
    two_group_csv: Path,
) -> None:
    result = magics._dispatch_cell("profile", [], str(two_group_csv))
    assert isinstance(result, notebook_api.ProfileReport)
    assert result.profile_dict["n_rows"] == 10


def test_dispatch_cell_recommend_respects_top_k(
    magics: Any,
    two_group_csv: Path,
) -> None:
    """--top-k=N caps the recommendation list."""
    result = magics._dispatch_cell(
        "recommend",
        ["--top-k=2"],
        str(two_group_csv),
    )
    assert isinstance(result, notebook_api.RecommendationReport)
    assert len(result.recommendations) <= 2


# --------------------------------------------------------------------------- #
# 5. _dispatch_cell("render", [recipe_name], json_dict)                        #
# --------------------------------------------------------------------------- #


_DEMO_RECIPE = "meta_and_diagnostic.outlier_detection_scatter"


def test_dispatch_cell_render_empty_body_falls_back_to_line(magics: Any) -> None:
    """Empty body delegates to _dispatch_line, where 'render' is not a
    line-magic subcommand → ValueError with the help suggestion.

    This documents the design: cell-magic ``render`` requires a body
    (the contract); a bare ``%%panelforge render foo`` with no body is
    not meaningful.
    """
    with pytest.raises(ValueError, match="unknown subcommand"):
        magics._dispatch_cell("render", [_DEMO_RECIPE], "")


def test_dispatch_cell_render_with_json_body(magics: Any) -> None:
    """A JSON dict body builds the recipe's contract from the parsed dict."""
    from panelforge_figures.core.contract import ensure_all_imported, get_recipe

    ensure_all_imported()
    rec = get_recipe(_DEMO_RECIPE)
    payload = rec.demo_contract().model_dump()
    import json as _json

    body = _json.dumps(payload)
    result = magics._dispatch_cell("render", [_DEMO_RECIPE], body)
    assert isinstance(result, notebook_api.RenderResult)


def test_dispatch_cell_render_with_user_namespace_eval(
    magics: Any,
    fake_ipython: _FakeIPython,
) -> None:
    """When the body is not JSON, it is eval()-ed in the shell's user_ns."""
    from panelforge_figures.core.contract import ensure_all_imported, get_recipe

    ensure_all_imported()
    rec = get_recipe(_DEMO_RECIPE)
    payload = rec.demo_contract().model_dump()
    # Place the dict in the user namespace under a name.
    fake_ipython.user_ns["my_contract"] = payload
    result = magics._dispatch_cell("render", [_DEMO_RECIPE], "my_contract")
    assert isinstance(result, notebook_api.RenderResult)


def test_dispatch_cell_render_without_name_raises(magics: Any) -> None:
    with pytest.raises(ValueError, match="recipe_full_name"):
        magics._dispatch_cell("render", [], "{}")


# --------------------------------------------------------------------------- #
# 6. _help()                                                                  #
# --------------------------------------------------------------------------- #


def test_help_returns_docstring_with_all_subcommands(magics: Any) -> None:
    text = magics._help()
    assert isinstance(text, str)
    for subcmd in (
        "profile",
        "recommend",
        "scout",
        "audit-venue",
        "audit-bias",
        "lint-xrefs",
        "verify-claims",
        "version",
    ):
        assert subcmd in text


def test_help_can_be_invoked_via_dispatch(magics: Any) -> None:
    """`%panelforge help` / `%panelforge ?` both yield the help text."""
    h1 = magics._dispatch_line("help", [])
    h2 = magics._dispatch_line("?", [])
    assert "profile" in h1
    assert h1 == h2


def test_empty_line_returns_help(magics: Any) -> None:
    """Calling the line magic with an empty string returns help."""
    result = magics.panelforge_line("")
    assert isinstance(result, str)
    assert "profile" in result


# --------------------------------------------------------------------------- #
# Additional cell-magic coverage                                              #
# --------------------------------------------------------------------------- #


def test_dispatch_cell_empty_body_falls_back_to_line(
    magics: Any,
    two_group_csv: Path,
) -> None:
    """Empty body + 'profile <path>' on the line == line magic behaviour."""
    result = magics._dispatch_cell("profile", [str(two_group_csv)], "")
    assert isinstance(result, notebook_api.ProfileReport)


def test_extract_top_k_helper() -> None:
    """The helper extracts --top-k in both space and = forms."""
    assert notebook_magic._extract_top_k(["--top-k", "3"]) == 3
    assert notebook_magic._extract_top_k(["--top-k=7"]) == 7
    assert notebook_magic._extract_top_k([]) == 5  # default
    # Malformed values fall back to the default.
    assert notebook_magic._extract_top_k(["--top-k", "abc"]) == 5
