"""Agent job endpoints: trigger match/generate/prepare, poll status."""
from __future__ import annotations
import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from ai_logs import list_ai_logs, read_ai_log
from models import JobStatus, Project, MatchRequest, GenerateRequest, EditRequest, SyncMapRequest
from routers.projects import _load_project, _save_project, PROJECTS_DIR

router = APIRouter(tags=["agent"])

# In-memory job store: job_id → JobStatus dict
_jobs: dict[str, dict[str, Any]] = {}

# Per-project locks to serialize project.json load-modify-save
_project_save_locks: dict[str, asyncio.Lock] = {}

def _project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_save_locks:
        _project_save_locks[project_id] = asyncio.Lock()
    return _project_save_locks[project_id]


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
    unsynced_ids = [
        it.id for it in project.items
        if it.excerpt and it.excerpt != it.syncedExcerpt
    ]
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


async def _run_match(job_id: str, project: Project, req: MatchRequest) -> None:
    from agent_runner import run_match_agent, run_map_update_agent, _stage_dir, _rules_path

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

        for iid in item_ids:
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

                async with _project_lock(project.id):
                    current = _load_project(project.id)
                    item = next((it for it in current.items if it.id == iid), None)
                    if item is not None:
                        item.excerpt = excerpt
                        _save_project(current)
                        results.append({"id": iid, "excerpt": item.excerpt, "status": item.status})
                        succeeded_ids.append(iid)
            except Exception as e:
                item_errors.append(f"{iid}: {e}")
            finally:
                _cleanup_stage_dir(stage_dir)

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
    from mkdocs_parser import get_admonition_types

    cwd = str(Path(project.blueprintPath).parent) if project.blueprintPath else str(PROJECTS_DIR)
    available_types = []
    if project.mkdocsRoot:
        try:
            adm_types = get_admonition_types(project.mkdocsRoot)
            available_types = [t["type"] for t in adm_types]
        except Exception:
            pass

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

        for iid in item_ids:
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
                        results.append({"id": iid, "document": item.document, "status": item.status})
            except Exception as e:
                item_errors.append(f"{iid}: {e}")
            finally:
                _cleanup_stage_dir(stage_dir)

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
        _jobs[job_id] = {"status": "done", "result": [{"itemId": item_id}], "error": None}
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
        _jobs[job_id] = {"status": "done", "result": [{"itemIds": item_ids}], "error": None}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}


@router.get("/api/projects/{project_id}/rules/{kind}")
def get_rules(project_id: str, kind: str) -> dict:
    if kind not in ("match", "generate", "map"):
        raise HTTPException(status_code=400, detail="kind must be 'match' or 'generate'")
    _load_project(project_id)  # ensures rules files exist
    from agent_runner import _rules_path
    path = _rules_path(project_id, kind)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Rules file not found: {path}")
    return {"kind": kind, "content": path.read_text(encoding="utf-8")}


@router.put("/api/projects/{project_id}/rules/{kind}")
def put_rules(project_id: str, kind: str, body: dict) -> dict:
    if kind not in ("match", "generate", "map"):
        raise HTTPException(status_code=400, detail="kind must be 'match' or 'generate'")
    content = body.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    _load_project(project_id)
    from agent_runner import _rules_path
    path = _rules_path(project_id, kind)
    path.write_text(content, encoding="utf-8")
    return {"kind": kind, "content": content}
