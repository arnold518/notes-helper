#!/usr/bin/env python3
"""Regression test for subject project natural numeric ordering."""

from __future__ import annotations

import sys
import types
from pathlib import Path

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

from routers import subjects as subject_routes  # noqa: E402


def _project_data(project_id: str, title: str) -> dict:
    return {
        "id": project_id,
        "subjectId": "linear-algebra",
        "title": title,
        "createdAt": "2026-01-01T00:00:00+00:00",
        "updatedAt": "2026-01-01T00:00:00+00:00",
        "outputPath": f"/notes/{project_id}.md",
        "items": [],
    }


def test_subject_projects_sort_numerically() -> None:
    paths = [Path("p10.json"), Path("p2.json"), Path("p1_10.json"), Path("p1_2.json")]
    data_by_path = {
        paths[0]: _project_data("p10", "[Linear Algebra] § 10. Composition"),
        paths[1]: _project_data("p2", "[Linear Algebra] § 2. Vector Spaces"),
        paths[2]: _project_data("p1_10", "[Linear Algebra] § 1.10. Later"),
        paths[3]: _project_data("p1_2", "[Linear Algebra] § 1.2. Earlier"),
    }

    original_get_subject = subject_routes._get_subject
    original_project_file_candidates = subject_routes._project_file_candidates
    original_load_project_data = subject_routes._load_project_data
    original_project_belongs_to_subject = subject_routes._project_belongs_to_subject
    try:
        subject_routes._get_subject = lambda subject_id: object()
        subject_routes._project_file_candidates = lambda: paths
        subject_routes._load_project_data = lambda path: data_by_path[path]
        subject_routes._project_belongs_to_subject = lambda project, subject_id: True

        projects = subject_routes.list_subject_projects("linear-algebra")
    finally:
        subject_routes._get_subject = original_get_subject
        subject_routes._project_file_candidates = original_project_file_candidates
        subject_routes._load_project_data = original_load_project_data
        subject_routes._project_belongs_to_subject = original_project_belongs_to_subject

    assert [project["id"] for project in projects] == ["p1_2", "p1_10", "p2", "p10"], projects


def run_tests() -> None:
    test_subject_projects_sort_numerically()
    print("PASS: subject project numeric sort")


if __name__ == "__main__":
    run_tests()
