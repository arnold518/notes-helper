"""Agent job endpoints: trigger match/generate/prepare, poll status."""
from __future__ import annotations
import asyncio
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from ai_conversation import (
    append_ai_message,
    load_ai_conversation,
    update_ai_message,
)
from ai_logs import list_ai_logs, read_ai_log
from backend_config import load_backend_config
from mapping_store import dependent_item_ids_from_mapping
from map_sync import unsynced_map_item_ids
from models import (
    AiCommandRequest,
    AiConversationThread,
    EditRequest,
    GenerateRequest,
    JobStatus,
    MatchRequest,
    Project,
    SyncMapRequest,
)
from routers.projects import _load_project, _save_project, PROJECTS_DIR

router = APIRouter(tags=["agent"])

# In-memory job store: job_id → JobStatus dict
_jobs: dict[str, dict[str, Any]] = {}

# Per-project locks to serialize project.json load-modify-save
_project_save_locks: dict[str, asyncio.Lock] = {}
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
_SNAPSHOT_SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "site",
}

def _project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_save_locks:
        _project_save_locks[project_id] = asyncio.Lock()
    return _project_save_locks[project_id]


def _bulk_worker_count() -> int:
    cfg = load_backend_config()
    return max(1, min(int(cfg.agent.worker_count), int(cfg.agent.max_concurrency)))


def _snapshot_display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_WORKSPACE_ROOT))
    except Exception:
        return str(path.resolve())


def _iter_workspace_snapshot_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            name for name in dirnames
            if name not in _SNAPSHOT_SKIP_DIRS and name not in {"ai_logs", "stage"}
        ]
        for filename in filenames:
            path = current / filename
            if path.name == "ai_conversation.json":
                continue
            files.append(path)
    return files


def _project_snapshot_paths(project: Project) -> list[Path]:
    extras: set[Path] = {
        PROJECTS_DIR / project.id / "project.json",
        PROJECTS_DIR / project.id / "ai_conversation.json",
    }
    for raw in [
        project.blueprintPath,
        project.mappingPath,
        project.outputPath,
    ]:
        if raw:
            extras.add(Path(os.path.abspath(os.path.expanduser(raw))))
    for ref in project.references:
        for raw in [ref.path, ref.originalPath]:
            if raw:
                extras.add(Path(os.path.abspath(os.path.expanduser(raw))))
    return sorted(extras)


def _snapshot_state(project: Project) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    paths = _iter_workspace_snapshot_files(_WORKSPACE_ROOT)
    extras = _project_snapshot_paths(project)
    seen = {path.resolve() for path in paths}
    for extra in extras:
        try:
            resolved = extra.resolve()
        except Exception:
            resolved = extra
        if resolved not in seen:
            paths.append(extra)
            seen.add(resolved)
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        if not path.is_file():
            continue
        snapshot[str(path.resolve())] = (int(stat.st_size), int(stat.st_mtime_ns))
    return snapshot


def _changed_files(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> list[str]:
    changed: list[str] = []
    keys = set(before) | set(after)
    for key in sorted(keys):
        if before.get(key) != after.get(key):
            changed.append(_snapshot_display_path(Path(key)))
    return changed


async def _run_with_workers(
    item_ids: list[str],
    *,
    worker_count: int,
    worker_fn: Callable[[str], Awaitable[None]],
) -> None:
    if not item_ids:
        return
    if worker_count <= 1:
        for iid in item_ids:
            await worker_fn(iid)
        return

    queue: asyncio.Queue[str] = asyncio.Queue()
    for iid in item_ids:
        queue.put_nowait(iid)

    async def worker() -> None:
        while True:
            try:
                iid = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await worker_fn(iid)
            finally:
                queue.task_done()

    tasks = [
        asyncio.create_task(worker())
        for _ in range(min(worker_count, len(item_ids)))
    ]
    await queue.join()
    await asyncio.gather(*tasks)


def _get_job(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.get("/api/jobs/{job_id}")
def poll_job(job_id: str) -> JobStatus:
    return JobStatus(**_get_job(job_id))


@router.get("/api/projects/{project_id}/ai-logs")
def list_project_ai_logs(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    _load_project(project_id)
    return list_ai_logs(project_id, limit=limit)


@router.get("/api/projects/{project_id}/ai-logs/{log_id}")
def get_project_ai_log(project_id: str, log_id: str) -> dict:
    _load_project(project_id)
    try:
        return read_ai_log(project_id, log_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="AI log not found")


@router.get("/api/projects/{project_id}/ai-conversation")
def get_project_ai_conversation(project_id: str) -> AiConversationThread:
    _load_project(project_id)
    return load_ai_conversation(project_id)


@router.post("/api/projects/{project_id}/ai-command")
def start_ai_command(
    project_id: str,
    background_tasks: BackgroundTasks,
    req: AiCommandRequest,
) -> dict:
    project = _load_project(project_id)
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    job_id = uuid.uuid4().hex[:16]
    user_message = append_ai_message(
        project_id,
        role="user",
        content=message,
        status="done",
    )
    assistant_message = append_ai_message(
        project_id,
        role="assistant",
        content="",
        status="running",
        job_id=job_id,
    )
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_ai_command, job_id, project, message, assistant_message.id)
    return {
        "job_id": job_id,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
    }


@router.post("/api/projects/{project_id}/match")
def start_match(project_id: str, background_tasks: BackgroundTasks, req: MatchRequest = None) -> dict:
    if req is None:
        req = MatchRequest()
    project = _load_project(project_id)
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_match, job_id, project, req)
    return {"job_id": job_id}


@router.post("/api/projects/{project_id}/generate")
def start_generate(project_id: str, background_tasks: BackgroundTasks, req: GenerateRequest = None) -> dict:
    if req is None:
        req = GenerateRequest()
    project = _load_project(project_id)
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_generate, job_id, project, req)
    return {"job_id": job_id}


@router.post("/api/projects/{project_id}/edit")
def start_edit(project_id: str, background_tasks: BackgroundTasks, req: EditRequest = None) -> dict:
    if req is None:
        req = EditRequest()
    if not req.itemId:
        raise HTTPException(status_code=400, detail="itemId is required")
    project = _load_project(project_id)
    if not any(it.id == req.itemId for it in project.items):
        raise HTTPException(status_code=404, detail="Item not found")
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_edit, job_id, project, req)
    return {"job_id": job_id}


@router.post("/api/projects/{project_id}/sync-map")
def start_sync_map(project_id: str, background_tasks: BackgroundTasks, req: SyncMapRequest) -> dict:
    project = _load_project(project_id)
    if not project.mappingPath:
        raise HTTPException(status_code=400, detail="Project has no mappingPath set")
    if not any(it.id == req.itemId for it in project.items):
        raise HTTPException(status_code=404, detail="Item not found")
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_sync_map, job_id, project, req.itemId)
    return {"job_id": job_id}


@router.post("/api/projects/{project_id}/sync-map-all")
def start_sync_map_all(project_id: str, background_tasks: BackgroundTasks) -> dict:
    project = _load_project(project_id)
    if not project.mappingPath:
        raise HTTPException(status_code=400, detail="Project has no mappingPath set")
    unsynced_ids = unsynced_map_item_ids(project)
    job_id = uuid.uuid4().hex[:16]
    if not unsynced_ids:
        _jobs[job_id] = {"status": "done", "result": [], "error": None}
        return {"job_id": job_id}
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_sync_map_all, job_id, project, unsynced_ids)
    return {"job_id": job_id}


@router.post("/api/projects/{project_id}/references/{ref_id}/prepare")
def start_prepare(project_id: str, ref_id: str, background_tasks: BackgroundTasks) -> dict:
    project = _load_project(project_id)
    ref = next((r for r in project.references if r.id == ref_id), None)
    if ref is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_prepare, job_id, project, ref_id)
    return {"job_id": job_id}


def _cleanup_stage_dir(stage_dir: Path) -> None:
    try:
        if stage_dir.exists():
            shutil.rmtree(stage_dir)
    except Exception:
        pass


def _direct_referencing_item_ids(project: Project, target_item_ids: list[str]) -> list[str]:
    target_set = set(target_item_ids)
    impacted: list[str] = []
    for item in project.items:
        if item.id in target_set:
            continue
        if any(ref_id in target_set for ref_id in item.references):
            impacted.append(item.id)
    return impacted


def _available_generate_types(project: Project) -> list[str]:
    if not project.mkdocsRoot:
        return []
    try:
        from mkdocs_parser import get_admonition_types
        adm_types = get_admonition_types(project.mkdocsRoot)
        return [t["type"] for t in adm_types]
    except Exception:
        return []


async def _regenerate_reference_dependents(
    project_id: str,
    changed_item_ids: list[str],
    *,
    cwd: str,
) -> tuple[list[str], list[str]]:
    from agent_runner import run_generate_agent, _stage_dir, _rules_path

    current = _load_project(project_id)
    impacted_item_ids = dependent_item_ids_from_mapping(current, changed_item_ids)
    if not impacted_item_ids:
        impacted_item_ids = _direct_referencing_item_ids(current, changed_item_ids)
    if not impacted_item_ids:
        return [], []

    available_types = _available_generate_types(current)
    regenerated_ids: list[str] = []
    errors: list[str] = []
    user_prompt = (
        "The canonical mapping changed for one or more referenced entries. "
        "Regenerate this note so its notes-side cross-references match the current mapping. "
        "Preserve the existing mathematical content and structure unless the excerpt requires a change."
    )

    for iid in impacted_item_ids:
        stage_dir = _stage_dir(project_id, iid)
        _cleanup_stage_dir(stage_dir)
        stage_dir.mkdir(parents=True, exist_ok=True)
        try:
            current = _load_project(project_id)
            await run_generate_agent(
                project=current,
                item_ids=[iid],
                user_prompt=user_prompt,
                available_types=available_types,
                stage_dir=str(stage_dir),
                generate_rules_path=str(_rules_path(project_id, "generate")),
                cwd=cwd,
            )
            stage_file = stage_dir / f"{iid}.document"
            if not stage_file.exists() or not stage_file.read_text(encoding="utf-8").strip():
                raise ValueError(f"Agent did not write document for dependent item {iid}")
            document = stage_file.read_text(encoding="utf-8").strip()

            async with _project_lock(project_id):
                current = _load_project(project_id)
                item = next((it for it in current.items if it.id == iid), None)
                if item is None:
                    raise ValueError(f"Dependent item {iid} not found during save")
                item.document = document
                _save_project(current)
            regenerated_ids.append(iid)
        except Exception as e:
            errors.append(f"{iid}: {e}")
        finally:
            _cleanup_stage_dir(stage_dir)

    return regenerated_ids, errors


async def _run_ai_command(
    job_id: str,
    project: Project,
    message: str,
    assistant_message_id: str,
) -> None:
    from agent_runner import run_ai_command_agent

    cwd = str(_WORKSPACE_ROOT)
    before = _snapshot_state(project)
    try:
        history = load_ai_conversation(project.id).messages[:-1]
        reply = await run_ai_command_agent(
            project=project,
            user_message=message,
            history=history,
            cwd=cwd,
        )
        project_file_display = _snapshot_display_path(PROJECTS_DIR / project.id / "project.json")
        interim_after = _snapshot_state(project)
        interim_changed_files = _changed_files(before, interim_after)
        if project_file_display in interim_changed_files:
            async with _project_lock(project.id):
                current = _load_project(project.id)
                _save_project(current)
        after = _snapshot_state(project)
        changed_files = _changed_files(before, after)
        update_ai_message(
            project.id,
            assistant_message_id,
            content=(reply or "").strip() or "Completed with no textual response.",
            status="done",
            changed_files=changed_files,
        )
        _jobs[job_id] = {
            "status": "done",
            "result": [{"messageId": assistant_message_id, "changedFiles": changed_files}],
            "error": None,
        }
    except Exception as exc:
        after = _snapshot_state(project)
        changed_files = _changed_files(before, after)
        update_ai_message(
            project.id,
            assistant_message_id,
            content="",
            status="error",
            changed_files=changed_files,
            error=str(exc),
        )
        _jobs[job_id] = {"status": "error", "result": None, "error": str(exc)}


async def _run_match(job_id: str, project: Project, req: MatchRequest) -> None:
    from agent_runner import (
        _normalize_excerpt_reference_headers,
        run_match_agent,
        run_map_update_agent,
        _stage_dir,
        _rules_path,
    )

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    try:
        if req.itemId:
            item_ids = [req.itemId]
        else:
            item_ids = [it.id for it in project.items]

        if not item_ids:
            _jobs[job_id] = {"status": "done", "result": [], "error": None}
            return

        results = []
        succeeded_ids: list[str] = []
        item_errors: list[str] = []
        item_order = {iid: idx for idx, iid in enumerate(item_ids)}
        worker_count = 1 if req.itemId else _bulk_worker_count()
        results_lock = asyncio.Lock()

        async def process_item(iid: str) -> None:
            stage_dir = _stage_dir(project.id, iid)
            _cleanup_stage_dir(stage_dir)
            stage_dir.mkdir(parents=True, exist_ok=True)
            try:
                current = _load_project(project.id)
                await run_match_agent(
                    project=current,
                    item_ids=[iid],
                    user_prompt=req.userPrompt or "",
                    stage_dir=str(stage_dir),
                    match_rules_path=str(_rules_path(project.id, "match")),
                    cwd=cwd,
                )
                stage_file = stage_dir / f"{iid}.excerpt"
                if not stage_file.exists() or not stage_file.read_text(encoding="utf-8").strip():
                    raise ValueError(f"Agent did not write excerpt for item {iid}")
                excerpt = stage_file.read_text(encoding="utf-8").strip()
                excerpt = _normalize_excerpt_reference_headers(current, excerpt)

                async with _project_lock(project.id):
                    current = _load_project(project.id)
                    item = next((it for it in current.items if it.id == iid), None)
                    if item is not None:
                        item.excerpt = excerpt
                        _save_project(current)
                        result = {"id": iid, "excerpt": item.excerpt, "status": item.status}
                    else:
                        raise ValueError(f"Item {iid} not found during save")
                async with results_lock:
                    results.append(result)
                    succeeded_ids.append(iid)
            except Exception as e:
                async with results_lock:
                    item_errors.append(f"{iid}: {e}")
            finally:
                _cleanup_stage_dir(stage_dir)

        await _run_with_workers(
            item_ids,
            worker_count=worker_count,
            worker_fn=process_item,
        )
        results.sort(key=lambda row: item_order.get(str(row.get("id")), len(item_order)))

        # Update numbering map after all items matched
        if succeeded_ids:
            current = _load_project(project.id)
            if current.mappingPath:
                try:
                    await run_map_update_agent(
                        project=current,
                        item_ids=succeeded_ids,
                        stage_dir="",
                        cwd=cwd,
                        map_rules_path=str(_rules_path(project.id, "map")),
                    )
                    # Stamp syncedExcerpt/syncedNumber/syncedNumberPrefix on success
                    current = _load_project(project.id)
                    for it in current.items:
                        if it.id in succeeded_ids:
                            it.syncedExcerpt = it.excerpt
                            it.syncedNumber = it.number
                    current.syncedNumberPrefix = current.numberPrefix
                    _save_project(current)
                    _, regen_errors = await _regenerate_reference_dependents(
                        project.id,
                        succeeded_ids,
                        cwd=cwd,
                    )
                    item_errors.extend(regen_errors)
                except Exception:
                    pass  # mapping update is best-effort

        if item_errors and not results:
            _jobs[job_id] = {"status": "error", "result": None, "error": "; ".join(item_errors)}
        else:
            err = ("; ".join(item_errors)) if item_errors else None
            _jobs[job_id] = {"status": "done", "result": results, "error": err}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}


async def _run_generate(job_id: str, project: Project, req: GenerateRequest) -> None:
    from agent_runner import run_generate_agent, _stage_dir, _rules_path

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    available_types = _available_generate_types(project)

    try:
        if req.itemId:
            item_ids = [req.itemId]
        else:
            item_ids = [it.id for it in project.items]

        if not item_ids:
            _jobs[job_id] = {"status": "done", "result": [], "error": None}
            return

        results = []
        item_errors: list[str] = []
        item_order = {iid: idx for idx, iid in enumerate(item_ids)}
        worker_count = 1 if req.itemId else _bulk_worker_count()
        results_lock = asyncio.Lock()

        async def process_item(iid: str) -> None:
            stage_dir = _stage_dir(project.id, iid)
            _cleanup_stage_dir(stage_dir)
            stage_dir.mkdir(parents=True, exist_ok=True)
            try:
                current = _load_project(project.id)
                await run_generate_agent(
                    project=current,
                    item_ids=[iid],
                    user_prompt=req.userPrompt or "",
                    available_types=available_types,
                    stage_dir=str(stage_dir),
                    generate_rules_path=str(_rules_path(project.id, "generate")),
                    cwd=cwd,
                )
                stage_file = stage_dir / f"{iid}.document"
                if not stage_file.exists() or not stage_file.read_text(encoding="utf-8").strip():
                    raise ValueError(f"Agent did not write document for item {iid}")
                document = stage_file.read_text(encoding="utf-8").strip()

                async with _project_lock(project.id):
                    current = _load_project(project.id)
                    item = next((it for it in current.items if it.id == iid), None)
                    if item is not None:
                        item.document = document
                        _save_project(current)
                        result = {"id": iid, "document": item.document, "status": item.status}
                    else:
                        raise ValueError(f"Item {iid} not found during save")
                async with results_lock:
                    results.append(result)
            except Exception as e:
                async with results_lock:
                    item_errors.append(f"{iid}: {e}")
            finally:
                _cleanup_stage_dir(stage_dir)

        await _run_with_workers(
            item_ids,
            worker_count=worker_count,
            worker_fn=process_item,
        )
        results.sort(key=lambda row: item_order.get(str(row.get("id")), len(item_order)))

        if item_errors and not results:
            _jobs[job_id] = {"status": "error", "result": None, "error": "; ".join(item_errors)}
        else:
            err = ("; ".join(item_errors)) if item_errors else None
            _jobs[job_id] = {"status": "done", "result": results, "error": err}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}


async def _run_prepare(job_id: str, project: Project, ref_id: str) -> None:
    from agent_runner import run_prepare_agent, run_section_extract_agent, SectionNotFound

    try:
        ref = next((r for r in project.references if r.id == ref_id), None)
        if ref is None:
            raise ValueError(f"Reference {ref_id} not found")

        cwd = str(Path(ref.path).parent)

        # Step 1: section extraction (full-textbook case); skip if not applicable.
        prep_path = ref.path
        try:
            extracted_path = await run_section_extract_agent(project, ref.path, cwd)
            prep_path = extracted_path
            cwd = str(Path(extracted_path).parent)
        except SectionNotFound:
            pass  # No extraction needed; OCR correction runs on the original file

        # Step 2: OCR correction on the (possibly extracted) file.
        updated_path = await run_prepare_agent(
            project_id=project.id,
            ref_path=prep_path,
            cwd=cwd,
        )
        project = _load_project(project.id)
        for r in project.references:
            if r.id == ref_id:
                r.prepared = True
                r.path = updated_path
                r.name = Path(updated_path).name
                break
        _save_project(project)
        _jobs[job_id] = {"status": "done", "result": [{"path": updated_path}], "error": None}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}


async def _run_edit(job_id: str, project: Project, req: EditRequest) -> None:
    from agent_runner import run_edit_agent, _stage_dir, _rules_path

    if not req.itemId:
        _jobs[job_id] = {"status": "error", "result": None, "error": "itemId is required"}
        return

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    stage_dir = _stage_dir(project.id, req.itemId)
    try:
        source_item = next((it for it in project.items if it.id == req.itemId), None)
        if source_item is None:
            raise ValueError(f"Item {req.itemId} not found")
        original_text = (
            req.content
            if req.content is not None
            else (source_item.excerpt if req.target == "excerpt" else source_item.document)
        )

        _cleanup_stage_dir(stage_dir)
        stage_dir.mkdir(parents=True, exist_ok=True)

        rules_kind = "match" if req.target == "excerpt" else "generate"
        await run_edit_agent(
            project=project,
            item_id=req.itemId,
            target=req.target,
            original_text=original_text,
            user_prompt=req.userPrompt,
            stage_dir=str(stage_dir),
            rules_path=str(_rules_path(project.id, rules_kind)),
            cwd=cwd,
        )

        stage_file = stage_dir / f"{req.itemId}.{req.target}"
        if not stage_file.exists():
            raise ValueError(f"Agent did not write result file at {stage_file}")
        edited_text = stage_file.read_text(encoding="utf-8").strip()
        if original_text.strip() and not edited_text:
            raise ValueError("Edit result is empty; refusing to overwrite existing content")

        project = _load_project(project.id)
        item = next((it for it in project.items if it.id == req.itemId), None)
        if item is None:
            raise ValueError(f"Item {req.itemId} not found during save")
        if req.target == "excerpt":
            item.excerpt = edited_text
        else:
            item.document = edited_text
        _save_project(project)
        _jobs[job_id] = {
            "status": "done",
            "result": [{"id": req.itemId, "target": req.target}],
            "error": None,
        }
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}
    finally:
        _cleanup_stage_dir(stage_dir)


async def _run_sync_map(job_id: str, project: Project, item_id: str) -> None:
    from agent_runner import run_map_update_agent, _rules_path

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    try:
        current = _load_project(project.id)
        await run_map_update_agent(
            project=current,
            item_ids=[item_id],
            stage_dir="",
            cwd=cwd,
            map_rules_path=str(_rules_path(project.id, "map")),
        )
        # Stamp syncedExcerpt/syncedNumber/syncedNumberPrefix on success
        current = _load_project(project.id)
        for it in current.items:
            if it.id == item_id:
                it.syncedExcerpt = it.excerpt
                it.syncedNumber = it.number
                break
        current.syncedNumberPrefix = current.numberPrefix
        _save_project(current)
        regenerated_ids, regen_errors = await _regenerate_reference_dependents(
            project.id,
            [item_id],
            cwd=cwd,
        )
        result = [{"itemId": item_id}]
        if regenerated_ids:
            result.append({"regeneratedItemIds": regenerated_ids})
        _jobs[job_id] = {
            "status": "done",
            "result": result,
            "error": "; ".join(regen_errors) if regen_errors else None,
        }
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}


async def _run_sync_map_all(job_id: str, project: Project, item_ids: list[str]) -> None:
    from agent_runner import run_map_update_agent, _rules_path

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    try:
        current = _load_project(project.id)
        await run_map_update_agent(
            project=current,
            item_ids=item_ids,
            stage_dir="",
            cwd=cwd,
            map_rules_path=str(_rules_path(project.id, "map")),
        )
        current = _load_project(project.id)
        synced_set = set(item_ids)
        for it in current.items:
            if it.id in synced_set:
                it.syncedExcerpt = it.excerpt
                it.syncedNumber = it.number
        current.syncedNumberPrefix = current.numberPrefix
        _save_project(current)
        regenerated_ids, regen_errors = await _regenerate_reference_dependents(
            project.id,
            item_ids,
            cwd=cwd,
        )
        result = [{"itemIds": item_ids}]
        if regenerated_ids:
            result.append({"regeneratedItemIds": regenerated_ids})
        _jobs[job_id] = {
            "status": "done",
            "result": result,
            "error": "; ".join(regen_errors) if regen_errors else None,
        }
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}
