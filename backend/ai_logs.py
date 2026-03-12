"""Persistent per-project AI run logs."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", Path(__file__).parent / "projects"))
MAX_TEXT_CHARS = 300_000
_SAFE_LOG_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def _project_logs_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "ai_logs"


def _log_path(project_id: str, log_id: str) -> Path:
    return _project_logs_dir(project_id) / f"{log_id}.json"


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n\n...[truncated {omitted} chars]..."


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def create_ai_log(
    project_id: str,
    *,
    run_type: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    cwd: str,
    command: list[str],
    prompt: str,
    started_at: str,
    status: str = "running",
    meta: dict[str, Any] | None = None,
) -> str:
    log_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex[:8]}"
    payload: dict[str, Any] = {
        "id": log_id,
        "projectId": project_id,
        "runType": run_type,
        "provider": provider,
        "model": model,
        "reasoningEffort": reasoning_effort,
        "cwd": cwd,
        "command": command,
        "prompt": _truncate(prompt),
        "status": status,
        "startedAt": started_at,
        "finishedAt": "",
        "durationMs": 0,
        "stdout": "",
        "stderr": "",
    }
    if meta:
        payload["meta"] = meta
    _write_json_atomic(_log_path(project_id, log_id), payload)
    return log_id


def update_ai_log(project_id: str, log_id: str, **fields: Any) -> None:
    safe_id = Path(log_id).name
    if not _SAFE_LOG_ID.match(safe_id):
        raise FileNotFoundError("Invalid log id")
    path = _log_path(project_id, safe_id)
    payload: dict[str, Any]
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"id": safe_id, "projectId": project_id}

    for k, v in fields.items():
        if v is None:
            payload.pop(k, None)
            continue
        if k in {"prompt", "stdout", "stderr", "error"} and isinstance(v, str):
            payload[k] = _truncate(v)
        else:
            payload[k] = v

    _write_json_atomic(path, payload)


def write_ai_log(
    project_id: str,
    *,
    run_type: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    cwd: str,
    command: list[str],
    prompt: str,
    started_at: str,
    finished_at: str,
    duration_ms: int,
    status: str,
    stdout: str,
    stderr: str,
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    log_id = create_ai_log(
        project_id,
        run_type=run_type,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        cwd=cwd,
        command=command,
        prompt=prompt,
        started_at=started_at,
        status="running",
        meta=meta,
    )
    update_ai_log(
        project_id,
        log_id,
        status=status,
        finishedAt=finished_at,
        durationMs=duration_ms,
        stdout=stdout,
        stderr=stderr,
        error=error,
    )
    return log_id


def list_ai_logs(project_id: str, limit: int = 100) -> list[dict[str, Any]]:
    logs_dir = _project_logs_dir(project_id)
    if not logs_dir.exists():
        return []

    files = sorted(logs_dir.glob("*.json"), key=lambda p: p.name, reverse=True)
    cap = max(1, min(limit, 500))
    out: list[dict[str, Any]] = []
    for path in files[:cap]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
            out.append({
                "id": str(raw.get("id") or path.stem),
                "runType": str(raw.get("runType") or ""),
                "status": str(raw.get("status") or ""),
                "provider": str(raw.get("provider") or ""),
                "model": str(raw.get("model") or ""),
                "reasoningEffort": str(raw.get("reasoningEffort") or ""),
                "startedAt": str(raw.get("startedAt") or ""),
                "finishedAt": str(raw.get("finishedAt") or ""),
                "durationMs": int(raw.get("durationMs") or 0),
                "error": str(raw.get("error") or ""),
                "itemIds": meta.get("itemIds"),
                "referencePath": meta.get("referencePath"),
            })
        except Exception:
            continue
    return out


def read_ai_log(project_id: str, log_id: str) -> dict[str, Any]:
    safe_id = Path(log_id).name
    if not _SAFE_LOG_ID.match(safe_id):
        raise FileNotFoundError("Invalid log id")
    path = _log_path(project_id, safe_id)
    if not path.exists():
        raise FileNotFoundError(f"Log not found: {log_id}")
    return json.loads(path.read_text(encoding="utf-8"))
