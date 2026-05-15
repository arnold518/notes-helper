from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from models import Item, Project


@dataclass
class MappingRow:
    source_doc: str
    new_ref: str
    location: str
    original_refs: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    referenced_by: list[str] = field(default_factory=list)
    note: str = ""


def strip_markdown_bold(text: str) -> str:
    value = text.strip()
    if len(value) >= 4 and value.startswith("**") and value.endswith("**"):
        return value[2:-2].strip()
    return value


def strip_wrapping_backticks(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def strip_all_markdown_bold(text: str) -> str:
    return text.replace("**", "").strip()


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def split_list_cell(text: str) -> list[str]:
    raw = strip_wrapping_backticks(text)
    return unique_preserve_order(
        [
            strip_wrapping_backticks(strip_all_markdown_bold(part))
            for part in raw.split(";")
        ]
    )


def parse_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return cells if cells else None


def natural_key(text: str) -> list[object]:
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", text.strip())
        if part
    ]


def canonical_output_location(output_path: str, mkdocs_root: str = "") -> str:
    raw = (output_path or "").strip()
    if not raw:
        return ""

    path = Path(os.path.abspath(os.path.expanduser(raw)))
    if mkdocs_root:
        docs_root = Path(os.path.abspath(os.path.expanduser(mkdocs_root))) / "docs"
        try:
            return path.relative_to(docs_root).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def output_location_candidates(output_path: str, mkdocs_root: str = "") -> list[str]:
    raw = (output_path or "").strip()
    if not raw:
        return []

    path = Path(os.path.abspath(os.path.expanduser(raw)))
    candidates = [canonical_output_location(output_path, mkdocs_root), path.name, path.as_posix()]
    return unique_preserve_order(candidates)


def mapping_locator(location: str, new_ref: str) -> str:
    loc = location.strip()
    ref = new_ref.strip()
    if not loc or not ref:
        return ""
    return f"{loc}::{ref}"


def item_reference_label(item: Item, prefix: str) -> str:
    if item.kind == "admonition":
        if item.number == 0:
            return ""
        cap_type = item.type.capitalize()
        return f"{cap_type} {prefix}.{item.number}" if prefix else f"{cap_type} {item.number}"
    if item.kind == "section":
        return f"§ {item.content}"
    return ""


def project_number_prefix(project: Project) -> str:
    for item in project.items:
        if item.kind == "section" and item.type == "h1":
            match = re.search(r"(?:§\s*)?(\d+(?:\.\d+)*)", item.content)
            if match:
                return match.group(1)
    return project.numberPrefix or ""


def project_entry_order_index(project: Project) -> dict[str, int]:
    location_candidates = output_location_candidates(project.outputPath, project.mkdocsRoot)
    if not location_candidates:
        return {}

    prefix = project.numberPrefix or project_number_prefix(project)
    order_index: dict[str, int] = {}
    for idx, item in enumerate(project.items):
        target_ref = item_reference_label(item, prefix)
        if not target_ref:
            continue
        for location in location_candidates:
            locator = mapping_locator(location, target_ref)
            if locator:
                order_index[locator] = idx
    return order_index


def parse_mapping_file(path: str) -> list[MappingRow]:
    mapping_path = Path(os.path.abspath(os.path.expanduser(path)))
    if not mapping_path.exists() or not mapping_path.is_file():
        return []

    rows: list[MappingRow] = []
    current_source_doc = ""
    header_cells: list[str] = []
    expect_separator = False

    for raw_line in mapping_path.read_text(encoding="utf-8", errors="replace").splitlines():
        section_match = re.match(r"##\s+Reference:\s*(.+?)\s*$", raw_line)
        if section_match:
            current_source_doc = section_match.group(1).strip()
            header_cells = []
            expect_separator = False
            continue

        if not current_source_doc:
            continue

        cells = parse_markdown_table_row(raw_line)
        if cells is None:
            continue

        if not header_cells:
            header_cells = cells
            expect_separator = True
            continue

        if expect_separator:
            separator_like = all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)
            if separator_like:
                expect_separator = False
                continue
            header_cells = []
            expect_separator = False
            continue

        if len(cells) != len(header_cells):
            continue

        values = {
            header_cells[idx].strip().lower(): cells[idx].strip()
            for idx in range(len(header_cells))
        }
        new_ref = (values.get("new ref") or values.get("target ref") or "").strip()
        original_refs = split_list_cell(
            values.get("original ref")
            or values.get("source refs")
            or ""
        )
        location = strip_wrapping_backticks(values.get("location") or values.get("target doc") or "")
        references = split_list_cell(values.get("references") or "")
        referenced_by = split_list_cell(values.get("referenced by") or "")
        note = (values.get("note") or "").strip()
        if not new_ref:
            continue

        rows.append(
            MappingRow(
                source_doc=current_source_doc,
                new_ref=new_ref,
                location=location,
                original_refs=original_refs,
                references=references,
                referenced_by=referenced_by,
                note=note,
            )
        )

    return rows


def rebuild_referenced_by(rows: list[MappingRow]) -> None:
    locator_to_row: dict[str, MappingRow] = {}
    duplicate_locators: set[str] = set()
    for row in rows:
        locator = mapping_locator(row.location, row.new_ref)
        if not locator:
            continue
        if locator in locator_to_row:
            duplicate_locators.add(locator)
            continue
        locator_to_row[locator] = row

    for locator in duplicate_locators:
        locator_to_row.pop(locator, None)

    for row in rows:
        row.references = unique_preserve_order(row.references)
        row.referenced_by = []

    for row in rows:
        source_locator = mapping_locator(row.location, row.new_ref)
        if not source_locator:
            continue
        for ref_locator in row.references:
            target_row = locator_to_row.get(ref_locator)
            if target_row is None or ref_locator == source_locator:
                continue
            target_row.referenced_by.append(source_locator)

    for row in rows:
        row.referenced_by = unique_preserve_order(row.referenced_by)


def serialize_mapping_file(
    rows: list[MappingRow],
    *,
    entry_order_index: dict[str, int] | None = None,
) -> str:
    if not rows:
        return ""

    order_index = entry_order_index or {}
    sections: dict[str, list[MappingRow]] = {}
    for row in rows:
        sections.setdefault(row.source_doc, []).append(row)

    def ordered_section_rows(section_rows: list[MappingRow]) -> list[MappingRow]:
        if not order_index:
            return section_rows

        grouped_rows: dict[str, list[MappingRow]] = {}
        group_order: list[str] = []
        for row in section_rows:
            key = row.location
            if key not in grouped_rows:
                grouped_rows[key] = []
                group_order.append(key)
            grouped_rows[key].append(row)

        ordered: list[MappingRow] = []
        for key in group_order:
            group = grouped_rows[key]
            if not any(mapping_locator(row.location, row.new_ref) in order_index for row in group):
                ordered.extend(group)
                continue

            sorted_group = sorted(
                enumerate(group),
                key=lambda pair: (
                    0,
                    order_index.get(mapping_locator(pair[1].location, pair[1].new_ref), 10**9),
                    natural_key(pair[1].new_ref),
                    "; ".join(pair[1].original_refs).casefold(),
                )
                if mapping_locator(pair[1].location, pair[1].new_ref) in order_index
                else (1, pair[0]),
            )
            ordered.extend(row for _, row in sorted_group)
        return ordered

    parts: list[str] = []
    source_docs = list(sections.keys())
    for source_doc in source_docs:
        section_rows = ordered_section_rows(sections[source_doc])
        parts.append(f"## Reference: {source_doc}\n")
        parts.append("| New ref | Original ref | Location | References | Referenced by |\n")
        parts.append("| --- | --- | --- | --- | --- |\n")
        for row in section_rows:
            original_ref = "; ".join(f"**{ref}**" for ref in row.original_refs)
            references = "; ".join(row.references)
            referenced_by = "; ".join(row.referenced_by)
            parts.append(
                f"| {row.new_ref} | {original_ref} | {row.location} | {references} | {referenced_by} |\n"
            )
        parts.append("\n")
    return "".join(parts).rstrip() + "\n"


def dedupe_exact_rows(rows: list[MappingRow]) -> list[MappingRow]:
    seen: set[tuple[object, ...]] = set()
    deduped: list[MappingRow] = []
    for row in rows:
        key = (
            row.source_doc,
            row.new_ref,
            row.location,
            tuple(row.original_refs),
            tuple(row.references),
            tuple(row.referenced_by),
            row.note,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def merge_duplicate_target_rows(rows: list[MappingRow]) -> list[MappingRow]:
    merged_by_key: dict[tuple[str, str, str], MappingRow] = {}
    order: list[tuple[str, str, str]] = []

    for row in rows:
        key = (row.source_doc, row.new_ref, row.location)
        existing = merged_by_key.get(key)
        if existing is None:
            merged_by_key[key] = MappingRow(
                source_doc=row.source_doc,
                new_ref=row.new_ref,
                location=row.location,
                original_refs=list(row.original_refs),
                references=list(row.references),
                referenced_by=list(row.referenced_by),
                note=row.note,
            )
            order.append(key)
            continue

        existing.original_refs = unique_preserve_order(existing.original_refs + row.original_refs)
        existing.references = unique_preserve_order(existing.references + row.references)
        existing.referenced_by = unique_preserve_order(existing.referenced_by + row.referenced_by)
        if row.note and row.note not in {existing.note, ""}:
            existing.note = f"{existing.note}; {row.note}".strip("; ").strip()

    return [merged_by_key[key] for key in order]


def write_mapping_file(
    path: str,
    rows: list[MappingRow],
    *,
    entry_order_index: dict[str, int] | None = None,
) -> None:
    mapping_path = Path(os.path.abspath(os.path.expanduser(path)))
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    deduped_rows = dedupe_exact_rows(merge_duplicate_target_rows(rows))
    mapping_path.write_text(
        serialize_mapping_file(deduped_rows, entry_order_index=entry_order_index),
        encoding="utf-8",
    )


def rename_target_ref(
    path: str,
    location: str,
    old_ref: str,
    new_ref: str,
    *,
    location_aliases: list[str] | None = None,
) -> None:
    rows = parse_mapping_file(path)
    if not rows:
        return

    aliases = unique_preserve_order((location_aliases or []) + [location])
    old_locators = {mapping_locator(alias, old_ref) for alias in aliases if alias}
    new_locator = mapping_locator(location, new_ref)
    changed = False

    for row in rows:
        if row.location in aliases and row.new_ref == old_ref:
            row.location = location
            row.new_ref = new_ref
            changed = True
        updated_refs: list[str] = []
        for locator in row.references:
            updated_refs.append(new_locator if locator in old_locators else locator)
        row.references = unique_preserve_order(updated_refs)

    if not changed:
        return

    rebuild_referenced_by(rows)
    write_mapping_file(path, rows)


def delete_target_row(
    path: str,
    location: str,
    target_ref: str,
    *,
    location_aliases: list[str] | None = None,
) -> None:
    rows = parse_mapping_file(path)
    if not rows:
        return

    aliases = unique_preserve_order((location_aliases or []) + [location])
    removed_locators = {mapping_locator(alias, target_ref) for alias in aliases if alias}
    kept_rows: list[MappingRow] = []
    changed = False
    for row in rows:
        if row.location in aliases and row.new_ref == target_ref:
            changed = True
            continue
        filtered = [locator for locator in row.references if locator not in removed_locators]
        if len(filtered) != len(row.references):
            changed = True
        row.references = filtered
        kept_rows.append(row)

    if not changed:
        return

    rebuild_referenced_by(kept_rows)
    write_mapping_file(path, kept_rows)


def sync_project_reverse_links(project: Project) -> None:
    if not project.mappingPath:
        return

    rows = parse_mapping_file(project.mappingPath)
    if not rows:
        return

    location = canonical_output_location(project.outputPath, project.mkdocsRoot)
    location_candidates = output_location_candidates(project.outputPath, project.mkdocsRoot)
    if not location:
        return

    prefix = project.numberPrefix or project_number_prefix(project)
    for item in project.items:
        target_ref = item_reference_label(item, prefix)
        if not target_ref:
            continue
        row = None
        locator_to_row = {
            mapping_locator(candidate.location, candidate.new_ref): candidate
            for candidate in rows
            if candidate.location and candidate.new_ref
        }
        for candidate_location in location_candidates:
            row = locator_to_row.get(mapping_locator(candidate_location, target_ref))
            if row is not None:
                row.location = location
                break
        if row is None:
            continue

    locator_to_row = {
        mapping_locator(row.location, row.new_ref): row
        for row in rows
        if row.location and row.new_ref
    }
    locators_by_target_ref: dict[str, list[str]] = {}
    for locator, row in locator_to_row.items():
        locators_by_target_ref.setdefault(row.new_ref, []).append(locator)

    for item in project.items:
        target_ref = item_reference_label(item, prefix)
        if not target_ref:
            continue
        row = locator_to_row.get(mapping_locator(location, target_ref))
        if row is None:
            continue

        references: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r"\*\*(.+?)\*\*", item.document or ""):
            bold_label = match.group(1).strip()
            if not bold_label or bold_label == target_ref:
                continue
            locators = unique_preserve_order(locators_by_target_ref.get(bold_label, []))
            if len(locators) != 1:
                continue
            locator = locators[0]
            if locator in seen:
                continue
            seen.add(locator)
            references.append(locator)
        row.references = references

    rebuild_referenced_by(rows)
    write_mapping_file(
        project.mappingPath,
        rows,
        entry_order_index=project_entry_order_index(project),
    )


def dependent_item_ids_from_mapping(project: Project, changed_item_ids: list[str]) -> list[str]:
    if not project.mappingPath:
        return []

    rows = parse_mapping_file(project.mappingPath)
    if not rows:
        return []

    location = canonical_output_location(project.outputPath, project.mkdocsRoot)
    location_candidates = output_location_candidates(project.outputPath, project.mkdocsRoot)
    if not location:
        return []

    prefix = project.numberPrefix or project_number_prefix(project)
    row_by_locator = {
        mapping_locator(row.location, row.new_ref): row
        for row in rows
        if row.location and row.new_ref
    }
    item_id_by_locator: dict[str, str] = {}
    for item in project.items:
        target_ref = item_reference_label(item, prefix)
        for candidate_location in location_candidates:
            locator = mapping_locator(candidate_location, target_ref)
            if locator:
                item_id_by_locator[locator] = item.id
        canonical_locator = mapping_locator(location, target_ref)
        if canonical_locator:
            item_id_by_locator[canonical_locator] = item.id

    impacted_ids: list[str] = []
    seen: set[str] = set()
    for item in project.items:
        if item.id not in changed_item_ids:
            continue
        target_ref = item_reference_label(item, prefix)
        row = None
        for candidate_location in location_candidates:
            row = row_by_locator.get(mapping_locator(candidate_location, target_ref))
            if row is not None:
                break
        if row is None:
            continue
        for dependent_locator in row.referenced_by:
            dependent_item_id = item_id_by_locator.get(dependent_locator)
            if not dependent_item_id or dependent_item_id in changed_item_ids or dependent_item_id in seen:
                continue
            seen.add(dependent_item_id)
            impacted_ids.append(dependent_item_id)

    return impacted_ids
