"""Parse blueprint.md → flat list of Items.

Each line (or multi-line bullet) becomes one Item. The type is inferred
from a prefix→type map. Section headings are handled natively (#/##/###).
Admonition types are validated against the mkdocs admonition set when provided.
"""
from __future__ import annotations
import re
from models import Item

# Default short-prefix → full type name.
# Keys are lower-case; values must match mkdocs admonition type names.
DEFAULT_PREFIX_MAP: dict[str, str] = {
    "def":  "definition",
    "con":  "concept",
    "thm":  "theorem",
    "lem":  "lemma",
    "cor":  "corollary",
    "prop": "proposition",
    "ex":   "example",
    "exc":  "exercise",
    "exer": "exercise",
    "exr":  "exercise",
    "prf":  "proof",
    "rem":  "remark",
    "note": "note",
    "warn": "warning",
    "tip":  "tip",
    "info": "info",
}


def parse_blueprint(
    path: str,
    prefix_map: dict[str, str] | None = None,
    admonition_types: list[str] | None = None,
) -> tuple[str, list[Item]]:
    """Return (title, items) from a blueprint file.

    Args:
        path: path to the blueprint .md file.
        prefix_map: optional overrides/additions to DEFAULT_PREFIX_MAP.
        admonition_types: valid mkdocs admonition type strings. When provided,
            resolved admonition types are validated against this set; the prefix
            itself is also tried as a direct type name before falling back.
    """
    raw_map = {**DEFAULT_PREFIX_MAP, **(prefix_map or {})}
    effective_map = {str(k).lower(): v for k, v in raw_map.items()}
    adm_set: set[str] = set(admonition_types or [])

    def resolve_admonition_type(prefix: str) -> str | None:
        """Map a bullet prefix to a validated admonition type, or None."""
        p = prefix.lower()

        # 1. Longest-prefix lookup in the prefix map (e.g., "exer" over "ex")
        map_keys = [k for k in effective_map.keys() if p.startswith(k)]
        if map_keys:
            best_key = max(map_keys, key=len)
            candidate = effective_map[best_key]
            if not adm_set or candidate in adm_set:
                return candidate
            # Mapped value not in mkdocs set — try the prefix itself
            if p in adm_set:
                return p
            # Still resolve to the mapped value; mkdocs may accept it anyway
            return candidate

        # 2. No map entry — accept if prefix is itself a known admonition type
        if p in adm_set:
            return p

        return None  # unrecognised prefix

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    items: list[Item] = []
    title = ""
    counter = 0

    # Buffer for the item currently being built (supports multi-line bullets)
    buf_kind: str | None = None
    buf_type: str = ""
    buf_lines: list[str] = []

    def flush() -> None:
        nonlocal buf_kind, buf_type, buf_lines, counter
        if buf_kind is None:
            return
        content = " ".join(buf_lines).strip()
        if content:
            items.append(Item(
                kind=buf_kind,
                id=f"i{counter}",
                type=buf_type,
                content=content,
            ))
            counter += 1
        buf_kind = None
        buf_type = ""
        buf_lines = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        # Empty line → end of current item
        if not stripped:
            flush()
            continue

        # ── Section heading: always single-line ──────────────────────────────
        # Markdown headings may be indented up to 3 spaces and often appear
        # without a space after hashes in hand-written blueprints.
        h_match = re.match(r"^\s{0,3}(#{1,3})\s*(.+?)\s*$", line)
        if h_match:
            flush()
            level = len(h_match.group(1))
            text = h_match.group(2).strip()
            if not title:
                title = text
            items.append(Item(
                kind="section",
                id=f"i{counter}",
                type=f"h{level}",
                content=text,
            ))
            counter += 1
            continue

        # ── Bullet entry: "- PREFIX : content" ───────────────────────────────
        bullet_match = re.match(r"^\s*-\s+(\S+?)\s*:\s*(.*)", line)
        if bullet_match:
            flush()
            prefix = bullet_match.group(1)
            text = bullet_match.group(2).strip()
            resolved = resolve_admonition_type(prefix)
            if resolved is not None:
                buf_kind = "admonition"
                buf_type = resolved
            else:
                # Unknown prefix — fall through as plain text
                buf_kind = "text"
                buf_type = ""
            buf_lines = [text] if text else []
            continue

        # ── Continuation line (indented under a bullet) ───────────────────────
        if buf_kind is not None and (line.startswith("  ") or line.startswith("\t")):
            buf_lines.append(stripped)
            continue

        # ── Plain text line ───────────────────────────────────────────────────
        flush()
        buf_kind = "text"
        buf_type = ""
        buf_lines = [stripped]

    flush()
    return title or "Untitled", items
