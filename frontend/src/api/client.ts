import type {
  Project,
  ProjectSummary,
  JobResponse,
  Item,
  Subject,
  AiLogSummary,
  AiLogDetail,
  AiConversationThread,
  ProjectSnippetsResponse,
} from "../types/project";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined)
  ?? "http://localhost:7999";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  listSubjects: (): Promise<Subject[]> =>
    req("/api/subjects"),

  createSubject: (body: {
    name?: string;
    titlePrefix?: string;
    mkdocsRoot?: string;
    docsDir?: string;
    blueprintDir?: string;
    mappingPath?: string;
  }): Promise<Subject> =>
    req("/api/subjects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getSubject: (id: string): Promise<Subject> =>
    req(`/api/subjects/${id}`),

  saveSubject: (subject: Subject): Promise<Subject> =>
    req(`/api/subjects/${subject.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(subject),
    }),

  getSubjectRules: (subjectId: string, kind: "match" | "generate" | "map"): Promise<{ kind: string; content: string }> =>
    req(`/api/subjects/${subjectId}/rules/${kind}`),

  putSubjectRules: (subjectId: string, kind: "match" | "generate" | "map", content: string): Promise<{ kind: string; content: string }> =>
    req(`/api/subjects/${subjectId}/rules/${kind}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }),

  listSubjectProjects: (subjectId: string): Promise<ProjectSummary[]> =>
    req(`/api/subjects/${subjectId}/projects`),

  createSubjectProject: (subjectId: string, body: {
    title?: string;
    blueprintPath?: string;
    mkdocsRoot?: string;
    outputPath?: string;
    mappingPath?: string;
  }): Promise<Project> =>
    req(`/api/subjects/${subjectId}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  listProjects: (): Promise<ProjectSummary[]> =>
    req("/api/projects"),

  createProject: (body: {
    title?: string;
    blueprintPath?: string;
    mkdocsRoot?: string;
    outputPath?: string;
    mappingPath?: string;
  }): Promise<Project> =>
    req("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getProject: (id: string): Promise<Project> =>
    req(`/api/projects/${id}`),

  saveProject: (project: Project): Promise<Project> =>
    req(`/api/projects/${project.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(project),
    }),

  // Items
  insertItem: (projectId: string, item: Partial<Item> & { afterId?: string }): Promise<Project> =>
    req(`/api/projects/${projectId}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),

  deleteItem: (projectId: string, itemId: string): Promise<Project> =>
    req(`/api/projects/${projectId}/items/${itemId}`, { method: "DELETE" }),

  patchItem: (projectId: string, itemId: string, patch: Partial<Item>): Promise<Project> =>
    req(`/api/projects/${projectId}/items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),

  // References
  addReference: (projectId: string, name: string, path?: string): Promise<Project> =>
    req(`/api/projects/${projectId}/references`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, path }),
    }),

  removeReference: (projectId: string, refId: string): Promise<Project> =>
    req(`/api/projects/${projectId}/references/${refId}`, { method: "DELETE" }),

  prepareReference: (projectId: string, refId: string): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/references/${refId}/prepare`, { method: "POST" }),

  // Match / Generate (with optional userPrompt and itemId)
  startMatch: (
    projectId: string,
    opts?: { userPrompt?: string; itemId?: string }
  ): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts ?? {}),
    }),

  startGenerate: (
    projectId: string,
    opts?: { userPrompt?: string; itemId?: string }
  ): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts ?? {}),
    }),

  startEdit: (
    projectId: string,
    opts: { userPrompt?: string; itemId: string; target: "excerpt" | "document"; content?: string }
  ): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts),
    }),

  syncMap: (projectId: string, itemId: string): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/sync-map`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ itemId }),
    }),

  syncMapAll: (projectId: string): Promise<{ job_id: string }> =>
    req(`/api/projects/${projectId}/sync-map-all`, { method: "POST" }),

  pollJob: (jobId: string): Promise<JobResponse> =>
    req(`/api/jobs/${jobId}`),

  listAiLogs: (projectId: string, limit = 100): Promise<AiLogSummary[]> =>
    req(`/api/projects/${projectId}/ai-logs?limit=${limit}`),

  getAiLog: (projectId: string, logId: string): Promise<AiLogDetail> =>
    req(`/api/projects/${projectId}/ai-logs/${encodeURIComponent(logId)}`),

  getAiConversation: (projectId: string): Promise<AiConversationThread> =>
    req(`/api/projects/${projectId}/ai-conversation`),

  startAiCommand: (
    projectId: string,
    body: { message: string }
  ): Promise<{ job_id: string; user_message_id: string; assistant_message_id: string }> =>
    req(`/api/projects/${projectId}/ai-command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getProjectSnippets: (projectId: string): Promise<ProjectSnippetsResponse> =>
    req(`/api/projects/${projectId}/vscode-snippets`),

  readFile: (path: string): Promise<string> =>
    fetch(`${BASE}/api/file?path=${encodeURIComponent(path)}`).then((r) =>
      r.ok ? r.text() : Promise.reject(new Error(`File read failed: ${path}`))
    ),

  writeFile: (path: string, content: string): Promise<void> =>
    req("/api/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }).then(() => {}),

  newReference: (projectId: string, name: string): Promise<Project> =>
    req(`/api/projects/${projectId}/references`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),

  getMkdocsConfig: (root: string): Promise<Array<{ type: string; color: string }>> =>
    req(`/api/mkdocs-config?root=${encodeURIComponent(root)}`),

  preview: (content: string, mkdocsRoot: string, outputPath?: string): Promise<{ url: string }> =>
    req("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mkdocsRoot, outputPath: outputPath ?? "" }),
    }),
};
