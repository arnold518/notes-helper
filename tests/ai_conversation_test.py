#!/usr/bin/env python3
"""Regression tests for project-level AI conversation storage and prompts."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

if "fastapi" not in sys.modules:
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return lambda fn: fn

        def post(self, *args, **kwargs):
            return lambda fn: fn

        def put(self, *args, **kwargs):
            return lambda fn: fn

        def patch(self, *args, **kwargs):
            return lambda fn: fn

        def delete(self, *args, **kwargs):
            return lambda fn: fn

    class BackgroundTasks:
        def add_task(self, *args, **kwargs):
            pass

    def Query(default=None, **kwargs):
        return default

    fastapi.APIRouter = APIRouter
    fastapi.BackgroundTasks = BackgroundTasks
    fastapi.HTTPException = HTTPException
    fastapi.Query = Query
    sys.modules["fastapi"] = fastapi

import agent_runner  # noqa: E402
import ai_conversation  # noqa: E402
from models import AiConversationMessage, Project, ReferenceFile  # noqa: E402


def test_ai_conversation_roundtrip() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "projects"
        root.mkdir(parents=True, exist_ok=True)
        ai_conversation.PROJECTS_DIR = root

        user = ai_conversation.append_ai_message("p1", role="user", content="Inspect the map")
        assistant = ai_conversation.append_ai_message(
            "p1",
            role="assistant",
            status="running",
            job_id="job123",
        )
        ai_conversation.update_ai_message(
            "p1",
            assistant.id,
            content="Updated the rules.",
            status="done",
            changed_files=["backend/routers/projects.py"],
        )

        thread = ai_conversation.load_ai_conversation("p1")
        assert len(thread.messages) == 2
        assert thread.messages[0].id == user.id
        assert thread.messages[1].jobId == "job123"
        assert thread.messages[1].content == "Updated the rules."
        assert thread.messages[1].changedFiles == ["backend/routers/projects.py"]


def test_run_ai_command_agent_prompt_includes_history_and_context() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        project = Project(
            id="p1",
            title="AI command prompt test",
            blueprintPath=str(root / "docs" / "blueprint.md"),
            mappingPath=str(root / "docs" / "mapping.md"),
            outputPath=str(root / "docs" / "qcqi" / "2.1.md"),
            mkdocsRoot=str(root / "mkdocs"),
            references=[
                ReferenceFile(
                    id="r1",
                    name="textbook.md",
                    path=str(root / "refs" / "textbook.md"),
                    originalPath=str(root / "refs" / "[NC2010]QCQI.md"),
                )
            ],
            createdAt="2026-03-22T00:00:00+00:00",
            updatedAt="2026-03-22T00:00:00+00:00",
        )

        history = [
            AiConversationMessage(
                id="m1",
                role="user",
                content="Inspect the project.",
                status="done",
                createdAt="2026-03-22T00:00:00+00:00",
                updatedAt="2026-03-22T00:00:00+00:00",
            ),
            AiConversationMessage(
                id="m2",
                role="assistant",
                content="I checked the rules.",
                status="done",
                createdAt="2026-03-22T00:00:01+00:00",
                updatedAt="2026-03-22T00:00:01+00:00",
            ),
        ]

        prompts: list[tuple[str, str]] = []
        original_run_agent = agent_runner.run_agent

        async def fake_run_agent(
            prompt: str,
            cwd: str,
            provider: str = "claude",
            model: str = "",
            reasoning_effort: str = "",
            project_id: str = "",
            run_type: str = "agent",
            log_meta: dict | None = None,
        ) -> str:
            prompts.append((run_type, prompt))
            return "Done."

        agent_runner.run_agent = fake_run_agent
        try:
            result = asyncio.run(
                agent_runner.run_ai_command_agent(
                    project=project,
                    user_message="Update the frontend tab labels.",
                    history=history,
                    cwd=str(root),
                )
            )
        finally:
            agent_runner.run_agent = original_run_agent

        assert result == "Done."
        assert len(prompts) == 1
        assert prompts[0][0] == "ai_command"
        prompt = prompts[0][1]
        assert "Project context:" in prompt
        assert "Conversation so far:" in prompt
        assert "Inspect the project." in prompt
        assert "I checked the rules." in prompt
        assert "Current user message:" in prompt
        assert "Update the frontend tab labels." in prompt
        assert "Work like a local Codex session" in prompt
        assert "item.excerpt and item.document fields directly" in prompt


if __name__ == "__main__":
    test_ai_conversation_roundtrip()
    test_run_ai_command_agent_prompt_includes_history_and_context()
    print("PASS: ai conversation")
