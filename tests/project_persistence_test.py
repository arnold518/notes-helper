#!/usr/bin/env python3
"""Project snapshots stay readable during overlapping and failed saves."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from models import Item, Project  # noqa: E402
from routers import projects as project_routes  # noqa: E402


def _project(version: int) -> Project:
    token = f"snapshot-{version}"
    return Project(
        id="persistence-test",
        subjectId="abstract-algebra",
        title=token,
        items=[Item(
            kind="text", id="i0", type="", content="Saved text",
            document=token * (1000 + version * 11),
        )],
        createdAt="2026-10-26T00:00:00+00:00",
        updatedAt="2026-10-26T00:00:00+00:00",
    )


class ProjectPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory(prefix="notes-helper-persistence-")
        self.addCleanup(self.temp.cleanup)
        root_patch = patch.object(project_routes, "PROJECTS_DIR", Path(self.temp.name))
        root_patch.start()
        self.addCleanup(root_patch.stop)
        project_routes._save_project(_project(0))
        self.path = project_routes._project_path("persistence-test")

    def assert_complete_snapshot(self) -> None:
        project = project_routes._load_project("persistence-test")
        version = int(project.title.removeprefix("snapshot-"))
        self.assertEqual(project.items[0].document, _project(version).items[0].document)

    def test_concurrent_saves_publish_complete_snapshots(self) -> None:
        writer_count = 4
        start = threading.Barrier(writer_count + 1)

        def write_snapshots(writer: int) -> None:
            start.wait(timeout=10)
            for iteration in range(30):
                project_routes._save_project(_project(1 + writer * 30 + iteration))

        with ThreadPoolExecutor(max_workers=writer_count) as pool:
            futures = [pool.submit(write_snapshots, writer) for writer in range(writer_count)]
            start.wait(timeout=10)
            reads = 0
            while not all(future.done() for future in futures):
                self.assert_complete_snapshot()
                reads += 1
            for future in futures:
                future.result(timeout=10)
        self.assertGreater(reads, 0)
        self.assert_complete_snapshot()
        self.assertEqual(list(self.path.parent.glob(".project-*.tmp")), [])

    def test_failed_commit_keeps_previous_snapshot_and_allows_retry(self) -> None:
        previous = self.path.read_bytes()
        with patch.object(project_routes.os, "replace", side_effect=OSError("commit failed")):
            with self.assertRaisesRegex(OSError, "commit failed"):
                project_routes._save_project(_project(1))
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob(".project-*.tmp")), [])
        project_routes._save_project(_project(1))
        self.assertEqual(json.loads(self.path.read_text())["title"], "snapshot-1")
        self.assert_complete_snapshot()

    def test_failed_flush_keeps_previous_snapshot(self) -> None:
        previous = self.path.read_bytes()
        with patch.object(project_routes.os, "fsync", side_effect=OSError("flush failed")):
            with self.assertRaisesRegex(OSError, "flush failed"):
                project_routes._save_project(_project(1))
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob(".project-*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
