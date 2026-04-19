"""Style-drift regression: cap the number of distinct hardcoded fontsize
and linewidth literals used across the recipe tree.

Rationale: every time a recipe picks a one-off fontsize (e.g. ``6.37``)
it widens the visual scale by one more tick and makes it harder for
future recipes to stay consistent. The ceilings here are set to the
counts observed when the test was introduced; lowering them is a
forcing function for migrating to ``PF_FONT_SIZES`` / ``PF_LINE_WIDTHS``
constants.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_RECIPES_DIR = Path(__file__).resolve().parents[1] / "src" / "panelforge_figures" / "recipes"

# Baseline distinct-count observed when this test was introduced (after
# the typography contract landed). Shrink these numbers to force
# consolidation; the intent is a one-way ratchet.
FONTSIZE_DISTINCT_CEILING = 20
LINEWIDTH_DISTINCT_CEILING = 20

_FONTSIZE_RE = re.compile(r"fontsize\s*=\s*([0-9]+(?:\.[0-9]+)?)")
_LINEWIDTH_RE = re.compile(r"\blw\s*=\s*([0-9]+(?:\.[0-9]+)?)")


def _iter_recipe_sources() -> list[Path]:
    return sorted(p for p in _RECIPES_DIR.rglob("*.py")
                  if p.name != "__init__.py" and not p.name.startswith("_"))


def _tally(pattern: re.Pattern[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for src in _iter_recipe_sources():
        for match in pattern.finditer(src.read_text(encoding="utf-8")):
            counts[match.group(1)] += 1
    return counts


def test_fontsize_literal_count_below_ceiling():
    """Distinct hardcoded fontsize literals must stay under the ceiling."""
    counts = _tally(_FONTSIZE_RE)
    distinct = sorted(counts)
    assert len(distinct) <= FONTSIZE_DISTINCT_CEILING, (
        f"distinct fontsize literals ({len(distinct)}) exceeds ceiling "
        f"{FONTSIZE_DISTINCT_CEILING}. "
        f"Observed values (value → count): "
        f"{sorted(counts.items(), key=lambda kv: -kv[1])}. "
        "Migrate to PF_FONT_SIZES.* or lower the ceiling if intentional."
    )


def test_linewidth_literal_count_below_ceiling():
    """Distinct hardcoded linewidth literals must stay under the ceiling."""
    counts = _tally(_LINEWIDTH_RE)
    distinct = sorted(counts)
    assert len(distinct) <= LINEWIDTH_DISTINCT_CEILING, (
        f"distinct linewidth literals ({len(distinct)}) exceeds ceiling "
        f"{LINEWIDTH_DISTINCT_CEILING}. "
        f"Observed values (value → count): "
        f"{sorted(counts.items(), key=lambda kv: -kv[1])}. "
        "Migrate to PF_LINE_WIDTHS.* or lower the ceiling if intentional."
    )
