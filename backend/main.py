"""FastAPI app entry point."""
from __future__ import annotations
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from models import PreviewRequest
from routers import projects as projects_router
from routers import agent as agent_router

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
    import subprocess
    import tempfile
    import shutil

    preview_dir = Path(__file__).parent / "preview"
    docs_dir = preview_dir / "docs"
    site_dir = preview_dir / "site"
    docs_dir.mkdir(parents=True, exist_ok=True)

    preview_md = docs_dir / "preview.md"
    preview_md.write_text(req.content, encoding="utf-8")

    # Symlink image assets from the document's directory into preview/docs/
    # Done before _write_preview_mkdocs so that function skips any dir we've already linked.
    if req.outputPath:
        src_assets = Path(os.path.expanduser(req.outputPath)).parent / "assets"
        dst_assets = docs_dir / "assets"
        if src_assets.is_dir() and not dst_assets.is_symlink():
            if dst_assets.exists():
                shutil.rmtree(dst_assets)
            dst_assets.symlink_to(os.path.relpath(src_assets, docs_dir))

    # Write minimal mkdocs.yml if not present
    mkdocs_yml = preview_dir / "mkdocs.yml"
    if not mkdocs_yml.exists() or req.mkdocsRoot:
        _write_preview_mkdocs(preview_dir, req.mkdocsRoot)

    mkdocs_bin = Path(__file__).parent / ".venv" / "bin" / "mkdocs"
    result = subprocess.run(
        [str(mkdocs_bin), "build", "--dirty", "--quiet", "--config-file", str(mkdocs_yml)],
        capture_output=True,
        text=True,
        cwd=str(preview_dir),
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr[:1000])

    return {"url": "/static/preview/preview/index.html"}


def _write_preview_mkdocs(preview_dir: Path, mkdocs_root: str) -> None:
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

    config = yaml.safe_load(orig_yml.read_text())

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
                continue  # already managed as a symlink (e.g. chapter image assets)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(str(src), str(dest))

    # If theme has a custom_dir, resolve it to absolute (relative to mkdocs root)
    theme = config.get("theme", {})
    if isinstance(theme, dict) and "custom_dir" in theme:
        custom_dir = src_root / theme["custom_dir"]
        if custom_dir.exists():
            config["theme"]["custom_dir"] = str(custom_dir)

    # Override docs_dir and site_dir to our preview paths (use absolute)
    config["docs_dir"] = str(docs_dir)
    config["site_dir"] = str(site_dir)

    (preview_dir / "mkdocs.yml").write_text(yaml.dump(config, allow_unicode=True, sort_keys=False))


# Mount static preview site
_preview_site = Path(__file__).parent / "preview" / "site"
_preview_site.mkdir(parents=True, exist_ok=True)
app.mount("/static/preview", StaticFiles(directory=str(_preview_site), html=True), name="preview_static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7999, reload=True)
