# notes-helper

AI-powered blog authoring tool for MkDocs Material.

## Quick Start

**Backend** (Python 3.10+):
```bash
cd backend
./start.sh
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5172.

## 5-Step Workflow

```
blueprint.md + textbook.md
  → [Step 2: AI match]      each entry gets a textbook excerpt
  → [Step 3: User edits]    user trims/adds excerpt context per entry
  → [Step 4: AI generate]   each excerpt → MkDocs admonition block
  → [Step 5: User approves] user edits/approves each admonition
  → export: final blog .md
```

## Requirements

- AI CLI in PATH:
  - `claude` (default), or
  - `codex`
- `mkdocs-material` installed if you want live MkDocs preview (`POST /api/preview`)

## Backend Agent Config

AI provider/model is configured globally for the backend in:

`backend/backend_config.json`

```json
{
  "agent": {
    "provider": "claude"
  },
  "codex": {
    "model": "",
    "reasoning_effort": ""
  }
}
```

Notes:
- `"provider"`: `"claude"` or `"codex"`
- `codex.model`: optional model for Codex runs only (empty string = Codex CLI default)
- `codex.reasoning_effort`: optional thought depth for Codex runs only (`minimal`, `low`, `medium`, `high`, `xhigh`)
- This applies to all projects (not per-project).

## Examples

See `examples/` for sample blueprint, textbook, and output blog files.

## Prompts / Rules

- Prompts can be found in `backend/agent_runner.py`.
- Default rules can be found in `backend/routers/project.py`.