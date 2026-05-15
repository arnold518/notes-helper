"""Persistent per-project AI conversation threads."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import AiConversationMessage, AiConversationThread

PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", Path(__file__).parent.parent / "projects"))


def _thread_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "ai_conversation.json"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_ai_conversation(project_id: str) -> AiConversationThread:
    path = _thread_path(project_id)
    if not path.exists():
        return AiConversationThread(messages=[])
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        raw_messages = []
    return AiConversationThread(messages=[AiConversationMessage(**row) for row in raw_messages])


def save_ai_conversation(project_id: str, thread: AiConversationThread) -> AiConversationThread:
    _write_json_atomic(_thread_path(project_id), thread.model_dump())
    return thread


def append_ai_message(
    project_id: str,
    *,
    role: str,
    content: str = "",
    status: str = "done",
    job_id: str = "",
    changed_files: list[str] | None = None,
    error: str = "",
) -> AiConversationMessage:
    now = datetime.now(timezone.utc).isoformat()
    message = AiConversationMessage(
        id=uuid.uuid4().hex[:16],
        role=role,
        content=content,
        status=status,
        createdAt=now,
        updatedAt=now,
        jobId=job_id,
        changedFiles=list(changed_files or []),
        error=error,
    )
    thread = load_ai_conversation(project_id)
    thread.messages.append(message)
    save_ai_conversation(project_id, thread)
    return message


def update_ai_message(project_id: str, message_id: str, **fields: Any) -> AiConversationMessage:
    thread = load_ai_conversation(project_id)
    target: AiConversationMessage | None = None
    for message in thread.messages:
        if message.id == message_id:
            target = message
            break
    if target is None:
        raise FileNotFoundError(f"AI conversation message not found: {message_id}")

    payload = target.model_dump()
    for key, value in fields.items():
        if key == "job_id":
            payload["jobId"] = value or ""
        elif key == "changed_files":
            payload["changedFiles"] = list(value or [])
        elif key in {"content", "status", "error"}:
            payload[key] = value or ""
        elif key in {"jobId", "changedFiles"}:
            payload[key] = value
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()

    updated = AiConversationMessage(**payload)
    index = thread.messages.index(target)
    thread.messages[index] = updated
    save_ai_conversation(project_id, thread)
    return updated
