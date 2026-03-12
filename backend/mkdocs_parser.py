"""Parse MkDocs root to extract custom admonition types and colors."""
from __future__ import annotations
import os
import re
from pathlib import Path


def get_admonition_types(mkdocs_root: str) -> list[dict]:
    """Return list of {type, color} from extra.css in the MkDocs root."""
    root = Path(os.path.expanduser(mkdocs_root))
    # Find extra.css - commonly in docs/stylesheets/ or docs/assets/
    candidates = [
        root / "docs" / "stylesheets" / "extra.css",
        root / "docs" / "assets" / "extra.css",
        root / "docs" / "extra.css",
        root / "extra.css",
    ]
    css_path = None
    for c in candidates:
        if c.exists():
            css_path = c
            break

    if css_path is None:
        # Try to find any CSS file with admonition rules
        for css_file in root.rglob("*.css"):
            content = css_file.read_text(errors="replace")
            if "--md-admonition-icon--" in content:
                css_path = css_file
                break

    if css_path is None:
        return []

    css = css_path.read_text(errors="replace")
    result = []

    # Find custom admonition type names from icon variable declarations
    # Pattern: --md-admonition-icon--{type}: ...
    type_names = re.findall(r"--md-admonition-icon--([a-z0-9_-]+)\s*:", css)

    # For each type, try to find its border color
    for atype in type_names:
        color = ""
        # Look for .admonition.{type} block
        block_match = re.search(
            rf"\.admonition\.{re.escape(atype)}\s*\{{([^}}]*)\}}", css
        )
        if block_match:
            block = block_match.group(1)
            color_match = re.search(r"border-color\s*:\s*([^;]+);", block)
            if color_match:
                color = color_match.group(1).strip()
        result.append({"type": atype, "color": color})

    return result
