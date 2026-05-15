#!/usr/bin/env python3
"""Smoke tests for automatic style example discovery."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from agent_runner import _discover_style_examples  # noqa: E402
from models import Project  # noqa: E402


def _write(path: Path, text: str = "# Sample\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_tests() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "notes"
        docs = root / "docs" / "qcqi"
        target = docs / "2.3.md"

        _write(target, "# Target\n")
        _write(docs / "2.2.md")
        _write(docs / "2.1.md")
        _write(docs / "10.1.md")
        _write(docs / "mapping.md")
        _write(docs / "[NC2010]QCQI.md")
        _write(docs / "index.md")
        _write(docs / "blueprints" / "2.1.md")
        _write(docs / "blueprints" / "2.2.md")
        _write(docs / "appendix" / "2.4.md")
        _write(docs / "appendix" / "note.md")

        project = Project(
            id="p1",
            title="Style example test",
            mkdocsRoot=str(root),
            outputPath=str(target),
            createdAt="2026-03-17T00:00:00+00:00",
            updatedAt="2026-03-17T00:00:00+00:00",
        )

        selected = _discover_style_examples(project, max_files=10, search_depth=3)
        rels = [str(path.relative_to(root / "docs")) for path in selected]

        assert rels[:3] == [
            "qcqi/2.2.md",
            "qcqi/2.1.md",
            "qcqi/10.1.md",
        ], rels
        assert set(rels) == {
            "qcqi/2.2.md",
            "qcqi/2.1.md",
            "qcqi/10.1.md",
        }, rels
        assert "qcqi/2.3.md" not in rels
        assert "qcqi/mapping.md" not in rels
        assert "qcqi/[NC2010]QCQI.md" not in rels
        assert "qcqi/index.md" not in rels
        assert "qcqi/blueprints/2.1.md" not in rels
        assert "qcqi/blueprints/2.2.md" not in rels
        assert "qcqi/appendix/2.4.md" not in rels
        assert "qcqi/appendix/note.md" not in rels

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "notes"
        docs = root / "docs"
        parent = docs / "qcqi"
        nested = parent / "section-a"
        target = nested / "2.3.md"

        _write(target, "# Target\n")
        _write(nested / "2.2.md")
        _write(nested / "2.10.md")
        _write(parent / "9.1.md")
        _write(parent / "1.2.md")
        _write(parent / "2.5.md")
        _write(parent / "blueprints" / "2.1.md")
        _write(docs / "3.1.md")

        project = Project(
            id="p2",
            title="Parent walk test",
            mkdocsRoot=str(root),
            outputPath=str(target),
            createdAt="2026-03-17T00:00:00+00:00",
            updatedAt="2026-03-17T00:00:00+00:00",
        )

        selected = _discover_style_examples(project, max_files=10, search_depth=2)
        rels = [str(path.relative_to(root / "docs")) for path in selected]

        assert rels == [
            "qcqi/section-a/2.2.md",
            "qcqi/section-a/2.10.md",
            "qcqi/1.2.md",
            "qcqi/2.5.md",
            "qcqi/9.1.md",
            "3.1.md",
        ], rels
        assert "qcqi/blueprints/2.1.md" not in rels

    print("PASS: style example selection")


if __name__ == "__main__":
    run_tests()
