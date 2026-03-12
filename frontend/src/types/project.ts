export type EntryKind = "admonition" | "section" | "text";
export type EntryStatus = "pending" | "matched" | "generated" | "approved";

export interface Item {
  kind: EntryKind;
  id: string;
  type: string;       // "h1"/"h2"/"h3" | "" | admonition type
  content: string;
  excerpt: string;
  syncedExcerpt: string;
  syncedNumber: number;
  document: string;
  status: EntryStatus;
  number: number;
  autonumber: boolean;
}

export interface ReferenceFile {
  id: string;
  name: string;
  path: string;
  originalPath: string;
  prepared: boolean;
}

export interface Project {
  id: string;
  title: string;
  blueprintPath: string;
  references: ReferenceFile[];
  markdownRulesPath: string;
  mkdocsRoot: string;
  outputPath: string;
  mappingPath: string;
  numberPrefix: string;
  syncedNumberPrefix: string;
  examplesDir?: string;
  items: Item[];
  createdAt: string;
  updatedAt: string;
}

export interface ProjectSummary {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface JobResponse {
  status: "running" | "done" | "error";
  result?: Array<Record<string, unknown>>;
  error?: string;
}

export interface AiLogSummary {
  id: string;
  runType: string;
  status: string;
  provider: string;
  model: string;
  reasoningEffort: string;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
  error?: string;
  itemIds?: string[];
  referencePath?: string;
}

export interface AiLogDetail extends AiLogSummary {
  projectId: string;
  cwd: string;
  command: string[];
  prompt: string;
  stdout: string;
  stderr: string;
  meta?: Record<string, unknown>;
}

export interface VscodeSnippet {
  name: string;
  prefix: string;
  body: string;
  description: string;
  scope: string;
  sourceFile: string;
}

export interface ProjectSnippetsResponse {
  mkdocsRoot: string;
  snippetDir: string;
  snippets: VscodeSnippet[];
}
