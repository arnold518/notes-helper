#!/usr/bin/env python3
"""Regression test for unified raw AI conversation command path."""

from __future__ import annotations

import asyncio
import json
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

import ai_conversation  # noqa: E402
import agent_runner  # noqa: E402
from models import Item, Project  # noqa: E402
from routers import agent as agent_routes  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def test_raw_ai_command_edits_project_file_and_normalizes() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        projects_dir = root / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        project_routes.PROJECTS_DIR = projects_dir
        agent_routes.PROJECTS_DIR = projects_dir
        ai_conversation.PROJECTS_DIR = projects_dir

        project = Project(
            id="p1",
            title="Raw AI command",
            items=[
                Item(
                    kind="section",
                    id="sec",
                    type="h1",
                    content="2.1. Linear Algebra",
                ),
                Item(
                    kind="admonition",
                    id="i1",
                    type="theorem",
                    content="Bra ket theorem",
                    document="!!! theorem \"Theorem 2.1.1 : Test\"\n    For any vector $\\ket{\\psi}$, ...",
                ),
            ],
            createdAt="2026-03-22T00:00:00+00:00",
            updatedAt="2026-03-22T00:00:00+00:00",
        )
        project_routes._save_project(project)
        before = project_routes._load_project("p1")

        assistant = ai_conversation.append_ai_message(
            "p1",
            role="assistant",
            content="",
            status="running",
            job_id="job1",
        )

        project_file = projects_dir / "p1" / "project.json"
        original_run_ai_command_agent = agent_runner.run_ai_command_agent

        async def fake_run_ai_command_agent(
            project: Project,
            user_message: str,
            history: list,
            cwd: str,
        ) -> str:
            payload = json.loads(project_file.read_text(encoding="utf-8"))
            payload["items"][1]["document"] = payload["items"][1]["document"].replace("\\ket{\\psi}", "|\\psi\\rangle")
            project_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return "Updated the canonical project document."

        agent_runner.run_ai_command_agent = fake_run_ai_command_agent
        try:
            asyncio.run(
                agent_routes._run_ai_command(
                    "job1",
                    project,
                    "Check the bra-ket notations for latex in the document. Unify the notation.",
                    assistant.id,
                )
            )
        finally:
            agent_runner.run_ai_command_agent = original_run_ai_command_agent

        updated = project_routes._load_project("p1")
        item = next(it for it in updated.items if it.id == "i1")
        assert "|\\psi\\rangle" in item.document
        assert "\\ket{\\psi}" not in item.document
        assert updated.updatedAt != before.updatedAt

        thread = ai_conversation.load_ai_conversation("p1")
        final_message = next(msg for msg in thread.messages if msg.id == assistant.id)
        assert final_message.status == "done"
        assert "Updated the canonical project document." in final_message.content
        assert any(path.endswith("projects/p1/project.json") for path in final_message.changedFiles), final_message.changedFiles


if __name__ == "__main__":
    test_raw_ai_command_edits_project_file_and_normalizes()
    print("PASS: ai command project file")
