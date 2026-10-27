#!/usr/bin/env python3
"""Regression test for selecting the Codex executable from backend config."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import agent_runner  # noqa: E402
from backend_config import load_backend_config  # noqa: E402


def run_tests() -> None:
    original_config_path = os.environ.get("BACKEND_CONFIG_PATH")
    try:
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backend_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "agent": {"provider": "codex"},
                        "codex": {
                            "command": "codex2",
                            "model": "test-model",
                            "reasoning_effort": "high",
                        },
                    }
                ),
                encoding="utf-8",
            )
            os.environ["BACKEND_CONFIG_PATH"] = str(config_path)

            cfg = load_backend_config()
            assert cfg.codex.command == "codex2"

            cmd = agent_runner._agent_command(
                "codex",
                "test prompt",
                model=cfg.codex.model,
                reasoning_effort=cfg.codex.reasoning_effort,
            )
            assert cmd[:2] == ["codex2", "exec"]

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "backend_config.json"
            config_path.write_text(
                json.dumps({"agent": {"provider": "codex"}, "codex": {}}),
                encoding="utf-8",
            )
            os.environ["BACKEND_CONFIG_PATH"] = str(config_path)

            assert agent_runner._agent_command("codex", "test prompt")[:2] == [
                "codex",
                "exec",
            ]
    finally:
        if original_config_path is None:
            os.environ.pop("BACKEND_CONFIG_PATH", None)
        else:
            os.environ["BACKEND_CONFIG_PATH"] = original_config_path

    print("PASS: configurable Codex command")


if __name__ == "__main__":
    run_tests()
