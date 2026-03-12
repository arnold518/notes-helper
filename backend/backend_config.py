"""Backend-wide runtime configuration for AI agent execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


AgentProvider = Literal["claude", "codex"]


class AgentRuntimeConfig(BaseModel):
    provider: AgentProvider = "claude"


class CodexRuntimeConfig(BaseModel):
    model: str = ""
    reasoning_effort: str = ""


class GenerationRuntimeConfig(BaseModel):
    auto_style_examples: bool = True
    max_example_files: int = 4
    max_example_file_bytes: int = 300_000
    max_example_snippet_chars: int = 2_000
    search_depth: int = 3


class BackendConfig(BaseModel):
    agent: AgentRuntimeConfig = AgentRuntimeConfig()
    codex: CodexRuntimeConfig = CodexRuntimeConfig()
    generation: GenerationRuntimeConfig = GenerationRuntimeConfig()


def _migrate_raw_config(raw: dict) -> dict:
    """Migrate legacy config keys to the current schema."""
    if not isinstance(raw, dict):
        return {}

    agent = raw.get("agent")
    if isinstance(agent, dict):
        legacy_model = str(agent.pop("model", "") or "").strip()
        legacy_effort = str(agent.pop("model_reasoning_effort", "") or "").strip()
        if legacy_model or legacy_effort:
            codex = raw.get("codex")
            if not isinstance(codex, dict):
                codex = {}
            if legacy_model and not codex.get("model"):
                codex["model"] = legacy_model
            if legacy_effort and not codex.get("reasoning_effort"):
                codex["reasoning_effort"] = legacy_effort
            raw["codex"] = codex
            raw["agent"] = agent
    return raw


def _config_path() -> Path:
    default_path = Path(__file__).parent / "backend_config.json"
    return Path(os.environ.get("BACKEND_CONFIG_PATH", str(default_path)))


def load_backend_config() -> BackendConfig:
    """Load backend config from disk, creating defaults if absent."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        cfg = BackendConfig()
        path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
        return cfg

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw = _migrate_raw_config(raw)
    return BackendConfig.model_validate(raw)
