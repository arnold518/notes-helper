import { useEffect, useState } from "react";
import type React from "react";
import { api } from "../api/client";
import type { ProjectSummary, ReferenceFile, Subject } from "../types/project";
import MarkdownEditor from "../components/MarkdownEditor";
import MappingView from "../components/MappingView";

interface Props {
  subjectId: string;
  onBack: () => void;
  onOpenProject: (id: string) => void;
}

type SaveStatus = "saved" | "unsaved" | "saving";
type RuleKind = "match" | "generate" | "map";
type SubjectPane = "settings" | "rules" | "mapping";

function newReferenceId(): string {
  return Math.random().toString(16).slice(2, 10);
}

function projectTitleSeed(subject: Subject): string {
  const prefix = subject.titlePrefix.trim();
  return `${prefix ? `[${prefix}] ` : ""}§ `;
}

export default function SubjectPage({ subjectId, onBack, onOpenProject }: Props) {
  const [subject, setSubject] = useState<Subject | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectBlueprintPath, setProjectBlueprintPath] = useState("");
  const [projectOutputPath, setProjectOutputPath] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newRefName, setNewRefName] = useState("");
  const [newRefPath, setNewRefPath] = useState("");
  const [activePane, setActivePane] = useState<SubjectPane>("settings");
  const [activeRuleKind, setActiveRuleKind] = useState<RuleKind>("match");
  const [ruleContent, setRuleContent] = useState<string | null>(null);
  const [ruleSaveStatus, setRuleSaveStatus] = useState<SaveStatus>("saved");
  const [ruleError, setRuleError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setProjectTitle("");
    setProjectBlueprintPath("");
    setProjectOutputPath("");
    Promise.all([
      api.getSubject(subjectId),
      api.listSubjectProjects(subjectId),
    ]).then(([loadedSubject, loadedProjects]) => {
      setSubject(loadedSubject);
      setProjects(loadedProjects);
      setProjectTitle(projectTitleSeed(loadedSubject));
      setSaveStatus("saved");
      setLoading(false);
    }).catch((e: Error) => {
      setError(e.message);
      setLoading(false);
    });
  }, [subjectId]);

  useEffect(() => {
    let cancelled = false;
    setRuleContent(null);
    setRuleError(null);
    setRuleSaveStatus("saved");
    api.getSubjectRules(subjectId, activeRuleKind)
      .then((res) => {
        if (cancelled) return;
        setRuleContent(res.content);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setRuleError(e.message);
      });
    return () => { cancelled = true; };
  }, [subjectId, activeRuleKind]);

  function updateSubject(patch: Partial<Subject>) {
    if (!subject) return;
    setSubject({ ...subject, ...patch });
    setSaveStatus("unsaved");
  }

  function updateReference(index: number, patch: Partial<ReferenceFile>) {
    if (!subject) return;
    const references = subject.references.map((ref, i) =>
      i === index ? { ...ref, ...patch } : ref
    );
    updateSubject({ references });
  }

  function removeReference(index: number) {
    if (!subject) return;
    updateSubject({ references: subject.references.filter((_, i) => i !== index) });
  }

  function addReference(e: React.FormEvent) {
    e.preventDefault();
    if (!subject || !newRefName.trim()) return;
    const path = newRefPath.trim();
    updateSubject({
      references: [
        ...subject.references,
        {
          id: newReferenceId(),
          name: newRefName.trim(),
          path,
          originalPath: path,
          prepared: false,
        },
      ],
    });
    setNewRefName("");
    setNewRefPath("");
  }

  async function saveSubject() {
    if (!subject) return;
    setSaveStatus("saving");
    try {
      const saved = await api.saveSubject(subject);
      setSubject(saved);
      setSaveStatus("saved");
    } catch (e: any) {
      setError(e.message);
      setSaveStatus("unsaved");
    }
  }

  async function createProject(e: React.FormEvent) {
    e.preventDefault();
    if (!subject) return;
    const title = projectTitle.trim();
    const unchangedSeed = title === projectTitleSeed(subject).trim();
    setCreatingProject(true);
    setCreateError(null);
    try {
      const project = await api.createSubjectProject(subject.id, {
        title: title && !unchangedSeed ? title : undefined,
        blueprintPath: projectBlueprintPath || undefined,
        outputPath: projectOutputPath || undefined,
      });
      onOpenProject(project.id);
    } catch (e: any) {
      setCreateError(e.message);
    } finally {
      setCreatingProject(false);
    }
  }

  async function saveRules() {
    if (!subject || ruleContent === null) return;
    setRuleSaveStatus("saving");
    setRuleError(null);
    try {
      const saved = await api.putSubjectRules(subject.id, activeRuleKind, ruleContent);
      setRuleContent(saved.content);
      setRuleSaveStatus("saved");
    } catch (e: any) {
      setRuleError(e.message);
      setRuleSaveStatus("unsaved");
    }
  }

  if (loading) return <div className="loading">Loading…</div>;
  if (error && !subject) return <div className="error-msg">{error}</div>;
  if (!subject) return null;

  return (
    <div className="subject-page">
      <div className="project-toolbar">
        <button onClick={onBack} className="btn-back">← Back</button>
        <h2 className="project-title-bar">{subject.name}</h2>
        <div className={`save-status save-status-${saveStatus}`}>
          {saveStatus === "saving" ? "Saving…" : saveStatus === "unsaved" ? "Unsaved" : "Saved"}
        </div>
        <button className="btn-primary" onClick={saveSubject} disabled={saveStatus === "saving"}>
          Save Settings
        </button>
      </div>

      <div className="subject-body">
        <section className="subject-panel subject-projects-panel">
          <div className="subject-panel-header">Projects</div>
          <form className="subject-create-project" onSubmit={createProject}>
            <div className="form-field">
              <label>Project title</label>
              <input
                value={projectTitle}
                onChange={(e) => setProjectTitle(e.target.value)}
                placeholder={`${projectTitleSeed(subject)}...`}
              />
            </div>
            <div className="form-field">
              <label>Output file</label>
              <input
                value={projectOutputPath}
                onChange={(e) => setProjectOutputPath(e.target.value)}
                placeholder={subject.docsDir ? "2.6.md or /absolute/path.md" : "/absolute/path.md"}
              />
            </div>
            <div className="form-field">
              <label>Blueprint file (optional)</label>
              <input
                value={projectBlueprintPath}
                onChange={(e) => setProjectBlueprintPath(e.target.value)}
                placeholder={subject.blueprintDir ? "2.6.md or /absolute/path.md" : "/absolute/path.md"}
              />
            </div>
            {createError && <div className="form-error">{createError}</div>}
            <button className="btn-primary" type="submit" disabled={creatingProject}>
              {creatingProject ? "Creating…" : "Create Project"}
            </button>
          </form>

          <div className="subject-project-list">
            {projects.length === 0 && (
              <div className="refs-view-empty">No projects in this subject yet.</div>
            )}
            {projects.map((project) => (
              <button
                key={project.id}
                className="subject-project-item"
                type="button"
                onClick={() => onOpenProject(project.id)}
              >
                <span className="subject-project-title">{project.title}</span>
                <span className="subject-project-meta">
                  {project.outputPath?.split("/").pop() ?? ""}
                  {typeof project.itemCount === "number" ? ` · ${project.itemCount} items` : ""}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="subject-panel subject-detail-panel">
          <div className="subject-pane-tabs">
            <button
              type="button"
              className={activePane === "settings" ? "subject-pane-tab active" : "subject-pane-tab"}
              onClick={() => setActivePane("settings")}
            >
              Subject Settings
            </button>
            <button
              type="button"
              className={activePane === "rules" ? "subject-pane-tab active" : "subject-pane-tab"}
              onClick={() => setActivePane("rules")}
            >
              Subject Rules
            </button>
            <button
              type="button"
              className={activePane === "mapping" ? "subject-pane-tab active" : "subject-pane-tab"}
              onClick={() => setActivePane("mapping")}
            >
              Mapping
            </button>
          </div>

          {activePane === "settings" ? (
            <div className="subject-pane-content">
              <div className="subject-settings-grid">
                <div className="form-field">
                  <label>Name</label>
                  <input value={subject.name} onChange={(e) => updateSubject({ name: e.target.value })} />
                </div>
                <div className="form-field">
                  <label>Title prefix</label>
                  <input value={subject.titlePrefix} onChange={(e) => updateSubject({ titlePrefix: e.target.value })} />
                </div>
                <div className="form-field subject-settings-full">
                  <label>MkDocs root</label>
                  <input value={subject.mkdocsRoot} onChange={(e) => updateSubject({ mkdocsRoot: e.target.value })} />
                </div>
                <div className="form-field subject-settings-full">
                  <label>Docs directory</label>
                  <input value={subject.docsDir} onChange={(e) => updateSubject({ docsDir: e.target.value })} />
                </div>
                <div className="form-field subject-settings-full">
                  <label>Blueprint directory</label>
                  <input value={subject.blueprintDir} onChange={(e) => updateSubject({ blueprintDir: e.target.value })} />
                </div>
                <div className="form-field subject-settings-full">
                  <label>Mapping path</label>
                  <input value={subject.mappingPath} onChange={(e) => updateSubject({ mappingPath: e.target.value })} />
                </div>
              </div>

              <div className="subject-panel-header subject-subheader">Shared References</div>
              <div className="subject-reference-list">
                {subject.references.length === 0 && (
                  <div className="refs-view-empty">No shared references configured.</div>
                )}
                {subject.references.map((ref, index) => (
                  <div key={ref.id || index} className="subject-reference-row">
                    <input
                      value={ref.name}
                      onChange={(e) => updateReference(index, { name: e.target.value })}
                      placeholder="name.md"
                    />
                    <input
                      value={ref.path}
                      onChange={(e) => updateReference(index, { path: e.target.value, originalPath: e.target.value })}
                      placeholder="/path/to/reference.md"
                    />
                    <button className="btn-danger ref-btn" type="button" onClick={() => removeReference(index)}>×</button>
                  </div>
                ))}
              </div>
              <form className="subject-reference-add" onSubmit={addReference}>
                <input
                  value={newRefName}
                  onChange={(e) => setNewRefName(e.target.value)}
                  placeholder="name.md"
                />
                <input
                  value={newRefPath}
                  onChange={(e) => setNewRefPath(e.target.value)}
                  placeholder="/path/to/reference.md"
                />
                <button className="btn-secondary" type="submit" disabled={!newRefName.trim()}>Add</button>
              </form>
            </div>
          ) : activePane === "rules" ? (
            <div className="subject-pane-content subject-rules-pane">
              <div className="subject-rules-toolbar">
                {(["match", "generate", "map"] as RuleKind[]).map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    className={activeRuleKind === kind ? "btn-primary" : "btn-secondary"}
                    onClick={() => setActiveRuleKind(kind)}
                  >
                    {kind === "match" ? "Match" : kind === "generate" ? "Generate" : "Map"}
                  </button>
                ))}
                <span className={`save-status save-status-${ruleSaveStatus}`}>
                  {ruleSaveStatus === "saving" ? "Saving…" : ruleSaveStatus === "unsaved" ? "Unsaved" : "Saved"}
                </span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={saveRules}
                  disabled={ruleContent === null || ruleSaveStatus === "saving"}
                >
                  Save Rules
                </button>
              </div>
              {ruleError && <div className="form-error subject-rule-error">{ruleError}</div>}
              <div className="subject-rules-editor">
                {ruleContent === null ? (
                  <div className="loading">Loading…</div>
                ) : (
                  <MarkdownEditor
                    value={ruleContent}
                    onChange={(value) => {
                      setRuleContent(value);
                      setRuleSaveStatus("unsaved");
                    }}
                    height="100%"
                    projectId={projects[0]?.id}
                  />
                )}
              </div>
            </div>
          ) : (
            <div className="subject-pane-content subject-mapping-pane">
              {subject.mappingPath.trim() ? (
                <MappingView mappingPath={subject.mappingPath} projectId={projects[0]?.id ?? ""} />
              ) : (
                <div className="refs-view-empty">No mapping path configured for this subject.</div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
