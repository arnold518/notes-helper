#!/usr/bin/env python3
"""Regression tests for docs-derived linear algebra mapping sync."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from mapping_store import mapping_locator  # noqa: E402
from sync_linear_algebra_mapping_from_docs import _sync_rows  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_tests() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        docs_dir = root / "docs" / "linear-algebra"
        source_doc = docs_dir / "book.md"
        mapping_path = docs_dir / "mapping.md"

        _write(
            docs_dir / "7.md",
            (
                '# § 7. Test\n\n'
                '!!! definition "Definition 7.4 : Chain of Sets"\n'
                '    Definition body.\n\n'
                '!!! exercise "Exercise 7.4"\n'
                '    Exercise body.\n\n'
                '!!! exercise "Exercise 7.5"\n'
                '    New exercise body.\n'
            ),
        )
        _write(
            docs_dir / "20.md",
            (
                '# § 20. Test\n\n'
                '!!! theorem "Lemma 20.6"\n'
                '    Uses **Exercise 7.4**.\n'
            ),
        )
        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location | References | Referenced by |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| Exercise 7.4 | **Exercise 4** | linear-algebra/7.md |  |  |\n"
                "| Theorem 20.6 | **Lemma source** | linear-algebra/20.md |  |  |\n"
            ),
        )

        result = _sync_rows(docs_dir=docs_dir, mapping_path=mapping_path, through_note=20)
        by_locator = {
            mapping_locator(row.location, row.new_ref): row
            for row in result.rows
        }

        assert mapping_locator("linear-algebra/7.md", "Definition 7.4") in by_locator
        assert mapping_locator("linear-algebra/7.md", "Exercise 7.4") in by_locator
        assert mapping_locator("linear-algebra/7.md", "Exercise 7.5") in by_locator
        assert by_locator[mapping_locator("linear-algebra/7.md", "Definition 7.4")].original_refs == []
        assert by_locator[mapping_locator("linear-algebra/7.md", "Exercise 7.4")].original_refs == ["Exercise 4"]
        assert by_locator[mapping_locator("linear-algebra/7.md", "Exercise 7.5")].original_refs == ["Exercise 5"]
        assert mapping_locator("linear-algebra/20.md", "Lemma 20.6") in by_locator
        assert mapping_locator("linear-algebra/20.md", "Theorem 20.6") not in by_locator
        assert by_locator[mapping_locator("linear-algebra/20.md", "Lemma 20.6")].references == [
            "linear-algebra/7.md::Exercise 7.4"
        ]

        assert result.report["renamed"] == [
            {
                "location": "linear-algebra/20.md",
                "oldRef": "Theorem 20.6",
                "newRef": "Lemma 20.6",
            }
        ]
        assert {
            "location": "linear-algebra/7.md",
            "newRef": "Exercise 7.5",
            "line": "9",
            "originalRefs": "Exercise 5",
        } in result.report["added"]

    print("PASS: docs mapping sync")


if __name__ == "__main__":
    run_tests()
