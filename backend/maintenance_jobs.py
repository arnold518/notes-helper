from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from agent_runner import _rules_path, _stage_dir, run_generate_agent, run_map_update_agent
from mkdocs_parser import get_admonition_types
from models import Project
from routers.projects import PROJECTS_DIR, _load_project, _project_path, _save_project


REFERENCE_ONLY_REFRESH_PROMPT = (
    "Treat the current document as canonical. "
    "Update only notes-side cross-references so they match the current canonical mapping and reference style. "
    "Do not add new notes-side references unless they are needed to replace explicit original-source references already present in the excerpt or current document. "
    "Preserve the existing mathematical content, structure, ordering, admonition type/title, and wording unless a small local edit is strictly necessary to repair a reference. "
    "Do not rewrite the note from scratch."
)


def _job_cwd(project: Project) -> str:
    if project.blueprintPath:
        return str(Path(project.blueprintPath).parent)
    return str(PROJECTS_DIR)


def _chunked(values: Sequence[str], size: int) -> Iterable[list[str]]:
    chunk_size = max(1, int(size))
    for start in range(0, len(values), chunk_size):
        yield list(values[start:start + chunk_size])


def _backup_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.rebuild.bak.{stamp}")
    shutil.copyfile(path, backup)
    return str(backup)


def _cleanup_stage_dir(stage_dir: Path) -> None:
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)


def _mapping_rebuild_item_ids(project: Project) -> list[str]:
    return [
        item.id
        for item in project.items
        if item.kind != "text" and item.excerpt.strip()
    ]


def _document_refresh_item_ids(project: Project) -> list[str]:
    return [
        item.id
        for item in project.items
        if item.kind != "section" and item.document.strip()
    ]


def _available_generate_types(project: Project) -> list[str]:
    if not project.mkdocsRoot:
        return []
    try:
        return [entry["type"] for entry in get_admonition_types(project.mkdocsRoot)]
    except Exception:
        return []


async def rebuild_mapping_from_scratch(
    project_id: str,
    *,
    batch_size: int = 20,
    backup: bool = True,
    limit: int | None = None,
) -> dict:
    project = _load_project(project_id)
    if not project.mappingPath:
        raise ValueError(f"Project {project_id} has no mappingPath set")

    mapping_path = Path(project.mappingPath).expanduser().resolve()
    mapping_path.parent.mkdir(parents=True, exist_ok=True)

    project_backup = _backup_file(_project_path(project_id)) if backup else ""
    mapping_backup = _backup_file(mapping_path) if backup else ""

    mapping_path.write_text("", encoding="utf-8")

    item_ids = _mapping_rebuild_item_ids(project)
    if limit is not None:
        item_ids = item_ids[: max(0, int(limit))]
    cwd = _job_cwd(project)
    processed_batches: list[list[str]] = []

    for batch in _chunked(item_ids, batch_size):
        current = _load_project(project_id)
        await run_map_update_agent(
            project=current,
            item_ids=batch,
            stage_dir="",
            cwd=cwd,
            map_rules_path=str(_rules_path(project_id, "map")),
        )
        current = _load_project(project_id)
        synced_set = set(batch)
        for item in current.items:
            if item.id in synced_set:
                item.syncedExcerpt = item.excerpt
                item.syncedNumber = item.number
        current.syncedNumberPrefix = current.numberPrefix
        _save_project(current)
        processed_batches.append(batch)

    return {
        "projectId": project_id,
        "projectBackup": project_backup,
        "mappingBackup": mapping_backup,
        "itemIds": item_ids,
        "batchSize": max(1, int(batch_size)),
        "batches": processed_batches,
    }


async def refresh_documents_from_mapping(
    project_id: str,
    *,
    backup: bool = False,
) -> dict:
    project = _load_project(project_id)
    if not project.mappingPath:
        raise ValueError(f"Project {project_id} has no mappingPath set")

    project_backup = _backup_file(_project_path(project_id)) if backup else ""
    mapping_backup = _backup_file(Path(project.mappingPath).expanduser().resolve()) if backup else ""

    item_ids = _document_refresh_item_ids(project)
    if not item_ids:
        return {
            "projectId": project_id,
            "projectBackup": project_backup,
            "mappingBackup": mapping_backup,
            "itemIds": [],
            "changedItemIds": [],
        }

    available_types = _available_generate_types(project)
    cwd = _job_cwd(project)
    changed_item_ids: list[str] = []

    for item_id in item_ids:
        stage_dir = _stage_dir(project_id, item_id)
        _cleanup_stage_dir(stage_dir)
        stage_dir.mkdir(parents=True, exist_ok=True)
        try:
            current = _load_project(project_id)
            previous_document = next(
                (item.document for item in current.items if item.id == item_id),
                "",
            )
            await run_generate_agent(
                project=current,
                item_ids=[item_id],
                user_prompt=REFERENCE_ONLY_REFRESH_PROMPT,
                available_types=available_types,
                stage_dir=str(stage_dir),
                generate_rules_path=str(_rules_path(project_id, "generate")),
                cwd=cwd,
            )
            stage_file = stage_dir / f"{item_id}.document"
            if not stage_file.exists():
                raise ValueError(f"Agent did not write document for item {item_id}")
            document = stage_file.read_text(encoding="utf-8").strip()
            if previous_document.strip() and not document:
                raise ValueError(f"Reference refresh produced an empty document for item {item_id}")

            current = _load_project(project_id)
            item = next((entry for entry in current.items if entry.id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found during save")
            if item.document.strip() != document:
                item.document = document
                _save_project(current)
                changed_item_ids.append(item_id)
        finally:
            _cleanup_stage_dir(stage_dir)

    return {
        "projectId": project_id,
        "projectBackup": project_backup,
        "mappingBackup": mapping_backup,
        "itemIds": item_ids,
        "changedItemIds": changed_item_ids,
    }
