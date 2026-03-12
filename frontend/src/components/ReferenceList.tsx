import { useState } from "react";
import { api } from "../api/client";
import type { Project } from "../types/project";

interface Props {
  project: Project;
  onProjectUpdate: (p: Project) => void;
}

export default function ReferenceList({ project, onProjectUpdate }: Props) {
  const [newPath, setNewPath] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [prepareJobs, setPrepareJobs] = useState<Record<string, "running" | "done" | "error">>({});

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newPath.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      const updated = await api.addReference(project.id, newPath.trim());
      onProjectUpdate(updated);
      setNewPath("");
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
    } catch (e: any) {
      console.error(e);
    }
  }

  async function handlePrepare(refId: string) {
    setPrepareJobs((j) => ({ ...j, [refId]: "running" }));
    try {
      const { job_id } = await api.prepareReference(project.id, refId);
      // Poll for completion
      const interval = setInterval(async () => {
        try {
          const job = await api.pollJob(job_id);
          if (job.status === "done") {
            clearInterval(interval);
            setPrepareJobs((j) => ({ ...j, [refId]: "done" }));
            const updated = await api.getProject(project.id);
            onProjectUpdate(updated);
          } else if (job.status === "error") {
            clearInterval(interval);
            setPrepareJobs((j) => ({ ...j, [refId]: "error" }));
          }
        } catch {
          clearInterval(interval);
          setPrepareJobs((j) => ({ ...j, [refId]: "error" }));
        }
      }, 3000);
    } catch (e: any) {
      setPrepareJobs((j) => ({ ...j, [refId]: "error" }));
    }
  }

  return (
    <div className="reference-list">
      <div className="reference-list-header">References</div>
      {project.references.map((ref) => (
        <div key={ref.id} className="reference-item">
          <span className="reference-item-name" title={ref.path}>{ref.name}</span>
          <span className="reference-item-status">
            {ref.prepared ? <span className="ref-prepared">prepared</span> : null}
          </span>
          <button
            className="btn-secondary ref-btn"
            onClick={() => handlePrepare(ref.id)}
            disabled={prepareJobs[ref.id] === "running"}
            title="Prepare (fix OCR/typos)"
          >
            {prepareJobs[ref.id] === "running" ? "…" : prepareJobs[ref.id] === "done" ? "✓" : "Prep"}
          </button>
          <button
            className="btn-danger ref-btn"
            onClick={() => handleRemove(ref.id)}
            title="Remove"
          >
            ×
          </button>
        </div>
      ))}
      <form onSubmit={handleAdd} className="reference-add-form">
        <input
          type="text"
          value={newPath}
          onChange={(e) => setNewPath(e.target.value)}
          placeholder="/path/to/reference.md"
          className="reference-add-input"
        />
        <button type="submit" className="btn-primary ref-btn" disabled={adding}>
          {adding ? "…" : "+"}
        </button>
      </form>
      {addError && <div className="ref-add-error">{addError}</div>}
    </div>
  );
}
