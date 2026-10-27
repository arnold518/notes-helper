"""FastAPI app entry point."""
from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from models import PreviewRequest
from preview_config import (
    build_preview_mkdocs_config,
    merge_preview_asset_tree,
    resolve_preview_document_path,
)
from routers import projects as projects_router
from routers import agent as agent_router
from routers import subjects as subjects_router

app = FastAPI(title="Notes Helper API")

# Strip path prefix forwarded by absproxy (e.g. /absproxy/7999)
_ROOT_PREFIX = os.environ.get("ROOT_PREFIX", "").rstrip("/")

class StripPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope["path"]
        if _ROOT_PREFIX and path.startswith(_ROOT_PREFIX):
            request.scope["path"] = path[len(_ROOT_PREFIX):] or "/"
        return await call_next(request)

app.add_middleware(StripPrefixMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5172", "http://localhost:4172", "http://localhost:3000",
                   "https://arnold.dream.ddns-ip.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router.router)
app.include_router(agent_router.router)
app.include_router(subjects_router.router)


@app.get("/api/file")
def read_file(path: str = Query(...)) -> PlainTextResponse:
    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        raise HTTPException(status_code=404, detail="File not found")
    content = Path(expanded).read_text(errors="replace")
    return PlainTextResponse(content)


@app.put("/api/file")
async def write_file(request: Request) -> dict:
    body = await request.json()
    path = body.get("path", "")
    content = body.get("content", "")
    if not path:
        raise HTTPException(status_code=400, detail="path is required")
    expanded = os.path.expanduser(path)
    Path(expanded).write_text(content, encoding="utf-8")
    return {"ok": True}


@app.get("/api/mkdocs-config")
def mkdocs_config(root: str = Query(...)) -> list[dict]:
    from mkdocs_parser import get_admonition_types
    expanded = os.path.expanduser(root)
    if not os.path.isdir(expanded):
        raise HTTPException(status_code=400, detail="MkDocs root not found")
    return get_admonition_types(expanded)


@app.post("/api/preview")
async def preview(req: PreviewRequest) -> dict:
    """Render markdown via MkDocs and return a URL to the rendered HTML."""
    import shutil
    import subprocess
    import yaml

    preview_dir = Path(__file__).parent / "preview"
    docs_dir = preview_dir / "docs"
    site_dir = preview_dir / "site"

    # The preview tree is derived and single-use. Recreate it so assets and
    # pages from a previously selected subject cannot leak into this build.
    if docs_dir.is_symlink():
        docs_dir.unlink()
    elif docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    src_root = Path(os.path.expanduser(req.mkdocsRoot)) if req.mkdocsRoot else Path()
    orig_yml = src_root / "mkdocs.yml" if req.mkdocsRoot else None
    source_config = (
        yaml.safe_load(orig_yml.read_text(encoding="utf-8")) or {}
        if orig_yml is not None and orig_yml.is_file()
        else {}
    )
    preview_path = resolve_preview_document_path(
        source_config,
        mkdocs_root=src_root,
        output_path=Path(req.outputPath) if req.outputPath else None,
    )
    preview_md = docs_dir / preview_path
    preview_md.parent.mkdir(parents=True, exist_ok=True)
    preview_md.write_text(req.content, encoding="utf-8")

    # Write minimal mkdocs.yml if not present
    mkdocs_yml = preview_dir / "mkdocs.yml"
    if not mkdocs_yml.exists() or req.mkdocsRoot:
        _write_preview_mkdocs(preview_dir, req.mkdocsRoot, preview_path=preview_path)

    # Merge assets beside the source document after the project-wide MkDocs
    # assets have been copied.  Both trees may use the top-level `assets/`
    # namespace: the former contains chapter images while the latter contains
    # extra.css and MathJax setup required to match the original site.
    if req.outputPath:
        src_assets = Path(os.path.expanduser(req.outputPath)).parent / "assets"
        merge_preview_asset_tree(src_assets, preview_md.parent / "assets")

    mkdocs_bin = Path(__file__).parent / ".venv" / "bin" / "mkdocs"
    result = subprocess.run(
        [str(mkdocs_bin), "build", "--quiet", "--config-file", str(mkdocs_yml)],
        capture_output=True,
        text=True,
        cwd=str(preview_dir),
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr[:1000])

    html_candidates = [
        preview_path.with_suffix(".html"),
        preview_path.with_suffix("") / "index.html",
    ]
    html_path = next((path for path in html_candidates if (site_dir / path).is_file()), None)
    if html_path is None:
        raise HTTPException(status_code=500, detail="MkDocs did not produce the preview page")

    return {"url": f"/static/preview/{quote(html_path.as_posix())}"}


def _write_preview_mkdocs(
    preview_dir: Path,
    mkdocs_root: str,
    *,
    preview_path: Path = Path("preview.md"),
) -> None:
    import shutil
    import yaml

    docs_dir = preview_dir / "docs"
    site_dir = preview_dir / "site"
    docs_dir.mkdir(parents=True, exist_ok=True)

    if not mkdocs_root:
        (preview_dir / "mkdocs.yml").write_text(
            "site_name: Preview\ndocs_dir: docs\nsite_dir: site\ntheme:\n  name: material\n"
        )
        return

    src_root = Path(os.path.expanduser(mkdocs_root))
    orig_yml = src_root / "mkdocs.yml"
    if not orig_yml.exists():
        (preview_dir / "mkdocs.yml").write_text(
            "site_name: Preview\ndocs_dir: docs\nsite_dir: site\ntheme:\n  name: material\n"
        )
        return

    config = yaml.safe_load(orig_yml.read_text(encoding="utf-8")) or {}

    # Resolve real docs_dir from the original config (default: "docs")
    real_docs_dir = src_root / config.get("docs_dir", "docs")

    # Copy only the directories needed by extra_css / extra_javascript
    # (stylesheets, assets, javascripts, etc.) into our preview docs_dir
    asset_dirs: set[str] = set()
    for entry in config.get("extra_css", []) + config.get("extra_javascript", []):
        top = Path(entry).parts[0] if Path(entry).parts else None
        if top:
            asset_dirs.add(top)
    for dirname in asset_dirs:
        src = real_docs_dir / dirname
        if src.is_dir():
            dest = docs_dir / dirname
            if dest.is_symlink():
                dest.unlink()
            if dest.exists():
                shutil.rmtree(dest)
            merge_preview_asset_tree(src, dest)

    # If theme has a custom_dir, resolve it to absolute (relative to mkdocs root)
    theme = config.get("theme", {})
    if isinstance(theme, dict) and "custom_dir" in theme:
        custom_dir = src_root / theme["custom_dir"]
        if custom_dir.exists():
            config["theme"]["custom_dir"] = str(custom_dir)

    config = build_preview_mkdocs_config(
        config,
        docs_dir=docs_dir,
        site_dir=site_dir,
        preview_path=preview_path.as_posix(),
    )

    (preview_dir / "mkdocs.yml").write_text(
        yaml.dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


# Mount static preview site
_preview_site = Path(__file__).parent / "preview" / "site"
_preview_site.mkdir(parents=True, exist_ok=True)
app.mount("/static/preview", StaticFiles(directory=str(_preview_site), html=True), name="preview_static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7999, reload=True)
