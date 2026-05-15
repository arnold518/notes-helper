import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Subject } from "../types/project";

interface Props {
  onOpenSubject: (id: string) => void;
}

export default function Home({ onOpenSubject }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [name, setName] = useState("");
  const [titlePrefix, setTitlePrefix] = useState("");
  const [mkdocsRoot, setMkdocsRoot] = useState("");
  const [docsDir, setDocsDir] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSubjects().then(setSubjects).catch(console.error);
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const subject = await api.createSubject({
        name: name || undefined,
        titlePrefix: titlePrefix || undefined,
        mkdocsRoot: mkdocsRoot || undefined,
        docsDir: docsDir || undefined,
      });
      onOpenSubject(subject.id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="home-page">
      <h1>Notes Helper</h1>
      <p className="home-subtitle">Select a subject to manage its note projects.</p>

      <section className="home-section">
        <h2>Create Subject</h2>
        <form onSubmit={handleCreate} className="home-form">
          <div className="form-field">
            <label>Subject name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Linear Algebra"
            />
          </div>
          <div className="form-field">
            <label>Title prefix (optional)</label>
            <input
              type="text"
              value={titlePrefix}
              onChange={(e) => setTitlePrefix(e.target.value)}
              placeholder="e.g. QCQI"
            />
          </div>
          <div className="form-field">
            <label>MkDocs root (optional)</label>
            <input
              type="text"
              value={mkdocsRoot}
              onChange={(e) => setMkdocsRoot(e.target.value)}
              placeholder="/path/to/mkdocs/root"
            />
          </div>
          <div className="form-field">
            <label>Docs directory (optional)</label>
            <input
              type="text"
              value={docsDir}
              onChange={(e) => setDocsDir(e.target.value)}
              placeholder="/path/to/mkdocs/docs/topic"
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Creating…" : "Create Subject"}
          </button>
        </form>
      </section>

      {subjects.length > 0 && (
        <section className="home-section">
          <h2>Subjects</h2>
          <ul className="project-list">
            {subjects.map((subject) => (
              <li key={subject.id} className="project-list-item" onClick={() => onOpenSubject(subject.id)}>
                <span className="project-title">{subject.name}</span>
                <span className="project-meta">
                  {subject.projectCount} projects
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
