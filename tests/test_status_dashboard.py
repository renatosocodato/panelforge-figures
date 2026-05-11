"""Tests for the Elevation 20 reproducibility / audit status dashboard.

Exercises the per-section collectors, the orchestrator's sandbox
behaviour (so a crashing collector becomes a single ``unknown`` entry
rather than a top-level failure), each renderer (text / JSON / HTML /
Markdown), and the ``figures status`` CLI command end-to-end.

Every test uses ``tmp_path`` for isolation; no test reads from the
real ``~/.config/panelforge/projects.yaml`` (conftest already redirects
``$XDG_CONFIG_HOME``).
"""

from __future__ import annotations

import html.parser
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.status_dashboard import (
    DashboardEntry,
    DashboardSection,
    StatusDashboard,
    StatusLevel,
    _collect_artifacts_section,
    _collect_audits_section,
    _collect_cache_section,
    _collect_inventory_section,
    _collect_project_section,
    _collect_provenance_section,
    _collect_safety_section,
    _collect_telemetry_section,
    _compute_overall_level,
    _compute_summary_line,
    collect_status,
    render_dashboard_html,
    render_dashboard_markdown,
    render_dashboard_text,
)

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _write_project_yaml(
    root: Path,
    *,
    project_id: str = "demo_project",
    modality: str = "actin_morphometry",
    data_class: str = "research",
    venue: str | None = None,
) -> Path:
    lines = [
        f"project_id: {project_id}",
        f"modality: {modality}",
        f"data_class: {data_class}",
    ]
    if venue:
        lines.append(f"venue: {venue}")
    yaml_path = root / "panelforge.project.yaml"
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return yaml_path


def _write_provenance_sidecar(
    figures_dir: Path,
    figure_id: str = "figure_1",
    *,
    with_audit: bool = False,
) -> Path:
    """Write a minimal provenance sidecar alongside a stub PDF."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    pdf = figures_dir / f"{figure_id}.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%stub")
    sidecar = figures_dir / f"{figure_id}.provenance.json"
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "figure_path": str(pdf),
        "figure_sha256": "abc",
        "rendered_at": datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "recipe": {
            "full_name": "demo.recipe",
            "module_sha": "deadbeef",
            "module_path": "/tmp/demo_recipe.py",
            "panelforge_version": "3.14.0",
            "panelforge_git_commit": "uncommitted",
        },
        "data": {"sources": [], "column_mapping": {}},
        "rendering_environment": {},
    }
    if with_audit:
        payload["audit"] = {
            "rules_passed": [],
            "rules_warned": [],
            "rules_failed": [],
        }
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    return sidecar


def _write_render_cache(project_root: Path, *, n_entries: int = 2,
                        n_outputs_exist: int = 2) -> Path:
    """Write a render_cache.json with ``n_entries`` rows.

    The first ``n_outputs_exist`` rows reference an on-disk PDF; the rest
    point at non-existent files (to exercise the hit-rate calculation).
    """
    from panelforge_figures.manifest.render_cache import (
        CACHE_SCHEMA_VERSION,
        CacheEntry,
        RenderCache,
        save_cache,
    )

    cache = RenderCache.empty()
    figs_dir = project_root / "panelforge_workspace" / "figures"
    figs_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_entries):
        out_rel = f"panelforge_workspace/figures/panel_{i}.pdf"
        if i < n_outputs_exist:
            (project_root / out_rel).parent.mkdir(parents=True, exist_ok=True)
            (project_root / out_rel).write_bytes(b"%PDF-1.4 stub")
        cache.entries[f"panel_{i}"] = CacheEntry(
            figure_id=str(i),
            panel_id=f"panel_{i}",
            recipe_full_name="demo.recipe",
            recipe_sha="aa",
            contract_sha="bb",
            data_sha="cc",
            output_sha="dd",
            output_path=out_rel,
            rendered_at=datetime.now(UTC).isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            panelforge_version="3.14.0",
            notes=(),
        )
    cache.schema_version = CACHE_SCHEMA_VERSION
    save_cache(cache, project_root)
    return project_root / "panelforge_workspace" / "render_cache.json"


# --------------------------------------------------------------------------- #
# 1. End-to-end collect on an empty project                                    #
# --------------------------------------------------------------------------- #


def test_collect_status_on_empty_project(tmp_path: Path) -> None:
    """An empty tmp project still yields a complete dashboard."""
    dash = collect_status(tmp_path)
    assert isinstance(dash, StatusDashboard)
    assert dash.panelforge_version
    assert dash.entries
    # All 8 sections should be represented.
    seen = {e.section for e in dash.entries}
    assert seen == set(DashboardSection)


# --------------------------------------------------------------------------- #
# 2. Tolerant: corrupt YAML must not crash                                     #
# --------------------------------------------------------------------------- #


def test_collect_status_tolerates_corrupt_yaml(tmp_path: Path) -> None:
    """A corrupt panelforge.project.yaml must not propagate exceptions."""
    (tmp_path / "panelforge.project.yaml").write_text(
        ":\n: : not yaml\n\t- []\n", encoding="utf-8"
    )
    dash = collect_status(tmp_path)
    # We get a valid dashboard back (no exception).
    assert isinstance(dash, StatusDashboard)
    # Project section still emits >= 1 entry.
    proj_entries = [e for e in dash.entries if e.section == DashboardSection.project]
    assert len(proj_entries) >= 1


# --------------------------------------------------------------------------- #
# 3. Project section with valid yaml                                           #
# --------------------------------------------------------------------------- #


def test_collect_project_section_with_valid_yaml(tmp_path: Path) -> None:
    """Valid project YAML → 4 entries (id, modality, data_class, registry)."""
    _write_project_yaml(tmp_path)
    entries = _collect_project_section(tmp_path)
    labels = {e.label for e in entries}
    assert "project_id" in labels
    assert "modality" in labels
    assert "data_class" in labels
    assert "registry" in labels
    # All present + populated.
    assert len(entries) == 4
    id_entry = next(e for e in entries if e.label == "project_id")
    assert id_entry.value == "demo_project"


# --------------------------------------------------------------------------- #
# 4. Inventory section counts                                                  #
# --------------------------------------------------------------------------- #


def test_collect_inventory_section_counts_files(tmp_path: Path) -> None:
    """Counts data files / models / notebooks correctly."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "raw.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "data" / "processed.parquet").write_bytes(b"PAR1stub")
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "fit.pkl").write_bytes(b"\x80")
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "explore.ipynb").write_text(
        '{"cells": []}', encoding="utf-8"
    )

    entries = _collect_inventory_section(tmp_path)
    by_label = {e.label: e for e in entries}
    assert "data files" in by_label
    assert by_label["data files"].value.startswith("2 ")
    assert by_label["models"].value == "1"
    assert by_label["notebooks"].value == "1"


# --------------------------------------------------------------------------- #
# 5. Cache section reads render_cache.json                                     #
# --------------------------------------------------------------------------- #


def test_collect_cache_section_emits_hit_rate(tmp_path: Path) -> None:
    """A render_cache.json with 2 entries (2 fresh) → 100% hit rate."""
    _write_render_cache(tmp_path, n_entries=2, n_outputs_exist=2)
    entries = _collect_cache_section(tmp_path)
    cache_entry = next(e for e in entries if e.label == "render cache")
    assert "2/2" in cache_entry.value
    assert "100%" in cache_entry.value
    assert cache_entry.level == StatusLevel.ok


def test_collect_cache_section_drift(tmp_path: Path) -> None:
    """A cache with stale outputs → partial hit rate, warn level."""
    _write_render_cache(tmp_path, n_entries=4, n_outputs_exist=1)
    entries = _collect_cache_section(tmp_path)
    cache_entry = next(e for e in entries if e.label == "render cache")
    assert "1/4" in cache_entry.value
    # 25% — should be warn
    assert cache_entry.level == StatusLevel.warn


# --------------------------------------------------------------------------- #
# 6. Provenance section walks sidecars                                         #
# --------------------------------------------------------------------------- #


def test_collect_provenance_section_walks_sidecars(tmp_path: Path) -> None:
    """All figures with sidecars → 100% coverage."""
    figs = tmp_path / "panelforge_workspace" / "figures"
    _write_provenance_sidecar(figs, "figure_1", with_audit=True)
    _write_provenance_sidecar(figs, "figure_2", with_audit=False)
    entries = _collect_provenance_section(tmp_path)
    cov_entry = next(e for e in entries if e.label == "figures w/ sidecar")
    assert "2/2" in cov_entry.value
    assert "100%" in cov_entry.value
    audit_entry = next(e for e in entries if e.label == "figures w/ audit")
    assert "1/2" in audit_entry.value


# --------------------------------------------------------------------------- #
# 7. Audits section runs all four audits                                       #
# --------------------------------------------------------------------------- #


def test_collect_audits_section_emits_per_audit_entries(tmp_path: Path) -> None:
    """All four audits should yield one entry each (even if skipped)."""
    _write_project_yaml(tmp_path, venue="cell")
    # Manuscript so verify-claims + lint-xrefs + audit-venue have inputs.
    manu_dir = tmp_path / "manuscript"
    manu_dir.mkdir()
    (manu_dir / "main.tex").write_text(
        r"\begin{document}"
        r"\begin{figure}\caption{stub caption with enough text to clear minimum.}"
        r"\label{fig:1}\end{figure}"
        r"Figure \ref{fig:1} shows a stub result."
        r"\end{document}",
        encoding="utf-8",
    )
    figs = tmp_path / "panelforge_workspace" / "figures"
    _write_provenance_sidecar(figs, "figure_1", with_audit=True)

    entries = _collect_audits_section(tmp_path)
    labels = {e.label for e in entries}
    # Each audit family is represented.
    assert "verify-claims" in labels
    assert "xref-linter" in labels
    assert "audit-bias" in labels
    # audit-venue might be parameterised "(cell)"
    assert any(lab.startswith("audit-venue") for lab in labels)


# --------------------------------------------------------------------------- #
# 8. Artifacts section counts PDFs + captions                                  #
# --------------------------------------------------------------------------- #


def test_collect_artifacts_section_counts_pdfs_and_captions(tmp_path: Path) -> None:
    figs = tmp_path / "panelforge_workspace" / "figures"
    figs.mkdir(parents=True)
    (figs / "figure_1.pdf").write_bytes(b"%PDF stub")
    (figs / "figure_2.pdf").write_bytes(b"%PDF stub")
    captions = tmp_path / "panelforge_workspace" / "captions"
    captions.mkdir(parents=True)
    (captions / "figure_1.md").write_text("Caption 1", encoding="utf-8")
    (tmp_path / "figures_plan.yaml").write_text(
        "version: 1\nfigures: []\n", encoding="utf-8"
    )

    entries = _collect_artifacts_section(tmp_path)
    by_label = {e.label: e for e in entries}
    assert by_label["figures"].value == "2 PDFs"
    assert by_label["captions"].value == "1 drafted"
    assert "present" in by_label["figures_plan.yaml"].value


# --------------------------------------------------------------------------- #
# 9. Safety section emits LLM/vision/telemetry policy                          #
# --------------------------------------------------------------------------- #


def test_collect_safety_section_emits_policy_entries(tmp_path: Path) -> None:
    entries = _collect_safety_section(tmp_path)
    labels = {e.label for e in entries}
    assert "data_class" in labels
    assert "LLM channel" in labels
    assert "vision channel" in labels
    assert "telemetry" in labels
    assert "plugin network" in labels


# --------------------------------------------------------------------------- #
# 10. Telemetry section reads usage.jsonl                                      #
# --------------------------------------------------------------------------- #


def test_collect_telemetry_section_no_log(tmp_path: Path) -> None:
    entries = _collect_telemetry_section(tmp_path)
    assert any(e.label == "usage.jsonl" for e in entries)
    log_entry = next(e for e in entries if e.label == "usage.jsonl")
    assert log_entry.value == "not present"


def test_collect_telemetry_section_reads_rows(tmp_path: Path) -> None:
    """A usage.jsonl with 3 rows (1 marked) → row + pick counters."""
    ws = tmp_path / "panelforge_workspace"
    ws.mkdir()
    log = ws / "usage.jsonl"
    now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = [
        {"timestamp": now, "user_picked": None},
        {"timestamp": now, "user_picked": "recipe_a"},
        {"timestamp": now, "user_picked": None},
    ]
    log.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )

    entries = _collect_telemetry_section(tmp_path)
    by_label = {e.label: e for e in entries}
    assert by_label["usage.jsonl"].value == "3 rows"
    assert by_label["user picks"].value == "1 marked"


# --------------------------------------------------------------------------- #
# 11. Overall level: max severity                                              #
# --------------------------------------------------------------------------- #


def test_compute_overall_level_returns_max_severity() -> None:
    entries = [
        DashboardEntry(DashboardSection.project, "a", "x", StatusLevel.ok),
        DashboardEntry(DashboardSection.project, "b", "x", StatusLevel.warn),
        DashboardEntry(DashboardSection.project, "c", "x", StatusLevel.info),
    ]
    assert _compute_overall_level(entries) == StatusLevel.warn

    entries.append(
        DashboardEntry(DashboardSection.project, "d", "x", StatusLevel.fail)
    )
    assert _compute_overall_level(entries) == StatusLevel.fail


def test_compute_overall_level_empty_returns_ok() -> None:
    assert _compute_overall_level([]) == StatusLevel.ok


def test_compute_summary_line_reflects_overall() -> None:
    entries = [
        DashboardEntry(DashboardSection.project, "a", "x", StatusLevel.fail),
        DashboardEntry(DashboardSection.project, "b", "x", StatusLevel.warn),
    ]
    line = _compute_summary_line(entries, StatusLevel.fail)
    assert "FAIL" in line
    line2 = _compute_summary_line(entries, StatusLevel.warn)
    assert "warning" in line2.lower()
    line3 = _compute_summary_line(entries, StatusLevel.ok)
    assert "passing" in line3


# --------------------------------------------------------------------------- #
# 12. to_dict serialisation                                                    #
# --------------------------------------------------------------------------- #


def test_dashboard_to_dict_serialises(tmp_path: Path) -> None:
    dash = collect_status(tmp_path)
    d = dash.to_dict()
    # Round-trip through JSON cleanly.
    text = json.dumps(d, default=str)
    re_parsed = json.loads(text)
    assert re_parsed["panelforge_version"] == dash.panelforge_version
    assert isinstance(re_parsed["entries"], list)
    assert all("section" in e and "level" in e for e in re_parsed["entries"])


# --------------------------------------------------------------------------- #
# 13. Text renderer contains identifying metadata                              #
# --------------------------------------------------------------------------- #


def test_render_dashboard_text_contains_project_root_and_version(tmp_path: Path) -> None:
    dash = collect_status(tmp_path)
    text = render_dashboard_text(dash, color=False)
    assert dash.panelforge_version in text
    assert str(dash.project_root) in text


# --------------------------------------------------------------------------- #
# 14. No-color suppresses ANSI                                                 #
# --------------------------------------------------------------------------- #


def test_render_dashboard_text_no_color_strips_ansi(tmp_path: Path) -> None:
    dash = collect_status(tmp_path)
    text = render_dashboard_text(dash, color=False)
    assert "\x1b[" not in text


def test_render_dashboard_text_color_includes_ansi(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    dash = collect_status(tmp_path)
    text = render_dashboard_text(dash, color=True)
    assert "\x1b[" in text


# --------------------------------------------------------------------------- #
# 15. HTML renderer is parseable                                               #
# --------------------------------------------------------------------------- #


class _HTMLValidator(html.parser.HTMLParser):
    """Counts open vs close tags to detect malformed output."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[no-untyped-def]
        if tag not in ("meta", "br", "hr", "img", "input"):
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            self.errors.append(f"closing {tag} with empty stack")
            return
        opened = self.stack.pop()
        if opened != tag:
            self.errors.append(f"mismatched: opened {opened}, closing {tag}")


def test_render_dashboard_html_is_parseable(tmp_path: Path) -> None:
    dash = collect_status(tmp_path)
    text = render_dashboard_html(dash)
    assert text.startswith("<!DOCTYPE html>")
    parser = _HTMLValidator()
    parser.feed(text)
    parser.close()
    assert not parser.errors, f"HTML structure errors: {parser.errors}"
    assert not parser.stack, f"unclosed tags: {parser.stack}"
    # Sanity: project root and version embedded.
    assert dash.panelforge_version in text


# --------------------------------------------------------------------------- #
# 16. Markdown renderer uses GitHub task-list markers                          #
# --------------------------------------------------------------------------- #


def test_render_dashboard_markdown_has_task_markers(tmp_path: Path) -> None:
    dash = collect_status(tmp_path)
    text = render_dashboard_markdown(dash)
    # At least one bracket marker should appear ([x], [i], [!], [ ], [-], [?])
    assert any(mark in text for mark in ("[x]", "[i]", "[!]", "[ ]", "[-]", "[?]"))
    # Section heading style.
    assert "## project" in text
    assert dash.panelforge_version in text


# --------------------------------------------------------------------------- #
# 17. CLI: --help                                                              #
# --------------------------------------------------------------------------- #


def test_cli_status_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["status", "--help"])
    assert result.exit_code == 0
    assert "Single-screen dashboard" in result.output
    assert "--format" in result.output


# --------------------------------------------------------------------------- #
# 18. CLI: empty project → exit 0                                              #
# --------------------------------------------------------------------------- #


def test_cli_status_on_empty_project_exits_zero(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["status", "--project-root", str(tmp_path), "--no-color"],
    )
    # Empty project has no FAIL entries → exit 0.
    assert result.exit_code == 0, result.output
    assert "panelforge status" in result.output


# --------------------------------------------------------------------------- #
# 19. CLI: --format json produces parseable JSON                               #
# --------------------------------------------------------------------------- #


def test_cli_status_json_format(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["status", "--project-root", str(tmp_path), "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert "entries" in parsed
    assert "overall_level" in parsed
    assert parsed["panelforge_version"]


# --------------------------------------------------------------------------- #
# 20. CLI: --format html --output writes a file                                #
# --------------------------------------------------------------------------- #


def test_cli_status_html_output_writes_file(tmp_path: Path) -> None:
    out_path = tmp_path / "report.html"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "status",
            "--project-root", str(tmp_path),
            "--format", "html",
            "--output", str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.is_file()
    text = out_path.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")


def test_cli_status_markdown_output_format(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["status", "--project-root", str(tmp_path), "--format", "markdown"],
    )
    assert result.exit_code == 0, result.output
    assert "## project" in result.output


# --------------------------------------------------------------------------- #
# 21. Section collectors that raise → unknown entry, not propagated            #
# --------------------------------------------------------------------------- #


def test_collector_exception_becomes_unknown_entry(tmp_path: Path,
                                                    monkeypatch) -> None:
    """A crashing collector must not abort collection."""
    import panelforge_figures.manifest.status_dashboard as sd

    def _exploding(project_root, **kwargs):  # noqa: ARG001
        raise RuntimeError("synthetic blowup")

    # Patch one collector to always raise.
    monkeypatch.setattr(sd, "_collect_safety_section", _exploding)

    dash = sd.collect_status(tmp_path)
    safety_entries = [e for e in dash.entries
                      if e.section == DashboardSection.safety]
    assert len(safety_entries) >= 1
    # The lone safety entry must be marked unknown with the exception detail.
    assert safety_entries[0].level == StatusLevel.unknown
    assert "synthetic blowup" in safety_entries[0].detail


# --------------------------------------------------------------------------- #
# 22. Verbose flag surfaces details                                            #
# --------------------------------------------------------------------------- #


def test_render_dashboard_text_verbose_shows_details(tmp_path: Path) -> None:
    """The verbose renderer surfaces ``detail`` strings on a secondary line."""
    dash = collect_status(tmp_path)
    text_v = render_dashboard_text(dash, color=False, verbose=True)
    text_q = render_dashboard_text(dash, color=False, verbose=False)
    # The verbose flag should produce a longer rendering (when at least one
    # entry has a detail string).
    assert len(text_v) >= len(text_q)
    # At least one detail string is surfaced.
    assert "->" in text_v or "run `figures" in text_v
