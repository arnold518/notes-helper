#!/usr/bin/env python3
"""Regression tests for reverse-link maintenance and downstream repairs."""

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
        def add_task(self, fn, *args, **kwargs):
            return None

    def Query(default=None, **kwargs):
        return default

    fastapi.APIRouter = APIRouter
    fastapi.BackgroundTasks = BackgroundTasks
    fastapi.HTTPException = HTTPException
    fastapi.Query = Query
    sys.modules["fastapi"] = fastapi

import agent_runner  # noqa: E402
from models import Item, Project  # noqa: E402
from routers import agent as agent_routes  # noqa: E402
from routers import projects as project_routes  # noqa: E402
from rules import default_rules  # noqa: E402


def _project_root(tmpdir: str) -> Path:
    root = Path(tmpdir) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    project_routes.PROJECTS_DIR = root
    agent_routes.PROJECTS_DIR = root
    return root


def _make_project(project_id: str, mapping_path: str = "") -> Project:
    return Project(
        id=project_id,
        title="Reverse link test",
        outputPath="/tmp/qcqi/2.1.md",
        mappingPath=mapping_path,
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
                content="Basis theorem",
                document='!!! theorem "Theorem 2.1.1 : Basis theorem"\n    Statement.',
                excerpt="theorem excerpt",
                number=1,
            ),
            Item(
                kind="admonition",
                id="ex",
                type="example",
                content="Uses theorem",
                document=(
                    '!!! example "Example 2.1.2 : Uses theorem"\n'
                    "    Apply **Theorem 2.1.1** to obtain the result."
                ),
                excerpt="example excerpt",
                number=2,
            ),
        ],
        createdAt="2026-03-21T00:00:00+00:00",
        updatedAt="2026-03-21T00:00:00+00:00",
    )


def test_reverse_links_and_renumber() -> None:
    with TemporaryDirectory() as tmpdir:
        _project_root(tmpdir)
        project = _make_project("p1")

        project_routes._save_project(project)
        current = project_routes._load_project("p1")

        theorem = next(item for item in current.items if item.id == "thm")
        example = next(item for item in current.items if item.id == "ex")
        assert example.references == ["thm"], example.references
        assert theorem.referencedBy == ["ex"], theorem.referencedBy

        current.items.insert(
            1,
            Item(
                kind="admonition",
                id="def",
                type="definition",
                content="Inserted first entry",
                document='!!! definition "Definition 2.1.1 : Inserted first entry"\n    New entry.',
                excerpt="definition excerpt",
                number=1,
            ),
        )
        project_routes._save_project(current)

        updated = project_routes._load_project("p1")
        theorem = next(item for item in updated.items if item.id == "thm")
        example = next(item for item in updated.items if item.id == "ex")

        assert theorem.number == 2, theorem.number
        assert "Theorem 2.1.2 : Basis theorem" in theorem.document, theorem.document
        assert "Example 2.1.3 : Uses theorem" in example.document, example.document
        assert "**Theorem 2.1.2**" in example.document, example.document
        assert example.references == ["thm"], example.references
        assert theorem.referencedBy == ["ex"], theorem.referencedBy


def test_default_generate_rules_include_multipart_list_rule() -> None:
    generate_rules = default_rules("generate")
    assert (
        "For a theorem, lemma, proposition, corollary, or proof with multiple labeled parts"
        in generate_rules
    ), generate_rules
    assert (
        "Keep all continuation paragraphs and display math indented so they remain inside the same list item and admonition block."
        in generate_rules
    ), generate_rules


def test_sync_map_regenerates_direct_dependents() -> None:
    with TemporaryDirectory() as tmpdir:
        root = _project_root(tmpdir)
        mapping_path = root / "shared-mapping.md"
        mapping_path.write_text("", encoding="utf-8")
        project = _make_project("p2", mapping_path=str(mapping_path))
        project_routes._save_project(project)

        regenerate_calls: list[tuple[list[str], str]] = []
        original_run_map_update_agent = agent_runner.run_map_update_agent
        original_run_generate_agent = agent_runner.run_generate_agent

        async def fake_run_map_update_agent(**_: object) -> None:
            return None

        async def fake_run_generate_agent(
            *,
            project: Project,
            item_ids: list[str],
            user_prompt: str,
            available_types: list[str],
            stage_dir: str,
            generate_rules_path: str,
            cwd: str,
        ) -> str:
            regenerate_calls.append((item_ids, user_prompt))
            assert item_ids == ["ex"], item_ids
            assert "canonical mapping changed" in user_prompt.lower()
            stage = Path(stage_dir)
            stage.mkdir(parents=True, exist_ok=True)
            (stage / "ex.document").write_text(
                '!!! example "Example 2.1.2 : Uses theorem"\n'
                "    Updated to cite **Theorem 2.1.1** after map sync.",
                encoding="utf-8",
            )
            return "done"

        agent_runner.run_map_update_agent = fake_run_map_update_agent
        agent_runner.run_generate_agent = fake_run_generate_agent
        try:
            asyncio.run(agent_routes._run_sync_map("job-sync", project, "thm"))
        finally:
            agent_runner.run_map_update_agent = original_run_map_update_agent
            agent_runner.run_generate_agent = original_run_generate_agent

        current = project_routes._load_project("p2")
        example = next(item for item in current.items if item.id == "ex")
        assert len(regenerate_calls) == 1, regenerate_calls
        assert regenerate_calls[0][0] == ["ex"], regenerate_calls
        assert "Updated to cite **Theorem 2.1.1** after map sync." in example.document, example.document
        assert agent_routes._jobs["job-sync"]["status"] == "done", agent_routes._jobs["job-sync"]
        assert {"regeneratedItemIds": ["ex"]} in agent_routes._jobs["job-sync"]["result"]


def run_tests() -> None:
    test_reverse_links_and_renumber()
    test_default_generate_rules_include_multipart_list_rule()
    test_sync_map_regenerates_direct_dependents()
    print("PASS: reverse link regression")


if __name__ == "__main__":
    run_tests()
