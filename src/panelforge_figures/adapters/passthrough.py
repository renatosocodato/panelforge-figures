"""Passthrough adapter — returns the raw `source` value unchanged.

Used for demo/testing pipelines where the 'source' is already the in-memory
object the recipe wants (e.g. a DataFrame constructed in-code).
"""

from __future__ import annotations

from typing import Any


def load_passthrough(source: Any, **_: Any) -> Any:
    return source
