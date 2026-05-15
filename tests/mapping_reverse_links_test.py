#!/usr/bin/env python3
"""Regression tests for reverse links stored in the shared mapping file."""

from __future__ import annotations

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

from mapping_store import parse_mapping_file  # noqa: E402
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


def test_mapping_file_reverse_links_and_renumber() -> None:
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
                "| Theorem 2.1.1 | **Gram-Schmidt procedure** | 2.1.md |\n"
                "| Example 2.1.2 | **trace identity example** | 2.1.md |\n"
            ),
        )

        project = Project(
            id="p1",
            title="Mapping reverse links",
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
                    document=(
                        '!!! example "Example 2.1.2 : Uses theorem"\n'
                        "    Using the gram-schmidt theorem (**Theorem 2.1.1**), obtain the basis."
                    ),
                ),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        project_routes._save_project(project)

        rows = parse_mapping_file(str(mapping_path))
        theorem_row = next(row for row in rows if row.new_ref == "Theorem 2.1.1")
        example_row = next(row for row in rows if row.new_ref == "Example 2.1.2")
        assert theorem_row.location == "qcqi/2.1.md", theorem_row.location
        assert example_row.location == "qcqi/2.1.md", example_row.location
        assert example_row.references == ["qcqi/2.1.md::Theorem 2.1.1"], example_row.references
        assert theorem_row.referenced_by == ["qcqi/2.1.md::Example 2.1.2"], theorem_row.referenced_by
        assert "References | Referenced by" in mapping_path.read_text(encoding="utf-8")

        current = project_routes._load_project("p1")
        current.items.insert(
            1,
            Item(
                kind="admonition",
                id="def",
                type="definition",
                content="Inserted definition",
                excerpt="definition excerpt",
                document='!!! definition "Definition 2.1.1 : Inserted definition"\n    New entry.',
            ),
        )
        project_routes._save_project(current)

        rows = parse_mapping_file(str(mapping_path))
        theorem_row = next(row for row in rows if row.new_ref == "Theorem 2.1.2")
        example_row = next(row for row in rows if row.new_ref == "Example 2.1.3")
        assert example_row.references == ["qcqi/2.1.md::Theorem 2.1.2"], example_row.references
        assert theorem_row.referenced_by == ["qcqi/2.1.md::Example 2.1.3"], theorem_row.referenced_by


def run_tests() -> None:
    test_mapping_file_reverse_links_and_renumber()
    print("PASS: mapping reverse links")


if __name__ == "__main__":
    run_tests()
