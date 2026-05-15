#!/usr/bin/env python3
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

from models import Project  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _setup_project_root(tmpdir: str) -> Path:
    root = Path(tmpdir) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    project_routes.PROJECTS_DIR = root
    return root


def test_remove_reference_deletes_project_copy_and_readd_reuses_name() -> None:
    with TemporaryDirectory() as tmpdir:
        _setup_project_root(tmpdir)
        external = Path(tmpdir) / "external" / "textbook.md"
        _write(external, "# External textbook\n")

        project = Project(
            id="prefcleanup",
            title="Reference cleanup",
            createdAt="2026-03-23T00:00:00+00:00",
            updatedAt="2026-03-23T00:00:00+00:00",
        )
        project_routes._save_project(project)

        updated = project_routes.add_reference(
            "prefcleanup",
            {"name": "textbook.md", "path": str(external)},
        )
        assert len(updated.references) == 1
        first_ref = updated.references[0]
        first_local_path = Path(first_ref.path)
        assert first_local_path.exists()
        assert first_local_path.name == "textbook.md"
        assert external.exists()

        updated = project_routes.remove_reference("prefcleanup", first_ref.id)
        assert updated.references == []
        assert not first_local_path.exists()
        assert external.exists()

        updated = project_routes.add_reference(
            "prefcleanup",
            {"name": "textbook.md", "path": str(external)},
        )
        assert len(updated.references) == 1
        second_ref = updated.references[0]
        second_local_path = Path(second_ref.path)
        assert second_local_path.exists()
        assert second_local_path.name == "textbook.md"
        assert not (second_local_path.parent / "textbook_2.md").exists()


if __name__ == "__main__":
    test_remove_reference_deletes_project_copy_and_readd_reuses_name()
    print("PASS: reference file cleanup")
