#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from mapping_store import (  # noqa: E402
    MappingRow,
    mapping_locator,
    parse_mapping_file,
    rebuild_referenced_by,
    unique_preserve_order,
    write_mapping_file,
)


DEFAULT_DOCS_DIR = Path("/home/arnold/arnold/github/math-notes/docs/linear-algebra")
DEFAULT_MAPPING_PATH = DEFAULT_DOCS_DIR / "mapping.md"

_ADMONITION_RE = re.compile(r'^!!!\s+([a-zA-Z0-9_-]+)(?:\s+"([^"]*)")?\s*$')
_LABEL_RE = re.compile(
    r"\b(Definition|Theorem|Lemma|Corollary|Example|Exercise|Concept|Proposition)"
    r"\s+\d+(?:\.\d+)*\b"
)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_REPRESENTED_SUFFIX_RE = re.compile(r"\s+\(represented as theorem block\)\s*$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_LINEAR_ALGEBRA_33_RENUMBERED_OLD_LABELS = [
    "Theorem 33.2",
    "Definition 33.3",
    "Example 33.4",
    "Example 33.5",
    "Definition 33.6",
    "Theorem 33.7",
    "Definition 33.8",
    "Example 33.9",
    "Theorem 33.10",
    "Example 33.11",
    "Definition 33.12",
    "Concept 33.13",
    "Example 33.14",
    "Definition 33.15",
    "Theorem 33.16",
    "Example 33.17",
    "Lemma 33.18",
    "Theorem 33.19",
    "Example 33.20",
    "Exercise 33.9",
    "Exercise 33.11",
    "Exercise 33.12",
    "Exercise 33.13",
    "Exercise 33.14",
    "Exercise 33.15",
    "Exercise 33.16",
    "Exercise 33.17",
    "Exercise 33.18",
    "Exercise 33.19",
    "Exercise 33.20",
    "Exercise 33.21",
    "Exercise 33.22",
    "Exercise 33.25",
    "Exercise 33.26",
    "Exercise 33.27",
]
_LINEAR_ALGEBRA_33_OLD_ORIGINAL_REFS_BY_LABEL = {
    "Theorem 33.2": ["Theorem 6.26"],
    "Definition 33.3": ["Definition (singular values of a linear transformation)"],
    "Example 33.4": ["Example 1"],
    "Example 33.5": ["Example 2"],
    "Definition 33.6": ["Definition (singular values of a matrix)"],
    "Theorem 33.7": ["Theorem 6.27"],
    "Definition 33.8": ["Definition (singular value decomposition)"],
    "Example 33.9": ["Example 3"],
    "Theorem 33.10": ["Theorem 6.28"],
    "Example 33.11": ["Example 4"],
    "Definition 33.12": ["Definition (pseudoinverse of a linear transformation)"],
    "Concept 33.13": ["(Unnumbered) Pseudoinverse from singular values"],
    "Example 33.14": ["Example 5"],
    "Definition 33.15": ["Definition (pseudoinverse of a matrix)"],
    "Theorem 33.16": ["Theorem 6.29"],
    "Example 33.17": ["Example 6"],
    "Lemma 33.18": ["Lemma (projection identities for the pseudoinverse)"],
    "Theorem 33.19": ["Theorem 6.30"],
    "Example 33.20": ["Example 7"],
}


def _decrement_33_label(label: str) -> str:
    match = re.fullmatch(
        r"(Definition|Theorem|Lemma|Corollary|Example|Exercise|Concept|Proposition)\s+33\.(\d+)",
        label.strip(),
    )
    if not match:
        return label
    number = int(match.group(2))
    if number <= 1:
        return label
    return f"{match.group(1)} 33.{number - 1}"


def _expected_original_refs_for_legacy_label(label: str) -> list[str]:
    if label in _LINEAR_ALGEBRA_33_OLD_ORIGINAL_REFS_BY_LABEL:
        return list(_LINEAR_ALGEBRA_33_OLD_ORIGINAL_REFS_BY_LABEL[label])

    match = re.fullmatch(r"Exercise\s+33\.(\d+)", label.strip())
    if match:
        return [f"Exercise {match.group(1)}"]
    return []


def _is_expected_legacy_alias(row: MappingRow, legacy_label: str) -> bool:
    expected_original_refs = _expected_original_refs_for_legacy_label(legacy_label)
    if not expected_original_refs:
        return True
    return row.original_refs == expected_original_refs


_LEGACY_LABEL_ALIASES_BY_LOCATION = {
    "linear-algebra/33.md": {
        _decrement_33_label(old_label): old_label
        for old_label in _LINEAR_ALGEBRA_33_RENUMBERED_OLD_LABELS
    }
}
_ORIGINAL_REFS_BY_LABEL = {
    _decrement_33_label(label): list(original_refs)
    for label, original_refs in _LINEAR_ALGEBRA_33_OLD_ORIGINAL_REFS_BY_LABEL.items()
}


@dataclass
class DocEntry:
    location: str
    label: str
    title: str
    admonition_type: str
    document: str
    line_number: int


@dataclass
class SyncResult:
    rows: list[MappingRow]
    report: dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite the linear-algebra mapping rows from the actual docs file order. "
            "By default this is a dry-run."
        )
    )
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    parser.add_argument("--mapping-path", default=str(DEFAULT_MAPPING_PATH))
    parser.add_argument(
        "--through-note",
        type=int,
        default=30,
        help="Only rewrite numeric note files with stem <= this value.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the mapping file. Without this flag only a report is printed.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped .docs-sync.bak backup before writing.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    return parser.parse_args()


def _note_number(path: Path) -> int | None:
    if not path.stem.isdigit():
        return None
    return int(path.stem)


def _note_paths(docs_dir: Path) -> list[Path]:
    paths = [path for path in docs_dir.glob("*.md") if _note_number(path) is not None]
    return sorted(paths, key=lambda path: int(path.stem))


def _location_for_path(path: Path, docs_dir: Path) -> str:
    docs_root = docs_dir.parent
    try:
        return path.relative_to(docs_root).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_label(title: str) -> str:
    match = _LABEL_RE.search(title)
    return match.group(0).strip() if match else ""


def _extract_number(label: str) -> str:
    match = re.search(r"\d+(?:\.\d+)*", label)
    return match.group(0) if match else ""


def _strip_label_prefix(text: str) -> str:
    return _LABEL_RE.sub("", text, count=1).replace(":", " ")


def _tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(text.replace("-", " "))
        if len(token) >= 3 and not token.isdigit()
    }


def _parse_doc_entries(path: Path, docs_dir: Path) -> list[DocEntry]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    location = _location_for_path(path, docs_dir)
    entries: list[DocEntry] = []
    i = 0
    while i < len(lines):
        match = _ADMONITION_RE.match(lines[i].strip())
        if not match or lines[i].startswith((" ", "\t")):
            i += 1
            continue

        start = i
        i += 1
        while i < len(lines):
            candidate = lines[i]
            if candidate.strip() and not candidate.startswith((" ", "\t")):
                break
            i += 1

        title = (match.group(2) or "").strip()
        label = _extract_label(title)
        if not label:
            continue

        entries.append(
            DocEntry(
                location=location,
                label=label,
                title=title,
                admonition_type=match.group(1).strip().lower(),
                document="\n".join(lines[start:i]).strip("\n"),
                line_number=start + 1,
            )
        )
    return entries


def _load_doc_entries(docs_dir: Path) -> dict[str, list[DocEntry]]:
    entries_by_location: dict[str, list[DocEntry]] = {}
    for path in _note_paths(docs_dir):
        location = _location_for_path(path, docs_dir)
        entries_by_location[location] = _parse_doc_entries(path, docs_dir)
    return entries_by_location


def _primary_source_doc(rows: list[MappingRow]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        if row.source_doc:
            counts[row.source_doc] = counts.get(row.source_doc, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _copy_row(row: MappingRow, *, new_ref: str | None = None, location: str | None = None) -> MappingRow:
    return MappingRow(
        source_doc=row.source_doc,
        new_ref=new_ref if new_ref is not None else row.new_ref,
        location=location if location is not None else row.location,
        original_refs=list(row.original_refs),
        references=list(row.references),
        referenced_by=list(row.referenced_by),
        note=row.note,
    )


def _best_alias_row(
    entry: DocEntry,
    rows: list[MappingRow],
    used_row_ids: set[int],
    doc_labels_for_location: set[str],
) -> MappingRow | None:
    clean_exact = entry.label
    clean_candidates = [
        row
        for row in rows
        if id(row) not in used_row_ids
        and row.location == entry.location
        and _REPRESENTED_SUFFIX_RE.sub("", row.new_ref).strip() == clean_exact
    ]
    if len(clean_candidates) == 1:
        return clean_candidates[0]

    entry_number = _extract_number(entry.label)
    if not entry_number:
        return None

    same_number = [
        row
        for row in rows
        if id(row) not in used_row_ids
        and row.location == entry.location
        and row.new_ref not in doc_labels_for_location
        and _extract_number(row.new_ref) == entry_number
    ]
    if len(same_number) == 1:
        return same_number[0]
    if not same_number:
        return None

    entry_tokens = _tokens(_strip_label_prefix(entry.title))
    scored: list[tuple[int, MappingRow]] = []
    for row in same_number:
        source_text = " ".join([_strip_label_prefix(row.new_ref), *row.original_refs])
        score = len(entry_tokens & _tokens(source_text))
        scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] > 0 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        return scored[0][1]
    return None


def _label_lookup(entries_by_location: dict[str, list[DocEntry]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    duplicates: set[str] = set()
    for location, entries in entries_by_location.items():
        for entry in entries:
            locator = mapping_locator(location, entry.label)
            if entry.label in lookup and lookup[entry.label] != locator:
                duplicates.add(entry.label)
            else:
                lookup[entry.label] = locator
    for label in duplicates:
        lookup.pop(label, None)
    return lookup


def _resolve_references(document: str, own_label: str, label_to_locator: dict[str, str]) -> list[str]:
    refs: list[str] = []
    for match in _BOLD_RE.finditer(document or ""):
        label = match.group(1).strip()
        if not label or label == own_label:
            continue
        locator = label_to_locator.get(label)
        if locator:
            refs.append(locator)
    return unique_preserve_order(refs)


def _original_refs_for_added_entry(entry: DocEntry) -> list[str]:
    if entry.label in _ORIGINAL_REFS_BY_LABEL:
        return list(_ORIGINAL_REFS_BY_LABEL[entry.label])

    match = re.fullmatch(r"Exercise\s+\d+\.(\d+)", entry.label)
    if match:
        return [f"Exercise {match.group(1)}"]
    return []


def _update_locators(
    values: Iterable[str],
    locator_renames: dict[str, str],
    valid_locators: set[str],
) -> list[str]:
    updated: list[str] = []
    for value in values:
        mapped = locator_renames.get(value, value)
        if mapped in valid_locators:
            updated.append(mapped)
    return unique_preserve_order(updated)


def _sync_rows(
    *,
    docs_dir: Path,
    mapping_path: Path,
    through_note: int,
) -> SyncResult:
    existing_rows = parse_mapping_file(str(mapping_path))
    primary_source_doc = _primary_source_doc(existing_rows)
    entries_by_location = _load_doc_entries(docs_dir)
    label_to_locator = _label_lookup(entries_by_location)

    processed_locations: list[str] = []
    for path in _note_paths(docs_dir):
        note_number = _note_number(path)
        if note_number is not None and note_number <= through_note:
            processed_locations.append(_location_for_path(path, docs_dir))
    processed_location_set = set(processed_locations)

    rows_by_location: dict[str, list[MappingRow]] = {}
    for row in existing_rows:
        rows_by_location.setdefault(row.location, []).append(row)

    exact_by_locator = {
        mapping_locator(row.location, row.new_ref): row
        for row in existing_rows
        if row.location and row.new_ref
    }

    used_row_ids: set[int] = set()
    locator_renames: dict[str, str] = {}
    new_rows: list[MappingRow] = []
    added: list[dict[str, str]] = []
    renamed: list[dict[str, str]] = []
    kept: list[str] = []

    for location in processed_locations:
        doc_labels_for_location = {
            entry.label for entry in entries_by_location.get(location, [])
        }
        for entry in entries_by_location.get(location, []):
            locator = mapping_locator(location, entry.label)
            legacy_alias_label = _LEGACY_LABEL_ALIASES_BY_LOCATION.get(location, {}).get(entry.label, "")
            legacy_alias = (
                exact_by_locator.get(mapping_locator(location, legacy_alias_label))
                if legacy_alias_label
                else None
            )
            if legacy_alias is not None and not _is_expected_legacy_alias(legacy_alias, legacy_alias_label):
                legacy_alias = None
            if legacy_alias is not None and id(legacy_alias) not in used_row_ids:
                old_locator = mapping_locator(legacy_alias.location, legacy_alias.new_ref)
                row = _copy_row(legacy_alias, new_ref=entry.label, location=location)
                used_row_ids.add(id(legacy_alias))
                locator_renames[old_locator] = locator
                renamed.append(
                    {
                        "location": location,
                        "oldRef": legacy_alias.new_ref,
                        "newRef": entry.label,
                    }
                )
            else:
                existing = exact_by_locator.get(locator)
                if (
                    existing is not None
                    and id(existing) not in used_row_ids
                    and (not legacy_alias_label or legacy_alias is None)
                ):
                    row = _copy_row(existing)
                    used_row_ids.add(id(existing))
                    kept.append(locator)
                else:
                    alias = _best_alias_row(
                        entry,
                        rows_by_location.get(location, []),
                        used_row_ids,
                        doc_labels_for_location,
                    )
                    if alias is not None:
                        old_locator = mapping_locator(alias.location, alias.new_ref)
                        row = _copy_row(alias, new_ref=entry.label, location=location)
                        used_row_ids.add(id(alias))
                        locator_renames[old_locator] = locator
                        renamed.append(
                            {
                                "location": location,
                                "oldRef": alias.new_ref,
                                "newRef": entry.label,
                            }
                        )
                    else:
                        original_refs = _original_refs_for_added_entry(entry)
                        row = MappingRow(
                            source_doc=primary_source_doc,
                            new_ref=entry.label,
                            location=location,
                            original_refs=original_refs,
                        )
                        added.append(
                            {
                                "location": location,
                                "newRef": entry.label,
                                "line": str(entry.line_number),
                                "originalRefs": "; ".join(original_refs),
                            }
                        )
            row.references = _resolve_references(row_document_for_entry(entry), row.new_ref, label_to_locator)
            row.referenced_by = []
            new_rows.append(row)

    dropped: list[dict[str, str]] = []
    for location in processed_locations:
        for row in rows_by_location.get(location, []):
            if id(row) in used_row_ids:
                continue
            dropped.append(
                {
                    "location": location,
                    "newRef": row.new_ref,
                    "originalRefs": "; ".join(row.original_refs),
                }
            )

    unprocessed_rows = [
        _copy_row(row)
        for row in existing_rows
        if row.location not in processed_location_set
    ]

    combined_rows = new_rows + unprocessed_rows
    valid_locators = {
        mapping_locator(row.location, row.new_ref)
        for row in combined_rows
        if row.location and row.new_ref
    }
    for row in combined_rows:
        row.references = _update_locators(row.references, locator_renames, valid_locators)
        row.referenced_by = []
    rebuild_referenced_by(combined_rows)

    report = {
        "mappingPath": str(mapping_path),
        "docsDir": str(docs_dir),
        "throughNote": through_note,
        "processedLocations": processed_locations,
        "existingRowCount": len(existing_rows),
        "newRowCount": len(combined_rows),
        "processedDocEntryCount": sum(len(entries_by_location.get(loc, [])) for loc in processed_locations),
        "keptExactCount": len(kept),
        "renamedCount": len(renamed),
        "addedCount": len(added),
        "droppedCount": len(dropped),
        "renamed": renamed,
        "added": added,
        "dropped": dropped,
    }
    return SyncResult(rows=combined_rows, report=report)


def row_document_for_entry(entry: DocEntry) -> str:
    return entry.document


def _backup_file(path: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.name}.docs-sync.bak.{stamp}")
    shutil.copyfile(path, backup_path)
    return str(backup_path)


def _format_report(report: dict, *, wrote: bool = False, backup_path: str = "") -> str:
    lines = [
        f"Mapping: {report['mappingPath']}",
        f"Docs: {report['docsDir']}",
        f"Scope: linear-algebra/*.md through {report['throughNote']}.md",
        f"Processed locations: {len(report['processedLocations'])}",
        f"Rows: {report['existingRowCount']} -> {report['newRowCount']}",
        (
            f"Rows in processed docs: {report['processedDocEntryCount']} docs entries, "
            f"{report['keptExactCount']} exact, {report['renamedCount']} renamed, "
            f"{report['addedCount']} added, {report['droppedCount']} dropped"
        ),
        f"Mode: {'wrote mapping' if wrote else 'dry-run only'}",
    ]
    if backup_path:
        lines.append(f"Backup: {backup_path}")
    if report["renamed"]:
        lines.append("")
        lines.append("Renames:")
        for item in report["renamed"]:
            lines.append(f"- {item['location']}: {item['oldRef']} -> {item['newRef']}")
    if report["dropped"]:
        lines.append("")
        lines.append("Dropped rows:")
        for item in report["dropped"]:
            suffix = f" ({item['originalRefs']})" if item["originalRefs"] else ""
            lines.append(f"- {item['location']}: {item['newRef']}{suffix}")
    if report["added"]:
        lines.append("")
        lines.append("Added rows:")
        for item in report["added"]:
            original_refs = item.get("originalRefs") or ""
            suffix = f", Original ref: {original_refs}" if original_refs else ", blank Original ref"
            lines.append(f"- {item['location']}: {item['newRef']} (line {item['line']}{suffix})")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    docs_dir = Path(os.path.abspath(os.path.expanduser(args.docs_dir)))
    mapping_path = Path(os.path.abspath(os.path.expanduser(args.mapping_path)))
    result = _sync_rows(
        docs_dir=docs_dir,
        mapping_path=mapping_path,
        through_note=args.through_note,
    )

    backup_path = ""
    if args.write:
        if not args.no_backup:
            backup_path = _backup_file(mapping_path)
        write_mapping_file(str(mapping_path), result.rows)

    if args.json:
        payload = dict(result.report)
        payload["wrote"] = bool(args.write)
        payload["backupPath"] = backup_path
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_format_report(result.report, wrote=bool(args.write), backup_path=backup_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
