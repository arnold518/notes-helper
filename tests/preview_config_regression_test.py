#!/usr/bin/env python3
"""Regression tests for MkDocs preview config generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from preview_config import (  # noqa: E402
    build_preview_mkdocs_config,
    merge_preview_asset_tree,
    resolve_preview_document_path,
)


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


def test_preview_config_uses_source_document_path() -> None:
    built = build_preview_mkdocs_config(
        {"theme": {"name": "material"}},
        docs_dir=Path("/tmp/preview/docs"),
        site_dir=Path("/tmp/preview/site"),
        preview_path="abstract-algebra/6.md",
    )

    assert built["nav"] == [{"Preview": "abstract-algebra/6.md"}]


def test_preview_document_path_is_relative_to_configured_docs_dir() -> None:
    relative_path = resolve_preview_document_path(
        {"docs_dir": "notes"},
        mkdocs_root=Path("/tmp/math-notes"),
        output_path=Path("/tmp/math-notes/notes/abstract-algebra/6.md"),
    )

    assert relative_path == Path("abstract-algebra/6.md")


def test_preview_document_path_falls_back_for_external_output() -> None:
    relative_path = resolve_preview_document_path(
        {"docs_dir": "docs"},
        mkdocs_root=Path("/tmp/math-notes"),
        output_path=Path("/tmp/other/6.md"),
    )

    assert relative_path == Path("preview.md")


def test_preview_assets_merge_project_styles_and_document_images(tmp_path: Path) -> None:
    project_assets = tmp_path / "project-assets"
    document_assets = tmp_path / "document-assets"
    preview_assets = tmp_path / "preview" / "docs" / "assets"

    (project_assets / "stylesheets").mkdir(parents=True)
    (project_assets / "stylesheets" / "extra.css").write_text(
        ".admonition.proof { border-color: blue; }",
        encoding="utf-8",
    )
    document_assets.mkdir()
    (document_assets / "6.1.jpg").write_bytes(b"chapter image")

    merge_preview_asset_tree(project_assets, preview_assets)
    merge_preview_asset_tree(document_assets, preview_assets)

    assert (preview_assets / "stylesheets" / "extra.css").is_file()
    assert (preview_assets / "6.1.jpg").is_file()


def test_preview_asset_merge_replaces_legacy_directory_symlink(tmp_path: Path) -> None:
    project_assets = tmp_path / "project-assets"
    legacy_assets = tmp_path / "legacy-assets"
    preview_assets = tmp_path / "preview" / "docs" / "assets"

    (project_assets / "stylesheets").mkdir(parents=True)
    (project_assets / "stylesheets" / "extra.css").write_text("proof styles", encoding="utf-8")
    legacy_assets.mkdir()
    preview_assets.parent.mkdir(parents=True)
    preview_assets.symlink_to(legacy_assets, target_is_directory=True)

    merge_preview_asset_tree(project_assets, preview_assets)

    assert not preview_assets.is_symlink()
    assert (preview_assets / "stylesheets" / "extra.css").is_file()


def run_tests() -> None:
    test_preview_config_replaces_invalid_source_nav()
    print("PASS: preview config regression")


if __name__ == "__main__":
    run_tests()
