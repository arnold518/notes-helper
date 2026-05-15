import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { api } from "../api/client";
import type { Project, ReferenceFile } from "../types/project";
import MarkdownEditor from "./MarkdownEditor";

const FILE_DISPLAY_LIMIT = 500_000;

type ReferenceMode = "raw" | "preview";

interface Props {
  project: Project;
  excerpt?: string;
  onOpenReferences?: () => void;
  onAppendToExcerpt?: (block: string) => void;
  canAppendToExcerpt?: boolean;
}

function storageKey(projectId: string) {
  return `notes-helper:project:${projectId}:reference-panel:selected`;
}

function readStoredReferenceId(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(storageKey(projectId));
  } catch {
    return null;
  }
}

function normalizeExcerptReferenceName(value: string): string {
  return value.replace(/\s+line\s+\d+(?:~\d+)?\s*$/i, "").trim();
}

function getExcerptReferenceNames(excerpt: string): string[] {
  const matches = excerpt.matchAll(/^\[([^\]]+)\]/gm);
  const names = new Set<string>();
  for (const match of matches) {
    const normalized = normalizeExcerptReferenceName(match[1] ?? "");
    if (normalized) names.add(normalized);
  }
  return [...names];
}

function getPreferredReference(
  references: ReferenceFile[],
  excerptReferenceNames: string[],
  storedId: string | null,
): string | null {
  if (storedId && references.some((ref) => ref.id === storedId)) return storedId;
  const usedRef = references.find((ref) => excerptReferenceNames.includes(ref.name));
  if (usedRef) return usedRef.id;
  const preparedRef = references.find((ref) => ref.prepared);
  return preparedRef?.id ?? references[0]?.id ?? null;
}

export default function ReferencePanel({
  project,
  excerpt = "",
  onOpenReferences,
  onAppendToExcerpt,
  canAppendToExcerpt = false,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(() =>
    getPreferredReference(project.references, getExcerptReferenceNames(excerpt), readStoredReferenceId(project.id)),
  );
  const [mode, setMode] = useState<ReferenceMode>("raw");
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedLines, setSelectedLines] = useState<{ fromLine: number; toLine: number; text: string } | null>(null);

  const excerptReferenceNames = useMemo(
    () => getExcerptReferenceNames(excerpt),
    [excerpt],
  );
  const preferredReferenceId = useMemo(
    () => getPreferredReference(project.references, excerptReferenceNames, readStoredReferenceId(project.id)),
    [project.id, project.references, excerptReferenceNames],
  );

  useEffect(() => {
    setSelectedId((current) => {
      if (current && project.references.some((ref) => ref.id === current)) return current;
      return preferredReferenceId;
    });
  }, [preferredReferenceId, project.references]);

  useEffect(() => {
    if (!selectedId || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(storageKey(project.id), selectedId);
    } catch {
      // Ignore localStorage failures and keep the selection in component state.
    }
  }, [project.id, selectedId]);

  const selectedRef = project.references.find((ref) => ref.id === selectedId) ?? null;
  const usedReferences = useMemo(
    () => project.references.filter((ref) => excerptReferenceNames.includes(ref.name)),
    [excerptReferenceNames, project.references],
  );

  useEffect(() => {
    if (!selectedRef) {
      setFileContent(null);
      setFileLoading(false);
      setFileError(null);
      setSelectedLines(null);
      return;
    }

    let cancelled = false;
    setFileLoading(true);
    setFileError(null);
    setSelectedLines(null);

    api.readFile(selectedRef.path)
      .then((text) => {
        if (cancelled) return;
        setFileContent(text);
        setFileLoading(false);
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setFileError(error.message);
        setFileLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedRef?.path]);

  useEffect(() => {
    if (mode !== "raw") {
      setSelectedLines(null);
    }
  }, [mode]);

  function formatExcerptBlock() {
    if (!selectedRef || !selectedLines) return null;
    return `[${selectedRef.name} line ${selectedLines.fromLine}~${selectedLines.toLine}]\n\n${selectedLines.text}`;
  }

  function handleAppendToExcerpt() {
    const block = formatExcerptBlock();
    if (!block || !onAppendToExcerpt) return;
    onAppendToExcerpt(block);
  }

  return (
    <div className="reference-panel">
      <div className="reference-panel-toolbar">
        <select
          className="reference-panel-select"
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
          disabled={project.references.length === 0}
        >
          {project.references.length === 0 ? (
            <option value="">No references</option>
          ) : (
            project.references.map((ref) => (
              <option key={ref.id} value={ref.id}>
                {ref.name}{ref.prepared ? " (prepared)" : ""}
              </option>
            ))
          )}
        </select>

        <div className="reference-panel-mode-toggle">
          <button
            type="button"
            className={`reference-panel-mode-btn${mode === "raw" ? " reference-panel-mode-btn-active" : ""}`}
            onClick={() => setMode("raw")}
          >
            Raw
          </button>
          <button
            type="button"
            className={`reference-panel-mode-btn${mode === "preview" ? " reference-panel-mode-btn-active" : ""}`}
            onClick={() => setMode("preview")}
          >
            Preview
          </button>
        </div>

        {onOpenReferences && (
          <button type="button" className="btn-secondary reference-panel-manage-btn" onClick={onOpenReferences}>
            Manage
          </button>
        )}
      </div>

      {usedReferences.length > 0 && (
        <div className="reference-panel-used-row">
          <span className="reference-panel-used-label">Used in excerpt</span>
          <div className="reference-panel-used-chips">
            {usedReferences.map((ref) => (
              <button
                key={ref.id}
                type="button"
                className={`reference-panel-used-chip${ref.id === selectedId ? " reference-panel-used-chip-active" : ""}`}
                onClick={() => setSelectedId(ref.id)}
              >
                {ref.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedRef && (
        <div className="reference-panel-meta">
          <span className="reference-panel-path" title={selectedRef.path}>
            {selectedRef.path}
          </span>
          {selectedRef.prepared && <span className="reference-panel-badge">prepared</span>}
        </div>
      )}

      {mode === "raw" && (
        <div className="reference-panel-selection-bar">
          <div className="reference-panel-selection-summary">
            {selectedLines
              ? `Selected lines ${selectedLines.fromLine}~${selectedLines.toLine}`
              : "Select text in the raw reference view to capture whole lines."}
          </div>
          <button
            type="button"
            className="btn-primary reference-panel-append-btn"
            onClick={handleAppendToExcerpt}
            disabled={!selectedLines || !canAppendToExcerpt}
            title={canAppendToExcerpt ? "Append selected lines to the current entry excerpt" : "Select an entry to append into its excerpt"}
          >
            Append to Excerpt
          </button>
        </div>
      )}

      <div className="reference-panel-content">
        {project.references.length === 0 && (
          <div className="reference-panel-empty">No references added yet.</div>
        )}
        {project.references.length > 0 && !selectedRef && (
          <div className="reference-panel-empty">Select a reference to view.</div>
        )}
        {selectedRef && fileLoading && (
          <div className="reference-panel-empty">Loading reference…</div>
        )}
        {selectedRef && fileError && (
          <div className="reference-panel-error">{fileError}</div>
        )}
        {selectedRef && !fileLoading && !fileError && fileContent !== null && fileContent.length > FILE_DISPLAY_LIMIT && (
          <div className="reference-panel-empty">
            File too large to display ({(fileContent.length / 1_000_000).toFixed(1)} MB).
            {onOpenReferences ? " Open the full References view to prepare or edit it." : ""}
          </div>
        )}
        {selectedRef && !fileLoading && !fileError && fileContent !== null && fileContent.length <= FILE_DISPLAY_LIMIT && (
          mode === "raw" ? (
            <div className="reference-panel-editor">
              <MarkdownEditor
                value={fileContent}
                onChange={() => {}}
                height="100%"
                editable={false}
                onLineSelectionChange={setSelectedLines}
              />
            </div>
          ) : (
            <div className="reference-panel-rendered">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                {fileContent}
              </ReactMarkdown>
            </div>
          )
        )}
      </div>
    </div>
  );
}
