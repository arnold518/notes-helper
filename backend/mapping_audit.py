from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from mapping_store import (
    canonical_output_location,
    item_reference_label,
    mapping_locator,
    parse_mapping_file,
    project_number_prefix,
)
from models import Project


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    return slug


def natural_key(text: str) -> list[object]:
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", text.strip())
        if part
    ]


def project_file_candidates(projects_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    if not projects_dir.exists():
        return candidates

    for path in sorted(projects_dir.iterdir()):
        if path.name == "_subjects":
            continue
        if path.is_dir():
            project_file = path / "project.json"
            if project_file.exists():
                candidates.append(project_file)

    for path in sorted(projects_dir.glob("*.json")):
        if (projects_dir / path.stem / "project.json").exists():
            continue
        candidates.append(path)

    return candidates


def bracket_title_prefix(title: str) -> str:
    match = re.match(r"^\s*\[([^\]]+)\]", title or "")
    return match.group(1).strip() if match else ""


def infer_subject_id(data: dict[str, Any]) -> str:
    explicit = str(data.get("subjectId") or "").strip()
    if explicit:
        return slugify(explicit)

    title_prefix = bracket_title_prefix(str(data.get("title") or ""))
    if title_prefix:
        return slugify(title_prefix)

    output_path = str(data.get("outputPath") or "").strip()
    if output_path:
        parent_name = Path(os.path.expanduser(output_path)).parent.name
        if parent_name:
            return slugify(parent_name)

    return slugify(str(data.get("title") or data.get("id") or "untitled"))


def load_subject_data(projects_dir: Path, subject_id: str) -> dict[str, Any]:
    path = projects_dir / "_subjects" / f"{slugify(subject_id)}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_subject_projects(projects_dir: Path, subject_id: str) -> list[tuple[Path, Project]]:
    target_subject_id = slugify(subject_id)
    projects: list[tuple[Path, Project]] = []

    for path in project_file_candidates(projects_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or infer_subject_id(data) != target_subject_id:
            continue
        try:
            projects.append((path, Project.model_validate(data)))
        except Exception:
            continue

    return projects


def mapping_path_for_subject(
    projects: list[tuple[Path, Project]],
    subject_data: dict[str, Any],
) -> str:
    subject_mapping_path = str(subject_data.get("mappingPath") or "").strip()
    if subject_mapping_path:
        return subject_mapping_path

    paths = [
        str(project.mappingPath or "").strip()
        for _, project in projects
        if str(project.mappingPath or "").strip()
    ]
    if not paths:
        return ""
    return Counter(paths).most_common(1)[0][0]


def audit_subject_mapping(projects_dir: Path, subject_id: str) -> dict[str, Any]:
    subject_data = load_subject_data(projects_dir, subject_id)
    projects = load_subject_projects(projects_dir, subject_id)
    mapping_path = mapping_path_for_subject(projects, subject_data)
    rows = parse_mapping_file(mapping_path) if mapping_path else []

    rows_by_locator: dict[str, list[Any]] = {}
    rows_by_location: dict[str, list[Any]] = {}
    for row in rows:
        rows_by_location.setdefault(row.location, []).append(row)
        locator = mapping_locator(row.location, row.new_ref)
        if locator:
            rows_by_locator.setdefault(locator, []).append(row)

    project_locations: set[str] = set()
    all_project_labels: dict[str, dict[str, str]] = {}
    project_reports: list[dict[str, Any]] = []
    totals = {
        "items": 0,
        "labels": 0,
        "admonitions": 0,
        "sections": 0,
        "excerptedItems": 0,
        "mappedLabels": 0,
        "mappedAdmonitions": 0,
        "mappedSections": 0,
        "missingLabels": 0,
        "missingAdmonitions": 0,
        "missingSections": 0,
    }

    for path, project in projects:
        location = canonical_output_location(project.outputPath, project.mkdocsRoot)
        prefix = project.numberPrefix or project_number_prefix(project)
        project_locations.add(location)
        missing_admonitions: list[str] = []
        missing_sections: list[str] = []
        mapped_admonitions = 0
        mapped_sections = 0
        label_count = 0
        admonition_count = 0
        section_count = 0
        excerpted_count = 0

        for item in project.items:
            totals["items"] += 1
            if item.excerpt.strip():
                totals["excerptedItems"] += 1
                excerpted_count += 1

            label = item_reference_label(item, prefix)
            if not label:
                continue

            label_count += 1
            kind = "section" if item.kind == "section" else "admonition"
            all_project_labels.setdefault(location, {})[label] = kind

            mapped = mapping_locator(location, label) in rows_by_locator
            if kind == "section":
                section_count += 1
                if mapped:
                    mapped_sections += 1
                else:
                    missing_sections.append(label)
            else:
                admonition_count += 1
                if mapped:
                    mapped_admonitions += 1
                else:
                    missing_admonitions.append(label)

        missing_admonitions.sort(key=natural_key)
        missing_sections.sort(key=natural_key)
        mapped_labels = mapped_admonitions + mapped_sections
        missing_labels = len(missing_admonitions) + len(missing_sections)
        totals["labels"] += label_count
        totals["admonitions"] += admonition_count
        totals["sections"] += section_count
        totals["mappedLabels"] += mapped_labels
        totals["mappedAdmonitions"] += mapped_admonitions
        totals["mappedSections"] += mapped_sections
        totals["missingLabels"] += missing_labels
        totals["missingAdmonitions"] += len(missing_admonitions)
        totals["missingSections"] += len(missing_sections)

        project_reports.append(
            {
                "projectId": project.id,
                "projectPath": str(path),
                "title": project.title,
                "outputPath": project.outputPath,
                "location": location,
                "itemCount": len(project.items),
                "labelCount": label_count,
                "admonitionCount": admonition_count,
                "sectionCount": section_count,
                "excerptedItemCount": excerpted_count,
                "mappedLabelCount": mapped_labels,
                "mappedAdmonitionCount": mapped_admonitions,
                "mappedSectionCount": mapped_sections,
                "missingAdmonitions": missing_admonitions,
                "missingSections": missing_sections,
                "mappingRowCount": len(rows_by_location.get(location, [])),
            }
        )

    stale_rows: list[dict[str, str]] = []
    orphan_rows: list[dict[str, str]] = []
    for row in rows:
        row_payload = {
            "sourceDoc": row.source_doc,
            "newRef": row.new_ref,
            "location": row.location,
            "originalRefs": list(row.original_refs),
        }
        if row.location not in project_locations:
            orphan_rows.append(row_payload)
            continue
        if row.new_ref not in all_project_labels.get(row.location, {}):
            stale_rows.append(row_payload)

    duplicate_locators = {
        locator: len(locator_rows)
        for locator, locator_rows in rows_by_locator.items()
        if len(locator_rows) > 1
    }

    project_reports.sort(key=lambda report: natural_key(str(report["location"])))
    stale_rows.sort(key=lambda row: (natural_key(row["location"]), natural_key(row["newRef"])))
    orphan_rows.sort(key=lambda row: (natural_key(row["location"]), natural_key(row["newRef"])))

    return {
        "subjectId": slugify(subject_id),
        "mappingPath": mapping_path,
        "projectCount": len(projects),
        "mappingRowCount": len(rows),
        "uniqueMappingLocatorCount": len(rows_by_locator),
        "duplicateLocators": duplicate_locators,
        "totals": totals,
        "projects": project_reports,
        "staleRows": stale_rows,
        "orphanRows": orphan_rows,
    }


def format_audit_report(report: dict[str, Any], *, include_sections: bool = False, limit: int = 12) -> str:
    totals = report["totals"]
    duplicate_locators = report["duplicateLocators"]
    stale_rows = report["staleRows"]
    orphan_rows = report["orphanRows"]
    lines = [
        f"Subject: {report['subjectId']}",
        f"Mapping: {report['mappingPath'] or '(none)'}",
        f"Projects: {report['projectCount']}",
        (
            f"Mapping rows: {report['mappingRowCount']} "
            f"({report['uniqueMappingLocatorCount']} unique locators, "
            f"{len(duplicate_locators)} duplicates)"
        ),
        (
            f"Excerpts: {totals['excerptedItems']}/{totals['items']} items have excerpts"
        ),
        (
            f"Admonition coverage: {totals['mappedAdmonitions']}/{totals['admonitions']} "
            f"mapped, {totals['missingAdmonitions']} missing"
        ),
        (
            f"Section coverage: {totals['mappedSections']}/{totals['sections']} "
            f"mapped, {totals['missingSections']} missing"
        ),
        f"Stale rows: {len(stale_rows)}",
        f"Rows for locations without a project: {len(orphan_rows)}",
    ]

    missing_projects = [
        project
        for project in report["projects"]
        if project["missingAdmonitions"] or (include_sections and project["missingSections"])
    ]
    if missing_projects:
        lines.append("")
        lines.append("Missing rows by project:")
        for project in missing_projects:
            missing = list(project["missingAdmonitions"])
            if include_sections:
                missing.extend(project["missingSections"])
            preview = "; ".join(missing[:limit])
            suffix = " ..." if len(missing) > limit else ""
            lines.append(
                f"- {project['location']}: {len(missing)} missing -> {preview}{suffix}"
            )

    if stale_rows:
        lines.append("")
        lines.append("Stale rows:")
        stale_by_location: dict[str, list[str]] = {}
        for row in stale_rows:
            stale_by_location.setdefault(row["location"], []).append(row["newRef"])
        for location in sorted(stale_by_location, key=natural_key):
            values = sorted(stale_by_location[location], key=natural_key)
            preview = "; ".join(values[:limit])
            suffix = " ..." if len(values) > limit else ""
            lines.append(f"- {location}: {len(values)} stale -> {preview}{suffix}")

    if orphan_rows:
        lines.append("")
        lines.append("Rows for locations without a project:")
        orphan_by_location: dict[str, list[str]] = {}
        for row in orphan_rows:
            orphan_by_location.setdefault(row["location"], []).append(row["newRef"])
        for location in sorted(orphan_by_location, key=natural_key):
            values = sorted(orphan_by_location[location], key=natural_key)
            preview = "; ".join(values[:limit])
            suffix = " ..." if len(values) > limit else ""
            lines.append(f"- {location}: {len(values)} rows -> {preview}{suffix}")

    return "\n".join(lines)
