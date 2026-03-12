"""Async subprocess wrapper for running AI agent CLIs (Claude, Codex)."""
from __future__ import annotations
import asyncio
import difflib
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_logs import create_ai_log, update_ai_log
from backend_config import load_backend_config
from models import Project


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
            error_text = f"Agent '{provider}' exited {returncode}: {stderr_text[:500]}"
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


def _rules_path(project_id: str, kind: str) -> Path:
    from routers.projects import PROJECTS_DIR
    return PROJECTS_DIR / project_id / f"{kind}_rules.md"


def _stage_dir(project_id: str, item_id: str = "") -> Path:
    from routers.projects import PROJECTS_DIR
    if item_id:
        return PROJECTS_DIR / project_id / "stage" / item_id
    return PROJECTS_DIR / project_id / "stage"



def _numeric_stem(path: Path) -> int | None:
    stem = path.stem.strip()
    if re.fullmatch(r"\d+", stem):
        try:
            return int(stem)
        except Exception:
            return None
    return None


def _path_distance(a: Path, b: Path) -> int:
    try:
        common = Path(os.path.commonpath([str(a), str(b)]))
        return len(a.relative_to(common).parts) + len(b.relative_to(common).parts)
    except Exception:
        return 10_000


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
    target_num = _numeric_stem(target_file) if target_file else None
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
            if path.suffix.lower() != ".md":
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
            cnum = _numeric_stem(path)
            num_dist = abs(cnum - target_num) if (cnum is not None and target_num is not None) else 10_000
            name_penalty = 50 if path.stem.lower() in {"index", "readme"} else 0
            same_dir_candidates.append(((num_dist, name_penalty, path.name.lower()), path))
    same_dir_candidates.sort(key=lambda x: x[0])
    for _, path in same_dir_candidates:
        consider(path)
        if len(selected) >= max_files:
            return selected[:max_files]

    # Second pass: nearby files under docs/root, ranked by directory distance.
    scored: list[tuple[tuple, Path]] = []
    if anchor.exists() and anchor.is_dir():
        for path in anchor.rglob("*.md"):
            try:
                if target_file_resolved is not None and path.resolve(strict=False) == target_file_resolved:
                    continue
                dir_dist = _path_distance(path.parent, target_dir)
                far_penalty = 1 if dir_dist > max(2, search_depth * 2) else 0
                cnum = _numeric_stem(path)
                num_dist = abs(cnum - target_num) if (cnum is not None and target_num is not None) else 10_000
                name_penalty = 50 if path.stem.lower() in {"index", "readme"} else 0
                depth_delta = abs(len(path.parent.parts) - len(target_dir.parts))
                score = (far_penalty, dir_dist, num_dist, depth_delta, name_penalty, str(path))
                scored.append((score, path))
            except Exception:
                continue
    scored.sort(key=lambda x: x[0])
    for _, path in scored:
        consider(path)
        if len(selected) >= max_files:
            break

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
        if line_ratio < 0.80 or line_ratio > 1.60:
            raise ValueError(
                f"Prepared output non-empty line-count drift too large "
                f"(ratio={line_ratio:.3f}, expected 0.80~1.60)"
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
    """AI agent: reads excerpts → identifies original refs → updates mappingPath."""
    if not project.mappingPath:
        return

    prefix = ""
    for it in project.items:
        if it.kind == "section" and it.type == "h1":
            m = re.search(r'(?:§\s*)?(\d+(?:\.\d+)*)', it.content)
            if m:
                prefix = m.group(1)
            break

    location = Path(os.path.abspath(os.path.expanduser(project.outputPath))).name if project.outputPath else ""

    # Build mapping: current ref name (as it appears in excerpt headers) → original path
    ref_name_to_original: dict[str, str] = {}
    for ref in project.references:
        original = (ref.originalPath or ref.path or "").strip()
        if ref.name and original:
            ref_name_to_original[ref.name] = original

    items_by_id = {it.id: it for it in project.items}
    item_blocks: list[str] = []
    for iid in item_ids:
        item = items_by_id.get(iid)
        if item is None or not item.excerpt:
            continue
        new_ref = _item_new_ref(item, prefix)
        if not new_ref:
            continue
        item_blocks.append(
            f'  New ref: "{new_ref}"\n'
            f"  Excerpt:\n{item.excerpt}\n"
        )

    if not item_blocks:
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
        f"Mapping file: {project.mappingPath}\n"
        f"Notes output file (Location): {location}\n\n"
        f"Reference name mapping (excerpt header name → original file path):\n{ref_hint}\n\n"
        f"Items:\n{items_str}\n\n"
        f"Output only: done"
    )
    provider, model, reasoning_effort = _runtime_agent_settings()
    await run_agent(
        task_prompt,
        cwd,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        project_id=project.id,
        run_type="map_update",
        log_meta={"itemIds": item_ids, "mappingPath": project.mappingPath},
    )


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
            block += f"Current excerpt:\n{item.excerpt}\n"
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
    for iid in item_ids:
        item = items_by_id.get(iid)
        if item is None:
            continue
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
            mapping_hint = (
                f"\nCross-reference map: {project.mappingPath}\n"
                f"Any citation in an excerpt to an original item (e.g. \"Theorem 1.3\", \"Replacement Theorem\") "
                f"must be looked up in the 'Original ref' column; use the corresponding 'New ref' as the notes reference.\n"
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
    task_prompt = (
        f"Read your writing rules from: {generate_rules_path}\n"
        f"Style reference files (tone/structure only — do not copy facts):\n{style_paths_str}\n\n"
        f"Target output file: {output_path or '(not provided)'}\n"
        f"Available admonition types: {types_hint}\n"
        f"{prefix_hint}\n"
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
    task_prompt = (
        f"Read your formatting rules from: {rules_path}\n\n"
        f"User instruction:\n{instruction}\n\n"
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


