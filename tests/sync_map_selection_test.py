#!/usr/bin/env python3
"""Regression tests for map sync selection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from map_sync import item_needs_map_sync, unsynced_map_item_ids  # noqa: E402
from models import Item, Project  # noqa: E402


def _project(*, number_prefix: str, synced_number_prefix: str, items: list[Item]) -> Project:
    return Project(
        id="p1",
        title="Sync selection test",
        numberPrefix=number_prefix,
        syncedNumberPrefix=synced_number_prefix,
        items=items,
        createdAt="2026-03-17T00:00:00+00:00",
        updatedAt="2026-03-17T00:00:00+00:00",
    )


def run_tests() -> None:
    excerpt_changed = Item(
        kind="admonition",
        id="i1",
        type="definition",
        content="Excerpt changed",
        excerpt="new excerpt",
        syncedExcerpt="old excerpt",
        number=1,
        syncedNumber=1,
    )
    number_changed = Item(
        kind="admonition",
        id="i2",
        type="theorem",
        content="Number changed",
        excerpt="stable excerpt",
        syncedExcerpt="stable excerpt",
        number=3,
        syncedNumber=2,
    )
    prefix_only = Item(
        kind="admonition",
        id="i3",
        type="concept",
        content="Prefix only",
        excerpt="stable excerpt",
        syncedExcerpt="stable excerpt",
        number=4,
        syncedNumber=4,
    )
    no_excerpt = Item(
        kind="admonition",
        id="i4",
        type="example",
        content="No excerpt",
        excerpt="",
        syncedExcerpt="",
        number=5,
        syncedNumber=4,
    )

    same_prefix = _project(
        number_prefix="2.1",
        synced_number_prefix="2.1",
        items=[excerpt_changed, number_changed, prefix_only, no_excerpt],
    )
    assert unsynced_map_item_ids(same_prefix) == ["i1", "i2"]

    changed_prefix = _project(
        number_prefix="2.2",
        synced_number_prefix="2.1",
        items=[excerpt_changed, number_changed, prefix_only, no_excerpt],
    )
    assert unsynced_map_item_ids(changed_prefix) == ["i1", "i2", "i3"]

    assert item_needs_map_sync(
        prefix_only,
        number_prefix="2.2",
        synced_number_prefix="2.1",
    )
    assert not item_needs_map_sync(
        no_excerpt,
        number_prefix="2.2",
        synced_number_prefix="2.1",
    )

    print("PASS: sync map selection")


if __name__ == "__main__":
    run_tests()
