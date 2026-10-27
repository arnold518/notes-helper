"""Parse MkDocs root to extract custom admonition types and colors."""
from __future__ import annotations
import os
import re
from pathlib import Path


_ADMONITION_SELECTOR_RE = re.compile(r"(?:\.admonition|\bdetails)\.([a-z0-9_-]+)")


def get_admonition_types(mkdocs_root: str) -> list[dict]:
    """Return list of {type, color} from extra.css in the MkDocs root."""
    root = Path(os.path.expanduser(mkdocs_root))
    # Find extra.css - commonly in docs/stylesheets/ or docs/assets/
    candidates = [
        root / "docs" / "stylesheets" / "extra.css",
        root / "docs" / "assets" / "stylesheets" / "extra.css",
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
            if "--md-admonition-icon--" in content or _ADMONITION_SELECTOR_RE.search(content):
                css_path = css_file
                break

    if css_path is None:
        return []

    css = re.sub(r"/\*.*?\*/", "", css_path.read_text(errors="replace"), flags=re.DOTALL)
    colors = dict.fromkeys(re.findall(r"--md-admonition-icon--([a-z0-9_-]+)\s*:", css), "")

    # Styled types may share an icon, as corollary does with theorem.
    # Read whole selector groups so .admonition and details share their color.
    for selectors, block in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        color_match = re.search(r"\bborder-color\s*:\s*([^;{}]+)", block)
        for atype in _ADMONITION_SELECTOR_RE.findall(selectors):
            colors.setdefault(atype, "")
            if color_match:
                colors[atype] = color_match.group(1).strip()

    return [{"type": atype, "color": color} for atype, color in colors.items()]
