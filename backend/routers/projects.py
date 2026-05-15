"""Project CRUD endpoints."""
from __future__ import annotations
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from mapping_store import (
    canonical_output_location,
    delete_target_row,
    item_reference_label,
    output_location_candidates,
    rename_target_ref,
    sync_project_reverse_links,
)
from models import Project, CreateProjectRequest, Item, ReferenceFile

router = APIRouter(prefix="/api/projects", tags=["projects"])

PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", Path(__file__).parent.parent.parent / "projects"))
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def _project_path(project_id: str) -> Path:
    return _project_dir(project_id) / "project.json"


def _legacy_project_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"


def _project_refs_dir(project_id: str) -> Path:
    return _project_dir(project_id) / "refs"


def _infer_mkdocs_root_from_output_path(output_path: str) -> str:
    """Infer MkDocs project root from an output markdown file path."""
    raw = output_path.strip()
    if not raw:
        return ""

    path = Path(os.path.abspath(os.path.expanduser(raw)))
    start = path.parent if path.suffix else path

    # Preferred: walk upward until mkdocs.yml is found.
    for candidate in [start, *start.parents]:
        if (candidate / "mkdocs.yml").is_file():
            return str(candidate)

    # Fallback: trim path at /docs/ segment if present.
    parts = start.parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx > 0:
            return str(Path(*parts[:idx]))

    # Last resort: use the containing directory.
    return str(start)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def _unique_file_path(parent: Path, file_name: str) -> Path:
    candidate = parent / file_name
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    index = 2
    while candidate.exists():
        candidate = parent / f"{stem}_{index}{suffix}"
        index += 1
    return candidate


def _strip_json_comments(content: str) -> str:
    """Remove // and /* */ comments from JSONC while preserving quoted strings."""
    out: list[str] = []
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(content):
        ch = content[i]
        nxt = content[i + 1] if i + 1 < len(content) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            if ch == "\n":
                out.append(ch)
            i += 1
            continue

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_string = False
            i += 1
            continue

        if ch == "\"":
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _coerce_prefixes(raw: Any) -> list[str]:
    if isinstance(raw, str):
        val = raw.strip()
        return [val] if val else []
    if isinstance(raw, list):
        vals: list[str] = []
        for item in raw:
            if isinstance(item, str):
                val = item.strip()
                if val:
                    vals.append(val)
        return vals
    return []


def _coerce_body(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        lines = [str(line) for line in raw]
        return "\n".join(lines)
    return ""


def _load_vscode_snippet_file(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json.loads(_strip_json_comments(text))

    if not isinstance(data, dict):
        return []

    snippets: list[dict[str, str]] = []
    for name, raw_snippet in data.items():
        if not isinstance(raw_snippet, dict):
            continue

        prefixes = _coerce_prefixes(raw_snippet.get("prefix"))
        body = _coerce_body(raw_snippet.get("body"))
        if not prefixes or not body:
            continue

        description = str(raw_snippet.get("description") or "").strip()
        scope = str(raw_snippet.get("scope") or "").strip()
        snippet_name = str(name).strip() or path.stem

        for prefix in prefixes:
            snippets.append({
                "name": snippet_name,
                "prefix": prefix,
                "body": body,
                "description": description,
                "scope": scope,
                "sourceFile": path.name,
            })
    return snippets


_VSCODE_CONFIG_FILES = frozenset({
    "settings.json", "extensions.json", "launch.json",
    "tasks.json", "c_cpp_properties.json", "keybindings.json",
})


def _collect_vscode_snippets(vscode_dir: Path) -> list[dict[str, str]]:
    # Prefer *.code-snippets; also allow *.json but skip known VS Code config files.
    files: list[Path] = sorted(vscode_dir.glob("*.code-snippets"))
    files.extend(
        p for p in sorted(vscode_dir.glob("*.json"))
        if p.name not in _VSCODE_CONFIG_FILES
    )

    snippets: list[dict[str, str]] = []
    for path in files:
        try:
            snippets.extend(_load_vscode_snippet_file(path))
        except Exception:
            # Ignore malformed files rather than failing the whole request.
            continue
    return snippets


def _copy_reference_to_project(project_id: str, source_path: Path, source_name: str | None = None) -> Path:
    refs_dir = _project_refs_dir(project_id)
    refs_dir.mkdir(parents=True, exist_ok=True)
    base_name = (source_name or source_path.name).strip() or source_path.name
    base_name = Path(base_name).name
    dest = _unique_file_path(refs_dir, base_name)
    shutil.copyfile(source_path, dest)
    return dest.resolve()


def _cleanup_removed_reference_file(
    project_id: str,
    removed_ref: ReferenceFile,
    remaining_refs: list[ReferenceFile],
) -> None:
    raw_path = os.path.expanduser((removed_ref.path or "").strip())
    if not raw_path:
        return

    ref_path = Path(raw_path)
    refs_dir = _project_refs_dir(project_id)
    if not _is_within(ref_path, refs_dir):
        return

    ref_resolved = ref_path.resolve(strict=False)
    remaining_paths = {
        str(Path(os.path.expanduser((ref.path or "").strip())).resolve(strict=False))
        for ref in remaining_refs
        if (ref.path or "").strip()
    }
    if str(ref_resolved) in remaining_paths:
        return

    if ref_path.exists() and ref_path.is_file():
        ref_path.unlink()

    prep_tmp = Path(str(ref_path) + ".prep.tmp")
    if prep_tmp.exists() and prep_tmp.is_file():
        prep_tmp.unlink()


def _normalize_references(data: dict) -> dict:
    refs: list[dict] = []
    for ref in data.get("references", []):
        if not isinstance(ref, dict):
            continue
        ref_id = str(ref.get("id") or uuid.uuid4().hex[:8])
        ref_name = str(ref.get("name") or "").strip()
        ref_path = str(ref.get("path") or "").strip()
        prepared = bool(ref.get("prepared", False))
        prepared_path = str(ref.get("preparedPath") or "").strip()

        # Legacy behavior had separate preparedPath. New behavior keeps one file path.
        if prepared and prepared_path:
            ref_path = prepared_path
        if not ref_name:
            ref_name = Path(ref_path).name if ref_path else f"{ref_id}.md"

        original_path = str(ref.get("originalPath") or "").strip()

        refs.append({
            "id": ref_id,
            "name": ref_name,
            "path": ref_path,
            "originalPath": original_path,
            "prepared": prepared,
        })
    data["references"] = refs
    return data


def _migrate_project_data(data: dict) -> dict:
    """Migrate old-format project data to new format in-place."""
    # Convert textbookPath → single reference
    if "textbookPath" in data and "references" not in data:
        tbp = data.pop("textbookPath", "")
        if tbp:
            data["references"] = [{
                "id": uuid.uuid4().hex[:8],
                "name": Path(tbp).name,
                "path": tbp,
                "prepared": False,
            }]
        else:
            data["references"] = []
    data.setdefault("references", [])
    data.pop("markdownRulesPath", None)
    data.setdefault("blueprintPath", "")
    data.setdefault("outputPath", "")
    data.setdefault("subjectId", "")
    data = _normalize_references(data)
    data.pop("agent", None)
    data.pop("agentProvider", None)

    # Migrate items
    new_items = []
    for item in data.get("items", []):
        if item.get("kind") == "section" and "type" not in item:
            # Old SectionItem → new Item (has "level"/"title" but no "type")
            level = item.get("level", 1)
            new_items.append({
                "kind": "section",
                "id": item["id"],
                "type": f"h{level}",
                "content": item.get("title", item.get("content", "")),
                "excerpt": "",
                "document": item.get("introText", ""),
                "status": "pending",
            })
        elif item.get("kind") == "entry":
            # Old EntryItem → new Item
            # blueprint field: "def : text" → content = "text", type = "def"
            blueprint = item.get("blueprint", item.get("content", ""))
            etype = item.get("type", "")
            content = blueprint
            # Strip leading "type : " prefix if present
            import re
            m = re.match(r"^[a-z]+\s*:\s*(.*)", blueprint, re.IGNORECASE)
            if m:
                content = m.group(1).strip()
            new_items.append({
                "kind": "admonition",
                "id": item["id"],
                "type": etype,
                "content": content,
                "excerpt": item.get("excerpt", ""),
                "document": item.get("admonition", item.get("document", "")),
                "status": item.get("status", "pending"),
            })
        else:
            # Already new format or unknown
            new_items.append(item)
    data["items"] = new_items
    return data


def _ensure_local_reference_files(project: Project) -> bool:
    changed = False
    project_root = _project_dir(project.id)
    for ref in project.references:
        raw_path = os.path.expanduser(ref.path)
        if not raw_path:
            continue
        source_path = Path(raw_path)
        if _is_within(source_path, project_root):
            continue
        if not source_path.exists() or not source_path.is_file():
            continue
        copied = _copy_reference_to_project(project.id, source_path, source_name=ref.name)
        if not ref.originalPath:
            ref.originalPath = str(source_path.resolve())
        ref.path = str(copied)
        ref.name = copied.name
        changed = True
    return changed


def _load_project(project_id: str) -> Project:
    p = _project_path(project_id)
    legacy = _legacy_project_path(project_id)
    source_path = p if p.exists() else legacy
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    raw = json.loads(source_path.read_text())
    raw = _migrate_project_data(raw)
    project = Project.model_validate(raw)

    migrated_from_legacy = source_path == legacy
    localized_refs = _ensure_local_reference_files(project)
    if migrated_from_legacy or localized_refs:
        _save_project(project, touch_updated=False)

    return project


import re as _re


def _extract_prefix(project: Project) -> str:
    for item in project.items:
        if item.kind == "section" and item.type == "h1":
            m = _re.search(r'(?:§\s*)?(\d+(?:\.\d+)*)', item.content)
            if m:
                return m.group(1)
    return ""


def _item_reference_label(item: Item, prefix: str) -> str:
    return item_reference_label(item, prefix)


def _build_reference_graph(
    project: Project,
    *,
    prefix: str,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    label_to_item_id: dict[str, str] = {}
    ambiguous_labels: set[str] = set()
    for item in project.items:
        label = _item_reference_label(item, prefix).strip()
        if not label:
            continue
        if label in label_to_item_id:
            ambiguous_labels.add(label)
            continue
        label_to_item_id[label] = item.id

    for label in ambiguous_labels:
        label_to_item_id.pop(label, None)

    references: dict[str, list[str]] = {item.id: [] for item in project.items}
    referenced_by: dict[str, list[str]] = {item.id: [] for item in project.items}

    for item in project.items:
        if not item.document:
            continue
        seen_targets: set[str] = set()
        for match in _re.finditer(r"\*\*(.+?)\*\*", item.document):
            label = match.group(1).strip()
            target_id = label_to_item_id.get(label)
            if not target_id or target_id == item.id or target_id in seen_targets:
                continue
            references[item.id].append(target_id)
            referenced_by[target_id].append(item.id)
            seen_targets.add(target_id)

    return references, referenced_by


def _apply_reference_graph(project: Project) -> None:
    references, referenced_by = _build_reference_graph(project, prefix=project.numberPrefix)
    for item in project.items:
        item.references = references.get(item.id, [])
        item.referencedBy = referenced_by.get(item.id, [])


def _reference_snapshot(project: Project) -> tuple[dict[str, str], dict[str, list[str]]]:
    prefix = project.numberPrefix or _extract_prefix(project)
    labels = {
        item.id: _item_reference_label(item, prefix)
        for item in project.items
    }
    _, referenced_by = _build_reference_graph(project, prefix=prefix)
    return labels, referenced_by


def _rewrite_document_reference_label(document: str, old_ref: str, new_ref: str) -> str:
    if not document or not old_ref or not new_ref or old_ref == new_ref:
        return document
    return document.replace(f"**{old_ref}**", f"**{new_ref}**")


def _renumber_items(
    project: Project,
    *,
    previous_reference_labels: dict[str, str] | None = None,
    previous_referenced_by: dict[str, list[str]] | None = None,
) -> None:
    """Sequentially number admonitions and keep downstream references consistent."""
    if previous_reference_labels is None or previous_referenced_by is None:
        previous_reference_labels, previous_referenced_by = _reference_snapshot(project)

    new_prefix = _extract_prefix(project)
    project.numberPrefix = new_prefix

    n = 1
    for item in project.items:
        if item.kind == "admonition":
            if item.autonumber:
                item.number = n
                n += 1
        else:
            item.number = 0

    items_by_id = {item.id: item for item in project.items}
    current_reference_labels = {
        item.id: _item_reference_label(item, new_prefix)
        for item in project.items
    }

    for item_id, old_ref in previous_reference_labels.items():
        new_ref = current_reference_labels.get(item_id, "")
        if not old_ref or not new_ref or old_ref == new_ref:
            continue

        item = items_by_id.get(item_id)
        if item is not None and item.document:
            item.document = item.document.replace(old_ref, new_ref)

        for source_id in previous_referenced_by.get(item_id, []):
            source_item = items_by_id.get(source_id)
            if source_item is None or not source_item.document or source_id == item_id:
                continue
            source_item.document = _rewrite_document_reference_label(source_item.document, old_ref, new_ref)

        if project.mappingPath:
            rename_target_ref(
                project.mappingPath,
                canonical_output_location(project.outputPath, project.mkdocsRoot),
                old_ref,
                new_ref,
                location_aliases=output_location_candidates(project.outputPath, project.mkdocsRoot),
            )


def _recompute_status(project: Project) -> None:
    for item in project.items:
        if item.status == "approved":
            continue
        if item.document.strip():
            item.status = "generated"
        elif item.excerpt.strip():
            item.status = "matched"
        else:
            item.status = "pending"


def _save_project(
    project: Project,
    touch_updated: bool = True,
    *,
    previous_reference_labels: dict[str, str] | None = None,
    previous_referenced_by: dict[str, list[str]] | None = None,
) -> None:
    _renumber_items(
        project,
        previous_reference_labels=previous_reference_labels,
        previous_referenced_by=previous_referenced_by,
    )
    _recompute_status(project)
    _apply_reference_graph(project)
    if project.mappingPath:
        sync_project_reverse_links(project)
    if touch_updated:
        project.updatedAt = datetime.now(timezone.utc).isoformat()
    path = _project_path(project.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(project.model_dump_json(indent=2))
    legacy = _legacy_project_path(project.id)
    if legacy.exists():
        legacy.unlink()


@router.get("")
def list_projects() -> list[dict]:
    projects = []
    seen: set[str] = set()

    file_candidates = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir():
            project_file = d / "project.json"
            if project_file.exists():
                file_candidates.append(project_file)
    for f in sorted(PROJECTS_DIR.glob("*.json")):
        if (PROJECTS_DIR / f.stem / "project.json").exists():
            continue
        file_candidates.append(f)

    for f in file_candidates:
        try:
            raw = json.loads(f.read_text())
            raw = _migrate_project_data(raw)
            p = Project.model_validate(raw)
            is_legacy_file = f.parent == PROJECTS_DIR and f.suffix == ".json"
            if is_legacy_file:
                # Migrate legacy flat JSON into projects/<id>/project.json on listing.
                p = _load_project(p.id)
            if p.id in seen:
                continue
            seen.add(p.id)
            projects.append({"id": p.id, "title": p.title, "createdAt": p.createdAt, "updatedAt": p.updatedAt})
        except Exception:
            pass
    return projects


def _clone_reference_defaults(references: list[ReferenceFile]) -> list[ReferenceFile]:
    cloned: list[ReferenceFile] = []
    for ref in references:
        cloned.append(
            ReferenceFile(
                id=uuid.uuid4().hex[:8],
                name=ref.name,
                path=ref.path,
                originalPath=ref.originalPath,
                prepared=ref.prepared,
            )
        )
    return cloned


def _create_project(
    req: CreateProjectRequest,
    *,
    subject_id: str = "",
    default_mkdocs_root: str = "",
    default_mapping_path: str = "",
    default_references: list[ReferenceFile] | None = None,
) -> Project:
    from blueprint_parser import parse_blueprint

    now = datetime.now(timezone.utc).isoformat()
    project_id = uuid.uuid4().hex[:12]
    user_title = req.title.strip()
    items: list[Item] = []
    output_path = (req.outputPath or "").strip()
    if output_path:
        output_path = os.path.abspath(os.path.expanduser(output_path))
    mkdocs_root = (req.mkdocsRoot or default_mkdocs_root or "").strip()
    if not mkdocs_root and output_path:
        mkdocs_root = _infer_mkdocs_root_from_output_path(output_path)
    if mkdocs_root:
        mkdocs_root = os.path.abspath(os.path.expanduser(mkdocs_root))

    if req.blueprintPath:
        blueprint_path = os.path.expanduser(req.blueprintPath)
        if not os.path.isfile(blueprint_path):
            raise HTTPException(status_code=400, detail=f"Blueprint not found: {blueprint_path}")
        admonition_types: list[str] = []
        if mkdocs_root:
            from mkdocs_parser import get_admonition_types
            try:
                admonition_types = [t["type"] for t in get_admonition_types(mkdocs_root)]
            except Exception:
                pass
        parsed_title, items = parse_blueprint(blueprint_path, admonition_types=admonition_types)
        title = user_title or parsed_title or "Untitled"
        blueprint_path = os.path.abspath(blueprint_path)
    else:
        blueprint_path = ""
        title = user_title or "Untitled"

    project = Project(
        id=project_id,
        subjectId=subject_id,
        title=title,
        blueprintPath=blueprint_path,
        references=_clone_reference_defaults(default_references or []),
        mkdocsRoot=mkdocs_root,
        outputPath=output_path,
        mappingPath=req.mappingPath or default_mapping_path or "",
        items=items,
        createdAt=now,
        updatedAt=now,
    )
    _ensure_local_reference_files(project)
    _save_project(project)
    return project


@router.post("", status_code=201)
def create_project(req: CreateProjectRequest) -> Project:
    return _create_project(req)


@router.get("/{project_id}/vscode-snippets")
def get_project_vscode_snippets(project_id: str) -> dict:
    project = _load_project(project_id)

    mkdocs_root = (project.mkdocsRoot or "").strip()
    if not mkdocs_root and project.outputPath:
        mkdocs_root = _infer_mkdocs_root_from_output_path(project.outputPath)

    if not mkdocs_root:
        return {"mkdocsRoot": "", "snippetDir": "", "snippets": []}

    mkdocs_root_path = Path(os.path.abspath(os.path.expanduser(mkdocs_root)))
    vscode_dir = mkdocs_root_path / ".vscode"
    if not vscode_dir.is_dir():
        return {
            "mkdocsRoot": str(mkdocs_root_path),
            "snippetDir": str(vscode_dir),
            "snippets": [],
        }

    snippets = _collect_vscode_snippets(vscode_dir)
    return {
        "mkdocsRoot": str(mkdocs_root_path),
        "snippetDir": str(vscode_dir),
        "snippets": snippets,
    }


@router.get("/{project_id}")
def get_project(project_id: str) -> Project:
    return _load_project(project_id)


@router.put("/{project_id}")
def update_project(project_id: str, body: Project) -> Project:
    current = _load_project(project_id)
    previous_reference_labels, previous_referenced_by = _reference_snapshot(current)
    body.id = project_id
    _ensure_local_reference_files(body)
    _save_project(
        body,
        previous_reference_labels=previous_reference_labels,
        previous_referenced_by=previous_referenced_by,
    )
    return body


# ── Item CRUD ──────────────────────────────────────────────────────────────────

class InsertItemRequest(Item):
    afterId: str | None = None


@router.post("/{project_id}/items", status_code=201)
def insert_item(project_id: str, body: dict) -> Project:
    project = _load_project(project_id)
    previous_reference_labels, previous_referenced_by = _reference_snapshot(project)
    after_id = body.pop("afterId", None)
    # Generate id if not provided
    if "id" not in body or not body["id"]:
        body["id"] = uuid.uuid4().hex[:8]
    body.setdefault("kind", "admonition")
    body.setdefault("type", "def")
    body.setdefault("content", "")
    body.setdefault("excerpt", "")
    body.setdefault("document", "")
    body.setdefault("status", "pending")
    new_item = Item.model_validate(body)

    if after_id:
        idx = next((i for i, it in enumerate(project.items) if it.id == after_id), None)
        if idx is not None:
            project.items.insert(idx + 1, new_item)
        else:
            project.items.append(new_item)
    else:
        project.items.append(new_item)

    _save_project(
        project,
        previous_reference_labels=previous_reference_labels,
        previous_referenced_by=previous_referenced_by,
    )
    return project


@router.delete("/{project_id}/items/{item_id}")
def delete_item(project_id: str, item_id: str) -> Project:
    project = _load_project(project_id)
    previous_reference_labels, previous_referenced_by = _reference_snapshot(project)
    if project.mappingPath:
        item = next((it for it in project.items if it.id == item_id), None)
        if item is not None:
            prefix = _extract_prefix(project)
            cap_type = item.type.capitalize() if item.kind == "admonition" else ""
            if item.kind == "admonition" and item.number != 0:
                new_ref = f"{cap_type} {prefix}.{item.number}" if prefix else f"{cap_type} {item.number}"
            elif item.kind == "section":
                new_ref = f"§ {item.content}"
            else:
                new_ref = ""
            if new_ref:
                delete_target_row(
                    project.mappingPath,
                    canonical_output_location(project.outputPath, project.mkdocsRoot),
                    new_ref,
                    location_aliases=output_location_candidates(project.outputPath, project.mkdocsRoot),
                )
    project.items = [it for it in project.items if it.id != item_id]
    _save_project(
        project,
        previous_reference_labels=previous_reference_labels,
        previous_referenced_by=previous_referenced_by,
    )
    return project


@router.patch("/{project_id}/items/{item_id}")
def patch_item(project_id: str, item_id: str, body: dict) -> Project:
    project = _load_project(project_id)
    previous_reference_labels, previous_referenced_by = _reference_snapshot(project)
    for i, it in enumerate(project.items):
        if it.id == item_id:
            data = it.model_dump()
            # Only allow updating specific fields
            for field in ("type", "content", "excerpt", "document", "status", "kind", "autonumber", "number"):
                if field in body:
                    data[field] = body[field]
            project.items[i] = Item.model_validate(data)
            break
    else:
        raise HTTPException(status_code=404, detail="Item not found")
    _save_project(
        project,
        previous_reference_labels=previous_reference_labels,
        previous_referenced_by=previous_referenced_by,
    )
    return project


# ── Reference Management ───────────────────────────────────────────────────────

@router.post("/{project_id}/references", status_code=201)
def add_reference(project_id: str, body: dict) -> Project:
    """Add a reference file.

    - name (required): filename to use in the project
    - path (optional): source file to copy; if omitted, an empty file is created
    """
    project = _load_project(project_id)
    name = body.get("name", "").strip()
    path = body.get("path", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not name.endswith(".md"):
        name += ".md"
    name = Path(name).name  # strip any directory component

    refs_dir = _project_refs_dir(project_id)
    refs_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_file_path(refs_dir, name)

    if path:
        expanded = os.path.expanduser(path)
        if not os.path.isfile(expanded):
            raise HTTPException(status_code=400, detail=f"File not found: {expanded}")
        shutil.copyfile(expanded, dest)
    else:
        dest.write_text("", encoding="utf-8")

    ref = ReferenceFile(
        id=uuid.uuid4().hex[:8],
        name=dest.name,
        path=str(dest.resolve()),
        originalPath=str(Path(os.path.abspath(os.path.expanduser(path)))) if path else str(dest.resolve()),
        prepared=False,
    )
    project.references.append(ref)
    _save_project(project)
    return project


@router.delete("/{project_id}/references/{ref_id}")
def remove_reference(project_id: str, ref_id: str) -> Project:
    project = _load_project(project_id)
    removed_ref = next((r for r in project.references if r.id == ref_id), None)
    if removed_ref is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    project.references = [r for r in project.references if r.id != ref_id]
    _save_project(project)
    _cleanup_removed_reference_file(project_id, removed_ref, project.references)
    return project
