"""Subject endpoints: group related projects and store shared defaults."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from rules import RULE_KINDS, default_rules
from models import CreateProjectRequest, CreateSubjectRequest, Project, ReferenceFile, Subject
from routers.projects import (
    PROJECTS_DIR,
    _create_project,
    _migrate_project_data,
)

router = APIRouter(prefix="/api/subjects", tags=["subjects"])

SUBJECTS_DIR = PROJECTS_DIR / "_subjects"
SUBJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _natural_sort_key(value: str) -> list[tuple[int, Any, int]]:
    key: list[tuple[int, Any, int]] = []
    for part in re.findall(r"\d+|\D+", value or ""):
        if part.isdigit():
            key.append((1, int(part), len(part)))
        else:
            key.append((0, part.casefold(), 0))
    return key


def _subject_path(subject_id: str) -> Path:
    return SUBJECTS_DIR / f"{_slugify(subject_id)}.json"


def _subject_rules_path(subject_id: str, kind: str) -> Path:
    if kind not in RULE_KINDS:
        raise ValueError("kind must be 'match', 'generate', or 'map'")
    return SUBJECTS_DIR / f"{_slugify(subject_id)}_{kind}_rules.md"


def _project_file_candidates() -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(PROJECTS_DIR.iterdir()):
        if path.name == "_subjects":
            continue
        if path.is_dir():
            project_file = path / "project.json"
            if project_file.exists():
                candidates.append(project_file)
    for path in sorted(PROJECTS_DIR.glob("*.json")):
        if (PROJECTS_DIR / path.stem / "project.json").exists():
            continue
        candidates.append(path)
    return candidates


def _load_project_data(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return _migrate_project_data(raw)
    except Exception:
        return None


def _bracket_title_prefix(title: str) -> str:
    match = re.match(r"^\s*\[([^\]]+)\]", title or "")
    return match.group(1).strip() if match else ""


def _infer_subject_id(data: dict[str, Any]) -> str:
    explicit = str(data.get("subjectId") or "").strip()
    if explicit:
        return _slugify(explicit)

    title_prefix = _bracket_title_prefix(str(data.get("title") or ""))
    if title_prefix:
        return _slugify(title_prefix)

    output_path = str(data.get("outputPath") or "").strip()
    if output_path:
        parent_name = Path(os.path.expanduser(output_path)).parent.name
        if parent_name:
            return _slugify(parent_name)

    return _slugify(str(data.get("title") or data.get("id") or "untitled"))


def _infer_subject_name(subject_id: str, projects: list[dict[str, Any]]) -> str:
    title_prefixes = [
        _bracket_title_prefix(str(project.get("title") or ""))
        for project in projects
    ]
    title_prefixes = [value for value in title_prefixes if value]
    if title_prefixes:
        return Counter(title_prefixes).most_common(1)[0][0]

    output_dirs = [
        Path(str(project.get("outputPath") or "")).parent.name
        for project in projects
        if str(project.get("outputPath") or "").strip()
    ]
    output_dirs = [value for value in output_dirs if value]
    if output_dirs:
        return Counter(output_dirs).most_common(1)[0][0].replace("-", " ").title()

    return subject_id.replace("-", " ").title()


def _most_common(values: list[str]) -> str:
    clean = [value for value in values if value]
    return Counter(clean).most_common(1)[0][0] if clean else ""


def _common_references(projects: list[dict[str, Any]]) -> list[ReferenceFile]:
    if not projects:
        return []

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for project in projects:
        for ref in project.get("references", []):
            if not isinstance(ref, dict):
                continue
            key = str(ref.get("originalPath") or ref.get("path") or "").strip()
            if key:
                by_key[key].append(ref)

    required_count = len(projects) if len(projects) > 1 else 1
    shared: list[ReferenceFile] = []
    for key, refs in sorted(by_key.items()):
        if len(refs) < required_count:
            continue
        names = [str(ref.get("name") or "").strip() for ref in refs]
        paths = [str(ref.get("path") or "").strip() for ref in refs]
        original_paths = [str(ref.get("originalPath") or "").strip() for ref in refs]
        canonical_path = _most_common(original_paths) or key
        shared.append(
            ReferenceFile(
                id=hashlib.sha1(key.encode("utf-8")).hexdigest()[:8],
                name=_most_common(names) or Path(key).name,
                path=canonical_path,
                originalPath=canonical_path,
                prepared=all(bool(ref.get("prepared", False)) for ref in refs),
            )
        )
    return shared


def _build_inferred_subject(subject_id: str, projects: list[dict[str, Any]]) -> Subject:
    now = _now()
    output_dirs = [
        str(Path(os.path.abspath(os.path.expanduser(str(project.get("outputPath"))))).parent)
        for project in projects
        if str(project.get("outputPath") or "").strip()
    ]
    blueprint_dirs = [
        str(Path(os.path.abspath(os.path.expanduser(str(project.get("blueprintPath"))))).parent)
        for project in projects
        if str(project.get("blueprintPath") or "").strip()
    ]
    return Subject(
        id=subject_id,
        name=_infer_subject_name(subject_id, projects),
        titlePrefix=_most_common([
            _bracket_title_prefix(str(project.get("title") or ""))
            for project in projects
        ]),
        mkdocsRoot=_most_common([
            str(project.get("mkdocsRoot") or "").strip()
            for project in projects
        ]),
        docsDir=_most_common(output_dirs),
        blueprintDir=_most_common(blueprint_dirs),
        mappingPath=_most_common([
            str(project.get("mappingPath") or "").strip()
            for project in projects
        ]),
        references=_common_references(projects),
        createdAt=now,
        updatedAt=now,
        projectCount=len(projects),
    )


def _load_saved_subjects() -> dict[str, Subject]:
    subjects: dict[str, Subject] = {}
    for path in sorted(SUBJECTS_DIR.glob("*.json")):
        try:
            subject = Subject.model_validate(json.loads(path.read_text(encoding="utf-8")))
            subjects[subject.id] = subject
        except Exception:
            continue
    return subjects


def _save_subject(subject: Subject) -> None:
    path = _subject_path(subject.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(subject.model_dump_json(indent=2), encoding="utf-8")


def _merge_subject(saved: Subject | None, inferred: Subject) -> Subject:
    if saved is None:
        return inferred
    data = saved.model_dump()
    for field in ("name", "titlePrefix", "mkdocsRoot", "docsDir", "blueprintDir", "mappingPath"):
        if not str(data.get(field) or "").strip():
            data[field] = getattr(inferred, field)
    if not data.get("references"):
        data["references"] = [ref.model_dump() for ref in inferred.references]
    data["projectCount"] = inferred.projectCount
    return Subject.model_validate(data)


def _subject_index() -> dict[str, Subject]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in _project_file_candidates():
        data = _load_project_data(path)
        if data is None:
            continue
        grouped[_infer_subject_id(data)].append(data)

    saved = _load_saved_subjects()
    subjects: dict[str, Subject] = {}
    for subject_id, projects in grouped.items():
        inferred = _build_inferred_subject(subject_id, projects)
        subjects[subject_id] = _merge_subject(saved.get(subject_id), inferred)

    for subject_id, subject in saved.items():
        subjects.setdefault(subject_id, subject)

    return subjects


def ensure_subject_rules(subject_id: str, kind: str) -> Path:
    path = _subject_rules_path(subject_id, kind)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(default_rules(kind), encoding="utf-8")
    return path


def subject_rules_path_for_project(project: Project, kind: str) -> Path:
    subject_id = project.subjectId or _infer_subject_id(project.model_dump())
    return ensure_subject_rules(subject_id, kind)


def _get_subject(subject_id: str) -> Subject:
    subject = _subject_index().get(_slugify(subject_id))
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


def _project_belongs_to_subject(project: dict[str, Any], subject_id: str) -> bool:
    return _infer_subject_id(project) == _slugify(subject_id)


def _resolve_subject_relative_path(raw_path: str, base_dir: str) -> str:
    value = (raw_path or "").strip()
    if not value:
        return ""
    expanded = os.path.expanduser(value)
    if os.path.isabs(expanded) or not base_dir:
        return expanded
    return str(Path(os.path.expanduser(base_dir)) / expanded)


@router.get("")
def list_subjects() -> list[Subject]:
    return sorted(_subject_index().values(), key=lambda subject: subject.name.casefold())


@router.post("", status_code=201)
def create_subject(req: CreateSubjectRequest) -> Subject:
    name = (req.name or req.titlePrefix or "Untitled Subject").strip()
    subject_id = _slugify(req.titlePrefix or name)
    existing = _subject_index()
    base_id = subject_id
    index = 2
    while subject_id in existing or _subject_path(subject_id).exists():
        subject_id = f"{base_id}-{index}"
        index += 1

    now = _now()
    subject = Subject(
        id=subject_id,
        name=name,
        titlePrefix=req.titlePrefix.strip(),
        mkdocsRoot=req.mkdocsRoot.strip(),
        docsDir=req.docsDir.strip(),
        blueprintDir=req.blueprintDir.strip(),
        mappingPath=req.mappingPath.strip(),
        references=req.references,
        createdAt=now,
        updatedAt=now,
        projectCount=0,
    )
    _save_subject(subject)
    for kind in RULE_KINDS:
        ensure_subject_rules(subject.id, kind)
    return subject


@router.get("/{subject_id}")
def get_subject(subject_id: str) -> Subject:
    return _get_subject(subject_id)


@router.put("/{subject_id}")
def update_subject(subject_id: str, body: Subject) -> Subject:
    current = _get_subject(subject_id)
    body.id = current.id
    body.createdAt = current.createdAt
    body.updatedAt = _now()
    body.projectCount = current.projectCount
    _save_subject(body)
    return body


@router.get("/{subject_id}/rules/{kind}")
def get_subject_rules(subject_id: str, kind: str) -> dict:
    if kind not in RULE_KINDS:
        raise HTTPException(status_code=400, detail="kind must be 'match', 'generate', or 'map'")
    _get_subject(subject_id)
    path = ensure_subject_rules(subject_id, kind)
    return {"kind": kind, "content": path.read_text(encoding="utf-8")}


@router.put("/{subject_id}/rules/{kind}")
def put_subject_rules(subject_id: str, kind: str, body: dict) -> dict:
    if kind not in RULE_KINDS:
        raise HTTPException(status_code=400, detail="kind must be 'match', 'generate', or 'map'")
    content = body.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    _get_subject(subject_id)
    path = _subject_rules_path(subject_id, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content), encoding="utf-8")
    return {"kind": kind, "content": str(content)}


@router.get("/{subject_id}/projects")
def list_subject_projects(subject_id: str) -> list[dict]:
    _get_subject(subject_id)
    projects: list[dict] = []
    for path in _project_file_candidates():
        data = _load_project_data(path)
        if data is None or not _project_belongs_to_subject(data, subject_id):
            continue
        try:
            project = Project.model_validate(data)
        except Exception:
            continue
        projects.append({
            "id": project.id,
            "subjectId": _slugify(subject_id),
            "title": project.title,
            "createdAt": project.createdAt,
            "updatedAt": project.updatedAt,
            "outputPath": project.outputPath,
            "itemCount": len(project.items),
        })
    return sorted(
        projects,
        key=lambda project: (
            _natural_sort_key(str(project["title"])),
            _natural_sort_key(str(project.get("outputPath") or "")),
            str(project["createdAt"]),
        ),
    )


@router.post("/{subject_id}/projects", status_code=201)
def create_subject_project(subject_id: str, req: CreateProjectRequest) -> Project:
    subject = _get_subject(subject_id)
    data = req.model_dump()
    data["outputPath"] = _resolve_subject_relative_path(data.get("outputPath", ""), subject.docsDir)
    data["blueprintPath"] = _resolve_subject_relative_path(data.get("blueprintPath", ""), subject.blueprintDir)
    normalized = CreateProjectRequest.model_validate(data)
    return _create_project(
        normalized,
        subject_id=subject.id,
        default_mkdocs_root=subject.mkdocsRoot,
        default_mapping_path=subject.mappingPath,
        default_references=subject.references,
    )
