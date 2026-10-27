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


def test_map_sync_selection() -> None:
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
    document_changed = Item(
        kind="admonition",
        id="i4",
        type="lemma",
        content="Document changed",
        excerpt="stable excerpt",
        syncedExcerpt="stable excerpt",
        document="Now references **Theorem 2.1.5**.",
        syncedDocument="Previously referenced nothing.",
        number=5,
        syncedNumber=5,
    )
    no_excerpt_document_changed = Item(
        kind="admonition",
        id="i5",
        type="example",
        content="No excerpt document changed",
        excerpt="",
        syncedExcerpt="",
        document="Now references **Theorem 2.1.5**.",
        syncedDocument="Previously referenced nothing.",
        number=5,
        syncedNumber=4,
    )
    empty_item = Item(
        kind="admonition",
        id="i6",
        type="example",
        content="No excerpt or document",
        excerpt="",
        syncedExcerpt="",
        document="",
        syncedDocument="",
        number=6,
        syncedNumber=5,
    )
    section_changed = Item(
        kind="section",
        id="sec",
        type="h1",
        content="2.1. Section",
        excerpt="section excerpt",
        syncedExcerpt="old section excerpt",
        document="# 2.1. Section",
        syncedDocument="# Old section",
    )

    same_prefix = _project(
        number_prefix="2.1",
        synced_number_prefix="2.1",
        items=[section_changed, excerpt_changed, number_changed, prefix_only, document_changed, no_excerpt_document_changed, empty_item],
    )
    assert unsynced_map_item_ids(same_prefix) == ["sec", "i1", "i2", "i4", "i5"]

    changed_prefix = _project(
        number_prefix="2.2",
        synced_number_prefix="2.1",
        items=[section_changed, excerpt_changed, number_changed, prefix_only, document_changed, no_excerpt_document_changed, empty_item],
    )
    assert unsynced_map_item_ids(changed_prefix) == ["sec", "i1", "i2", "i3", "i4", "i5"]

    assert item_needs_map_sync(
        prefix_only,
        number_prefix="2.2",
        synced_number_prefix="2.1",
    )
    assert not item_needs_map_sync(
        empty_item,
        number_prefix="2.2",
        synced_number_prefix="2.1",
    )


def test_heading_sync_selection() -> None:
    for level in range(1, 7):
        for field in ("excerpt", "document"):
            item = Item(kind="section", id="heading", type=f"h{level}", content="Heading")
            project = _project(number_prefix="2.1", synced_number_prefix="2.1", items=[item])
            assert unsynced_map_item_ids(project) == []

            setattr(item, field, "   \n")
            assert unsynced_map_item_ids(project) == []

            setattr(item, field, f"{'#' * level} Heading")
            assert unsynced_map_item_ids(project) == [item.id]

            item.syncedExcerpt = item.excerpt
            item.syncedDocument = item.document
            assert unsynced_map_item_ids(project) == []

            project.numberPrefix = "2.2"
            assert unsynced_map_item_ids(project) == [item.id]


def run_tests() -> None:
    test_map_sync_selection()
    test_heading_sync_selection()
    print("PASS: sync map selection")


if __name__ == "__main__":
    run_tests()
