import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { ProjectSummary } from "../types/project";

interface Props {
  onOpenProject: (id: string) => void;
}

export default function Home({ onOpenProject }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [blueprintPath, setBlueprintPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [mappingPath, setMappingPath] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(console.error);
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const project = await api.createProject({
        blueprintPath: blueprintPath || undefined,
        outputPath: outputPath || undefined,
        mappingPath: mappingPath || undefined,
      });
      onOpenProject(project.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="home-page">
      <h1>Notes Helper</h1>
      <p className="home-subtitle">AI-powered blog authoring tool for MkDocs Material</p>

      <section className="home-section">
        <h2>Create New Project</h2>
        <form onSubmit={handleCreate} className="home-form">
          <div className="form-field">
            <label>Blueprint path (optional)</label>
            <input
              type="text"
              value={blueprintPath}
              onChange={(e) => setBlueprintPath(e.target.value)}
              placeholder="/path/to/blueprint.md"
            />
          </div>
          <div className="form-field">
            <label>Output file path</label>
            <input
              type="text"
              value={outputPath}
              onChange={(e) => setOutputPath(e.target.value)}
              placeholder="/home/arnold/arnold/github/math-notes/docs/linear-algebra/4.md"
            />
          </div>
          <div className="form-field">
            <label>Numbering map path (optional)</label>
            <input
              type="text"
              value={mappingPath}
              onChange={(e) => setMappingPath(e.target.value)}
              placeholder="/home/arnold/arnold/github/math-notes/ORIGINAL_TO_NOTES_NUMBERING_MAP.md"
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Creating…" : "Create Project"}
          </button>
        </form>
      </section>

      {projects.length > 0 && (
        <section className="home-section">
          <h2>Existing Projects</h2>
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id} className="project-list-item" onClick={() => onOpenProject(p.id)}>
                <span className="project-title">{p.title}</span>
                <span className="project-meta">
                  Updated {new Date(p.updatedAt).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
