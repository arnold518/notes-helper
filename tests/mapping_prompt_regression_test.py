#!/usr/bin/env python3
"""Regression tests for canonical map prompts and AI reference-link prompts."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import agent_runner  # noqa: E402
from models import Item, Project, ReferenceFile  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_tests() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source_doc = root / "refs" / "[NC2010]QCQI.md"
        mapping = root / "mapping.md"
        generate_rules = root / "generate_rules.md"
        map_rules = root / "map_rules.md"
        stage_dir = root / "stage"
        stage_dir.mkdir(parents=True, exist_ok=True)

        _write(
            mapping,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location |\n"
                "| --- | --- | --- |\n"
                "| Theorem 2.1.18 | **Gram-Schmidt procedure**; **orthonormal basis extension** | 2.1.md |\n"
                "| Definition 2.1.11 | **Pauli matrices**; **2.1.3 The Pauli matrices** | 2.1.md |\n"
            ),
        )
        _write(generate_rules, "# Generate Rules\n")
        _write(map_rules, "# Map Rules\n")

        project = Project(
            id="p1",
            title="Prompt regression test",
            outputPath=str(root / "docs" / "2.1.md"),
            mappingPath=str(mapping),
            references=[
                ReferenceFile(
                    id="r1",
                    name="textbook.md",
                    path=str(root / "refs" / "textbook.md"),
                    originalPath=str(source_doc),
                )
            ],
            items=[
                Item(
                    kind="section",
                    id="sec",
                    type="h1",
                    content="2.1. Linear Algebra",
                    number=0,
                ),
                Item(
                    kind="admonition",
                    id="i1",
                    type="theorem",
                    content="trace identity",
                    excerpt=(
                        "[textbook.md line 1~3]\n\n"
                        "Use the Gram-Schmidt process to extend the vector to an orthonormal basis."
                    ),
                    number=62,
                ),
                Item(
                    kind="admonition",
                    id="i2",
                    type="theorem",
                    content="",
                    excerpt=(
                        "[textbook.md line 9~9]\n\n"
                        "It follows from the previous construction."
                    ),
                    number=63,
                ),
            ],
            createdAt="2026-03-21T00:00:00+00:00",
            updatedAt="2026-03-21T00:00:00+00:00",
        )

        prompts: list[tuple[str, str]] = []
        original_run_agent = agent_runner.run_agent

        async def fake_run_agent(
            prompt: str,
            cwd: str,
            provider: str = "claude",
            model: str = "",
            reasoning_effort: str = "",
            project_id: str = "",
            run_type: str = "agent",
            log_meta: dict | None = None,
        ) -> str:
            prompts.append((run_type, prompt))
            if run_type == "reference_link":
                return json.dumps(
                    [
                        {
                            "mention": "Gram-Schmidt process",
                            "target_ref": "Theorem 2.1.18",
                            "target_doc": "2.1.md",
                            "matched_source_ref": "Gram-Schmidt procedure",
                            "confidence": "high",
                            "reason": "semantic variant of canonical source ref",
                        }
                    ]
                )
            if run_type == "map_update":
                return json.dumps(
                    [
                        {
                            "item_id": "i2",
                            "source_docs": [str(source_doc)],
                            "original_refs": ["previous construction"],
                        }
                    ]
                )
            return "done"

        agent_runner.run_agent = fake_run_agent
        try:
            asyncio.run(
                agent_runner.run_map_update_agent(
                    project=project,
                    item_ids=["i1", "i2"],
                    stage_dir=str(stage_dir),
                    cwd=str(root),
                    map_rules_path=str(map_rules),
                )
            )
            assert prompts[0][0] == "map_update"
            assert "Stable mapping policy:" in prompts[0][1]
            assert "Do not try to encode exhaustive synonyms or alias variants in the mapping file" in prompts[0][1]
            assert "Use the canonical notes document path relative to the MkDocs docs/ root when available" in prompts[0][1]
            assert "Never return the notes-side label itself as an Original ref." in prompts[0][1]
            assert "Use the deterministic candidate Original refs when they are already good" in prompts[0][1]
            assert "Output ONLY a JSON array." in prompts[0][1]

            prompts.clear()
            asyncio.run(
                agent_runner.run_generate_agent(
                    project=project,
                    item_ids=["i1"],
                    user_prompt="",
                    available_types=["definition", "theorem", "concept", "example"],
                    stage_dir=str(stage_dir),
                    generate_rules_path=str(generate_rules),
                    cwd=str(root),
                )
            )
        finally:
            agent_runner.run_agent = original_run_agent

        rewritten_mapping = mapping.read_text(encoding="utf-8")
        assert "**Gram-Schmidt procedure**" in rewritten_mapping, rewritten_mapping
        assert "**previous construction**" in rewritten_mapping, rewritten_mapping

        assert len(prompts) == 2, prompts
        assert prompts[0][0] == "reference_link", prompts
        assert "User explicitly requested additional references: no" in prompts[0][1]
        assert "close semantic match" in prompts[0][1]
        assert 'Source refs: Gram-Schmidt procedure; orthonormal basis extension' in prompts[0][1]
        assert 'Source refs: Pauli matrices; 2.1.3 The Pauli matrices' in prompts[0][1]
        assert "Do not infer new conceptual backlinks merely because a concept is discussed" in prompts[0][1]
        assert "return only replacements for references already present in the excerpt or current document" in prompts[0][1]
        assert "Output ONLY a JSON array of objects with keys" in prompts[0][1]

        assert prompts[1][0] == "generate", prompts
        assert "Resolved cross-reference candidates" in prompts[1][1]
        assert '"Gram-Schmidt process" -> Theorem 2.1.18 (2.1.md)' in prompts[1][1]
        assert 'matched via "Gram-Schmidt procedure"' in prompts[1][1]
        assert "replace corresponding original-source references already present in the excerpt or current document" in prompts[1][1]
        assert "Do not add new notes-side references beyond those replacements" in prompts[1][1]
        assert 'according to **Definition 3.5.1**' in prompts[1][1]
        assert 'Using the gram-schmidt theorem (**Theorem 2.5.1**)' in prompts[1][1]
        assert "Bold only the notes-side reference label itself" in prompts[1][1]

        prompts.clear()
        agent_runner.run_agent = fake_run_agent
        try:
            asyncio.run(
                agent_runner.run_generate_agent(
                    project=project,
                    item_ids=["i1"],
                    user_prompt="Please add additional references where useful.",
                    available_types=["definition", "theorem", "concept", "example"],
                    stage_dir=str(stage_dir),
                    generate_rules_path=str(generate_rules),
                    cwd=str(root),
                )
            )
        finally:
            agent_runner.run_agent = original_run_agent

        assert len(prompts) == 2, prompts
        assert prompts[0][0] == "reference_link", prompts
        assert "User explicitly requested additional references: yes" in prompts[0][1]
        assert "you may add a small number of additional high-confidence mapping-based references" in prompts[0][1]
        assert prompts[1][0] == "generate", prompts
        assert "Additional references were explicitly requested by the user" in prompts[1][1]

        prompts.clear()
        agent_runner.run_agent = fake_run_agent
        try:
            asyncio.run(
                agent_runner.run_edit_agent(
                    project=project,
                    item_id="i1",
                    target="document",
                    original_text='!!! theorem "Theorem 2.1.62 : Trace identity"\n    Use the Gram-Schmidt process.',
                    user_prompt="Update only notes-side cross-references to match the canonical mapping.",
                    stage_dir=str(stage_dir),
                    rules_path=str(generate_rules),
                    cwd=str(root),
                )
            )
        finally:
            agent_runner.run_agent = original_run_agent

        assert len(prompts) == 2, prompts
        assert prompts[0][0] == "reference_link", prompts
        assert prompts[1][0] == "edit_document", prompts
        assert "Resolved cross-reference candidates" in prompts[1][1]
        assert '"Gram-Schmidt process" -> Theorem 2.1.18 (2.1.md)' in prompts[1][1]
        assert "Excerpt context (for source-side reference context only" in prompts[1][1]
        assert 'Using the gram-schmidt theorem (**Theorem 2.5.1**)' in prompts[1][1]

    print("PASS: mapping prompt regression")


if __name__ == "__main__":
    run_tests()
