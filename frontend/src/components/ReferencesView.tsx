import { useState, useEffect, useRef, useCallback } from "react";
import type React from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { api } from "../api/client";
import type { Project, ReferenceFile } from "../types/project";
import MarkdownEditor from "./MarkdownEditor";

const FILE_DISPLAY_LIMIT = 500_000; // chars (~500KB)

type SaveStatus = "saved" | "unsaved" | "saving";
type PrepareJobStatus = "running" | "done" | "error";

export interface PrepareJobState {
  status: PrepareJobStatus;
  jobId?: string;
}

interface Props {
  project: Project;
  onProjectUpdate: (p: Project) => void;
  onSaveStatusChange?: (s: SaveStatus) => void;
  flushRef?: React.MutableRefObject<(() => void) | null>;
  prepareJobs: Record<string, PrepareJobState>;
  onPrepareJobsChange: React.Dispatch<React.SetStateAction<Record<string, PrepareJobState>>>;
}

export default function ReferencesView({
  project,
  onProjectUpdate,
  onSaveStatusChange,
  flushRef,
  prepareJobs,
  onPrepareJobsChange,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(
    project.references[0]?.id ?? null
  );
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const [newName, setNewName] = useState("");
  const [newPath, setNewPath] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollersRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const selectedRef = project.references.find((r) => r.id === selectedId) ?? null;

  // Load file content whenever selection changes
  useEffect(() => {
    if (!selectedRef) { setFileContent(null); return; }
    const path = selectedRef.path;
    setFileLoading(true);
    setFileError(null);
    api.readFile(path)
      .then((text) => { setFileContent(text); setFileLoading(false); })
      .catch((e) => { setFileError(e.message); setFileLoading(false); });
  }, [selectedId, selectedRef?.path]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      const updated = await api.addReference(project.id, newName.trim(), newPath.trim() || undefined);
      onProjectUpdate(updated);
      setNewName("");
      setNewPath("");
      const added = updated.references[updated.references.length - 1];
      if (added) setSelectedId(added.id);
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(refId: string) {
    try {
      const updated = await api.removeReference(project.id, refId);
      onProjectUpdate(updated);
      onPrepareJobsChange((jobs) => {
        if (!(refId in jobs)) return jobs;
        const next = { ...jobs };
        delete next[refId];
        return next;
      });
      if (selectedId === refId) {
        setSelectedId(updated.references[0]?.id ?? null);
      }
    } catch (e: any) {
      console.error(e);
    }
  }

  function getActivePath() {
    if (!selectedRef) return null;
    return selectedRef.path;
  }

  function flushFileSave() {
    if (!saveTimer.current) return;
    clearTimeout(saveTimer.current);
    saveTimer.current = null;
    const path = getActivePath();
    if (path && fileContent !== null) {
      onSaveStatusChange?.("saving");
      api.writeFile(path, fileContent)
        .then(() => onSaveStatusChange?.("saved"))
        .catch(console.error);
    }
  }

  useEffect(() => {
    if (flushRef) flushRef.current = flushFileSave;
    return () => { if (flushRef) flushRef.current = null; };
  });

  function handleEditorChange(value: string) {
    setFileContent(value);
    onSaveStatusChange?.("unsaved");
    const path = getActivePath();
    if (!path) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      onSaveStatusChange?.("saving");
      api.writeFile(path, value)
        .then(() => onSaveStatusChange?.("saved"))
        .catch(console.error);
    }, 800);
  }


  async function handlePrepare(ref: ReferenceFile) {
    onPrepareJobsChange((jobs) => ({ ...jobs, [ref.id]: { status: "running" } }));
    try {
      const { job_id } = await api.prepareReference(project.id, ref.id);
      onPrepareJobsChange((jobs) => ({ ...jobs, [ref.id]: { status: "running", jobId: job_id } }));
    } catch {
      onPrepareJobsChange((jobs) => ({ ...jobs, [ref.id]: { status: "error" } }));
    }
  }

  const stopPolling = useCallback((refId: string) => {
    const timer = pollersRef.current[refId];
    if (timer) {
      clearInterval(timer);
      delete pollersRef.current[refId];
    }
  }, []);

  const pollPrepareJob = useCallback(async (refId: string, jobId: string) => {
    try {
      const job = await api.pollJob(jobId);
      if (job.status === "done") {
        stopPolling(refId);
        onPrepareJobsChange((jobs) => ({ ...jobs, [refId]: { status: "done", jobId } }));
        const updated = await api.getProject(project.id);
        onProjectUpdate(updated);
      } else if (job.status === "error") {
        stopPolling(refId);
        onPrepareJobsChange((jobs) => ({ ...jobs, [refId]: { status: "error", jobId } }));
      }
    } catch {
      stopPolling(refId);
      onPrepareJobsChange((jobs) => ({ ...jobs, [refId]: { status: "error", jobId } }));
    }
  }, [onPrepareJobsChange, onProjectUpdate, project.id, stopPolling]);

  const startPolling = useCallback((refId: string, jobId: string) => {
    if (!jobId || pollersRef.current[refId]) return;
    void pollPrepareJob(refId, jobId);
    pollersRef.current[refId] = setInterval(() => {
      void pollPrepareJob(refId, jobId);
    }, 3000);
  }, [pollPrepareJob]);

  useEffect(() => {
    for (const [refId, state] of Object.entries(prepareJobs)) {
      if (state.status === "running" && state.jobId) {
        startPolling(refId, state.jobId);
      } else {
        stopPolling(refId);
      }
    }
  }, [prepareJobs, startPolling, stopPolling]);

  useEffect(() => () => {
    for (const timer of Object.values(pollersRef.current)) {
      clearInterval(timer);
    }
    pollersRef.current = {};
  }, []);

  return (
    <div className="refs-view">
      {/* Left: reference list */}
      <div className="refs-view-nav">
        <div className="refs-view-nav-header">References</div>
        <div className="refs-view-list">
          {project.references.length === 0 && (
            <div className="refs-view-empty">No references added yet.</div>
          )}
          {project.references.map((ref) => (
            <div
              key={ref.id}
              className={`refs-view-item${selectedId === ref.id ? " refs-view-item-active" : ""}`}
              onClick={() => setSelectedId(ref.id)}
            >
              <div className="refs-view-item-name" title={ref.path}>{ref.name}</div>
              <div className="refs-view-item-actions">
                {ref.prepared && <span className="ref-badge-prepared">prep</span>}
                <button
                  className="btn-secondary ref-btn"
                  onClick={(e) => { e.stopPropagation(); handlePrepare(ref); }}
                  disabled={prepareJobs[ref.id]?.status === "running"}
                  title="Prepare (fix OCR/typos)"
                >
                  {prepareJobs[ref.id]?.status === "running" ? "…" : "Prep"}
                </button>
                <button
                  className="btn-danger ref-btn"
                  onClick={(e) => { e.stopPropagation(); handleRemove(ref.id); }}
                  title="Remove"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
        <form onSubmit={handleAdd} className="refs-view-add-form refs-view-add-form-unified">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="filename.md"
            className="refs-view-add-input"
          />
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="/path/to/source (optional)"
            className="refs-view-add-input refs-view-add-path"
          />
          <button type="submit" className="btn-primary ref-btn" disabled={adding || !newName.trim()}>
            {adding ? "…" : "+"}
          </button>
        </form>
        {addError && <div className="ref-add-error">{addError}</div>}
      </div>

      {/* Center: raw text */}
      <div className="refs-view-raw">
        <div className="refs-view-panel-header">Raw</div>
        <div className="refs-view-editor-content">
          {fileLoading && <div className="refs-view-loading">Loading…</div>}
          {fileError && <div className="refs-view-error" style={{ padding: 12 }}>{fileError}</div>}
          {!fileLoading && !fileError && fileContent !== null && fileContent.length > FILE_DISPLAY_LIMIT && (
            <div className="refs-view-too-large">
              File too large to display ({(fileContent.length / 1_000_000).toFixed(1)} MB).
              Press <strong>Prep</strong> to extract and prepare the relevant section first.
            </div>
          )}
          {!fileLoading && !fileError && fileContent !== null && fileContent.length <= FILE_DISPLAY_LIMIT && (
            <MarkdownEditor
              value={fileContent}
              onChange={handleEditorChange}
              height="100%"
              projectId={project.id}
            />
          )}
          {!selectedRef && <div className="no-selection">Select a reference to view</div>}
        </div>
      </div>

      {/* Right: rendered preview */}
      <div className="refs-view-preview">
        <div className="refs-view-panel-header">Preview</div>
        <div className="refs-view-panel-content">
          {!selectedRef && <div className="no-selection">Select a reference to preview</div>}
          {selectedRef && fileContent !== null && !fileLoading && fileContent.length > FILE_DISPLAY_LIMIT && (
            <div className="refs-view-too-large">
              File too large to preview. Press <strong>Prep</strong> to extract the relevant section first.
            </div>
          )}
          {selectedRef && fileContent !== null && !fileLoading && fileContent.length <= FILE_DISPLAY_LIMIT && (
            <div className="refs-view-rendered">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                {fileContent}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
