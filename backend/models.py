from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


EntryKind = Literal["admonition", "section", "text"]
EntryStatus = Literal["pending", "matched", "generated", "approved"]


class Item(BaseModel):
    kind: EntryKind
    id: str
    type: str          # "h1"/"h2"/"h3" for section; "" for text; admonition type string
    content: str       # blueprint description / entry intent
    excerpt: str = ""  # matched chunks: "[file line X~Y]\n...\n---\n[file line A~B]\n..."
    syncedExcerpt: str = ""  # excerpt value at last successful map sync
    syncedNumber: int = 0    # item.number at last successful map sync
    document: str = "" # generated markdown (heading, paragraph, or admonition block)
    status: EntryStatus = "pending"
    number: int = 0
    autonumber: bool = True


class ReferenceFile(BaseModel):
    id: str
    name: str
    path: str
    originalPath: str = ""  # source path before any copy/prep; shared across projects
    prepared: bool = False


class Project(BaseModel):
    id: str
    title: str
    blueprintPath: str = ""
    references: list[ReferenceFile] = []
    markdownRulesPath: str = ""
    mkdocsRoot: str = ""
    outputPath: str = ""
    mappingPath: str = ""
    examplesDir: Optional[str] = None
    items: list[Item] = []
    numberPrefix: str = ""
    syncedNumberPrefix: str = ""  # numberPrefix at last successful map sync
    createdAt: str
    updatedAt: str


class CreateProjectRequest(BaseModel):
    title: str = ""
    blueprintPath: str = ""
    mkdocsRoot: str = ""
    outputPath: str = ""
    mappingPath: str = ""
    examplesDir: Optional[str] = None


class MatchRequest(BaseModel):
    userPrompt: str = ""
    itemId: Optional[str] = None  # None = all pending admonition items


class GenerateRequest(BaseModel):
    userPrompt: str = ""
    itemId: Optional[str] = None  # None = all matched items


class SyncMapRequest(BaseModel):
    itemId: str


class EditRequest(BaseModel):
    userPrompt: str = ""
    itemId: Optional[str] = None
    target: Literal["excerpt", "document"] = "excerpt"
    content: Optional[str] = None


class JobStatus(BaseModel):
    status: Literal["running", "done", "error"]
    result: Optional[list[dict]] = None
    error: Optional[str] = None


class PreviewRequest(BaseModel):
    content: str
    mkdocsRoot: str = ""
    outputPath: str = ""
