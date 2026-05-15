#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from import_existing_notes import split_existing_markdown_into_items  # noqa: E402


SAMPLE = """# § 8. Linear Transformations, Null Spaces, and Ranges

Intro paragraph.
Still intro.

!!! theorem "Theorem 8.10 : Null space and range are subspaces."
    Statement.

Note that **Theorem 8.10** is useful.

## Exercise

!!! exercise "Exercise 8.33"
    Prove the infinite-basis version.
"""


def run_tests() -> None:
    title, items = split_existing_markdown_into_items(SAMPLE, default_prefix="8")
    assert title == "§ 8. Linear Transformations, Null Spaces, and Ranges"
    assert [item.kind for item in items] == [
        "section",
        "text",
        "admonition",
        "text",
        "section",
        "admonition",
    ]
    theorem = items[2]
    assert theorem.type == "theorem"
    assert theorem.number == 10
    assert theorem.autonumber is False
    assert theorem.content == "Null space and range are subspaces."
    exercise = items[5]
    assert exercise.type == "exercise"
    assert exercise.number == 33
    assert exercise.document.startswith('!!! exercise "Exercise 8.33"')
    print("PASS: import existing notes parser")


if __name__ == "__main__":
    run_tests()
