#!/usr/bin/env python3
"""Regression tests for mapping updates after generate/edit saves."""

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

    class BackgroundTasks:
        def add_task(self, *args, **kwargs):
            return None

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

    def Query(default=None, **kwargs):
        return default

    fastapi.APIRouter = APIRouter
    fastapi.BackgroundTasks = BackgroundTasks
    fastapi.HTTPException = HTTPException
    fastapi.Query = Query
    sys.modules["fastapi"] = fastapi

import agent_runner  # noqa: E402
from mapping_store import parse_mapping_file  # noqa: E402
from models import EditRequest, GenerateRequest, Item, Project  # noqa: E402
from routers import agent as agent_routes  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup_project_root(tmpdir: str) -> None:
    root = Path(tmpdir) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    project_routes.PROJECTS_DIR = root
    agent_routes.PROJECTS_DIR = root


def _make_project(tmpdir: str, *, example_document: str = "") -> Project:
    root = Path(tmpdir)
    mkdocs_root = root / "mkdocs"
    output_path = mkdocs_root / "docs" / "qcqi" / "2.1.md"
    mapping_path = root / "mapping.md"
    source_doc = root / "refs" / "[NC2010]QCQI.md"

    _write(
        mapping_path,
        (
            f"## Reference: {source_doc}\n\n"
            "| New ref | Original ref | Location |\n"
            "| --- | --- | --- |\n"
            "| Theorem 2.1.1 | **Gram-Schmidt procedure** | qcqi/2.1.md |\n"
            "| Example 2.1.2 | **trace identity example** | qcqi/2.1.md |\n"
        ),
    )

    project = Project(
        id="p1",
        title="Generate/edit mapping sync",
        mkdocsRoot=str(mkdocs_root),
        outputPath=str(output_path),
        mappingPath=str(mapping_path),
        items=[
            Item(
                kind="section",
                id="sec",
                type="h1",
                content="2.1. Linear Algebra",
                document="# 2.1. Linear Algebra",
            ),
            Item(
                kind="admonition",
                id="thm",
                type="theorem",
                content="Gram-Schmidt",
                excerpt="theorem excerpt",
                document='!!! theorem "Theorem 2.1.1 : Gram-Schmidt"\n    Statement.',
            ),
            Item(
                kind="admonition",
                id="ex",
                type="example",
                content="Uses theorem",
                excerpt="example excerpt",
                document=example_document,
            ),
        ],
        createdAt="2026-03-22T00:00:00+00:00",
        updatedAt="2026-03-22T00:00:00+00:00",
    )
    project_routes._save_project(project)
    return project


def test_generate_updates_mapping_reverse_links() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
        _make_project(tmpdir)

        original_run_generate_agent = agent_runner.run_generate_agent

        async def fake_run_generate_agent(**kwargs) -> str:
            stage_dir = Path(str(kwargs["stage_dir"]))
            stage_dir.mkdir(parents=True, exist_ok=True)
            _write(
                stage_dir / "ex.document",
                (
                    '!!! example "Example 2.1.2 : Uses theorem"\n'
                    "    Using the gram-schmidt theorem (**Theorem 2.1.1**), obtain the basis."
                ),
            )
            return "done"

        agent_runner.run_generate_agent = fake_run_generate_agent
        try:
            asyncio.run(
                agent_routes._run_generate(
                    "job-generate",
                    project_routes._load_project("p1"),
                    GenerateRequest(itemId="ex"),
                )
            )
        finally:
            agent_runner.run_generate_agent = original_run_generate_agent

        rows = parse_mapping_file(str(Path(tmpdir) / "mapping.md"))
        theorem_row = next(row for row in rows if row.new_ref == "Theorem 2.1.1")
        example_row = next(row for row in rows if row.new_ref == "Example 2.1.2")
        assert example_row.references == ["qcqi/2.1.md::Theorem 2.1.1"], example_row.references
        assert theorem_row.referenced_by == ["qcqi/2.1.md::Example 2.1.2"], theorem_row.referenced_by


def test_edit_updates_mapping_reverse_links() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
        _make_project(
            tmpdir,
            example_document='!!! example "Example 2.1.2 : Uses theorem"\n    Obtain the basis.',
        )

        original_run_edit_agent = agent_runner.run_edit_agent

        async def fake_run_edit_agent(**kwargs) -> str:
            stage_dir = Path(str(kwargs["stage_dir"]))
            stage_dir.mkdir(parents=True, exist_ok=True)
            _write(
                stage_dir / "ex.document",
                (
                    '!!! example "Example 2.1.2 : Uses theorem"\n'
                    "    Using the gram-schmidt theorem (**Theorem 2.1.1**), obtain the basis."
                ),
            )
            return "done"

        agent_runner.run_edit_agent = fake_run_edit_agent
        try:
            asyncio.run(
                agent_routes._run_edit(
                    "job-edit",
                    project_routes._load_project("p1"),
                    EditRequest(
                        itemId="ex",
                        target="document",
                        userPrompt="Update the notes-side references.",
                    ),
                )
            )
        finally:
            agent_runner.run_edit_agent = original_run_edit_agent

        rows = parse_mapping_file(str(Path(tmpdir) / "mapping.md"))
        theorem_row = next(row for row in rows if row.new_ref == "Theorem 2.1.1")
        example_row = next(row for row in rows if row.new_ref == "Example 2.1.2")
        assert example_row.references == ["qcqi/2.1.md::Theorem 2.1.1"], example_row.references
        assert theorem_row.referenced_by == ["qcqi/2.1.md::Example 2.1.2"], theorem_row.referenced_by


def run_tests() -> None:
    test_generate_updates_mapping_reverse_links()
    test_edit_updates_mapping_reverse_links()
    print("PASS: generate/edit mapping sync")


if __name__ == "__main__":
    run_tests()
