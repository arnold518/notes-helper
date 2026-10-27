from __future__ import annotations

from models import Item, Project


def item_has_map_surface(item: Item) -> bool:
    return bool((item.excerpt or "").strip() or (item.document or "").strip())


def item_needs_map_sync(
    item: Item,
    *,
    number_prefix: str,
    synced_number_prefix: str,
) -> bool:
    return item_has_map_surface(item) and (
        item.excerpt != item.syncedExcerpt
        or item.number != item.syncedNumber
        or item.document != item.syncedDocument
        or number_prefix != synced_number_prefix
    )


def unsynced_map_item_ids(project: Project) -> list[str]:
    return [
        item.id
        for item in project.items
        if item_needs_map_sync(
            item,
            number_prefix=project.numberPrefix,
            synced_number_prefix=project.syncedNumberPrefix,
        )
    ]
