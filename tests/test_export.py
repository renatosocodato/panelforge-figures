"""Export helpers — multi-format output to a temp directory."""

from pathlib import Path

import matplotlib.pyplot as plt

from panelforge_figures.core.export import export_figure


def test_export_figure_writes_requested_formats(tmp_path: Path):
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 4])
    paths = export_figure(fig, stem="demo", formats=("pdf", "png"), outdir=tmp_path, dpi=120)
    assert len(paths) == 2
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 0
    plt.close(fig)


def test_export_figure_dry_outdir_creation(tmp_path: Path):
    fig, ax = plt.subplots()
    ax.bar([0, 1, 2], [1, 2, 3])
    sub = tmp_path / "a" / "b" / "c"
    paths = export_figure(fig, stem="nested", formats=("png",), outdir=sub)
    assert sub.is_dir()
    assert paths[0].is_file()
    plt.close(fig)
