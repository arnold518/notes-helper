"""Helpers for building resilient MkDocs preview configs."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
from typing import Any


_FALLBACK_PREVIEW_PATH = Path("preview.md")


def build_preview_mkdocs_config(
    config: dict[str, Any],
    *,
    docs_dir: Path,
    site_dir: Path,
    preview_label: str = "Preview",
    preview_path: str = "preview.md",
) -> dict[str, Any]:
    """Return a preview-safe MkDocs config derived from an existing config.

    The preview renders one page inside a synthetic docs directory, preserving
    its source-relative path when available so links to nearby assets resolve.
    Source nav trees often reference files outside that synthetic docs dir and
    may even contain malformed entries such as YAML ``null`` from dangling list
    items. Source plugins can also assume a full site and crash when pointed at
    a single synthetic preview page. Replace the nav with a single preview page
    and drop inherited plugins so MkDocs can build reliably while still
    preserving theme, extensions, and asset settings.
    """
    result = deepcopy(config if isinstance(config, dict) else {})
    result["docs_dir"] = str(docs_dir)
    result["site_dir"] = str(site_dir)
    result["nav"] = [{preview_label: preview_path}]
    result["plugins"] = []
    return result


def resolve_preview_document_path(
    config: dict[str, Any],
    *,
    mkdocs_root: Path,
    output_path: Path | None,
) -> Path:
    """Preserve a source document's path relative to the MkDocs docs directory."""
    if output_path is None:
        return _FALLBACK_PREVIEW_PATH

    configured_docs_dir = config.get("docs_dir", "docs")
    if not isinstance(configured_docs_dir, str):
        return _FALLBACK_PREVIEW_PATH

    docs_dir = Path(configured_docs_dir).expanduser()
    if not docs_dir.is_absolute():
        docs_dir = mkdocs_root / docs_dir

    try:
        relative_path = output_path.expanduser().resolve().relative_to(docs_dir.resolve())
    except ValueError:
        return _FALLBACK_PREVIEW_PATH

    if relative_path.suffix.lower() not in {".md", ".markdown"}:
        return _FALLBACK_PREVIEW_PATH
    return relative_path


def merge_preview_asset_tree(source_dir: Path, destination_dir: Path) -> None:
    """Merge one asset tree into the synthetic preview docs directory.

    Preview pages need both project-wide MkDocs assets (for example,
    ``assets/stylesheets/extra.css``) and assets beside the document being
    previewed (for example, ``abstract-algebra/assets/6.1.jpg``).  A directory
    symlink cannot represent both trees, so replace any legacy symlink and copy
    the source into a real mergeable directory.
    """
    if not source_dir.is_dir():
        return

    if destination_dir.is_symlink() or (
        destination_dir.exists() and not destination_dir.is_dir()
    ):
        destination_dir.unlink()

    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
