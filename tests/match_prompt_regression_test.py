#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import agent_runner  # noqa: E402
from models import Item, Project, ReferenceFile  # noqa: E402


def run_tests() -> None:
    captured: dict[str, str] = {}

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
        captured["prompt"] = prompt
        captured["cwd"] = cwd
        captured["run_type"] = run_type
        return "done"

    original_run_agent = agent_runner.run_agent
    original_runtime_agent_settings = agent_runner._runtime_agent_settings
    agent_runner.run_agent = fake_run_agent
    agent_runner._runtime_agent_settings = lambda: ("codex", "", "")
    try:
        project = Project(
            id="pmatch",
            title="Prompt regression",
            references=[
                ReferenceFile(
                    id="r1",
                    name="textbook.md",
                    path="/tmp/textbook.md",
                    originalPath="/orig/textbook.md",
                    prepared=True,
                )
            ],
            items=[
                Item(
                    kind="admonition",
                    id="i1",
                    type="definition",
                    content="entanglement",
                    excerpt="[refs/textbook.md line 506~517]\n\nOld excerpt text.",
                )
            ],
            createdAt="2026-03-23T00:00:00+00:00",
            updatedAt="2026-03-23T00:00:00+00:00",
        )

        asyncio.run(
            agent_runner.run_match_agent(
                project=project,
                item_ids=["i1"],
                user_prompt="",
                stage_dir="/tmp/stage",
                match_rules_path="/tmp/match_rules.md",
                cwd="/tmp",
            )
        )
    finally:
        agent_runner.run_agent = original_run_agent
        agent_runner._runtime_agent_settings = original_runtime_agent_settings

    prompt = captured["prompt"]
    assert captured["run_type"] == "match"
    assert "Important matching instructions:" in prompt
    assert "rewrite each excerpt from scratch" in prompt
    assert "Treat any previous excerpt shown below as a stale hint only." in prompt
    assert "Previous excerpt hint (may be stale; re-extract from current reference files):" in prompt
    assert "Current excerpt:" not in prompt

    normalized = agent_runner._normalize_excerpt_reference_headers(
        project,
        "[refs/textbook.md line 506~517]\n\nOld excerpt text.",
    )
    assert normalized.startswith("[textbook.md line 506~517]")

    normalized_escaped = agent_runner._normalize_excerpt_reference_headers(
        project,
        "[/tmp/textbook.md line 581~582]\\n\\nExercise text.",
    )
    assert normalized_escaped.startswith("[textbook.md line 581~582]\n\nExercise text.")
    print("PASS: match prompt regression")


if __name__ == "__main__":
    run_tests()
