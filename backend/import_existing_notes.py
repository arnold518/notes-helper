from __future__ import annotations

import re
from typing import Iterable

from models import Item


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_ADMONITION_RE = re.compile(r'^!!!\s+([a-zA-Z0-9_-]+)(?:\s+"([^"]*)")?\s*$')
_REF_NUMBER_RE = re.compile(r"\b(\d+)\.(\d+)\b")


def summarize_text_block(document: str, *, limit: int = 120) -> str:
    text = " ".join(document.strip().split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def parse_admonition_header(
    line: str,
    *,
    default_prefix: str = "",
) -> tuple[str, str, int]:
    match = _ADMONITION_RE.match(line.strip())
    if not match:
        raise ValueError(f"Not an admonition header: {line!r}")

    admonition_type = match.group(1).strip().lower()
    title = (match.group(2) or "").strip()
    number = extract_note_number(title, default_prefix=default_prefix)
    return admonition_type, title, number


def extract_note_number(title: str, *, default_prefix: str = "") -> int:
    text = title.strip()
    if not text:
        return 0

    default_prefix = default_prefix.strip()
    if default_prefix:
        match = re.search(rf"\b{re.escape(default_prefix)}\.(\d+)\b", text)
        if match:
            return int(match.group(1))

    match = _REF_NUMBER_RE.search(text)
    if not match:
        return 0
    return int(match.group(2))


def extract_item_content_from_title(title: str) -> str:
    text = title.strip()
    if not text:
        return ""

    if " : " in text:
        return text.split(" : ", 1)[1].strip()
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text


def _join_block(lines: Iterable[str]) -> str:
    return "\n".join(lines).strip("\n")


def _is_top_level_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line))


def _is_top_level_admonition(line: str) -> bool:
    return bool(_ADMONITION_RE.match(line))


def split_existing_markdown_into_items(
    text: str,
    *,
    default_prefix: str = "",
) -> tuple[str, list[Item]]:
    lines = text.splitlines()
    items: list[Item] = []
    title = ""
    item_index = 0
    line_index = 0

    while line_index < len(lines):
        line = lines[line_index]

        if not line.strip():
            line_index += 1
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            heading_text = heading_match.group(2).strip()
            if not title and heading_match.group(1) == "#":
                title = heading_text
            items.append(
                Item(
                    kind="section",
                    id=f"i{item_index}",
                    type=f"h{len(heading_match.group(1))}",
                    content=heading_text,
                    document=line.rstrip(),
                    status="approved",
                )
            )
            item_index += 1
            line_index += 1
            continue

        if _is_top_level_admonition(line):
            start = line_index
            line_index += 1
            while line_index < len(lines):
                candidate = lines[line_index]
                if candidate.strip() and not candidate.startswith((" ", "\t")):
                    break
                line_index += 1
            document = _join_block(lines[start:line_index])
            admonition_type, admonition_title, number = parse_admonition_header(
                lines[start],
                default_prefix=default_prefix,
            )
            items.append(
                Item(
                    kind="admonition",
                    id=f"i{item_index}",
                    type=admonition_type,
                    content=extract_item_content_from_title(admonition_title),
                    document=document,
                    status="approved",
                    number=number,
                    autonumber=(number == 0),
                    syncedNumber=number,
                )
            )
            item_index += 1
            continue

        start = line_index
        line_index += 1
        while line_index < len(lines):
            candidate = lines[line_index]
            if _is_top_level_heading(candidate) or _is_top_level_admonition(candidate):
                break
            line_index += 1
        document = _join_block(lines[start:line_index])
        if not document.strip():
            continue
        items.append(
            Item(
                kind="text",
                id=f"i{item_index}",
                type="",
                content=summarize_text_block(document),
                document=document,
                status="approved",
            )
        )
        item_index += 1

    return title, items
