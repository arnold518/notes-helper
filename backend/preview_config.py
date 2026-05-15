"""Helpers for building resilient MkDocs preview configs."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def build_preview_mkdocs_config(
    config: dict[str, Any],
    *,
    docs_dir: Path,
    site_dir: Path,
    preview_label: str = "Preview",
) -> dict[str, Any]:
    """Return a preview-safe MkDocs config derived from an existing config.

    The preview only renders ``preview.md`` inside a synthetic docs directory.
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
    result["nav"] = [{preview_label: "preview.md"}]
    result["plugins"] = []
    return result
