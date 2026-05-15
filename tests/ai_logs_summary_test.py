#!/usr/bin/env python3
"""Smoke tests for AI log summaries."""

from __future__ import annotations

import json
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import ai_logs as ai_logs_mod  # noqa: E402
from ai_logs import list_ai_logs, summarize_ai_error  # noqa: E402


def run_tests() -> None:
    retry_payload = {
        "stderr": (
            "OpenAI Codex v0.114.0 (research preview)\n"
            "...\n"
            "ERROR: exceeded retry limit, last status: 429 Too Many Requests, "
            "request id: abc-123\n"
            "tokens used\n"
            "4,440\n"
            "Agent 'codex' exited 1: OpenAI Codex v0.114.0\n"
        ),
        "error": "Agent 'codex' exited 1: OpenAI Codex v0.114.0",
    }
    assert summarize_ai_error(retry_payload) == (
        "exceeded retry limit: 429 Too Many Requests (request id: abc-123)"
    )

    generic_payload = {
        "stderr": "line 1\nfatal: repository not found\n",
        "error": "Agent exited 128",
    }
    assert summarize_ai_error(generic_payload) == "fatal: repository not found"

    fallback_payload = {
        "stderr": "",
        "error": "plain fallback error",
    }
    assert summarize_ai_error(fallback_payload) == "plain fallback error"

    original_projects_dir = ai_logs_mod.PROJECTS_DIR
    try:
        with TemporaryDirectory() as tmpdir:
            ai_logs_mod.PROJECTS_DIR = Path(tmpdir)
            logs_dir = ai_logs_mod.PROJECTS_DIR / "p1" / "ai_logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "done.json").write_text(json.dumps({
                "id": "done",
                "projectId": "p1",
                "status": "done",
                "stderr": "tokens used\n17,002",
                "error": "tokens used\n17,002",
            }), encoding="utf-8")
            (logs_dir / "error.json").write_text(json.dumps({
                "id": "error",
                "projectId": "p1",
                "status": "error",
                "stderr": "ERROR: exceeded retry limit, last status: 429 Too Many Requests, request id: abc-123\n",
                "error": "Agent exited 1",
            }), encoding="utf-8")
            summaries = {entry["id"]: entry for entry in list_ai_logs("p1", limit=10)}
            assert summaries["done"]["error"] == ""
            assert summaries["error"]["error"] == (
                "exceeded retry limit: 429 Too Many Requests (request id: abc-123)"
            )
    finally:
        ai_logs_mod.PROJECTS_DIR = original_projects_dir

    print("PASS: AI log error summaries")


if __name__ == "__main__":
    run_tests()
