#!/usr/bin/env python3
"""Regression tests for MkDocs preview config generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from preview_config import build_preview_mkdocs_config  # noqa: E402


def test_preview_config_replaces_invalid_source_nav() -> None:
    config = {
        "site_name": "Artificial Intelligence Notes",
        "theme": {"name": "material"},
        "nav": [
            {"Quantum Computation and Quantum Information": [
                "qcqi/index.md",
                {"Ch 2. Introduction to Quantum Mechanics": [
                    "qcqi/2.1.md",
                    None,
                ]},
            ]},
        ],
        "extra_css": ["assets/stylesheets/extra.css"],
    }

    built = build_preview_mkdocs_config(
        config,
        docs_dir=Path("/tmp/preview/docs"),
        site_dir=Path("/tmp/preview/site"),
    )

    assert built["nav"] == [{"Preview": "preview.md"}], built["nav"]
    assert built["site_name"] == "Artificial Intelligence Notes"
    assert built["theme"] == {"name": "material"}
    assert built["extra_css"] == ["assets/stylesheets/extra.css"]
    assert built["docs_dir"] == "/tmp/preview/docs"
    assert built["site_dir"] == "/tmp/preview/site"
    assert built["plugins"] == []


def run_tests() -> None:
    test_preview_config_replaces_invalid_source_nav()
    print("PASS: preview config regression")


if __name__ == "__main__":
    run_tests()
