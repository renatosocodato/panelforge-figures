"""IPython cell-/line-magic commands for panelforge-figures.

Usage::

    %load_ext panelforge_figures.notebook

    %panelforge profile data/cells.csv
    %panelforge recommend data/cells.csv
    %panelforge version

    %%panelforge profile
    data/cells.csv

    %%panelforge render biophysics_scaling.compartment_paired_delta_scatter
    {"estimates": [...]}

The line-magic form takes its argument string directly; the cell-magic
form is useful when the contract is a multi-line JSON / Python literal.
Cell-magic bodies are parsed in priority order:

* If the body is empty or whitespace, fall back to the line-magic
  behaviour with the line as a single argument.
* If the body parses as JSON, use the parsed object.
* Otherwise the body is ``eval()``-ed in the user's namespace (so
  expressions like ``df.head()`` or ``my_contract`` resolve).
"""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "PanelforgeMagics",
    "build_magics_class",
    "load_ipython_extension",
]


# Lazily built on first access — only IPython users pay the import cost.
PanelforgeMagics: Any = None


def build_magics_class() -> Any:
    """Construct and return the ``PanelforgeMagics`` class.

    Deferred so importing :mod:`panelforge_figures.notebook.magic` does not
    require IPython to be installed.
    """
    global PanelforgeMagics
    if PanelforgeMagics is not None:
        return PanelforgeMagics

    try:
        from IPython.core.magic import (
            Magics,
            cell_magic,
            line_magic,
            magics_class,
        )
    except ImportError as exc:  # pragma: no cover — IPython missing path
        raise RuntimeError(
            "IPython is required for panelforge_figures.notebook.magic. "
            "Install with: pip install 'panelforge-figures[notebook]'"
        ) from exc

    @magics_class
    class _PanelforgeMagics(Magics):
        """Line + cell magics that dispatch to :mod:`notebook.api`."""

        # ── line magic ────────────────────────────────────────────────
        @line_magic("panelforge")
        def panelforge_line(self, line: str) -> Any:
            """``%panelforge <subcommand> <args>`` — dispatch to api.*.

            Subcommands::

              profile <path>
              recommend <path> [--top-k N]
              scout [project_root]
              audit-venue <manuscript> <venue>
              audit-bias [figures_dir]
              lint-xrefs <manuscript> [figures_dir]
              verify-claims <manuscript> [figures_dir]
              version
              help
            """
            parts = line.strip().split()
            if not parts:
                return self._help()
            cmd = parts[0]
            args = parts[1:]
            return self._dispatch_line(cmd, args)

        # ── cell magic ────────────────────────────────────────────────
        @cell_magic("panelforge")
        def panelforge_cell(self, line: str, cell: str) -> Any:
            """``%%panelforge <subcommand>`` — multi-line body support.

            The cell body is parsed as JSON when possible; otherwise it
            is ``eval()``-ed in the calling shell's user namespace.
            """
            parts = line.strip().split()
            if not parts:
                return self._help()
            cmd = parts[0]
            args = parts[1:]
            return self._dispatch_cell(cmd, args, cell)

        # ── dispatch tables ───────────────────────────────────────────
        def _dispatch_line(self, cmd: str, args: list[str]) -> Any:
            """Handle line-magic forms.  Returns the API object or a string."""
            from . import api

            if cmd in {"help", "?"}:
                return self._help()
            if cmd == "version":
                from panelforge_figures import __version__ as v

                return f"panelforge-figures {v}"

            if cmd == "profile":
                if not args:
                    raise ValueError("usage: %panelforge profile <path>")
                return api.profile(args[0])

            if cmd == "recommend":
                if not args:
                    raise ValueError("usage: %panelforge recommend <path>")
                top_k = _extract_top_k(args)
                return api.recommend(args[0], top_k=top_k)

            if cmd == "scout":
                root = args[0] if args else "."
                return api.scout(root)

            if cmd == "audit-venue":
                if len(args) < 2:
                    raise ValueError(
                        "usage: %panelforge audit-venue <manuscript> <venue>"
                    )
                return api.audit_venue(args[0], venue=args[1])

            if cmd == "audit-bias":
                fdir = args[0] if args else "panelforge_workspace/figures"
                return api.audit_bias(fdir)

            if cmd == "lint-xrefs":
                if not args:
                    raise ValueError(
                        "usage: %panelforge lint-xrefs <manuscript> [figures_dir]"
                    )
                fdir = args[1] if len(args) > 1 else "panelforge_workspace/figures"
                return api.lint_xrefs(args[0], figures_dir=fdir)

            if cmd == "verify-claims":
                if not args:
                    raise ValueError(
                        "usage: %panelforge verify-claims <manuscript> [figures_dir]"
                    )
                fdir = args[1] if len(args) > 1 else "panelforge_workspace/figures"
                return api.verify_claims(args[0], figures_dir=fdir)

            raise ValueError(f"unknown subcommand: {cmd!r}; try '%panelforge help'")

        def _dispatch_cell(self, cmd: str, args: list[str], cell: str) -> Any:
            """Handle cell-magic forms.  Parses the body and forwards."""
            from . import api

            body = (cell or "").strip()

            # Empty body → fall back to line-magic semantics; the user is
            # probably writing %%panelforge profile / data.csv on the line.
            if not body:
                return self._dispatch_line(cmd, args)

            if cmd in {"profile", "recommend"}:
                # Body is a single path (or a Python expression yielding one).
                path = self._parse_path_body(body)
                if cmd == "profile":
                    return api.profile(path)
                top_k = _extract_top_k(args)
                return api.recommend(path, top_k=top_k)

            if cmd == "render":
                if not args:
                    raise ValueError(
                        "usage: %%panelforge render <recipe_full_name>"
                    )
                recipe_name = args[0]
                payload = self._parse_dict_body(body)
                save = "--save" in args
                return api.render(
                    recipe_name,
                    contract=payload,
                    save=save,
                )

            if cmd == "scout":
                # Body overrides the project root.
                return api.scout(body)

            if cmd == "audit-venue":
                if not args:
                    raise ValueError(
                        "usage: %%panelforge audit-venue <venue>\\n<manuscript_path>"
                    )
                venue = args[0]
                return api.audit_venue(self._parse_path_body(body), venue=venue)

            if cmd == "audit-bias":
                return api.audit_bias(self._parse_path_body(body))

            if cmd == "lint-xrefs":
                return api.lint_xrefs(self._parse_path_body(body))

            if cmd == "verify-claims":
                return api.verify_claims(self._parse_path_body(body))

            raise ValueError(f"unknown subcommand: {cmd!r}; try '%panelforge help'")

        # ── small helpers ─────────────────────────────────────────────
        def _parse_path_body(self, body: str) -> str:
            """First non-blank line of the cell body, stripped."""
            for line in body.splitlines():
                stripped = line.strip()
                if stripped:
                    return stripped
            raise ValueError("empty cell body — expected a path")

        def _parse_dict_body(self, body: str) -> dict[str, Any]:
            """Parse the cell body as JSON, falling back to ``eval`` in the
            user namespace if JSON parsing fails.
            """
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    return parsed
            except (TypeError, ValueError):
                pass

            # Fallback: eval in the user namespace if one is attached.
            ns = {}
            shell = getattr(self, "shell", None)
            if shell is not None and hasattr(shell, "user_ns"):
                ns = shell.user_ns
            try:
                result = eval(body, ns, {})  # noqa: S307 — IPython convention
            except Exception as exc:
                raise ValueError(
                    f"cell body is neither valid JSON nor evaluable: {exc}"
                ) from exc
            if not isinstance(result, dict):
                raise ValueError(
                    f"cell body must yield a dict, got {type(result).__name__}"
                )
            return result

        def _help(self) -> str:
            return (
                "panelforge magics — usage:\n"
                "  %panelforge profile <path>\n"
                "  %panelforge recommend <path> [--top-k N]\n"
                "  %panelforge scout [project_root]\n"
                "  %panelforge audit-venue <manuscript> <venue>\n"
                "  %panelforge audit-bias [figures_dir]\n"
                "  %panelforge lint-xrefs <manuscript> [figures_dir]\n"
                "  %panelforge verify-claims <manuscript> [figures_dir]\n"
                "  %panelforge version\n"
                "\n"
                "Cell-magic forms (%%panelforge) accept multi-line bodies:\n"
                "  %%panelforge profile        → body = path\n"
                "  %%panelforge recommend      → body = path\n"
                "  %%panelforge render <name>  → body = JSON contract\n"
                "  %%panelforge scout          → body = project_root\n"
            )

    PanelforgeMagics = _PanelforgeMagics
    return PanelforgeMagics


# --------------------------------------------------------------------------- #
# Helpers / entry points                                                       #
# --------------------------------------------------------------------------- #


def _extract_top_k(args: list[str]) -> int:
    """Pull ``--top-k N`` out of a line-magic argument list.

    Returns ``5`` (the API default) when the flag is absent or malformed.
    """
    for i, arg in enumerate(args):
        if arg == "--top-k" and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                return 5
        if arg.startswith("--top-k="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                return 5
    return 5


def load_ipython_extension(ipython: Any) -> None:
    """Register the panelforge magics with ``ipython``.

    Called automatically by IPython when the user runs::

        %load_ext panelforge_figures.notebook
    """
    cls = build_magics_class()
    ipython.register_magics(cls(ipython))


def unload_ipython_extension(ipython: Any) -> None:  # pragma: no cover
    """Symmetric companion to :func:`load_ipython_extension`.

    IPython does not currently support clean magic removal, so this is a
    no-op kept for symmetry / future-proofing.
    """
    return None
