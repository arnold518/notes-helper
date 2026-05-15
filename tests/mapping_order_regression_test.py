#!/usr/bin/env python3
"""Regression test for mapping row order following project entry order."""

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

from models import Item, Project  # noqa: E402
from agent_runner import _merge_mapping_updates  # noqa: E402
from mapping_store import parse_mapping_file, write_mapping_file  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup_project_root(tmpdir: str) -> None:
    root = Path(tmpdir) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    project_routes.PROJECTS_DIR = root


def run_tests() -> None:
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
                "| Concept 2.1.2 | **matrix representation** | qcqi/2.1.md |\n"
                "| Theorem 2.1.3 | **Exercise 2.6** | qcqi/2.1.md |\n"
                "| Definition 2.1.1 | **complex vector space** | qcqi/2.1.md |\n"
                "| § 2.1.1. Bases and Linear Independence | **2.1.1 Bases and linear independence** | qcqi/2.1.md |\n"
            ),
        )

        project = Project(
            id="p1",
            title="Mapping order regression",
            mkdocsRoot=str(mkdocs_root),
            outputPath=str(output_path),
            mappingPath=str(mapping_path),
            items=[
                Item(kind="section", id="sec", type="h1", content="2.1. Linear Algebra"),
                Item(kind="admonition", id="i1", type="definition", content="complex vector space"),
                Item(kind="section", id="sec2", type="h2", content="2.1.1. Bases and Linear Independence"),
                Item(kind="admonition", id="i2", type="concept", content="matrix representation"),
                Item(kind="admonition", id="i3", type="theorem", content="exercise 2.6"),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        project_routes._save_project(project)

        lines = [
            line
            for line in mapping_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and not line.startswith("| New ref |")
        ]
        assert lines == [
            "| Definition 2.1.1 | **complex vector space** | qcqi/2.1.md |  |  |",
            "| § 2.1.1. Bases and Linear Independence | **2.1.1 Bases and linear independence** | qcqi/2.1.md |  |  |",
            "| Concept 2.1.2 | **matrix representation** | qcqi/2.1.md |  |  |",
            "| Theorem 2.1.3 | **Exercise 2.6** | qcqi/2.1.md |  |  |",
        ], lines

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        mapping_path = root / "mapping.md"
        source_doc = root / "refs" / "[NC2010]QCQI.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location |\n"
                "| --- | --- | --- |\n"
                "| Definition 2.1.1 | **complex vector space** | qcqi/2.1.md |\n"
                "| § 2.1.1. Bases and Linear Independence | **2.1.1 Bases and linear independence** | qcqi/2.1.md |\n"
                "| Concept 2.1.2 | **matrix representation** | qcqi/2.1.md |\n"
                "| Theorem 2.1.3 | **Exercise 2.6** | qcqi/2.1.md |\n"
            ),
        )

        rows = parse_mapping_file(str(mapping_path))
        write_mapping_file(str(mapping_path), rows)

        lines = [
            line
            for line in mapping_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and not line.startswith("| New ref |")
        ]
        assert lines == [
            "| Definition 2.1.1 | **complex vector space** | qcqi/2.1.md |  |  |",
            "| § 2.1.1. Bases and Linear Independence | **2.1.1 Bases and linear independence** | qcqi/2.1.md |  |  |",
            "| Concept 2.1.2 | **matrix representation** | qcqi/2.1.md |  |  |",
            "| Theorem 2.1.3 | **Exercise 2.6** | qcqi/2.1.md |  |  |",
        ], lines

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        mkdocs_root = root / "mkdocs"
        output_path = mkdocs_root / "docs" / "alpha" / "1.md"
        mapping_path = root / "mapping.md"
        source_doc = root / "refs" / "shared.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location | References | Referenced by |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| Definition 9.1 | **zeta first** | zeta/9.md |  |  |\n"
                "| Theorem 9.2 | **zeta second** | zeta/9.md |  |  |\n"
                "| Theorem 1.2 | **alpha second** | alpha/1.md |  |  |\n"
                "| Definition 1.1 | **alpha first** | alpha/1.md |  |  |\n"
            ),
        )

        project = Project(
            id="p3",
            title="Shared map ordering",
            mkdocsRoot=str(mkdocs_root),
            outputPath=str(output_path),
            mappingPath=str(mapping_path),
            items=[
                Item(kind="section", id="sec", type="h1", content="1. Alpha"),
                Item(kind="admonition", id="i1", type="definition", content="alpha first", excerpt="[book.md line 1~1]\n\nalpha first", number=1),
                Item(kind="admonition", id="i2", type="theorem", content="alpha second", excerpt="[book.md line 2~2]\n\nalpha second", number=2),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        _merge_mapping_updates(project, [(str(source_doc), "Definition 1.1", ["alpha first"])])

        lines = [
            line
            for line in mapping_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and not line.startswith("| New ref |")
        ]
        assert lines == [
            "| Definition 9.1 | **zeta first** | zeta/9.md |  |  |",
            "| Theorem 9.2 | **zeta second** | zeta/9.md |  |  |",
            "| Definition 1.1 | **alpha first** | alpha/1.md |  |  |",
            "| Theorem 1.2 | **alpha second** | alpha/1.md |  |  |",
        ], lines

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        mapping_path = root / "mapping.md"
        source_doc = root / "refs" / "shared.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location | References | Referenced by |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| Theorem 1.1 | **same** | alpha/1.md |  |  |\n"
                "| Theorem 1.1 | **same** | alpha/1.md |  |  |\n"
                "| Example 1.2 | **other** | alpha/1.md |  |  |\n"
            ),
        )

        rows = parse_mapping_file(str(mapping_path))
        write_mapping_file(str(mapping_path), rows)

        lines = [
            line
            for line in mapping_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and not line.startswith("| New ref |")
        ]
        assert lines == [
            "| Theorem 1.1 | **same** | alpha/1.md |  |  |",
            "| Example 1.2 | **other** | alpha/1.md |  |  |",
        ], lines

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        mapping_path = root / "mapping.md"
        source_doc = root / "refs" / "shared.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location | References | Referenced by |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| Concept 2.2.32 | **relative phase** | qcqi/2.2.md |  |  |\n"
                "| Concept 2.2.32 | **global phase** | qcqi/2.2.md | qcqi/2.2.md::Definition 2.2.33 |  |\n"
            ),
        )

        rows = parse_mapping_file(str(mapping_path))
        write_mapping_file(str(mapping_path), rows)

        lines = [
            line
            for line in mapping_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and not line.startswith("| New ref |")
        ]
        assert lines == [
            "| Concept 2.2.32 | **relative phase**; **global phase** | qcqi/2.2.md | qcqi/2.2.md::Definition 2.2.33 |  |",
        ], lines

    print("PASS: mapping order regression")


if __name__ == "__main__":
    run_tests()
