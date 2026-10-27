"""Regression tests for discovering styled admonitions with shared icons."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from mkdocs_parser import get_admonition_types  # noqa: E402


def test_corollary_reuses_theorem_icon() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        css = root / "docs" / "assets" / "stylesheets" / "extra.css"
        css.parent.mkdir(parents=True)
        css.write_text(
            """
            :root { --md-admonition-icon--theorem: url(theorem.svg); }
            .md-typeset .admonition.theorem,
            .md-typeset details.theorem { border-color: rgb(68, 138, 255); }
            .md-typeset .admonition.corollary,
            .md-typeset details.corollary { border-color: rgb(68, 138, 255); }
            .md-typeset .corollary > summary::before {
                mask-image: var(--md-admonition-icon--theorem);
            }
            """,
            encoding="utf-8",
        )

        assert get_admonition_types(str(root)) == [
            {"type": "theorem", "color": "rgb(68, 138, 255)"},
            {"type": "corollary", "color": "rgb(68, 138, 255)"},
        ]


def test_selector_only_types_in_nonstandard_stylesheet() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        css = root / "docs" / "custom.css"
        css.parent.mkdir()
        css.write_text(
            ".md-typeset details.lemma { border-color: blue; }\n"
            ".md-typeset .admonition.proposition { border-color: green; }\n",
            encoding="utf-8",
        )

        assert get_admonition_types(str(root)) == [
            {"type": "lemma", "color": "blue"},
            {"type": "proposition", "color": "green"},
        ]


def test_icon_types_are_unique_and_comments_are_ignored() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "extra.css").write_text(
            """
            /* :root { --md-admonition-icon--unused: url(unused.svg); }
               .admonition.removed { border-color: red; } */
            :root { --md-admonition-icon--theorem: url(theorem.svg); }
            [data-theme=dark] { --md-admonition-icon--theorem: url(other.svg); }
            .admonition-title { font-weight: bold; }
            """,
            encoding="utf-8",
        )

        assert get_admonition_types(str(root)) == [{"type": "theorem", "color": ""}]


if __name__ == "__main__":
    test_corollary_reuses_theorem_icon()
    test_selector_only_types_in_nonstandard_stylesheet()
    test_icon_types_are_unique_and_comments_are_ignored()
    print("MkDocs admonition discovery regression tests passed")
