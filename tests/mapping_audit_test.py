#!/usr/bin/env python3
"""Regression tests for subject mapping audits."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from mapping_audit import audit_subject_mapping, format_audit_report  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_tests() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        projects_dir = root / "projects"
        mapping_path = root / "site" / "docs" / "linear-algebra" / "mapping.md"
        source_doc = root / "refs" / "book.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location | References | Referenced by |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| Definition 2.1 | **vector space** | linear-algebra/2.md |  |  |\n"
                "| Theorem 2.99 | **stale theorem** | linear-algebra/2.md |  |  |\n"
                "| Example 9.1 | **orphan example** | linear-algebra/9.md |  |  |\n"
            ),
        )
        _write_json(
            projects_dir / "_subjects" / "linear-algebra.json",
            {
                "id": "linear-algebra",
                "name": "Linear Algebra",
                "mappingPath": str(mapping_path),
                "createdAt": "2026-05-25T00:00:00+00:00",
                "updatedAt": "2026-05-25T00:00:00+00:00",
            },
        )
        _write_json(
            projects_dir / "la02" / "project.json",
            {
                "id": "la02",
                "title": "[Linear Algebra] § 2. Vector Spaces",
                "mkdocsRoot": str(root / "site"),
                "outputPath": str(root / "site" / "docs" / "linear-algebra" / "2.md"),
                "mappingPath": str(mapping_path),
                "numberPrefix": "2",
                "createdAt": "2026-05-25T00:00:00+00:00",
                "updatedAt": "2026-05-25T00:00:00+00:00",
                "items": [
                    {
                        "kind": "section",
                        "id": "s1",
                        "type": "h1",
                        "content": "2. Vector Spaces",
                    },
                    {
                        "kind": "admonition",
                        "id": "i1",
                        "type": "definition",
                        "content": "Vector Space",
                        "number": 1,
                    },
                    {
                        "kind": "admonition",
                        "id": "i2",
                        "type": "theorem",
                        "content": "Missing theorem",
                        "number": 2,
                        "excerpt": "source excerpt",
                    },
                ],
            },
        )

        report = audit_subject_mapping(projects_dir, "linear-algebra")
        assert report["projectCount"] == 1
        assert report["mappingRowCount"] == 3
        assert report["totals"]["excerptedItems"] == 1
        assert report["totals"]["mappedAdmonitions"] == 1
        assert report["totals"]["missingAdmonitions"] == 1
        assert report["projects"][0]["missingAdmonitions"] == ["Theorem 2.2"]
        assert [row["newRef"] for row in report["staleRows"]] == ["Theorem 2.99"]
        assert [row["newRef"] for row in report["orphanRows"]] == ["Example 9.1"]

        rendered = format_audit_report(report)
        assert "Admonition coverage: 1/2 mapped, 1 missing" in rendered
        assert "Theorem 2.2" in rendered
        assert "Theorem 2.99" in rendered

    print("PASS: mapping audit")


if __name__ == "__main__":
    run_tests()
