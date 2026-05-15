#!/usr/bin/env python3
"""Regression tests for standalone maintenance jobs."""

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

    fastapi.APIRouter = APIRouter
    fastapi.HTTPException = HTTPException
    sys.modules["fastapi"] = fastapi

import maintenance_jobs  # noqa: E402
from models import Item, Project  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup_project_root(tmpdir: str) -> Path:
    root = Path(tmpdir) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    project_routes.PROJECTS_DIR = root
    return root


def test_rebuild_mapping_from_scratch_batches_and_stamps() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
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
                "| Old ref | **old source** | qcqi/2.1.md |\n"
            ),
        )

        project = Project(
            id="p1",
            title="Standalone rebuild",
            mkdocsRoot=str(mkdocs_root),
            outputPath=str(output_path),
            mappingPath=str(mapping_path),
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
                    type="definition",
                    content="Pauli matrices",
                    excerpt="definition excerpt",
                ),
                Item(
                    kind="admonition",
                    id="i2",
                    type="theorem",
                    content="Gram-Schmidt",
                    excerpt="theorem excerpt",
                ),
                Item(
                    kind="admonition",
                    id="i3",
                    type="example",
                    content="Trace identity",
                    excerpt="example excerpt",
                ),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        project_routes._save_project(project)

        calls: list[list[str]] = []
        original_run_map_update_agent = maintenance_jobs.run_map_update_agent

        async def fake_run_map_update_agent(
            project: Project,
            item_ids: list[str],
            stage_dir: str,
            cwd: str,
            map_rules_path: str = "",
        ) -> None:
            calls.append(list(item_ids))
            existing = mapping_path.read_text(encoding="utf-8") if mapping_path.exists() else ""
            lines: list[str] = []
            if not existing.strip():
                lines.append(
                    f"## Reference: {source_doc}\n\n"
                    "| New ref | Original ref | Location |\n"
                    "| --- | --- | --- |\n"
                )
            for item_id in item_ids:
                item = next(entry for entry in project.items if entry.id == item_id)
                lines.append(
                    f"| {item.type.capitalize()} 2.1.{item.number} | **{item.content}** | qcqi/2.1.md |\n"
                )
            with mapping_path.open("a", encoding="utf-8") as handle:
                handle.write("".join(lines))

        maintenance_jobs.run_map_update_agent = fake_run_map_update_agent
        try:
            result = asyncio.run(
                maintenance_jobs.rebuild_mapping_from_scratch(
                    "p1",
                    batch_size=2,
                    backup=True,
                )
            )
        finally:
            maintenance_jobs.run_map_update_agent = original_run_map_update_agent

        current = project_routes._load_project("p1")
        assert calls == [["i1", "i2"], ["i3"]]
        assert current.numberPrefix == "2.1"
        assert current.syncedNumberPrefix == "2.1"
        for item in current.items:
            if item.id not in {"i1", "i2", "i3"}:
                continue
            assert item.syncedExcerpt == item.excerpt
            assert item.syncedNumber == item.number
        assert Path(result["projectBackup"]).exists()
        assert Path(result["mappingBackup"]).exists()


def test_rebuild_mapping_from_scratch_limit() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
        root = Path(tmpdir)
        mkdocs_root = root / "mkdocs"
        output_path = mkdocs_root / "docs" / "qcqi" / "2.1.md"
        mapping_path = root / "mapping.md"

        project = Project(
            id="p_limit",
            title="Standalone rebuild limit",
            mkdocsRoot=str(mkdocs_root),
            outputPath=str(output_path),
            mappingPath=str(mapping_path),
            items=[
                Item(kind="section", id="sec", type="h1", content="2.1. Linear Algebra"),
                Item(kind="admonition", id="i1", type="definition", content="One", excerpt="one"),
                Item(kind="admonition", id="i2", type="theorem", content="Two", excerpt="two"),
                Item(kind="admonition", id="i3", type="example", content="Three", excerpt="three"),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        project_routes._save_project(project)

        calls: list[list[str]] = []
        original_run_map_update_agent = maintenance_jobs.run_map_update_agent

        async def fake_run_map_update_agent(
            project: Project,
            item_ids: list[str],
            stage_dir: str,
            cwd: str,
            map_rules_path: str = "",
        ) -> None:
            calls.append(list(item_ids))
            mapping_path.write_text("", encoding="utf-8")

        maintenance_jobs.run_map_update_agent = fake_run_map_update_agent
        try:
            result = asyncio.run(
                maintenance_jobs.rebuild_mapping_from_scratch(
                    "p_limit",
                    batch_size=20,
                    backup=False,
                    limit=2,
                )
            )
        finally:
            maintenance_jobs.run_map_update_agent = original_run_map_update_agent

        assert calls == [["i1", "i2"]]
        assert result["itemIds"] == ["i1", "i2"]


def test_refresh_documents_from_mapping_uses_minimal_prompt() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
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
            ),
        )

        project = Project(
            id="p2",
            title="Reference-only refresh",
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
                    id="i1",
                    type="theorem",
                    content="Gram-Schmidt",
                    excerpt="theorem excerpt",
                    document='!!! theorem "Theorem 2.1.1 : Gram-Schmidt"\n    Statement.',
                ),
                Item(
                    kind="admonition",
                    id="i2",
                    type="example",
                    content="Trace identity",
                    excerpt="example excerpt",
                    document="",
                ),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        project_routes._save_project(project)

        calls: list[tuple[list[str], str]] = []
        original_run_generate_agent = maintenance_jobs.run_generate_agent

        async def fake_run_generate_agent(
            project: Project,
            item_ids: list[str],
            user_prompt: str,
            available_types: list[str],
            stage_dir: str,
            generate_rules_path: str,
            cwd: str,
        ) -> str:
            calls.append((list(item_ids), user_prompt))
            item = next(entry for entry in project.items if entry.id == item_ids[0])
            stage_file = Path(stage_dir) / f"{item.id}.document"
            stage_file.parent.mkdir(parents=True, exist_ok=True)
            stage_file.write_text(
                item.document + "\n    Using the current mapping (**Theorem 2.1.1**).",
                encoding="utf-8",
            )
            return "done"

        maintenance_jobs.run_generate_agent = fake_run_generate_agent
        try:
            result = asyncio.run(maintenance_jobs.refresh_documents_from_mapping("p2"))
        finally:
            maintenance_jobs.run_generate_agent = original_run_generate_agent

        current = project_routes._load_project("p2")
        item = next(entry for entry in current.items if entry.id == "i1")
        untouched = next(entry for entry in current.items if entry.id == "i2")

        assert calls == [(["i1"], maintenance_jobs.REFERENCE_ONLY_REFRESH_PROMPT)]
        assert item.document.endswith("Using the current mapping (**Theorem 2.1.1**).")
        assert untouched.document == ""
        assert result["changedItemIds"] == ["i1"]


if __name__ == "__main__":
    test_rebuild_mapping_from_scratch_batches_and_stamps()
    test_rebuild_mapping_from_scratch_limit()
    test_refresh_documents_from_mapping_uses_minimal_prompt()
