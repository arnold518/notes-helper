import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { api } from "../api/client";
import type { Project, Item } from "../types/project";
import NavPanel from "../components/NavPanel";
import CodingPanel from "../components/CodingPanel";
import PreviewPanel from "../components/PreviewPanel";
import ItemMetaBar from "../components/ItemMetaBar";
import ReferencesView from "../components/ReferencesView";
import type { PrepareJobState } from "../components/ReferencesView";
import AiLogsView from "../components/AiLogsView";
import RunButton from "../components/RunButton";
import FinalPreviewView from "../components/FinalPreviewView";
import RulesView from "../components/RulesView";
import MappingView from "../components/MappingView";

type PanelTab = "excerpt" | "document";
type ProjectView = "main" | "references" | "aiLogs" | "final" | "rules" | "map";

interface Props {
  projectId: string;
  onBack: () => void;
}

type SaveStatus = "saved" | "unsaved" | "saving";

export default function ProjectPage({ projectId, onBack }: Props) {
  const [project, setProject] = useState<Project | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Per-item job IDs (itemId → jobId)
  const [matchItemJobs, setMatchItemJobs] = useState<Record<string, string>>({});
  const [generateItemJobs, setGenerateItemJobs] = useState<Record<string, string>>({});
  const [editExcerptJobId, setEditExcerptJobId] = useState<string | null>(null);
  const [editDocumentJobId, setEditDocumentJobId] = useState<string | null>(null);
  const [matchPrompt, setMatchPrompt] = useState("");
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [docAutoPreviewKey, setDocAutoPreviewKey] = useState(0);
  const [finalPreviewKey, setFinalPreviewKey] = useState(0);
  const [panelTab, setPanelTab] = useState<PanelTab>("excerpt");
  const [view, setView] = useState<ProjectView>("main");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [prepareJobs, setPrepareJobs] = useState<Record<string, PrepareJobState>>({});
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<"idle" | "saved" | "error">("idle");
  const [exportMessage, setExportMessage] = useState("");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingSaveRef = useRef<Project | null>(null);
  const pendingDocPreviewRef = useRef(false);
  const refsFlushRef = useRef<(() => void) | null>(null);
  const metaFlushRef = useRef<(() => void) | null>(null);
  const projectRef = useRef<Project | null>(null);
  projectRef.current = project;

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      setProject(p);
      if (p.items.length > 0) setSelectedId(p.items[0].id);
      setLoading(false);
    }).catch((e) => {
      setError(e.message);
      setLoading(false);
    });
  }, [projectId]);

  useEffect(() => {
    setPrepareJobs({});
  }, [projectId]);

  useEffect(() => {
    if (!project) return;
    const refIds = new Set(project.references.map((r) => r.id));
    setPrepareJobs((jobs) => {
      let changed = false;
      const next: Record<string, PrepareJobState> = {};
      for (const [refId, state] of Object.entries(jobs)) {
        if (refIds.has(refId)) {
          next[refId] = state;
        } else {
          changed = true;
        }
      }
      return changed ? next : jobs;
    });
  }, [project]);

  const matchRunning = Object.keys(matchItemJobs).length > 0;
  const generateRunning = Object.keys(generateItemJobs).length > 0;

  const matchItemJobsRef = useRef(matchItemJobs);
  matchItemJobsRef.current = matchItemJobs;
  const generateItemJobsRef = useRef(generateItemJobs);
  generateItemJobsRef.current = generateItemJobs;

  // Poll all active match jobs — steady interval, reads current jobs via ref
  useEffect(() => {
    const interval = setInterval(async () => {
      const entries = Object.entries(matchItemJobsRef.current);
      for (const [itemId, jobId] of entries) {
        try {
          const job = await api.pollJob(jobId);
          if (job.status === "done" || job.status === "error") {
            setMatchItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
            if (job.status === "done") {
              api.getProject(projectId).then(setProject).catch(console.error);
            }
          }
        } catch {
          setMatchItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
        }
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Poll all active generate jobs — steady interval, reads current jobs via ref
  useEffect(() => {
    const interval = setInterval(async () => {
      const entries = Object.entries(generateItemJobsRef.current);
      for (const [itemId, jobId] of entries) {
        try {
          const job = await api.pollJob(jobId);
          if (job.status === "done" || job.status === "error") {
            setGenerateItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
            if (job.status === "done") {
              api.getProject(projectId).then((p) => { setProject(p); setDocAutoPreviewKey((k) => k + 1); }).catch(console.error);
            }
          }
        } catch {
          setGenerateItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
        }
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  function dispatchMatch(itemId: string, prompt: string) {
    if (matchItemJobs[itemId]) return;
    api.startMatch(projectRef.current!.id, { itemId, userPrompt: prompt || undefined })
      .then(({ job_id }) => setMatchItemJobs((j) => ({ ...j, [itemId]: job_id })))
      .catch(console.error);
  }

  function dispatchGenerate(itemId: string, prompt: string) {
    if (generateItemJobs[itemId]) return;
    api.startGenerate(projectRef.current!.id, { itemId, userPrompt: prompt || undefined })
      .then(({ job_id }) => setGenerateItemJobs((j) => ({ ...j, [itemId]: job_id })))
      .catch(console.error);
  }

  function handleMatchItemJobFinish(itemId: string) {
    setMatchItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
  }

  function handleGenerateItemJobFinish(itemId: string) {
    setGenerateItemJobs((j) => { const n = { ...j }; delete n[itemId]; return n; });
    setDocAutoPreviewKey((k) => k + 1);
  }

  const scheduleSave = useCallback((updated: Project, changedField?: "excerpt" | "document") => {
    if (changedField === "document") pendingDocPreviewRef.current = true;
    setSaveStatus("unsaved");
    pendingSaveRef.current = updated;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setSaveStatus("saving");
      api.saveProject(updated)
        .then(() => {
          setSaveStatus("saved");
          pendingSaveRef.current = null;
          if (pendingDocPreviewRef.current) {
            setDocAutoPreviewKey((k) => k + 1);
            pendingDocPreviewRef.current = false;
          }
        })
        .catch(console.error);
    }, 800);
  }, []);

  const flushProjectSave = useCallback(() => {
    const pending = pendingSaveRef.current;
    if (!pending) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveStatus("saving");
    api.saveProject(pending)
      .then(() => {
        setSaveStatus("saved");
        pendingSaveRef.current = null;
        if (pendingDocPreviewRef.current) {
          setDocAutoPreviewKey((k) => k + 1);
          pendingDocPreviewRef.current = false;
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        flushProjectSave();
        refsFlushRef.current?.();
        metaFlushRef.current?.();
      }
    }
    window.addEventListener("keydown", onKeyDown, { capture: true });
    return () => window.removeEventListener("keydown", onKeyDown, { capture: true });
  }, [flushProjectSave]);

  useEffect(() => {
    if (panelTab === "document") {
      setDocAutoPreviewKey((k) => k + 1);
    }
  }, [panelTab]);

  async function patchSelectedItem(patch: Partial<Item>) {
    if (!project || !selectedId) return;
    setSaveStatus("saving");
    try {
      const updated = await api.patchItem(project.id, selectedId, patch);
      setProject(updated);
      setSaveStatus("saved");
    } catch (e: any) {
      console.error(e);
      setSaveStatus("unsaved");
    }
  }

  function updateItem(field: "excerpt" | "document", value: string) {
    if (!project || !selectedId) return;
    const items = project.items.map((it) =>
      it.id === selectedId ? { ...it, [field]: value } : it
    );
    const updated = { ...project, items };
    setProject(updated);
    scheduleSave(updated, field);
  }

  async function handleInsertAfter(afterId: string) {
    if (!project) return;
    try {
      const updated = await api.insertItem(project.id, {
        kind: "admonition",
        type: "def",
        content: "New entry",
        afterId,
      });
      setProject(updated);
      // Select the newly inserted item
      const afterIdx = updated.items.findIndex((it) => it.id === afterId);
      if (afterIdx !== -1 && updated.items[afterIdx + 1]) {
        setSelectedId(updated.items[afterIdx + 1].id);
      }
    } catch (e: any) {
      console.error(e);
    }
  }

  async function handleDeleteItem(itemId: string) {
    if (!project) return;
    try {
      const updated = await api.deleteItem(project.id, itemId);
      setProject(updated);
      if (selectedId === itemId) {
        setSelectedId(updated.items[0]?.id ?? null);
      }
    } catch (e: any) {
      console.error(e);
    }
  }

  const unsyncedCount = useMemo(() => {
    if (!project?.mappingPath) return 0;
    return project.items.filter((it) =>
      it.excerpt && (
        it.excerpt !== it.syncedExcerpt ||
        it.number !== it.syncedNumber ||
        project.numberPrefix !== project.syncedNumberPrefix
      )
    ).length;
  }, [project]);

  const numberPrefix = useMemo(() => {
    if (!project) return "";
    const h1 = project.items.find((it) => it.kind === "section" && it.type === "h1");
    const m = h1?.content.match(/(?:§\s*)?(\d+(?:\.\d+)*)/);
    return m ? m[1] : "";
  }, [project?.items]);

  const finalMarkdown = useMemo(() => {
    if (!project) return "";
    const lines: string[] = [];
    for (const item of project.items) {
      if (item.document.trim()) {
        lines.push(item.document.trim());
        lines.push("");
      } else if (item.kind === "section") {
        const level = parseInt(item.type.slice(1)) || 1;
        lines.push(`${"#".repeat(level)} ${item.content}`);
        lines.push("");
      }
    }
    return lines.join("\n");
  }, [project]);

  useEffect(() => {
    if (view === "final") {
      setFinalPreviewKey((k) => k + 1);
    }
  }, [view, finalMarkdown]);

  useEffect(() => {
    setExportStatus("idle");
    setExportMessage("");
  }, [project?.outputPath, view]);

  const handleExportFinal = useCallback(async () => {
    if (!project) return;
    const outputPath = (project.outputPath || "").trim();
    if (!outputPath) {
      setExportStatus("error");
      setExportMessage("No output file path configured");
      return;
    }
    setExporting(true);
    setExportStatus("idle");
    setExportMessage("");
    try {
      await api.writeFile(outputPath, finalMarkdown);
      setExportStatus("saved");
      setExportMessage(`Exported to ${outputPath}`);
    } catch (e: any) {
      setExportStatus("error");
      setExportMessage(e?.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }, [project, finalMarkdown]);

  if (loading) return <div className="loading">Loading…</div>;
  if (error) return <div className="error-msg">{error}</div>;
  if (!project) return null;

  const selectedItem = project.items.find((it) => it.id === selectedId) ?? null;
  return (
    <div className="project-page">
      <div className="project-toolbar">
        <button onClick={onBack} className="btn-back">← Back</button>
        <h2 className="project-title-bar">{project.title}</h2>
        <div className={`save-status save-status-${saveStatus}`}>
          {saveStatus === "saving" ? "Saving…" : saveStatus === "unsaved" ? "Unsaved" : "Saved"}
        </div>
        <div className="toolbar-actions">
          <button
            className="btn-primary"
            disabled={matchRunning}
            onClick={() => (projectRef.current?.items ?? []).forEach((it) => dispatchMatch(it.id, matchPrompt))}
          >
            {matchRunning ? "Matching…" : "Match All ▶"}
          </button>
          <button
            className="btn-primary"
            disabled={generateRunning}
            onClick={() => (projectRef.current?.items ?? []).forEach((it) => dispatchGenerate(it.id, generatePrompt))}
          >
            {generateRunning ? "Generating…" : "Generate All ▶"}
          </button>
          {project.mappingPath && unsyncedCount > 0 && (
            <RunButton
              projectId={project.id}
              action="sync-map-all"
              label={`Sync Map (${unsyncedCount}) ⟳`}
              onDone={setProject}
            />
          )}
          <button
            className={view === "references" ? "btn-primary" : "btn-secondary"}
            onClick={() => setView((v) => v === "references" ? "main" : "references")}
          >
            References{project.references.length > 0 && ` (${project.references.length})`}
          </button>
          {project.mappingPath && (
            <button
              className={view === "map" ? "btn-primary" : "btn-secondary"}
              onClick={() => setView((v) => v === "map" ? "main" : "map")}
            >
              Map
            </button>
          )}
          <button
            className={view === "aiLogs" ? "btn-primary" : "btn-secondary"}
            onClick={() => setView((v) => v === "aiLogs" ? "main" : "aiLogs")}
          >
            AI Logs
          </button>
          <button
            className={view === "rules" ? "btn-primary" : "btn-secondary"}
            onClick={() => setView((v) => v === "rules" ? "main" : "rules")}
          >
            Rules
          </button>
          <button
            className={view === "final" ? "btn-primary" : "btn-secondary"}
            onClick={() => setView((v) => v === "final" ? "main" : "final")}
          >
            Final View
          </button>
        </div>
      </div>

      <div className="project-body">
        {view === "references" ? (
          <ReferencesView
            project={project}
            onProjectUpdate={setProject}
            onSaveStatusChange={setSaveStatus}
            flushRef={refsFlushRef}
            prepareJobs={prepareJobs}
            onPrepareJobsChange={setPrepareJobs}
          />
        ) : view === "aiLogs" ? (
          <AiLogsView projectId={project.id} />
        ) : view === "rules" ? (
          <RulesView projectId={project.id} />
        ) : view === "map" ? (
          <MappingView mappingPath={project.mappingPath} projectId={project.id} />
        ) : view === "final" ? (
          <FinalPreviewView
            content={finalMarkdown}
            mkdocsRoot={project.mkdocsRoot}
            outputPath={project.outputPath}
            autoPreviewKey={finalPreviewKey}
            onExport={handleExportFinal}
            exporting={exporting}
            exportStatus={exportStatus}
            exportMessage={exportMessage}
          />
        ) : (
          <>
            <div className="project-nav">
              <NavPanel
                items={project.items}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onInsertAfter={handleInsertAfter}
                onDelete={handleDeleteItem}
                numberPrefix={numberPrefix}
                syncedNumberPrefix={project.syncedNumberPrefix}
                mappingPath={project.mappingPath}
              />
            </div>
            <div className="right-column">
              <ItemMetaBar
                item={selectedItem}
                project={project}
                numberPrefix={numberPrefix}
                onUpdate={patchSelectedItem}
                onSaveStatusChange={setSaveStatus}
                flushRef={metaFlushRef}
              />
              <div className="main-split">
                <CodingPanel
                  item={selectedItem}
                  project={project}
                  activeTab={panelTab}
                  onTabChange={setPanelTab}
                  matchItemJobId={selectedItem ? (matchItemJobs[selectedItem.id] ?? null) : null}
                  editExcerptJobId={editExcerptJobId}
                  generateItemJobId={selectedItem ? (generateItemJobs[selectedItem.id] ?? null) : null}
                  editDocumentJobId={editDocumentJobId}
                  matchPrompt={matchPrompt}
                  generatePrompt={generatePrompt}
                  onMatchPromptChange={setMatchPrompt}
                  onGeneratePromptChange={setGeneratePrompt}
                  onRunMatch={() => selectedItem && dispatchMatch(selectedItem.id, matchPrompt)}
                  onEditExcerptJobStart={setEditExcerptJobId}
                  onRunGenerate={() => selectedItem && dispatchGenerate(selectedItem.id, generatePrompt)}
                  onEditDocumentJobStart={setEditDocumentJobId}
                  onMatchItemJobFinish={handleMatchItemJobFinish}
                  onEditExcerptJobFinish={() => setEditExcerptJobId(null)}
                  onGenerateItemJobFinish={handleGenerateItemJobFinish}
                  onEditDocumentJobFinish={() => { setEditDocumentJobId(null); setDocAutoPreviewKey((k) => k + 1); }}
                  onItemChange={updateItem}
                  onProjectUpdate={setProject}
                />
                <PreviewPanel
                  item={selectedItem}
                  project={project}
                  activeTab={panelTab}
                  onTabChange={setPanelTab}
                  autoPreviewKey={docAutoPreviewKey}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
