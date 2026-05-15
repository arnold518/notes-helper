"""Async subprocess wrapper for running AI agent CLIs (Claude, Codex)."""
from __future__ import annotations
import asyncio
import difflib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_logs import create_ai_log, summarize_ai_error, update_ai_log, write_ai_log
from backend_config import load_backend_config
from mapping_store import (
    MappingRow,
    canonical_output_location,
    output_location_candidates,
    parse_mapping_file,
    project_entry_order_index,
    write_mapping_file,
)
from models import AiConversationMessage, Project

_agent_run_semaphore: asyncio.Semaphore | None = None
_agent_run_semaphore_limit = 0
_agent_run_semaphore_guard: asyncio.Lock | None = None


async def _agent_run_slots() -> asyncio.Semaphore:
    global _agent_run_semaphore
    global _agent_run_semaphore_guard
    global _agent_run_semaphore_limit

    limit = max(1, int(load_backend_config().agent.max_concurrency))
    if _agent_run_semaphore_guard is None:
        _agent_run_semaphore_guard = asyncio.Lock()

    async with _agent_run_semaphore_guard:
        if _agent_run_semaphore is None or _agent_run_semaphore_limit != limit:
            _agent_run_semaphore = asyncio.Semaphore(limit)
            _agent_run_semaphore_limit = limit
        return _agent_run_semaphore


def _agent_command(
    provider: str,
    prompt: str,
    model: str = "",
    reasoning_effort: str = "",
) -> list[str]:
    if provider == "claude":
        return [
            "claude",
            "-p",
            prompt,
            "--dangerously-skip-permissions",
            "--output-format",
            "text",
        ]
    if provider == "codex":
        cmd = ["codex", "exec"]
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
        return cmd
    raise ValueError(f"Unsupported agent provider: {provider}. Expected one of: claude, codex")


async def run_agent(
    prompt: str,
    cwd: str,
    provider: str = "claude",
    model: str = "",
    reasoning_effort: str = "",
    project_id: str = "",
    run_type: str = "agent",
    log_meta: dict | None = None,
) -> str:
    """Run configured agent CLI in cwd and return stdout."""
    cmd = _agent_command(
        provider,
        prompt,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    status = "error"
    error_text = ""
    returncode = -1
    log_id = ""
    last_flush = 0.0
    flush_lock = asyncio.Lock()
    semaphore = await _agent_run_slots()

    if project_id:
        log_id = create_ai_log(
            project_id,
            run_type=run_type,
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            cwd=cwd,
            command=cmd,
            prompt=prompt,
            started_at=started.isoformat(),
            status="running",
            meta=log_meta,
        )

    async def flush_running_log(force: bool = False) -> None:
        nonlocal last_flush
        if not project_id or not log_id:
            return
        now = time.perf_counter()
        if not force and (now - last_flush) < 0.5:
            return
        async with flush_lock:
            now2 = time.perf_counter()
            if not force and (now2 - last_flush) < 0.5:
                return
            update_ai_log(
                project_id,
                log_id,
                status="running",
                durationMs=int((now2 - t0) * 1000),
                stdout="".join(stdout_parts),
                stderr="".join(stderr_parts),
            )
            last_flush = now2

    async def read_stream(stream: asyncio.StreamReader | None, sink: list[str]) -> None:
        if stream is None:
            return
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            sink.append(chunk.decode(errors="replace"))
            await flush_running_log(force=False)

    try:
        async with semaphore:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_task = asyncio.create_task(read_stream(proc.stdout, stdout_parts))
            stderr_task = asyncio.create_task(read_stream(proc.stderr, stderr_parts))
            returncode = await proc.wait()
            await stdout_task
            await stderr_task
            await flush_running_log(force=True)
            stdout_text = "".join(stdout_parts)
            stderr_text = "".join(stderr_parts)
            if returncode != 0:
                error_text = summarize_ai_error({"stderr": stderr_text})
                if not error_text:
                    error_text = f"Agent '{provider}' exited {returncode}"
                raise RuntimeError(error_text)
            status = "done"
            return stdout_text
    except Exception as exc:
        if not error_text:
            error_text = str(exc)
        if not stderr_parts or stderr_parts[-1] != str(exc):
            stderr_parts.append(str(exc))
        raise
    finally:
        finished = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if project_id and log_id:
            update_ai_log(
                project_id,
                log_id,
                status=status if returncode == 0 else "error",
                finishedAt=finished.isoformat(),
                durationMs=duration_ms,
                stdout="".join(stdout_parts),
                stderr="".join(stderr_parts),
                error=error_text or None,
            )


def _runtime_agent_settings() -> tuple[str, str, str]:
    cfg = load_backend_config()
    if cfg.agent.provider == "codex":
        return cfg.agent.provider, cfg.codex.model, cfg.codex.reasoning_effort
    return cfg.agent.provider, "", ""


def _runtime_generation_settings() -> tuple[bool, int, int, int, int]:
    cfg = load_backend_config()
    return (
        bool(cfg.generation.auto_style_examples),
        int(cfg.generation.max_example_files),
        int(cfg.generation.search_depth),
    )


def _conversation_history_block(messages: list[AiConversationMessage], limit: int = 12) -> str:
    if not messages:
        return "(none)"
    rendered: list[str] = []
    for message in messages[-limit:]:
        content = (message.content or "").strip()
        if len(content) > 4000:
            content = f"{content[:4000]}\n...[truncated]..."
        status = f" [{message.status}]" if message.role == "assistant" else ""
        rendered.append(f"{message.role.capitalize()}{status}:\n{content or '(empty)'}")
    return "\n\n".join(rendered)


def _project_context_block(project: Project) -> str:
    reference_lines: list[str] = []
    for ref in project.references[:20]:
        primary_path = ref.path or ref.originalPath
        reference_lines.append(f"- {ref.name}: {primary_path}")
    refs_text = "\n".join(reference_lines) if reference_lines else "- (none)"
    return (
        f"- Project id: {project.id}\n"
        f"- Title: {project.title}\n"
        f"- Project file: {Path(__file__).resolve().parent.parent / 'projects' / project.id / 'project.json'}\n"
        "- Canonical project document content lives in the item.document fields inside the project file.\n"
        "- Derived artifacts such as backend/preview/, frontend/dist/, ai_logs/, and stage/ are not canonical sources and must not be edited unless the user explicitly asks for them.\n"
        f"- Blueprint path: {project.blueprintPath or '(none)'}\n"
        f"- Mapping path: {project.mappingPath or '(none)'}\n"
        f"- Output path: {project.outputPath or '(none)'}\n"
        f"- MkDocs root: {project.mkdocsRoot or '(none)'}\n"
        f"- Match rules: {_rules_path(project.id, 'match')}\n"
        f"- Generate rules: {_rules_path(project.id, 'generate')}\n"
        f"- Map rules: {_rules_path(project.id, 'map')}\n"
        f"- References:\n{refs_text}"
    )


def _rules_path(project_id: str, kind: str) -> Path:
    from routers.projects import _load_project
    from routers.subjects import subject_rules_path_for_project

    return subject_rules_path_for_project(_load_project(project_id), kind)


def _stage_dir(project_id: str, item_id: str = "") -> Path:
    from routers.projects import PROJECTS_DIR
    if item_id:
        return PROJECTS_DIR / project_id / "stage" / item_id
    return PROJECTS_DIR / project_id / "stage"



def _numbered_stem_parts(path: Path) -> tuple[int, ...] | None:
    stem = path.stem.strip()
    if not re.fullmatch(r"\d+(?:\.\d+)*", stem):
        return None
    try:
        return tuple(int(part) for part in stem.split("."))
    except Exception:
        return None


def _numbered_distance(
    left: tuple[int, ...] | None,
    right: tuple[int, ...] | None,
) -> int:
    if left is None or right is None:
        return 10_000
    max_len = max(len(left), len(right))
    left_parts = left + (0,) * (max_len - len(left))
    right_parts = right + (0,) * (max_len - len(right))
    total = 0
    for idx, (lpart, rpart) in enumerate(zip(left_parts, right_parts)):
        total += abs(lpart - rpart) * (100 ** (max_len - idx - 1))
    return total


def _is_blueprints_path(path: Path) -> bool:
    return any(part.lower() == "blueprints" for part in path.parts)


def _is_style_example_candidate(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    if _is_blueprints_path(path):
        return False
    return _numbered_stem_parts(path) is not None


def _nearest_existing_dir(path: Path) -> Path:
    cur = path
    while not cur.exists() and cur.parent != cur:
        cur = cur.parent
    if cur.exists() and cur.is_dir():
        return cur
    return path


def _guess_docs_anchor(target_dir: Path, mkdocs_root: str) -> Path:
    for candidate in [target_dir, *target_dir.parents]:
        if candidate.name == "docs":
            return candidate
    if mkdocs_root:
        root = Path(os.path.abspath(os.path.expanduser(mkdocs_root)))
        docs_dir = root / "docs"
        if docs_dir.exists() and docs_dir.is_dir():
            return docs_dir
        if root.exists() and root.is_dir():
            return root
    return target_dir


def _is_within_dir(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def _discover_style_examples(
    project: Project,
    *,
    max_files: int,
    search_depth: int,
) -> list[Path]:
    raw_output = (project.outputPath or "").strip()
    if not raw_output or max_files <= 0:
        return []

    output = Path(os.path.abspath(os.path.expanduser(raw_output)))
    target_file = output if output.suffix.lower() == ".md" else None
    target_dir = output.parent if target_file else output
    target_dir = _nearest_existing_dir(target_dir)
    target_num = _numbered_stem_parts(target_file) if target_file else None
    target_file_resolved = target_file.resolve(strict=False) if target_file else None
    anchor = _guess_docs_anchor(target_dir, project.mkdocsRoot)
    anchor = _nearest_existing_dir(anchor)

    selected: list[Path] = []
    seen: set[str] = set()

    def consider(path: Path) -> bool:
        try:
            if not path.is_file():
                return False
            if path.stat().st_size <= 0:
                return False
            if not _is_style_example_candidate(path):
                return False
            resolved = path.resolve(strict=False)
            if target_file_resolved is not None and resolved == target_file_resolved:
                return False
            key = str(resolved)
            if key in seen:
                return False
            seen.add(key)
            selected.append(resolved)
            return True
        except Exception:
            return False

    # First pass: same directory as output file (strongest style signal).
    same_dir_candidates: list[tuple[tuple, Path]] = []
    if target_dir.exists() and target_dir.is_dir():
        for path in target_dir.glob("*.md"):
            cnum = _numbered_stem_parts(path)
            num_dist = _numbered_distance(cnum, target_num)
            same_dir_candidates.append(((num_dist, cnum or (10_000,), path.name.lower()), path))
    same_dir_candidates.sort(key=lambda x: x[0])
    for _, path in same_dir_candidates:
        consider(path)
        if len(selected) >= max_files:
            return selected[:max_files]

    # Second pass: walk up through parent folders only; within each parent,
    # use plain numeric order rather than neighbor distance.
    if search_depth <= 0 or not anchor.exists() or not anchor.is_dir():
        return selected[:max_files]

    current_dir = target_dir.parent
    parent_levels = 0
    while (
        current_dir != current_dir.parent
        and parent_levels < search_depth
        and _is_within_dir(current_dir, anchor)
    ):
        parent_candidates: list[tuple[tuple, Path]] = []
        for path in current_dir.glob("*.md"):
            cnum = _numbered_stem_parts(path)
            parent_candidates.append(((cnum or (10_000,), path.name.lower()), path))
        parent_candidates.sort(key=lambda x: x[0])
        for _, path in parent_candidates:
            consider(path)
            if len(selected) >= max_files:
                return selected[:max_files]

        if current_dir.resolve(strict=False) == anchor.resolve(strict=False):
            break
        current_dir = current_dir.parent
        parent_levels += 1

    return selected[:max_files]



def _normalize_display_math_spacing(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    in_display_math = False

    for line in lines:
        stripped = line.strip()
        if stripped == "$$":
            if not in_display_math:
                # Opening $$: keep exactly one empty line before the block.
                while out and out[-1].strip() == "":
                    out.pop()
                if out:
                    out.append("")
                out.append("$$")
                in_display_math = True
            else:
                # Closing $$: drop trailing empty lines inside the block.
                while out and out[-1].strip() == "":
                    out.pop()
                out.append("$$")
                in_display_math = False
                # Keep exactly one empty line after the block.
                out.append("")
            continue

        if in_display_math and stripped == "" and out and out[-1].strip() == "$$":
            # Avoid inserting a blank line immediately after opening $$.
            continue
        out.append(line)

    while out and out[-1].strip() == "":
        out.pop()
    return "\n".join(out) + "\n"


def _normalize_paragraph_breaks(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    in_fence = False
    in_display_math = False
    pending_blank = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if pending_blank and out and out[-1].strip() != "":
                out.append("")
            pending_blank = False
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
            continue
        if stripped == "$$":
            if pending_blank and out and out[-1].strip() != "":
                out.append("")
            pending_blank = False
            out.append(line)
            in_display_math = not in_display_math
            continue
        if in_display_math:
            out.append(line)
            continue
        if stripped == "":
            pending_blank = True
            continue

        if pending_blank:
            prev = out[-1].strip() if out else ""
            prev_is_table = prev.startswith("|")
            curr_is_table = stripped.startswith("|")
            if not (prev_is_table and curr_is_table):
                out.append("")
            pending_blank = False

        out.append(line)

    while out and out[-1].strip() == "":
        out.pop()
    return "\n".join(out) + "\n"


def _heading_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if re.match(r"^\s{0,3}#{1,6}\s", line))


def _nonempty_line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _safe_sentence_reflow_line_ratio(original: str, candidate: str) -> bool:
    """Return True when extra line count is explained by sentence-per-line reflow."""
    orig = original.strip()
    cand = candidate.strip()
    if not orig or not cand:
        return False

    length_ratio = len(cand) / len(orig)
    if length_ratio < 0.90 or length_ratio > 1.10:
        return False

    similarity = difflib.SequenceMatcher(a=orig, b=cand).ratio()
    if similarity < 0.82:
        return False

    return _nonempty_line_count(cand) > _nonempty_line_count(orig)


def _validate_prepared_text(original: str, candidate: str) -> None:
    if not candidate.strip():
        raise ValueError("Prepared output is empty")

    orig_len = len(original)
    cand_len = len(candidate)
    if orig_len > 0:
        ratio = cand_len / orig_len
        if ratio < 0.85 or ratio > 1.20:
            raise ValueError(
                f"Prepared output length drift too large (ratio={ratio:.3f}, expected 0.85~1.20)"
            )
    orig_lines = _nonempty_line_count(original)
    cand_lines = _nonempty_line_count(candidate)
    if orig_lines > 0:
        line_ratio = cand_lines / orig_lines
        max_line_ratio = 3.00 if _safe_sentence_reflow_line_ratio(original, candidate) else 1.60
        if line_ratio < 0.80 or line_ratio > max_line_ratio:
            raise ValueError(
                f"Prepared output non-empty line-count drift too large "
                f"(ratio={line_ratio:.3f}, expected 0.80~{max_line_ratio:.2f})"
            )

    orig_dollars = original.count("$$")
    cand_dollars = candidate.count("$$")
    if cand_dollars % 2 != 0:
        raise ValueError("Prepared output has unbalanced $$ delimiters")
    if orig_dollars % 2 == 0:
        if orig_dollars != cand_dollars:
            raise ValueError(
                f"Prepared output changed $$ delimiter count ({orig_dollars} -> {cand_dollars})"
            )
    else:
        # Allow small delimiter-count correction when source is already broken.
        if abs(cand_dollars - orig_dollars) > 2:
            raise ValueError(
                f"Prepared output changed $$ delimiter count too much ({orig_dollars} -> {cand_dollars})"
            )

    begin_counts: dict[str, int] = {}
    end_counts: dict[str, int] = {}
    for env in re.findall(r"\\begin\{([^{}]+)\}", candidate):
        begin_counts[env] = begin_counts.get(env, 0) + 1
    for env in re.findall(r"\\end\{([^{}]+)\}", candidate):
        end_counts[env] = end_counts.get(env, 0) + 1
    env_names = set(begin_counts.keys()) | set(end_counts.keys())
    for env in env_names:
        if begin_counts.get(env, 0) != end_counts.get(env, 0):
            raise ValueError(f"Prepared output has unbalanced LaTeX environment: {env}")

    orig_headings = _heading_count(original)
    cand_headings = _heading_count(candidate)
    if cand_headings < orig_headings:
        raise ValueError(
            f"Prepared output removed headings ({orig_headings} -> {cand_headings})"
        )

    similarity = difflib.SequenceMatcher(a=original, b=candidate).ratio()
    if similarity < 0.70:
        raise ValueError(
            f"Prepared output changed too much (similarity={similarity:.3f}, threshold=0.700)"
        )


def extract_text_from_output(output: str) -> str:
    """Extract plain text from agent output, unwrapping one fenced block if present."""
    text = output.replace("\r\n", "\n")
    fenced = re.search(r"```(?:[a-zA-Z0-9_-]+)?\n?(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return text.strip("\n")


def _strip_markdown_bold(text: str) -> str:
    text = text.strip()
    if len(text) >= 4 and text.startswith("**") and text.endswith("**"):
        return text[2:-2].strip()
    return text


def _strip_wrapping_backticks(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        return text[1:-1].strip()
    return text


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _split_mapping_values(text: str) -> list[str]:
    raw = _strip_wrapping_backticks(text).replace("**", "")
    return _unique_preserve_order(
        [_strip_wrapping_backticks(part).strip() for part in raw.split(";")]
    )


def _normalize_inline_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _clean_source_ref_candidate(text: str) -> str:
    value = _normalize_inline_whitespace(text)
    value = value.strip(" \t\r\n\"'`")
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    value = value.rstrip(" .,:;")
    if value.startswith("(") and value.endswith(")") and value.count("(") == 1 and value.count(")") == 1:
        value = value[1:-1].strip()
    return value


_FORMAL_SOURCE_REF_RE = re.compile(
    r"^(Exercise|Exercises|Theorem|Corollary|Lemma|Definition|Figure|Box|Section|Equation)\s+",
    re.IGNORECASE,
)


def _is_formal_source_ref(text: str) -> bool:
    return bool(_FORMAL_SOURCE_REF_RE.match(text.strip()))


def _formal_source_ref_identity(text: str) -> tuple[str, str] | None:
    value = _clean_source_ref_candidate(text)
    match = re.match(
        r"^(Exercise|Exercises|Theorem|Corollary|Lemma|Definition|Figure|Box|Section|Equation)\s+(.+)$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    kind = match.group(1).casefold()
    identifier = _clean_source_ref_candidate(match.group(2))
    if identifier.startswith("(") and identifier.endswith(")"):
        identifier = identifier[1:-1].strip()
    identifier = re.sub(r"\s+", " ", identifier)
    if not identifier:
        return None
    return kind, identifier.casefold()


def _source_ref_similarity_key(text: str) -> str:
    value = _clean_source_ref_candidate(text).casefold()
    value = re.sub(r"^(?:the|a|an)\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _source_ref_score(item, text: str) -> int:
    value = _clean_source_ref_candidate(text)
    lower = value.casefold()
    words = value.split()
    score = 0

    if _is_formal_source_ref(value):
        score += 200
        if lower.startswith("equation "):
            score += 5
    else:
        score += 60
        if len(words) >= 2:
            score += 10
        if re.search(r"[A-Z]", value):
            score += 5

    if lower.startswith(("show that", "verify", "prove", "suppose", "let ", "express", "find ", "compute", "demonstrate", "use ")):
        score -= 80
    if any(ch in value for ch in "$\\{}_^=<>\u27e8\u27e9"):
        score -= 60
    if len(words) > 12:
        score -= 20
    if words and words[-1].casefold() in {"a", "an", "and", "are", "as", "for", "from", "in", "is", "it", "of", "or", "that", "the", "to", "with"}:
        score -= 60
    if len(words) == 1 and len(words[0]) == 1:
        score -= 100
    if len(words) >= 2 and len(words[-1]) == 1:
        score -= 25
    if lower in {"vectors", "operators", "matrices", "matrix", "operator", "vector"}:
        score -= 40
    if item.kind == "section" and not re.match(r"^\d+(?:\.\d+)*", value):
        score -= 30

    return score


def _canonicalize_original_refs(item, refs: list[str]) -> list[str]:
    cleaned = [_clean_source_ref_candidate(ref) for ref in refs]
    cleaned = [ref for ref in cleaned if ref]

    ranked = sorted(
        ((ref, _source_ref_score(item, ref), _source_ref_similarity_key(ref)) for ref in cleaned),
        key=lambda entry: (
            -entry[1],
            0 if _is_formal_source_ref(entry[0]) else 1,
            len(entry[0]),
            entry[0].casefold(),
        ),
    )

    selected: list[tuple[str, int, str]] = []
    for ref, score, key in ranked:
        if score < 0:
            continue

        formal_identity = _formal_source_ref_identity(ref)
        replaced = False
        duplicate = False
        for idx, (existing_ref, existing_score, existing_key) in enumerate(selected):
            existing_formal_identity = _formal_source_ref_identity(existing_ref)
            if formal_identity and existing_formal_identity:
                similar = formal_identity == existing_formal_identity
            else:
                similar = (
                    key == existing_key
                    or (key and existing_key and (key in existing_key or existing_key in key))
                    or difflib.SequenceMatcher(a=key, b=existing_key).ratio() >= 0.92
                )
            if not similar:
                continue
            if score > existing_score:
                selected[idx] = (ref, score, key)
                replaced = True
            duplicate = True
            break
        if duplicate and not replaced:
            continue
        if not duplicate:
            selected.append((ref, score, key))

    selected.sort(
        key=lambda entry: (
            0 if _is_formal_source_ref(entry[0]) else 1,
            -entry[1],
            len(entry[0]),
            entry[0].casefold(),
        )
    )
    return _unique_preserve_order([ref for ref, _, _ in selected])


def _target_ref_kind(target_ref: str) -> str:
    value = target_ref.strip()
    if value.startswith("§ "):
        return "section"
    return value.split(" ", 1)[0].casefold() if value else ""


def _normalize_reference_phrase(text: str) -> str:
    value = _clean_source_ref_candidate(text)
    value = value.replace("**", "").replace("`", "")
    value = value.casefold()
    value = value.replace("-", " ")
    value = re.sub(r"\\[a-zA-Z]+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _reference_phrase_similarity(left: str, right: str) -> float:
    left_key = _normalize_reference_phrase(left)
    right_key = _normalize_reference_phrase(right)
    if not left_key or not right_key:
        return 0.0
    if left_key == right_key:
        return 1.0
    if left_key in right_key or right_key in left_key:
        shorter = min(len(left_key), len(right_key))
        longer = max(len(left_key), len(right_key))
        if longer:
            return shorter / longer
    return difflib.SequenceMatcher(a=left_key, b=right_key).ratio()


def _allow_resolved_candidate_without_additional_refs(
    mention: str,
    target_ref: str,
    matched_source_ref: str,
) -> bool:
    matched = matched_source_ref.strip() or mention.strip()
    if not matched:
        return False
    if _is_formal_source_ref(matched):
        return True

    kind = _target_ref_kind(target_ref)
    similarity = _reference_phrase_similarity(mention, matched)

    if kind in {"theorem", "lemma", "corollary", "example", "proof"}:
        return similarity >= 0.72
    if kind == "section":
        mention_key = _normalize_reference_phrase(mention)
        return similarity >= 0.90 and (
            "section" in mention_key or bool(re.search(r"\d+(?:\.\d+)+", mention))
        )
    return False


def _split_content_source_refs(content: str) -> list[str]:
    text = _normalize_inline_whitespace(content)
    if not text:
        return []

    values: list[str] = []
    paren_labels = re.findall(
        r"\((?:(exercise|exercises|theorem|corollary|lemma|definition|figure|box|section)\s+([^)]+))\)",
        text,
        flags=re.IGNORECASE,
    )
    for kind, number in paren_labels:
        label_kind = kind.capitalize()
        cleaned_number = _clean_source_ref_candidate(number)
        if cleaned_number:
            values.append(f"{label_kind} {cleaned_number}")
    text = re.sub(r"\((?:exercise|exercises|theorem|corollary|lemma|definition|figure|box|section)\s+[^)]+\)", "", text, flags=re.IGNORECASE)
    for part in re.split(r"\s*[,;]\s*", text):
        candidate = _clean_source_ref_candidate(part)
        if candidate:
            values.append(candidate)
    return _unique_preserve_order(values)


def _extract_source_labels_from_excerpt(text: str) -> list[str]:
    labels: list[str] = []

    for match in re.finditer(
        r"^\s*##\s*((?P<label>(?:Box|Figure)\s+\d+(?:\.\d+)*)):\s*(?P<title>.+?)\s*$",
        text,
        re.MULTILINE,
    ):
        label = _clean_source_ref_candidate(match.group("label"))
        title = _clean_source_ref_candidate(match.group("title"))
        if label:
            labels.append(label)
        if title:
            labels.append(title)

    for match in re.finditer(
        r"^\s*##\s*(?P<section>\d+(?:\.\d+)*\s+.+?)\s*$",
        text,
        re.MULTILINE,
    ):
        section_title = _clean_source_ref_candidate(match.group("section"))
        if section_title:
            labels.append(section_title)

    for match in re.finditer(
        r"^\s*(?P<label>(?:Exercise|Exercises|Theorem|Corollary|Lemma|Definition|Figure|Box|Section)\s+\d+(?:\.\d+)*(?:[–-]\d+(?:\.\d+)*)?)\s*:\s*(?P<title>[^.\n]+)",
        text,
        re.MULTILINE,
    ):
        label = _clean_source_ref_candidate(match.group("label"))
        raw_title = _normalize_inline_whitespace(match.group("title"))
        paren_match = re.match(r"^\(([^)]+)\)", raw_title)
        title = _clean_source_ref_candidate(paren_match.group(1)) if paren_match else ""
        if label:
            labels.append(label)
        if title:
            labels.append(title)

    for match in re.finditer(r"\\tag\{([^{}]+)\}", text):
        tag = _clean_source_ref_candidate(match.group(1))
        if tag:
            labels.append(f"Equation ({tag})")

    phrase_patterns = (
        r"\bknown as (?:the )?([^.,\n]+)",
        r"\bcalled (?:the )?([^.,\n]+)",
        r"\bthe ([A-Z][A-Za-z0-9\-]*(?:\s+[A-Za-z0-9\-]+){0,6} (?:procedure|relation|inequality|decomposition|product|representation|function|space|operator|operators|matrices|matrix))\b",
    )
    for pattern in phrase_patterns:
        for match in re.finditer(pattern, text):
            candidate = _clean_source_ref_candidate(match.group(1))
            if candidate and len(candidate) > 2:
                labels.append(candidate)

    return _unique_preserve_order(labels)


def _fallback_section_source_ref(item) -> list[str]:
    content = _normalize_inline_whitespace(item.content or "")
    if not content:
        return []
    content = re.sub(r"^\u00a7\s*", "", content).strip()
    content = re.sub(r"^#+\s*", "", content).strip()
    return [_clean_source_ref_candidate(content)] if content else []


def _deterministic_original_refs(item, new_ref: str) -> list[str]:
    if item.kind == "section":
        return _fallback_section_source_ref(item)

    excerpt_text = item.excerpt or ""
    candidates: list[str] = []
    candidates.extend(_extract_source_labels_from_excerpt(excerpt_text))
    candidates.extend(_split_content_source_refs(item.content or ""))

    if not candidates:
        first_sentence = excerpt_text.split("\n\n", 1)[-1].split(". ", 1)[0].strip()
        first_sentence = re.sub(r"^\[[^\]]+\]\s*", "", first_sentence)
        for match in re.finditer(
            r"\b(?:an?|the)\s+([^.,\n]{3,80}?)\s+(?:is|are|refers to|denote|denotes|defined by|defined to be)\b",
            first_sentence,
            flags=re.IGNORECASE,
        ):
            candidate = _clean_source_ref_candidate(match.group(1))
            if candidate:
                candidates.append(candidate)

    cleaned: list[str] = []
    new_ref_key = _clean_source_ref_candidate(new_ref).casefold()
    trailing_stopwords = {"a", "an", "and", "are", "as", "for", "from", "in", "is", "it", "of", "or", "that", "the", "to", "with"}
    for candidate in candidates:
        value = _clean_source_ref_candidate(candidate)
        if not value:
            continue
        if value.casefold() == new_ref_key:
            continue
        if re.fullmatch(rf"{re.escape(item.type.capitalize())}\s+\d+(?:\.\d+)*", value):
            continue
        words = value.split()
        if words and words[-1].casefold() in trailing_stopwords:
            continue
        cleaned.append(value)
    return _canonicalize_original_refs(item, cleaned)


def _merge_mapping_updates(
    project: Project,
    updates: list[tuple[str, str, list[str]]],
) -> None:
    if not project.mappingPath:
        return

    rows = parse_mapping_file(project.mappingPath)
    canonical_location = canonical_output_location(project.outputPath, project.mkdocsRoot)
    location_aliases = set(output_location_candidates(project.outputPath, project.mkdocsRoot))
    location_aliases.add(canonical_location)

    for source_doc, new_ref, original_refs in updates:
        if not source_doc or not new_ref or not original_refs:
            continue

        row = next(
            (
                existing
                for existing in rows
                if existing.source_doc == source_doc
                and existing.new_ref == new_ref
                and existing.location in location_aliases
            ),
            None,
        )
        if row is None:
            rows.append(
                MappingRow(
                    source_doc=source_doc,
                    new_ref=new_ref,
                    location=canonical_location,
                    original_refs=_unique_preserve_order(original_refs),
                )
            )
            continue

        row.location = canonical_location
        row.original_refs = _unique_preserve_order(original_refs)

    write_mapping_file(
        project.mappingPath,
        rows,
        entry_order_index=project_entry_order_index(project),
    )


def _parse_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return cells if cells else None


def _parse_mapping_sections(mapping_path: str) -> dict[str, list[dict[str, str]]]:
    """Parse mapping markdown into source-doc sections with generic row dicts."""
    path = Path(os.path.abspath(os.path.expanduser(mapping_path)))
    if not path.exists() or not path.is_file():
        return {}

    sections: dict[str, list[dict[str, str]]] = {}
    current_source_doc = ""
    header_cells: list[str] = []
    expect_separator = False

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        section_match = re.match(r"##\s+Reference:\s*(.+?)\s*$", raw_line)
        if section_match:
            current_source_doc = section_match.group(1).strip()
            sections.setdefault(current_source_doc, [])
            header_cells = []
            expect_separator = False
            continue

        if not current_source_doc:
            continue

        cells = _parse_markdown_table_row(raw_line)
        if cells is None:
            continue

        if not header_cells:
            header_cells = cells
            expect_separator = True
            continue

        if expect_separator:
            separator_like = all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)
            if separator_like:
                expect_separator = False
                continue
            header_cells = []
            expect_separator = False
            continue

        if len(cells) != len(header_cells):
            continue

        row = {
            header_cells[idx].strip().lower(): cells[idx].strip()
            for idx in range(len(header_cells))
        }
        sections[current_source_doc].append(row)

    return sections


def _mapping_target_doc_candidates(project: Project) -> list[str]:
    output_path = (project.outputPath or "").strip()
    if not output_path:
        return []

    path = Path(os.path.abspath(os.path.expanduser(output_path)))
    candidates = [canonical_output_location(project.outputPath, project.mkdocsRoot), path.name]

    mkdocs_root = (project.mkdocsRoot or "").strip()
    if mkdocs_root:
        docs_root = Path(os.path.abspath(os.path.expanduser(mkdocs_root))) / "docs"
        try:
            rel = path.relative_to(docs_root)
            candidates.append(str(rel))
        except ValueError:
            pass

    candidates.append(str(path))
    return _unique_preserve_order(candidates)


def _excerpt_ref_name_aliases(project: Project) -> dict[str, str]:
    alias_to_name: dict[str, str] = {}
    ambiguous: set[str] = set()

    def add_alias(alias: str, canonical: str) -> None:
        value = alias.strip()
        if not value:
            return
        existing = alias_to_name.get(value)
        if existing is not None and existing != canonical:
            ambiguous.add(value)
            return
        alias_to_name[value] = canonical

    for ref in project.references:
        canonical = (ref.name or "").strip()
        if not canonical:
            continue
        add_alias(canonical, canonical)
        add_alias(f"refs/{canonical}", canonical)
        ref_path = (ref.path or "").strip()
        if ref_path:
            add_alias(ref_path, canonical)
            add_alias(Path(ref_path).name, canonical)

    for alias in ambiguous:
        alias_to_name.pop(alias, None)
    return alias_to_name


def _normalize_excerpt_reference_headers(project: Project, excerpt: str) -> str:
    if not excerpt.strip():
        return excerpt

    alias_to_name = _excerpt_ref_name_aliases(project)
    if not alias_to_name:
        return excerpt

    def repl(match: re.Match[str]) -> str:
        raw_name = match.group(1).strip()
        line_span = match.group(2)
        canonical = alias_to_name.get(raw_name)
        if canonical is None:
            canonical = alias_to_name.get(Path(raw_name).name)
        if canonical is None and raw_name.startswith("refs/"):
            canonical = alias_to_name.get(raw_name.split("/", 1)[1])
        if canonical is None:
            return match.group(0)
        return f"[{canonical} line {line_span}]"

    normalized = re.sub(
        r"(?:(?<=^)|(?<=\n))\[([^\]\n]+?) line (\d+~\d+)\](?=(?:\n|\\n|$))",
        repl,
        excerpt,
    )
    return re.sub(
        r"(^\[[^\]\n]+? line \d+~\d+\])(?:\\n)+",
        lambda match: match.group(1) + "\n\n",
        normalized,
        flags=re.MULTILINE,
    )


def _excerpt_source_docs(project: Project, excerpt: str) -> list[str]:
    if not excerpt.strip():
        return []

    ref_name_to_original: dict[str, str] = {}
    for ref in project.references:
        original = (ref.originalPath or ref.path or "").strip()
        if ref.name and original:
            ref_name_to_original[ref.name] = original

    source_docs: list[str] = []
    for match in re.finditer(r"^\[([^\]\n]+?) line \d+~\d+\]$", excerpt, re.MULTILINE):
        ref_name = match.group(1).strip()
        original = ref_name_to_original.get(ref_name)
        if original:
            source_docs.append(original)

    if source_docs:
        return _unique_preserve_order(source_docs)

    for ref in project.references:
        original = (ref.originalPath or ref.path or "").strip()
        if original:
            source_docs.append(original)
    return _unique_preserve_order(source_docs)


def _mapping_rows_for_excerpt(project: Project, excerpt: str) -> list[dict[str, object]]:
    if not project.mappingPath:
        return []

    sections = _parse_mapping_sections(project.mappingPath)
    if not sections:
        return []

    rows: list[dict[str, object]] = []
    for source_doc in _excerpt_source_docs(project, excerpt):
        for raw_row in sections.get(source_doc, []):
            target_ref = (raw_row.get("target ref") or raw_row.get("new ref") or "").strip()
            target_doc = (raw_row.get("target doc") or raw_row.get("location") or "").strip()
            refs_text = (raw_row.get("source refs") or raw_row.get("original ref") or "").strip()
            aliases_text = (raw_row.get("aliases") or "").strip()
            note = (raw_row.get("note") or "").strip()
            if not target_ref:
                continue

            source_refs = _split_mapping_values(refs_text)
            aliases = _split_mapping_values(_strip_markdown_bold(aliases_text))

            rows.append(
                {
                    "source_doc": source_doc,
                    "target_ref": target_ref,
                    "target_doc": target_doc,
                    "source_refs": source_refs,
                    "aliases": aliases,
                    "note": note,
                }
            )
    return rows


def _normalize_target_doc_for_match(value: str) -> str:
    return value.strip().replace("\\", "/").casefold()


async def _resolve_reference_candidates(
    project: Project,
    item,
    prefix: str,
    cwd: str,
    *,
    user_prompt: str = "",
) -> list[dict[str, str]]:
    if not project.mappingPath or not item.excerpt.strip():
        return []

    relevant_rows = _mapping_rows_for_excerpt(project, item.excerpt)
    if not relevant_rows:
        return []

    current_target_ref = _item_new_ref(item, prefix)
    current_target_docs = _mapping_target_doc_candidates(project)
    current_target_doc_keys = {_normalize_target_doc_for_match(value) for value in current_target_docs}

    valid_by_pair: dict[tuple[str, str], dict[str, object]] = {}
    unique_target_docs_by_ref: dict[str, set[str]] = {}
    row_lines: list[str] = []
    for row in relevant_rows:
        target_ref = str(row.get("target_ref") or "").strip()
        target_doc = str(row.get("target_doc") or "").strip()
        valid_by_pair[(target_ref, target_doc)] = row
        unique_target_docs_by_ref.setdefault(target_ref, set()).add(target_doc)
        source_refs = row.get("source_refs") or []
        aliases = row.get("aliases") or []
        note = str(row.get("note") or "").strip()
        line = (
            f'- Target ref: "{target_ref}"'
            f' | Target doc: "{target_doc or "(unknown)"}"'
            f' | Source refs: {"; ".join(source_refs) if source_refs else "(none)"}'
            f' | Aliases: {"; ".join(aliases) if aliases else "(none)"}'
        )
        if note:
            line += f" | Note: {note}"
        row_lines.append(line)

    if not row_lines:
        return []

    allow_additional_references = _user_requested_additional_references(user_prompt)
    current_document_hint = ""
    if item.document.strip():
        current_document_hint = (
            "Current document (for reference-repair context only; NOT a factual source):\n"
            f"{item.document}\n\n"
        )

    prompt = (
        "You are resolving cross-references for notes generation.\n"
        "The excerpt below is the ONLY factual source.\n"
        "The mapping rows below are canonical lookup rows from the shared mapping file for the same original source document.\n\n"
        f'Current notes target: "{current_target_ref or "(none)"}"\n'
        f"Current notes document identifiers: {', '.join(current_target_docs) if current_target_docs else '(none)'}\n\n"
        f"Excerpt:\n{item.excerpt}\n\n"
        f"{current_document_hint}"
        f'User explicitly requested additional references: {"yes" if allow_additional_references else "no"}\n\n'
        f"Canonical mapping rows:\n" + "\n".join(row_lines) + "\n\n"
        "Task:\n"
        "1. Identify explicit source-side citations, labels, equations, figures, boxes, section titles, or named results already present in the excerpt that likely refer to one of the mapping rows.\n"
        "2. Prefer exact matches to Source refs.\n"
        "3. If exact match is not available, you may choose a close semantic match, but only if it is specific and high-confidence.\n"
        "4. Do not invent any target that is not present in the mapping rows.\n"
        "5. Do not return the current notes target itself as a self-reference.\n"
        "6. Do not infer new conceptual backlinks merely because a concept is discussed in the excerpt.\n"
        "7. If additional references were not explicitly requested, return only replacements for references already present in the excerpt or current document.\n"
        "8. In that replacement-only mode, do not return definition/concept targets for ordinary term mentions; reserve non-formal semantic matches for clearly named theorem/lemma/corollary/example-style results.\n"
        "9. If additional references were explicitly requested, you may add a small number of additional high-confidence mapping-based references when they materially clarify the note.\n"
        "10. Avoid generic or ambiguous matches.\n"
        "11. Return at most 8 candidates.\n\n"
        "Output ONLY a JSON array of objects with keys:\n"
        '  mention, target_ref, target_doc, matched_source_ref, confidence, reason\n'
        'confidence must be one of: "high", "medium", "low"\n'
    )

    provider, model, reasoning_effort = _runtime_agent_settings()
    raw_output = await run_agent(
        prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="reference_link",
        log_meta={"itemId": item.id, "mappingPath": project.mappingPath},
    )

    try:
        parsed = json.loads(extract_text_from_output(raw_output) or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    resolved: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        mention = str(entry.get("mention") or "").strip()
        target_ref = str(entry.get("target_ref") or "").strip()
        target_doc = str(entry.get("target_doc") or "").strip()
        matched_source_ref = str(entry.get("matched_source_ref") or "").strip()
        confidence = str(entry.get("confidence") or "").strip().lower()
        reason = str(entry.get("reason") or "").strip()
        if not mention or not target_ref:
            continue
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"

        pair_row = None
        if target_doc:
            pair_row = valid_by_pair.get((target_ref, target_doc))
            if pair_row is None:
                requested_doc_key = _normalize_target_doc_for_match(target_doc)
                for (row_target_ref, row_target_doc), candidate_row in valid_by_pair.items():
                    if row_target_ref != target_ref:
                        continue
                    row_doc_key = _normalize_target_doc_for_match(row_target_doc)
                    if row_doc_key == requested_doc_key or Path(row_target_doc).name.casefold() == Path(target_doc).name.casefold():
                        pair_row = candidate_row
                        target_doc = row_target_doc
                        break
        else:
            docs_for_ref = unique_target_docs_by_ref.get(target_ref, set())
            if len(docs_for_ref) == 1:
                target_doc = next(iter(docs_for_ref))
                pair_row = valid_by_pair.get((target_ref, target_doc))

        if pair_row is None:
            continue

        if target_ref == current_target_ref and (
            not target_doc or _normalize_target_doc_for_match(target_doc) in current_target_doc_keys
        ):
            continue

        if (
            not allow_additional_references
            and not _allow_resolved_candidate_without_additional_refs(
                mention,
                target_ref,
                matched_source_ref,
            )
        ):
            continue

        dedupe_key = (mention.casefold(), target_ref, target_doc)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        resolved.append(
            {
                "mention": mention,
                "target_ref": target_ref,
                "target_doc": target_doc,
                "matched_source_ref": matched_source_ref,
                "confidence": confidence,
                "reason": reason,
            }
        )

    if any(row["confidence"] in {"high", "medium"} for row in resolved):
        resolved = [row for row in resolved if row["confidence"] in {"high", "medium"}]

    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    resolved.sort(
        key=lambda row: (
            confidence_rank.get(row.get("confidence", "low"), 2),
            row.get("target_doc", ""),
            row.get("target_ref", ""),
            row.get("mention", ""),
        )
    )
    return resolved


def _user_requested_additional_references(user_prompt: str) -> bool:
    text = (user_prompt or "").strip().casefold()
    if not text:
        return False
    if re.search(r"\b(?:do not|don't|avoid|without)\s+add(?:ing)?\s+(?:additional\s+)?(?:cross[- ]?)?references?\b", text):
        return False
    patterns = (
        r"\badd(?:itional)?\s+(?:cross[- ]?)?references?\b",
        r"\badd\s+(?:citations?|xrefs?|cross[- ]?refs?)\b",
        r"\buse\s+the\s+(?:canonical\s+)?map(?:ping)?\b",
        r"\blook\s+at\s+the\s+map(?:ping)?s?\b",
        r"\binclude\s+additional\s+(?:cross[- ]?)?references?\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _user_requested_reference_work(user_prompt: str) -> bool:
    text = (user_prompt or "").strip().casefold()
    if not text:
        return False
    patterns = (
        r"\bcross[- ]?references?\b",
        r"\bnotes-side references?\b",
        r"\bcanonical mapping\b",
        r"\bmapping\b",
        r"\bupdate .*references?\b",
        r"\bfix .*references?\b",
        r"\brepair .*references?\b",
        r"\breference style\b",
        r"\bcitations?\b",
        r"\bxrefs?\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _format_resolved_reference_hint(
    resolved: list[dict[str, str]],
    *,
    allow_additional_references: bool,
) -> str:
    if not resolved:
        return ""

    lines = []
    for row in resolved:
        mention = row.get("mention", "").strip()
        target_ref = row.get("target_ref", "").strip()
        target_doc = row.get("target_doc", "").strip() or "(unknown)"
        matched_source_ref = row.get("matched_source_ref", "").strip()
        confidence = row.get("confidence", "").strip() or "medium"
        reason = row.get("reason", "").strip()
        line = f'  - "{mention}" -> {target_ref} ({target_doc}) [confidence: {confidence}]'
        if matched_source_ref:
            line += f'; matched via "{matched_source_ref}"'
        if reason:
            line += f"; reason: {reason}"
        lines.append(line)

    return (
        "\nResolved cross-reference candidates (already selected from the canonical mapping rows for this excerpt):\n"
        + "\n".join(lines)
        + (
            "\nUse these notes-side references to replace corresponding original-source references already present in the excerpt or current document.\n"
            "Do not add new notes-side references beyond those replacements unless the user explicitly asked for additional references.\n"
            if not allow_additional_references else
            "\nUse these notes-side references when the generated note refers to the corresponding source-side items.\n"
            "Additional references were explicitly requested by the user, so you may add a small number of other high-confidence mapping-based references when genuinely helpful.\n"
        )
    )


def _item_new_ref(item, prefix: str) -> str:
    """Return the 'New ref' label for an item (used in the numbering map)."""
    if item.kind == "admonition":
        if item.number == 0:
            return ""
        cap = item.type.capitalize()
        return f"{cap} {prefix}.{item.number}" if prefix else f"{cap} {item.number}"
    elif item.kind == "section":
        return f"§ {item.content}"
    return ""


async def run_map_update_agent(
    project: Project,
    item_ids: list[str],
    stage_dir: str,
    cwd: str,
    map_rules_path: str = "",
) -> None:
    """Update mapping rows for items using deterministic extraction, with AI fallback."""
    if not project.mappingPath:
        return

    started_at = datetime.now(timezone.utc)

    prefix = ""
    for it in project.items:
        if it.kind == "section" and it.type == "h1":
            m = re.search(r'(?:§\s*)?(\d+(?:\.\d+)*)', it.content)
            if m:
                prefix = m.group(1)
            break

    location = canonical_output_location(project.outputPath, project.mkdocsRoot)

    # Build mapping: current ref name (as it appears in excerpt headers) → original path
    ref_name_to_original: dict[str, str] = {}
    for ref in project.references:
        original = (ref.originalPath or ref.path or "").strip()
        if ref.name and original:
            ref_name_to_original[ref.name] = original

    items_by_id = {it.id: it for it in project.items}
    updates: list[tuple[str, str, list[str]]] = []
    unresolved_items: list[tuple[str, object, str]] = []
    item_blocks: list[str] = []

    for iid in item_ids:
        item = items_by_id.get(iid)
        if item is None or not item.excerpt:
            continue
        new_ref = _item_new_ref(item, prefix)
        if not new_ref:
            continue

        deterministic_refs = _deterministic_original_refs(item, new_ref)
        source_docs = _excerpt_source_docs(project, item.excerpt)
        if deterministic_refs and source_docs:
            for source_doc in source_docs:
                updates.append((source_doc, new_ref, deterministic_refs))
            continue

        unresolved_items.append((iid, item, new_ref))
        candidate_text = "; ".join(deterministic_refs) if deterministic_refs else "(none)"
        item_blocks.append(
            f'<<<ITEM id="{iid}">\n'
            f'  New ref: "{new_ref}"\n'
            f"  Blueprint content: {item.content}\n"
            f"  Deterministic candidate Original refs: {candidate_text}\n"
            f"  Excerpt:\n{item.excerpt}\n"
            f"<<<END_ITEM>>>"
        )

    if updates:
        _merge_mapping_updates(project, updates)

    if not item_blocks:
        finished_at = datetime.now(timezone.utc)
        duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
        summary = (
            "Deterministic map sync completed without AI fallback.\n"
            f"Updated items: {', '.join(item_ids) if item_ids else '(none)'}\n"
            f"Mapping path: {project.mappingPath}"
        )
        write_ai_log(
            project.id,
            run_type="map_update",
            provider="deterministic",
            model="",
            reasoning_effort="",
            cwd=cwd,
            command=[],
            prompt=summary,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            status="done",
            stdout=summary,
            stderr="",
            meta={"itemIds": item_ids, "mappingPath": project.mappingPath, "deterministic": True},
        )
        return

    items_str = "\n\n".join(item_blocks)

    # Build ref-name-to-original hint for the agent
    ref_hint_lines = [
        f"  {name}  →  {orig}"
        for name, orig in ref_name_to_original.items()
    ]
    ref_hint = "\n".join(ref_hint_lines) if ref_hint_lines else "  (none)"

    rules_hint = f"Read your mapping rules from: {map_rules_path}\n\n" if map_rules_path else ""
    task_prompt = (
        f"{rules_hint}"
        f"Notes output file (Location): {location}\n"
        "Use the canonical notes document path relative to the MkDocs docs/ root when available.\n\n"
        "Stable mapping policy:\n"
        "  - Keep each row narrow and canonical.\n"
        "  - 'Original ref' must identify the item itself, not dependencies or supporting mentions inside the excerpt.\n"
        "  - If the item has multiple equally canonical source-side identifiers, store them in the same 'Original ref' cell separated by '; '.\n"
        '  - Prefer explicit source-side labels when available (for example: "Theorem 2.3", "Exercise 2.19", "Equation (2.61)", "Box 2.1", "Figure 2.2", section title).\n'
        "  - If no formal label exists, use the exact named result or concept from the source text.\n"
        "  - Do not try to encode exhaustive synonyms or alias variants in the mapping file; generation now performs semantic search over canonical rows.\n\n"
        "  - Never return the notes-side label itself as an Original ref.\n"
        "  - Use the deterministic candidate Original refs when they are already good; only improve or supplement them if the excerpt clearly supports it.\n\n"
        f"Reference name mapping (excerpt header name → original file path):\n{ref_hint}\n\n"
        "Task:\n"
        "For each item, return a JSON object with:\n"
        '  item_id, source_docs, original_refs\n'
        "source_docs must be the list of original file paths inferred from the excerpt headers.\n"
        "original_refs must be a list of one or more canonical source-side identifiers for that item.\n"
        "Return only items that still need help.\n\n"
        f"Items:\n{items_str}\n\n"
        "Output ONLY a JSON array."
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    raw_output = await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="map_update",
        log_meta={"itemIds": item_ids, "mappingPath": project.mappingPath},
    )

    try:
        parsed = json.loads(extract_text_from_output(raw_output) or "[]")
    except json.JSONDecodeError:
        return
    if not isinstance(parsed, list):
        return

    fallback_updates: list[tuple[str, str, list[str]]] = []
    unresolved_by_id = {iid: (item, new_ref) for iid, item, new_ref in unresolved_items}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        item_id = str(entry.get("item_id") or "").strip()
        unresolved = unresolved_by_id.get(item_id)
        if unresolved is None:
            continue
        item, new_ref = unresolved
        source_docs = entry.get("source_docs")
        if not isinstance(source_docs, list):
            source_docs = _excerpt_source_docs(project, item.excerpt)
        source_doc_values = _unique_preserve_order([str(doc).strip() for doc in source_docs if str(doc).strip()])
        if not source_doc_values:
            source_doc_values = _excerpt_source_docs(project, item.excerpt)

        raw_refs = entry.get("original_refs")
        if isinstance(raw_refs, list):
            original_refs = _unique_preserve_order([_clean_source_ref_candidate(str(ref)) for ref in raw_refs])
        else:
            original_refs = _split_mapping_values(str(raw_refs or ""))
        original_refs = [
            ref for ref in original_refs
            if ref
            and ref.casefold() != _clean_source_ref_candidate(new_ref).casefold()
        ]
        if not original_refs:
            original_refs = _split_content_source_refs(item.content or "")
        original_refs = _canonicalize_original_refs(item, original_refs)
        if not original_refs:
            continue

        for source_doc in source_doc_values:
            fallback_updates.append((source_doc, new_ref, original_refs))

    if fallback_updates:
        _merge_mapping_updates(project, fallback_updates)


async def run_match_agent(
    project: Project,
    item_ids: list[str],
    user_prompt: str,
    stage_dir: str,
    match_rules_path: str,
    cwd: str,
) -> str:
    """Run match agent: writes one plain-text excerpt file per item into stage_dir."""
    ref_lines = []
    for ref in project.references:
        ref_lines.append(f"  - {ref.path} (name: {ref.name})")
    refs_str = "\n".join(ref_lines) if ref_lines else "  (none)"

    items_by_id = {it.id: it for it in project.items}
    item_blocks: list[str] = []
    for iid in item_ids:
        item = items_by_id.get(iid)
        if item is None:
            continue
        block = (
            f'<<<ITEM id="{iid}" kind="{item.kind}" type="{item.type}">\n'
            f"Blueprint content: {item.content}\n"
        )
        if item.excerpt.strip():
            block += (
                "Previous excerpt hint "
                "(may be stale; re-extract from current reference files):\n"
                f"{item.excerpt}\n"
            )
        block += "<<<END_ITEM>>>"
        item_blocks.append(block)
    items_str = "\n\n".join(item_blocks)
    file_list = "\n".join(
        f"  {stage_dir}/{iid}.excerpt"
        for iid in item_ids if iid in items_by_id
    )

    user_hint = f"\nAdditional instructions: {user_prompt}" if user_prompt else ""

    task_prompt = (
        f"Read your extraction rules from: {match_rules_path}\n\n"
        f"Reference files:\n{refs_str}\n\n"
        "Important matching instructions:\n"
        "- Re-read the CURRENT reference files for every item and rewrite each excerpt from scratch.\n"
        "- Treat any previous excerpt shown below as a stale hint only.\n"
        "- Do not preserve old file names, paths, line numbers, or chunk boundaries unless you freshly verify them in the current reference files.\n"
        "- If the previous excerpt conflicts with the current reference files, replace it.\n\n"
        f"Items to match:\n{items_str}\n"
        f"{user_hint}\n\n"
        f"For each item, write its excerpt to:\n{file_list}\n\n"
        f"Output only: done"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    return await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="match",
        log_meta={"itemIds": item_ids},
    )


async def run_generate_agent(
    project: Project,
    item_ids: list[str],
    user_prompt: str,
    available_types: list[str],
    stage_dir: str,
    generate_rules_path: str,
    cwd: str,
) -> str:
    """Run generate agent: writes one plain-text document file per item into stage_dir."""
    types_hint = ", ".join(available_types) if available_types else "definition, theorem, concept, example"
    output_path = (project.outputPath or "").strip()
    (
        auto_style_examples,
        max_example_files,
        search_depth,
    ) = _runtime_generation_settings()

    prefix = ""
    for it in project.items:
        if it.kind == "section" and it.type == "h1":
            m = re.search(r'(?:§\s*)?(\d+(?:\.\d+)*)', it.content)
            if m:
                prefix = m.group(1)
            break

    items_by_id = {it.id: it for it in project.items}
    item_blocks: list[str] = []
    resolved_mapping_hint = ""
    allow_additional_references = _user_requested_additional_references(user_prompt)
    for iid in item_ids:
        item = items_by_id.get(iid)
        if item is None:
            continue
        resolved_candidates = await _resolve_reference_candidates(
            project,
            item,
            prefix,
            cwd,
            user_prompt=user_prompt,
        )
        if resolved_candidates:
            resolved_mapping_hint += _format_resolved_reference_hint(
                resolved_candidates,
                allow_additional_references=allow_additional_references,
            )
        block = (
            f'<<<ITEM id="{iid}" kind="{item.kind}" type="{item.type}" number="{item.number}">\n'
            f"Blueprint content:\n{item.content}\n\n"
            f"Excerpt (ONLY factual source):\n{item.excerpt}\n"
        )
        if item.document.strip():
            block += f"\nCurrent document:\n{item.document}\n"
        block += "<<<END_ITEM>>>"
        item_blocks.append(block)
    items_str = "\n\n".join(item_blocks) if item_blocks else "(none)"

    user_hint = f"\nAdditional instructions: {user_prompt}" if user_prompt else ""

    mapping_hint = ""
    if project.mappingPath:
        mp = Path(os.path.abspath(os.path.expanduser(project.mappingPath)))
        if mp.exists():
            if resolved_mapping_hint.strip():
                mapping_hint = resolved_mapping_hint + "\n"
            else:
                mapping_hint = f"\nCanonical cross-reference map: {project.mappingPath}\n"
                if not allow_additional_references:
                    mapping_hint += (
                        "Use the canonical map only to replace explicit original-source citations already present in the excerpt or current document.\n"
                        "Do not add new notes-side references from the map unless the user explicitly asked for additional references.\n"
                    )
                else:
                    mapping_hint += (
                        "If the user explicitly asked for additional references, you may consult the canonical map to add a small number of high-confidence notes-side references.\n"
                        "Otherwise, use it only to replace explicit original-source citations already present in the excerpt or current document.\n"
                    )

    style_paths: list[Path] = []
    if auto_style_examples:
        style_paths = _discover_style_examples(
            project,
            max_files=max(0, max_example_files),
            search_depth=max(0, search_depth),
        )
    style_paths_str = "\n".join(f"  - {str(p)}" for p in style_paths) if style_paths else "  (none)"

    items_by_id_for_files = {it.id: it for it in project.items}
    file_list = "\n".join(
        f"  {stage_dir}/{iid}.document"
        for iid in item_ids if iid in items_by_id_for_files
    )

    prefix_hint = f'Number prefix: {prefix}  (use as: "{{Type}} {prefix}.{{number}}")' if prefix else "Number prefix: (none)"
    reference_style_hint = (
        "Cross-reference style:\n"
        'Write notes-side references naturally in prose, for example: "according to **Definition 3.5.1**" '
        'or "Using the gram-schmidt theorem (**Theorem 2.5.1**)".\n'
        "Bold only the notes-side reference label itself; keep the surrounding prose outside the bold span.\n"
    )
    task_prompt = (
        f"Read your writing rules from: {generate_rules_path}\n"
        f"Style reference files (tone/structure only — do not copy facts):\n{style_paths_str}\n\n"
        f"Target output file: {output_path or '(not provided)'}\n"
        f"Available admonition types: {types_hint}\n"
        f"{prefix_hint}\n"
        f"{reference_style_hint}"
        f"{mapping_hint}"
        f"Items to generate:\n{items_str}\n"
        f"{user_hint}\n\n"
        f"For each item, write its generated markdown to:\n{file_list}\n\n"
        f"Output only: done"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    return await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="generate",
        log_meta={
            "itemIds": item_ids,
            "outputPath": output_path,
            "exampleFiles": [str(p) for p in style_paths],
        },
    )


async def run_prepare_agent(
    project_id: str,
    ref_path: str,
    cwd: str,
) -> str:
    """Run preparation agent with staging + validation + backup."""
    source = Path(os.path.abspath(os.path.expanduser(ref_path)))
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Reference file not found: {source}")
    stage = source.with_suffix(source.suffix + ".prep.tmp")
    if stage.exists():
        stage.unlink()

    original_text = source.read_text(encoding="utf-8", errors="replace")
    task_prompt = (
        f"Read the reference file at {source}.\n"
        f"Correct OCR errors, typos, and formatting issues while preserving all mathematical meaning.\n"
        f"Formatting rules for the rewritten file:\n"
        f"1) Add a line break after each completed sentence in prose.\n"
        f"2) For every display-math block delimited by $$...$$, include one empty line before the opening $$ and one empty line after the closing $$.\n"
        f"Keep equations, symbols, and references intact.\n"
        f"Write the corrected content to: {stage}\n"
        f"Output ONLY the string: done"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project_id,
        run_type="prepare",
        log_meta={"referencePath": str(source), "stagePath": str(stage)},
    )

    if not stage.exists() or not stage.is_file():
        raise ValueError(f"Prepare staging file was not created: {stage}")

    staged_text = stage.read_text(encoding="utf-8", errors="replace")
    normalized_text = _normalize_paragraph_breaks(_normalize_display_math_spacing(staged_text))
    _validate_prepared_text(original_text, normalized_text)

    backup = source.with_suffix(
        source.suffix + f".bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    shutil.copyfile(source, backup)
    source.write_text(normalized_text, encoding="utf-8")
    try:
        stage.unlink()
    except Exception:
        pass
    return str(source)


class SectionNotFound(ValueError):
    """Raised when no suitable section match is found in the reference."""


def _parse_headings_from_text(text: str) -> list[tuple[int, int, str]]:
    result = []
    for i, line in enumerate(text.splitlines()):
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            result.append((i, len(m.group(1)), m.group(2).strip()))
    return result


def _heading_words(text: str) -> set[str]:
    text = re.sub(r"\b\d[\d.]*\b", " ", text.lower())
    return {w for w in re.split(r"[^a-z]+", text) if len(w) > 1}


def _score_heading_match(query: str, candidate: str) -> float:
    qw, cw = _heading_words(query), _heading_words(candidate)
    if not qw or not cw:
        return 0.0
    return len(qw & cw) / len(qw | cw)


def _find_best_heading_match(
    query: str,
    headings: list[tuple[int, int, str]],
    min_score: float = 0.3,
) -> tuple[int, int, str] | None:
    best_score, best = -1.0, None
    for entry in headings:
        s = _score_heading_match(query, entry[2])
        if s > best_score:
            best_score, best = s, entry
    return best if best_score >= min_score else None


async def _agent_find_section_end(
    start_line: int,
    start_level: int,
    start_heading: str,
    subsequent_headings: list[tuple[int, int, str]],
    total_lines: int,
    project_id: str,
    cwd: str,
) -> int:
    """Return 0-indexed exclusive end line of the section."""
    heading_list = "\n".join(
        f"  line {line + 1}, level {level}, {'#' * level} {text}"
        for line, level, text in subsequent_headings
    )
    prompt = (
        f"A markdown textbook section starts at line {start_line + 1}:\n"
        f"  {'#' * start_level} {start_heading}\n\n"
        f"The following headings appear after it:\n"
        f"{heading_list}\n\n"
        f"Task: identify which heading line marks the END of section '{start_heading}'.\n"
        f"The section ends where a new peer or parent section begins "
        f"(i.e. a heading that is NOT a subsection of '{start_heading}').\n"
        f"Note: heading levels may be inconsistent due to OCR — use title content "
        f"and numbering patterns (e.g. '2.2' ends '2.1') to decide.\n"
        f"If no heading ends the section, output {total_lines + 1}.\n\n"
        f"Output ONLY a single integer: the 1-indexed line number of the first heading "
        f"that is NOT part of this section. No explanation."
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    raw = await run_agent(
        prompt, cwd,
        provider=provider, model=model, reasoning_effort=reasoning_effort,
        project_id=project_id, run_type="extract_section",
    )
    m = re.search(r"\d+", raw)
    if not m:
        raise ValueError(f"Agent returned non-integer for section end: {raw!r}")
    return int(m.group()) - 1  # 0-indexed exclusive


async def run_section_extract_agent(
    project: Project,
    ref_path: str,
    cwd: str,
) -> str:
    """Extract the section matching the project's h1 title from a full-textbook reference.

    Returns the path of the newly written section file.
    Raises SectionNotFound if no suitable match exists (caller should fall back to OCR prep).
    """
    h1_title = ""
    for item in project.items:
        if item.kind == "section" and item.type == "h1":
            h1_title = item.content
            break
    if not h1_title:
        raise SectionNotFound("No h1 section item in project")

    source = Path(os.path.abspath(os.path.expanduser(ref_path)))
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Reference file not found: {source}")

    text = source.read_text(encoding="utf-8", errors="replace")
    all_lines = text.splitlines()
    headings = _parse_headings_from_text(text)

    if len(headings) < 5:
        raise SectionNotFound("Reference has too few headings to be a full textbook")

    match = _find_best_heading_match(h1_title, headings)
    if match is None:
        raise SectionNotFound(f"No heading in reference matches project h1 {h1_title!r}")

    start_line, start_level, start_heading = match
    match_idx = headings.index(match)
    subsequent = headings[match_idx + 1:]

    end_line = await _agent_find_section_end(
        start_line, start_level, start_heading, subsequent, len(all_lines),
        project_id=project.id, cwd=cwd,
    )

    section_text = "\n".join(all_lines[start_line:end_line]) + "\n"
    out_path = source
    out_path.write_text(section_text, encoding="utf-8")
    return str(out_path.resolve())


async def run_ai_command_agent(
    project: Project,
    user_message: str,
    history: list[AiConversationMessage],
    cwd: str,
) -> str:
    """Run a project-wide AI command that may inspect or edit relevant files."""
    prompt = (
        "You are the project-level AI workspace assistant for this repository.\n"
        "Work like a local Codex session in the current workspace: inspect and edit files directly when needed.\n"
        "Use the current workspace and the linked project files below as your working context.\n\n"
        "Project context:\n"
        f"{_project_context_block(project)}\n\n"
        "Conversation so far:\n"
        f"{_conversation_history_block(history)}\n\n"
        "Current user message:\n"
        f"{user_message.strip()}\n\n"
        "Requirements:\n"
        "- Answer the user's request directly.\n"
        "- If edits are needed, make them.\n"
        "- Prefer small, targeted changes over broad rewrites unless the user requested a broader change.\n"
        "- Preserve valid syntax and existing workflows when editing structured files.\n"
        "- If the request involves note excerpts or note documents, edit the canonical project file item.excerpt and item.document fields directly.\n"
        "- Do not edit backend/preview/, frontend/dist/, ai_logs/, stage/, or __pycache__ unless the user explicitly asks for those derived files.\n"
        "- Avoid destructive actions unless the user explicitly requested them.\n"
        "- If no edits are needed, explain what you found.\n\n"
        "After you edit the project file, the system will reload and normalize it automatically, so keep the JSON valid.\n\n"
        "When finished, reply in concise Markdown with:\n"
        "- what you changed or found\n"
        "- important files touched, if any\n"
        "- blockers or follow-up notes, if any\n"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    return await run_agent(
        prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="ai_command",
        log_meta={"messageLength": len(user_message.strip())},
    )


async def run_edit_agent(
    project: Project,
    item_id: str,
    target: str,
    original_text: str,
    user_prompt: str,
    stage_dir: str,
    rules_path: str,
    cwd: str,
) -> str:
    """Run edit agent: writes rewritten content to {stage_dir}/{item_id}.{target}."""
    instruction = user_prompt.strip() or (
        "Improve clarity while preserving meaning, math notation, and structure."
    )
    stage_file = f"{stage_dir}/{item_id}.{target}"
    mapping_hint = ""
    reference_style_hint = ""
    excerpt_context = ""

    if target == "document" and _user_requested_reference_work(user_prompt):
        source_item = next((it for it in project.items if it.id == item_id), None)
        if source_item is not None:
            prefix = ""
            for it in project.items:
                if it.kind == "section" and it.type == "h1":
                    m = re.search(r'(?:§\s*)?(\d+(?:\.\d+)*)', it.content)
                    if m:
                        prefix = m.group(1)
                    break

            if hasattr(source_item, "model_copy"):
                item_for_mapping = source_item.model_copy(update={"document": original_text})
            else:
                item_for_mapping = source_item.copy(update={"document": original_text})

            allow_additional_references = _user_requested_additional_references(user_prompt)
            resolved_candidates = await _resolve_reference_candidates(
                project,
                item_for_mapping,
                prefix,
                cwd,
                user_prompt=user_prompt,
            )
            if resolved_candidates:
                mapping_hint = _format_resolved_reference_hint(
                    resolved_candidates,
                    allow_additional_references=allow_additional_references,
                ) + "\n"
            elif project.mappingPath:
                mp = Path(os.path.abspath(os.path.expanduser(project.mappingPath)))
                if mp.exists():
                    mapping_hint = f"\nCanonical cross-reference map: {project.mappingPath}\n"
                    mapping_hint += (
                        "Use the canonical map only to replace explicit original-source citations already present in the current content or excerpt.\n"
                        "Do not add new notes-side references unless the user explicitly asked for additional references.\n"
                    )

            reference_style_hint = (
                "Cross-reference style:\n"
                'Write notes-side references naturally in prose, for example: "according to **Definition 3.5.1**" '
                'or "Using the gram-schmidt theorem (**Theorem 2.5.1**)".\n'
                "Bold only the notes-side reference label itself; keep the surrounding prose outside the bold span.\n\n"
            )
            if source_item.excerpt.strip():
                excerpt_context = (
                    "Excerpt context (for source-side reference context only; do not add facts beyond the current content unless the user asks):\n"
                    f"{source_item.excerpt}\n\n"
                )

    task_prompt = (
        f"Read your formatting rules from: {rules_path}\n\n"
        f"User instruction:\n{instruction}\n\n"
        f"{reference_style_hint}"
        f"{mapping_hint}"
        f"{excerpt_context}"
        f"Current content:\n"
        f"<<<CONTENT\n{original_text}\nCONTENT>>>\n\n"
        f"Rewrite the content according to the user instruction and formatting rules.\n"
        f"Write the rewritten content to: {stage_file}\n"
        f"Important: this is a plain-text file. Write backslashes as-is (e.g. \\sigma, \\begin{{pmatrix}}). Do not double-escape.\n"
        f"Output only: done"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    return await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type=f"edit_{target}",
        log_meta={"itemIds": [item_id], "target": target},
    )
