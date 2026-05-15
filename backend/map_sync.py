from __future__ import annotations

from models import Item, Project


def item_needs_map_sync(
    item: Item,
    *,
    number_prefix: str,
    synced_number_prefix: str,
) -> bool:
    return bool(item.excerpt) and (
        item.excerpt != item.syncedExcerpt
        or item.number != item.syncedNumber
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
