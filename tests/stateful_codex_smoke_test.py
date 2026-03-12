#!/usr/bin/env python3
"""Standalone smoke test for stateful Codex memory behavior.

This file intentionally has no project dependencies.
Run: python tests/stateful_codex_smoke_test.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Turn:
    user: str
    assistant: str


@dataclass
class SessionMemory:
    turns: list[Turn] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


class StatefulCodexAgent:
    """Simple wrapper that adds persistent per-session memory to a stateless model call."""

    def __init__(self, model_call: Callable[[str], str]) -> None:
        self._model_call = model_call
        self._sessions: dict[str, SessionMemory] = {}

    def ask(self, session_id: str, user_message: str) -> str:
        session = self._sessions.setdefault(session_id, SessionMemory())

        for rule in self._extract_rules_to_memorize(user_message):
            if rule not in session.rules:
                session.rules.append(rule)

        prompt = self._compose_prompt(session=session, user_message=user_message)
        response = self._model_call(prompt)
        session.turns.append(Turn(user=user_message, assistant=response))
        return response

    @staticmethod
    def _extract_rules_to_memorize(text: str) -> list[str]:
        patterns = [
            r"(?is)\bmemorize this rule\s*:\s*(.+)",
            r"(?is)\bremember this rule\s*:\s*(.+)",
            r"(?is)\bmemorize\s*:\s*(.+)",
            r"(?is)\bremember\s*:\s*(.+)",
            r"(?is)\bplease memorize\b\s+(.+)",
            r"(?is)\bplease remember\b\s+(.+)",
        ]
        found: list[str] = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            rule = match.group(1).strip().strip("\"'")
            if rule:
                found.append(rule)
        return found

    @staticmethod
    def _compose_prompt(session: SessionMemory, user_message: str) -> str:
        lines: list[str] = []
        lines.append(
            "You are Codex running a deterministic smoke test. "
            "Follow the algorithm exactly and output strict JSON only."
        )

        lines.append("<MEMORIZED_RULES>")
        if session.rules:
            for rule in session.rules:
                lines.append(f"- {rule}")
        else:
            lines.append("(none)")
        lines.append("</MEMORIZED_RULES>")

        lines.append("<CONVERSATION_HISTORY>")
        if session.turns:
            for turn in session.turns[-8:]:
                lines.append(f"User: {turn.user}")
                lines.append(f"Assistant: {turn.assistant}")
        else:
            lines.append("(empty)")
        lines.append("</CONVERSATION_HISTORY>")

        lines.append("<USER_MESSAGE>")
        lines.append(user_message)
        lines.append("</USER_MESSAGE>")
        lines.append(
            "Algorithm:\n"
            "1) Find city from the latest USER line in CONVERSATION_HISTORY matching "
            "'I live in <city>'. If none, city='unknown'.\n"
            "2) From MEMORIZED_RULES, find first rule matching "
            "'prefix every reply with <prefix>'. If none, prefix=''.\n"
            "3) Build base reply:\n"
            "   - If USER_MESSAGE asks 'What city do I live in?' => 'You live in <city>.'\n"
            "   - If USER_MESSAGE asks 'Say hello' => 'Hello there.'\n"
            "   - Else => 'Acknowledged.'\n"
            "4) Final reply = '<prefix> <base>' if prefix is not empty, else '<base>'.\n"
            "Output exactly one RFC8259 JSON object with keys:\n"
            '{"reply":"...","memory_city":"...","applied_prefix":"..."}\n'
            "No markdown code fences. No extra keys. No extra text."
        )
        return "\n".join(lines)


def _extract_json_object(output: str) -> dict:
    text = output.strip()

    if text.startswith("```"):
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in codex output: {output[:500]!r}")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError(f"Codex output JSON root is not an object: {parsed!r}")
    return parsed


def real_codex_model(prompt: str) -> str:
    """Real non-interactive codex call, aligned with backend codex invocation style."""
    if shutil.which("codex") is None:
        raise RuntimeError(
            "codex CLI not found in PATH. Install/authenticate codex CLI first."
        )

    cmd = ["codex", "exec"]
    model = os.environ.get("CODEX_MODEL", "").strip()
    reasoning_effort = os.environ.get("CODEX_REASONING_EFFORT", "").strip()
    if model:
        cmd += ["-m", model]
    if reasoning_effort:
        cmd += ["-c", f'model_reasoning_effort="{reasoning_effort}"']
    cmd += [
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--color",
        "never",
        prompt,
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "codex exec failed with "
            f"exit={proc.returncode}, stderr={proc.stderr[:1200]!r}"
        )

    parsed = _extract_json_object(proc.stdout)
    reply = str(parsed.get("reply", "")).strip()
    if not reply:
        raise RuntimeError(f"codex returned empty reply field: {proc.stdout[:1200]!r}")
    return reply


def run_smoke_test_single_agent() -> None:
    agent = StatefulCodexAgent(model_call=real_codex_model)

    session = "demo-session"

    agent.ask(session, "My name is Mina. I live in Seattle.")
    recall = agent.ask(session, "What city do I live in?")
    assert "Seattle" in recall, f"Expected recall to include Seattle, got: {recall!r}"

    agent.ask(session, "Memorize this rule: prefix every reply with RULED:")
    ruled_reply = agent.ask(session, "Say hello")
    assert ruled_reply.startswith("RULED:"), (
        "Expected memorized rule to be applied on future turns, "
        f"got: {ruled_reply!r}"
    )

    other_session_reply = agent.ask("new-session", "Say hello")
    assert not other_session_reply.startswith("RULED:"), (
        "Expected session isolation: rule from first session leaked into a new session."
    )

    print("PASS: single-agent stateful memory + rule memory + session isolation")


def run_smoke_test_multi_agent_isolation() -> None:
    # Simulate multiple independently stateful codex agents.
    agent_a = StatefulCodexAgent(model_call=real_codex_model)
    agent_b = StatefulCodexAgent(model_call=real_codex_model)

    # Intentionally use the same session id string in both agents.
    sid = "shared-session-id"

    agent_a.ask(sid, "I live in Seattle.")
    agent_a.ask(sid, "Memorize this rule: prefix every reply with RULED:")

    agent_b.ask(sid, "I live in Boston.")
    agent_b.ask(sid, "Memorize this rule: prefix every reply with AGENT_B:")

    recall_a = agent_a.ask(sid, "What city do I live in?")
    recall_b = agent_b.ask(sid, "What city do I live in?")
    assert "Seattle" in recall_a, f"Agent A should recall Seattle, got: {recall_a!r}"
    assert "Boston" in recall_b, f"Agent B should recall Boston, got: {recall_b!r}"

    hello_a = agent_a.ask(sid, "Say hello")
    hello_b = agent_b.ask(sid, "Say hello")
    assert hello_a.startswith("RULED:"), (
        f"Agent A should keep its own rule prefix, got: {hello_a!r}"
    )
    assert hello_b.startswith("AGENT_B:"), (
        f"Agent B should keep its own rule prefix, got: {hello_b!r}"
    )
    assert not hello_a.startswith("AGENT_B:"), "Agent A leaked Agent B rule"
    assert not hello_b.startswith("RULED:"), "Agent B leaked Agent A rule"

    print("PASS: multi-agent memory isolation (agent A vs agent B)")


def run_all_smoke_tests() -> None:
    run_smoke_test_single_agent()
    run_smoke_test_multi_agent_isolation()
    print("PASS: all smoke tests")


if __name__ == "__main__":
    run_all_smoke_tests()
