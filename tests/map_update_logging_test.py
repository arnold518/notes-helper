#!/usr/bin/env python3
"""Regression test for deterministic map sync logging."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import ai_logs as ai_logs_mod  # noqa: E402
from agent_runner import run_map_update_agent  # noqa: E402
from models import Item, Project, ReferenceFile  # noqa: E402


def run_tests() -> None:
    original_projects_dir = ai_logs_mod.PROJECTS_DIR
    try:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ai_logs_mod.PROJECTS_DIR = root / "projects"

            mapping_path = root / "mapping.md"
            source_doc = root / "refs" / "book.md"
            project = Project(
                id="p1",
                title="Deterministic map logging",
                mkdocsRoot=str(root),
                outputPath=str(root / "docs" / "notes" / "2.1.md"),
                mappingPath=str(mapping_path),
                references=[
                    ReferenceFile(
                        id="r1",
                        name="textbook.md",
                        path=str(root / "project_refs" / "textbook.md"),
                        originalPath=str(source_doc),
                    )
                ],
                items=[
                    Item(kind="section", id="sec", type="h1", content="2.1. Linear Algebra"),
                    Item(
                        kind="admonition",
                        id="i1",
                        type="definition",
                        content="complex vector space",
                        excerpt="[textbook.md line 10~12]\n\nA complex vector space is ...",
                        number=1,
                    ),
                ],
                createdAt="2026-03-24T00:00:00+00:00",
                updatedAt="2026-03-24T00:00:00+00:00",
            )

            asyncio.run(
                run_map_update_agent(
                    project=project,
                    item_ids=["i1"],
                    stage_dir="",
                    cwd=str(root),
                    map_rules_path="",
                )
            )

            logs_dir = ai_logs_mod.PROJECTS_DIR / "p1" / "ai_logs"
            logs = sorted(logs_dir.glob("*.json"))
            assert len(logs) == 1, logs
            payload = json.loads(logs[0].read_text(encoding="utf-8"))
            assert payload["runType"] == "map_update"
            assert payload["provider"] == "deterministic"
            assert payload["status"] == "done"
            assert payload["meta"]["deterministic"] is True
            assert payload["meta"]["itemIds"] == ["i1"]
            assert "Deterministic map sync completed without AI fallback." in payload["stdout"]

            rendered = mapping_path.read_text(encoding="utf-8")
            assert "| Definition 2.1.1 | **complex vector space** | notes/2.1.md |" in rendered
    finally:
        ai_logs_mod.PROJECTS_DIR = original_projects_dir

    print("PASS: map update logging")


if __name__ == "__main__":
    run_tests()
