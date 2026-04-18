"""Recipe registry — modality subpackages live here.

Importing this package does NOT automatically import every modality. Callers
should use `panelforge_figures.core.contract.ensure_all_imported()` to trigger
the scan, which walks this package's submodules.
"""
