"""Allow ``python -m panelforge_figures.cli`` as an alias for ``figures``.

The ``cli`` module was promoted to a package in v3.9.0 (E15 — interactive
scout TUI) so we could co-locate :mod:`panelforge_figures.cli.tui_scout`
alongside the main Click group.  This shim preserves the existing
``python -m panelforge_figures.cli <subcommand>`` invocation that some
tests + downstream scripts rely on.
"""

from . import main

if __name__ == "__main__":  # pragma: no cover
    main()
