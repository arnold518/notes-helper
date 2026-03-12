#!/usr/bin/env python3
"""Smoke test for heuristic section extraction from a full textbook.

Strategy:
  1. Parse blueprint.md to find the h1 title.
  2. Parse all headings from the textbook.
  3. Match the best heading by word overlap.
  4. Pass the subsequent heading list to the agent to find the end boundary.
  5. Extract and verify the slice.

Run:
  python tests/section_extract_smoke_test.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXAMPLES = Path(__file__).parent.parent / "examples"
TEXTBOOK = EXAMPLES / "[NC2010]QCQI.md"
BLUEPRINT = EXAMPLES / "blueprint.md"


# ---------------------------------------------------------------------------
# Step 1: extract h1 title from blueprint
# ---------------------------------------------------------------------------

def parse_blueprint_h1(blueprint_path: Path) -> str:
    for line in blueprint_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    raise ValueError(f"No h1 heading found in {blueprint_path}")


# ---------------------------------------------------------------------------
# Step 2: parse all headings from textbook
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")


def parse_headings(text: str) -> list[tuple[int, int, str]]:
    """Return list of (line_index, level, heading_text), 0-indexed lines."""
    result = []
    for i, line in enumerate(text.splitlines()):
        m = _HEADING_RE.match(line)
        if m:
            result.append((i, len(m.group(1)), m.group(2).strip()))
    return result


# ---------------------------------------------------------------------------
# Step 3: word-overlap heading match
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\b\d[\d.]*\b")


def _words(text: str) -> set[str]:
    text = _NUMBER_RE.sub(" ", text.lower())
    return {w for w in re.split(r"[^a-z]+", text) if len(w) > 1}


def score_heading(query: str, candidate: str) -> float:
    qw, cw = _words(query), _words(candidate)
    if not qw or not cw:
        return 0.0
    return len(qw & cw) / len(qw | cw)


def find_best_heading(
    query: str,
    headings: list[tuple[int, int, str]],
    min_score: float = 0.3,
) -> tuple[int, int, str] | None:
    best_score, best = -1.0, None
    for entry in headings:
        s = score_heading(query, entry[2])
        if s > best_score:
            best_score, best = s, entry
    return best if best_score >= min_score else None


# ---------------------------------------------------------------------------
# Step 4: agent finds end boundary from heading list
# ---------------------------------------------------------------------------

def _run_agent(prompt: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    if shutil.which("codex"):
        model = os.environ.get("CODEX_MODEL", "").strip()
        reasoning = os.environ.get("CODEX_REASONING_EFFORT", "").strip()
        cmd = ["codex", "exec"]
        if model:
            cmd += ["-m", model]
        if reasoning:
            cmd += ["-c", f'model_reasoning_effort="{reasoning}"']
        cmd += [
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--color", "never",
            prompt,
        ]
    elif shutil.which("claude"):
        cmd = [
            "claude", "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "text",
        ]
    else:
        raise RuntimeError("Neither codex nor claude CLI found in PATH.")

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"Agent exited {proc.returncode}: {proc.stderr[:800]}")
    return proc.stdout.strip()


def agent_find_end_line(
    match_line: int,
    match_level: int,
    match_heading: str,
    subsequent_headings: list[tuple[int, int, str]],
    total_lines: int,
) -> int:
    """Ask the agent which subsequent heading marks the end of the matched section.

    Returns the 0-indexed exclusive end line.
    """
    heading_list = "\n".join(
        f"  line {line + 1}, level {level}, {'#' * level} {text}"
        for line, level, text in subsequent_headings
    )

    prompt = (
        f"A markdown textbook section starts at line {match_line + 1}:\n"
        f"  {'#' * match_level} {match_heading}\n\n"
        f"The following headings appear after it:\n"
        f"{heading_list}\n\n"
        f"Task: identify which heading line marks the END of section '{match_heading}'.\n"
        f"The section ends where a new peer or parent section begins "
        f"(i.e. a heading that is NOT a subsection of '{match_heading}').\n"
        f"Note: heading levels may be inconsistent due to OCR — use title content "
        f"and numbering patterns (e.g. '2.2' ends '2.1') to decide.\n"
        f"If no heading ends the section, output {total_lines + 1}.\n\n"
        f"Output ONLY a single integer: the 1-indexed line number of the first heading "
        f"that is NOT part of this section. No explanation."
    )

    raw = _run_agent(prompt)
    m = re.search(r"\d+", raw)
    if not m:
        raise ValueError(f"Agent returned non-integer: {raw!r}")
    return int(m.group()) - 1  # 0-indexed exclusive


# ---------------------------------------------------------------------------
# Step 5: extract and verify
# ---------------------------------------------------------------------------

EXPECTED_TERMS = ["vector space", "linear", "basis", "inner product", "operator"]


def run_smoke_test() -> None:
    print(f"Blueprint : {BLUEPRINT}")
    print(f"Textbook  : {TEXTBOOK}")

    if not TEXTBOOK.exists():
        print(f"SKIP: textbook not found at {TEXTBOOK}", file=sys.stderr)
        sys.exit(0)

    # Step 1
    h1_title = parse_blueprint_h1(BLUEPRINT)
    print(f"\nBlueprint h1 : {h1_title!r}")

    # Step 2
    textbook_text = TEXTBOOK.read_text(encoding="utf-8")
    all_lines = textbook_text.splitlines()
    headings = parse_headings(textbook_text)
    print(f"Headings found : {len(headings)}")

    # Step 3
    match = find_best_heading(h1_title, headings)
    if match is None:
        raise AssertionError(f"No heading matched {h1_title!r} in textbook")
    start_line, start_level, start_heading = match
    score = score_heading(h1_title, start_heading)
    print(f"Best match     : line {start_line + 1}, level {start_level}, {start_heading!r}  (score {score:.3f})")
    assert score >= 0.3, f"Match score too low: {score:.3f}"

    # Step 4 — pass only headings that come after the match
    match_idx = headings.index(match)
    subsequent = headings[match_idx + 1:]
    print(f"Subsequent headings passed to agent: {len(subsequent)}")

    print("\nAsking agent for end boundary...")
    end_line = agent_find_end_line(start_line, start_level, start_heading, subsequent, len(all_lines))
    print(f"Agent end line : {end_line + 1} (exclusive, 1-indexed)")
    assert end_line > start_line, f"End line {end_line} must be after start {start_line}"

    # Step 5
    section_lines = all_lines[start_line:end_line]
    section_text = "\n".join(section_lines)
    print(f"Extracted      : {len(section_lines)} lines, {len(section_text)} chars")

    assert len(section_text) > 500, f"Extracted section too short ({len(section_text)} chars)"
    missing = [t for t in EXPECTED_TERMS if t not in section_text.lower()]
    assert not missing, f"Expected terms missing: {missing}"

    print(f"\nFirst 300 chars:\n{section_text[:300]}\n...")
    print("\nPASS: section extraction smoke test")


if __name__ == "__main__":
    run_smoke_test()
