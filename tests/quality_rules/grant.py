"""Quality rules for grant_and_conceptual families."""

from __future__ import annotations


def _text_artists(fig):
    out = []
    for a in fig.axes:
        out.extend(a.texts)
    return out


def _patches(fig):
    out = []
    for a in fig.axes:
        out.extend(p for p in a.patches)
    return out


def assert_conceptual_ok(fig, entry):
    """Conceptual family — ≥3 text artists and ≥2 rectangles/patches."""
    txts = _text_artists(fig)
    pchs = _patches(fig)
    assert len(txts) >= 3, f"{entry.full_name}: needs ≥3 text artists (got {len(txts)})"
    assert len(pchs) >= 2, f"{entry.full_name}: needs ≥2 decorative patches (got {len(pchs)})"


def assert_flow_ok(fig, entry):
    """Flow family — ≥2 rounded boxes AND ≥1 annotation arrow."""
    pchs = _patches(fig)
    assert len(pchs) >= 2, f"{entry.full_name}: needs ≥2 boxes (got {len(pchs)})"
    # Arrowed annotations live in fig._suptitle? No — in ax.texts with arrow_patch.
    arrow_count = 0
    for a in fig.axes:
        for child in a.get_children():
            if hasattr(child, "arrow_patch") and child.arrow_patch is not None or type(child).__name__ == "FancyArrowPatch":
                arrow_count += 1
    assert arrow_count >= 1, f"{entry.full_name}: needs ≥1 arrow annotation (got {arrow_count})"


def assert_gantt_ok(fig, entry):
    """Gantt family — ≥3 horizontal bars/patches AND ≥1 milestone marker."""
    bar_like = []
    for a in fig.axes:
        bar_like.extend(a.patches)
    assert len(bar_like) >= 3, f"{entry.full_name}: needs ≥3 task bars (got {len(bar_like)})"
    # Milestone markers appear as PathCollection scatters (marker="D").
    coll_count = sum(len(a.collections) for a in fig.axes)
    assert coll_count >= 1, f"{entry.full_name}: needs ≥1 scatter collection for milestones"


def assert_matrix_ok(fig, entry):
    """Matrix family — at least one imshow/pcolormesh present."""
    has_image = False
    for a in fig.axes:
        if a.images:
            has_image = True
            break
        for c in a.collections:
            if type(c).__name__ in ("QuadMesh", "PolyQuadMesh"):
                has_image = True
                break
        # The missing-data matrix uses Rectangle patches instead of imshow.
        if len(a.patches) >= 4 and not has_image:
            has_image = True
    assert has_image, f"{entry.full_name}: needs an imshow/pcolormesh or ≥4 cell patches"
