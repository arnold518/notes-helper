#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from import_existing_notes import split_existing_markdown_into_items  # noqa: E402
from mapping_store import MappingRow, parse_mapping_file, write_mapping_file  # noqa: E402
from models import Project, ReferenceFile  # noqa: E402
from routers.projects import _load_project, _save_project  # noqa: E402


DEFAULT_SOURCE_DOCS = Path("/home/arnold/arnold/github/math-notes/docs/linear-algebra")
DEFAULT_SOURCE_MKDOCS_ROOT = Path("/home/arnold/arnold/github/math-notes")
DEFAULT_SOURCE_BOOK = DEFAULT_SOURCE_DOCS / (
    "Stephen H. Friedberg, Arnold J. Insel, Lawrence E. Spence - "
    "Linear Algebra (Part 1) (1).md"
)
DEFAULT_LEGACY_MAP = DEFAULT_SOURCE_DOCS / "ORIGINAL_TO_NOTES_NUMBERING_MAP.md"

_VALID_NEW_REF_RE = (
    r"^(?:Definition|Theorem|Corollary|Lemma|Example|Exercise|Concept|Proposition)\b"
)

MANUAL_NOTE_MAPS: dict[int, list[tuple[str, list[str]]]] = {
    8: [
        ("Definition 8.1", ["Definition (linear transformation)"]),
        ("Concept 8.2", ["Properties 1-4 of linear transformation"]),
        ("Example 8.3", ["Example 2"]),
        ("Example 8.4", ["Example 3"]),
        ("Example 8.5", ["Example 4"]),
        ("Example 8.6", ["Example 6"]),
        ("Example 8.7", ["Example 7"]),
        ("Definition 8.8", ["Identity transformation", "Zero transformation"]),
        ("Definition 8.9", ["Null space", "Range"]),
        ("Theorem 8.10", ["Theorem 2.1"]),
        ("Theorem 8.11", ["Theorem 2.2"]),
        ("Definition 8.12", ["Nullity", "Rank"]),
        ("Theorem 8.13", ["Theorem 2.3"]),
        ("Theorem 8.14", ["Theorem 2.4"]),
        ("Theorem 8.15", ["Theorem 2.5"]),
        ("Theorem 8.16", ["Exercise 14"]),
        ("Theorem 8.17", ["Theorem 2.6"]),
        ("Corollary 8.18", ["Corollary (to Theorem 2.6)"]),
        ("Exercise 8.15", ["Exercise 15"]),
        ("Exercise 8.16", ["Exercise 16"]),
        ("Exercise 8.21", ["Exercise 21"]),
        ("Definition 8.19", ["Definition (projection on W_1 along W_2)"]),
        ("Exercise 8.26", ["Exercise 26"]),
        ("Definition 8.20", ["Definition (T-invariant)", "Definition (restriction of T on W)"]),
        ("Exercise 8.31", ["Exercise 31"]),
        ("Exercise 8.32", ["Exercise 32"]),
        ("Exercise 8.33", ["Exercise 33"]),
        ("Exercise 8.34", ["Exercise 34"]),
        ("Exercise 8.37", ["Exercise 37"]),
        ("Exercise 8.39", ["Exercise 39"]),
        ("Exercise 8.40", ["Exercise 40"]),
    ],
    9: [
        ("Definition 9.1", ["Definition (ordered basis)"]),
        ("Definition 9.2", ["Definition (standard ordered basis)"]),
        ("Definition 9.3", ["Definition (coordinate vector of x relative to β)"]),
        ("Example 9.4", ["Example 2"]),
        (
            "Definition 9.5",
            ["Definition (matrix representation of T in the ordered bases β and γ)"],
        ),
        ("Example 9.6", ["Example 4"]),
        (
            "Definition 9.7",
            ["Definition (addition and scalar multiplication of linear transformations)"],
        ),
        ("Theorem 9.8", ["Theorem 2.7"]),
        ("Definition 9.9", ["Definitions (L(V, W) / L(V))"]),
        ("Theorem 9.10", ["Theorem 2.8"]),
        ("Exercise 9.8", ["Exercise 8"]),
        ("Exercise 9.11", ["Exercise 11"]),
        ("Exercise 9.13", ["Exercise 13"]),
    ],
    10: [
        ("Theorem 10.1", ["Theorem 2.9"]),
        ("Theorem 10.2", ["Theorem 2.10"]),
        ("Concept 10.3", ["(Unnumbered) Motivation for matrix multiplication"]),
        ("Definition 10.4", ["Definition (product of matrices)"]),
        (
            "Concept 10.5",
            [
                "(Unnumbered) Properties of matrix multiplication",
                "Example 1",
            ],
        ),
        ("Theorem 10.6", ["Theorem 2.11"]),
        ("Corollary 10.7", ["Corollary (to Theorem 2.11)"]),
        ("Definition 10.8", ["Definitions (Kronecker delta / identity matrix)"]),
        ("Theorem 10.9", ["Theorem 2.12"]),
        ("Corollary 10.10", ["Corollary (to Theorem 2.12)"]),
        ("Definition 10.11", ["Definition (power of a matrix)"]),
        ("Theorem 10.12", ["Theorem 2.13"]),
        (
            "Theorem 10.13",
            ["(Unnumbered) Columns and rows of a product as linear combinations"],
        ),
        ("Theorem 10.14", ["Theorem 2.14"]),
        ("Definition 10.15", ["Definition (left-multiplication transformation)"]),
        ("Theorem 10.16", ["Theorem 2.15"]),
        ("Theorem 10.17", ["Theorem 2.16"]),
        ("Exercise 10.8", ["Exercise 8"]),
        ("Exercise 10.11", ["Exercise 11"]),
        ("Exercise 10.13", ["Exercise 13"]),
        ("Exercise 10.15", ["Exercise 15"]),
        ("Exercise 10.16", ["Exercise 16"]),
        ("Exercise 10.17", ["Exercise 17"]),
    ],
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import existing linear-algebra note files into notes-helper projects, "
            "create a shared mapping file, and keep source backups."
        )
    )
    parser.add_argument("note_numbers", nargs="+", type=int, help="Note file numbers to import, e.g. 2 3 4 5 6 7 8")
    parser.add_argument("--source-docs", default=str(DEFAULT_SOURCE_DOCS))
    parser.add_argument("--source-mkdocs-root", default=str(DEFAULT_SOURCE_MKDOCS_ROOT))
    parser.add_argument("--source-book", default=str(DEFAULT_SOURCE_BOOK))
    parser.add_argument("--legacy-map", default=str(DEFAULT_LEGACY_MAP))
    parser.add_argument("--project-title-prefix", default="[Linear Algebra] ")
    return parser.parse_args()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _strip_formatting(text: str) -> str:
    return text.replace("**", "").replace("`", "").strip()


def _normalize_new_ref(text: str) -> str:
    value = _strip_formatting(text)
    value = re.sub(r"\s+\(source [^)]+\)$", "", value).strip()
    return value


def _note_location(note_number: int) -> str:
    return f"linear-algebra/{note_number}.md"


def _bundle_root(note_numbers: list[int], *, stamp: str) -> Path:
    label = f"{min(note_numbers)}_{max(note_numbers)}"
    return ROOT / "projects" / f"linear_algebra_import_{label}_{stamp}"


def _shadow_root(bundle_root: Path) -> Path:
    return bundle_root / "shadow_site"


def _shadow_output_path(shadow_root: Path, note_number: int) -> Path:
    return shadow_root / "docs" / "linear-algebra" / f"{note_number}.md"


def _copy_file(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return str(dest.resolve())


def _copy_tree(src: Path, dest: Path) -> str:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return str(dest.resolve())


def _write_shadow_mkdocs(shadow_root: Path) -> None:
    shadow_root.mkdir(parents=True, exist_ok=True)
    (shadow_root / "mkdocs.yml").write_text(
        (
            "site_name: Imported Linear Algebra Notes\n"
            "docs_dir: docs\n"
            "site_dir: site\n"
            "theme:\n"
            "  name: material\n"
        ),
        encoding="utf-8",
    )


def _load_legacy_mapping_rows(
    legacy_map_path: Path,
    *,
    note_numbers: list[int],
    source_doc_path: Path,
) -> list[MappingRow]:
    text = legacy_map_path.read_text(encoding="utf-8")
    rows: list[MappingRow] = []
    header: list[str] = []
    expect_separator = False

    def parse_row(line: str) -> list[str] | None:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            return None
        return [cell.strip() for cell in stripped.strip("|").split("|")]

    for raw_line in text.splitlines():
        cells = parse_row(raw_line)
        if cells is None:
            continue

        if not header:
            lowered = [cell.lower() for cell in cells]
            if lowered == ["original ref", "new ref", "location"]:
                header = cells
                expect_separator = True
            continue

        if expect_separator:
            expect_separator = False
            continue

        if len(cells) != len(header):
            header = []
            expect_separator = False
            continue

        original_ref = _strip_formatting(cells[0])
        new_ref = _normalize_new_ref(cells[1])
        location = _strip_formatting(cells[2])
        if not location.endswith(".md"):
            continue
        try:
            note_number = int(Path(location).stem)
        except ValueError:
            continue
        if note_number not in note_numbers:
            continue
        if not new_ref or not os.path.basename(location):
            continue
        if not re.match(_VALID_NEW_REF_RE, new_ref):
            continue
        rows.append(
            MappingRow(
                source_doc=str(source_doc_path),
                new_ref=new_ref,
                location=_note_location(note_number),
                original_refs=[original_ref],
            )
        )
    return rows


def _manual_mapping_rows(*, note_number: int, source_doc_path: Path) -> list[MappingRow]:
    rows: list[MappingRow] = []
    for new_ref, original_refs in MANUAL_NOTE_MAPS.get(note_number, []):
        rows.append(
            MappingRow(
                source_doc=str(source_doc_path),
                new_ref=new_ref,
                location=_note_location(note_number),
                original_refs=list(original_refs),
            )
        )
    return rows


def _dedupe_rows(rows: list[MappingRow]) -> list[MappingRow]:
    result: list[MappingRow] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.source_doc, row.location, row.new_ref)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _backup_inputs(
    *,
    bundle_root: Path,
    source_docs: Path,
    source_book: Path,
    legacy_map: Path,
    note_numbers: list[int],
) -> dict[str, str]:
    backup_root = bundle_root / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    for note_number in note_numbers:
        source_note = source_docs / f"{note_number}.md"
        copied[f"{note_number}.md"] = _copy_file(source_note, backup_root / "notes" / source_note.name)
    copied["ORIGINAL_TO_NOTES_NUMBERING_MAP.md"] = _copy_file(
        legacy_map,
        backup_root / "references" / legacy_map.name,
    )
    copied[source_book.name] = _copy_file(
        source_book,
        backup_root / "references" / source_book.name,
    )

    assets_dir = source_docs / "assets"
    if assets_dir.is_dir():
        copied["assets"] = _copy_tree(assets_dir, backup_root / "assets")

    return copied


def _prepare_shadow_site(
    *,
    bundle_root: Path,
    source_docs: Path,
    note_numbers: list[int],
) -> Path:
    shadow_root = _shadow_root(bundle_root)
    docs_root = shadow_root / "docs" / "linear-algebra"
    docs_root.mkdir(parents=True, exist_ok=True)

    _write_shadow_mkdocs(shadow_root)
    for note_number in note_numbers:
        source_note = source_docs / f"{note_number}.md"
        _copy_file(source_note, docs_root / source_note.name)

    assets_dir = source_docs / "assets"
    if assets_dir.is_dir():
        _copy_tree(assets_dir, docs_root / "assets")

    return shadow_root


def _make_reference(path: Path, *, name: str) -> ReferenceFile:
    raw_path = str(path.resolve())
    return ReferenceFile(
        id=uuid.uuid4().hex[:8],
        name=name,
        path=raw_path,
        originalPath=raw_path,
        prepared=False,
    )


def _project_id_for(note_number: int) -> str:
    return (f"la{note_number:02d}{uuid.uuid4().hex[:8]}")[:12]


def _import_projects(
    *,
    note_numbers: list[int],
    source_docs: Path,
    source_mkdocs_root: Path,
    source_book: Path,
    legacy_map: Path,
    mapping_path: Path,
    title_prefix: str,
) -> list[dict[str, str]]:
    created: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat()

    for note_number in note_numbers:
        source_note = source_docs / f"{note_number}.md"
        note_text = source_note.read_text(encoding="utf-8")
        title, items = split_existing_markdown_into_items(
            note_text,
            default_prefix=str(note_number),
        )
        project_id = _project_id_for(note_number)
        project = Project(
            id=project_id,
            title=f"{title_prefix}{title or f'Linear Algebra {note_number}'}",
            references=[
                _make_reference(source_book, name="source_part1.md"),
                _make_reference(legacy_map, name="legacy_numbering_map.md"),
            ],
            mkdocsRoot=str(source_mkdocs_root.resolve()),
            outputPath=str((source_docs / f"{note_number}.md").resolve()),
            mappingPath=str(mapping_path.resolve()),
            items=items,
            numberPrefix=str(note_number),
            syncedNumberPrefix=str(note_number),
            createdAt=now,
            updatedAt=now,
        )
        _save_project(project, touch_updated=False)
        localized = _load_project(project_id)
        localized.syncedNumberPrefix = localized.numberPrefix
        for item in localized.items:
            item.syncedNumber = item.number
        _save_project(localized, touch_updated=False)
        created.append(
            {
                "noteNumber": str(note_number),
                "projectId": project_id,
                "title": localized.title,
                "projectPath": str((ROOT / "projects" / project_id / "project.json").resolve()),
                "outputPath": localized.outputPath,
            }
        )
    return created


def _finalize_mapping_order(mapping_path: Path, *, note_numbers: list[int]) -> None:
    rows = parse_mapping_file(str(mapping_path))
    order_index: dict[str, int] = {}
    counter = 0
    for note_number in note_numbers:
        location = _note_location(note_number)
        for row in rows:
            if row.location != location:
                continue
            order_index[f"{row.location}::{row.new_ref}"] = counter
            counter += 1
    write_mapping_file(str(mapping_path), rows, entry_order_index=order_index)


def main() -> int:
    args = _parse_args()
    note_numbers = sorted(set(args.note_numbers))
    source_docs = Path(args.source_docs).expanduser().resolve()
    source_mkdocs_root = Path(args.source_mkdocs_root).expanduser().resolve()
    source_book = Path(args.source_book).expanduser().resolve()
    legacy_map = Path(args.legacy_map).expanduser().resolve()

    for note_number in note_numbers:
        note_path = source_docs / f"{note_number}.md"
        if not note_path.is_file():
            raise FileNotFoundError(f"Source note not found: {note_path}")
    if not source_book.is_file():
        raise FileNotFoundError(f"Source book not found: {source_book}")
    if not legacy_map.is_file():
        raise FileNotFoundError(f"Legacy map not found: {legacy_map}")

    stamp = _timestamp()
    bundle_root = _bundle_root(note_numbers, stamp=stamp)
    bundle_root.mkdir(parents=True, exist_ok=True)

    backups = _backup_inputs(
        bundle_root=bundle_root,
        source_docs=source_docs,
        source_book=source_book,
        legacy_map=legacy_map,
        note_numbers=note_numbers,
    )
    shadow_root = _prepare_shadow_site(
        bundle_root=bundle_root,
        source_docs=source_docs,
        note_numbers=note_numbers,
    )

    mapping_path = bundle_root / "linear_algebra_mapping.md"
    mapping_rows = _load_legacy_mapping_rows(
        legacy_map,
        note_numbers=note_numbers,
        source_doc_path=source_book,
    )
    for note_number in note_numbers:
        mapping_rows.extend(_manual_mapping_rows(note_number=note_number, source_doc_path=source_book))
    mapping_rows = _dedupe_rows(mapping_rows)
    write_mapping_file(str(mapping_path), mapping_rows)

    created_projects = _import_projects(
        note_numbers=note_numbers,
        source_docs=source_docs,
        source_mkdocs_root=source_mkdocs_root,
        source_book=source_book,
        legacy_map=legacy_map,
        mapping_path=mapping_path,
        title_prefix=args.project_title_prefix,
    )
    _finalize_mapping_order(mapping_path, note_numbers=note_numbers)

    manifest = {
        "bundleRoot": str(bundle_root.resolve()),
        "shadowMkdocsRoot": str(shadow_root.resolve()),
        "sourceMkdocsRoot": str(source_mkdocs_root.resolve()),
        "mappingPath": str(mapping_path.resolve()),
        "backups": backups,
        "projects": created_projects,
    }
    (bundle_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
