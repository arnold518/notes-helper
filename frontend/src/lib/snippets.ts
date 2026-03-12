import { completeFromList, snippetCompletion, type Completion, type CompletionSource } from "@codemirror/autocomplete";
import { api } from "../api/client";
import type { VscodeSnippet } from "../types/project";

const projectSnippetCache = new Map<string, Promise<VscodeSnippet[]>>();

// Fallback root used when a project has no mkdocsRoot configured.
const DEFAULT_MKDOCS_SNIPPET_ROOT = "/home/arnold/arnold/github/math-notes";

// Sentinel to protect escaped dollar signs during template normalization.
const DOLLAR_SENTINEL = "\x00DOLLAR\x00";

// Well-known snippet file names to probe in the legacy path.
const LEGACY_SNIPPET_FILES = [
  "theorem.code-snippets",
  "definition.code-snippets",
  "proof.code-snippets",
  "example.code-snippets",
  "exercise.code-snippets",
  "concept.code-snippets",
  "corollary.code-snippets",
  "center.code-snippets",
  "image.code-snippets",
];

// ── Cache management ──────────────────────────────────────────────────────────

/** Bust the snippet cache for a project. Call this after saving project settings. */
export function invalidateSnippetCache(projectId: string): void {
  projectSnippetCache.delete(projectId);
}

// ── Snippet loading ───────────────────────────────────────────────────────────

/** Load snippets for a project, using the backend API with legacy file-read fallback. */
export function loadProjectSnippets(projectId: string): Promise<VscodeSnippet[]> {
  const cached = projectSnippetCache.get(projectId);
  if (cached) return cached;

  const pending = api.getProjectSnippets(projectId)
    .then((res) => res.snippets ?? [])
    .catch((): VscodeSnippet[] => [])                    // primary network failure → treat as empty
    .then((snippets) => snippets.length > 0 ? snippets : loadSnippetsViaLegacyApis(projectId))
    .catch(() => {
      // Legacy path also failed; evict so the next mount retries.
      projectSnippetCache.delete(projectId);
      return [] as VscodeSnippet[];
    });

  projectSnippetCache.set(projectId, pending);
  return pending;
}

function inferMkdocsRootFromOutputPath(outputPath: string): string {
  const normalized = outputPath.trim().replaceAll("\\", "/");
  const idx = normalized.indexOf("/docs/");
  return idx > 0 ? normalized.slice(0, idx) : "";
}

async function loadSnippetsViaLegacyApis(projectId: string): Promise<VscodeSnippet[]> {
  const project = await api.getProject(projectId);
  const mkdocsRoot = project.mkdocsRoot.trim() || inferMkdocsRootFromOutputPath(project.outputPath);
  const snippets = await loadSnippetsFromMkdocsRoot(mkdocsRoot);
  if (snippets.length > 0) return snippets;
  // Try the default root as a last resort, but skip if we already tried it.
  if (mkdocsRoot !== DEFAULT_MKDOCS_SNIPPET_ROOT) {
    return loadSnippetsFromMkdocsRoot(DEFAULT_MKDOCS_SNIPPET_ROOT);
  }
  return snippets;
}

async function loadSnippetsFromMkdocsRoot(mkdocsRoot: string): Promise<VscodeSnippet[]> {
  if (!mkdocsRoot) return [];

  const typeFiles = await api.getMkdocsConfig(mkdocsRoot)
    .then((types) => types.map((t) => `${t.type}.code-snippets`))
    .catch(() => [] as string[]);

  const candidates = Array.from(new Set([...LEGACY_SNIPPET_FILES, ...typeFiles]));

  const results = await Promise.all(
    candidates.map(async (fileName) => {
      try {
        const text = await api.readFile(`${mkdocsRoot}/.vscode/${fileName}`);
        return parseSnippetFileContent(text, fileName);
      } catch {
        return [] as VscodeSnippet[];
      }
    }),
  );

  return results.flat();
}

// ── JSONC parsing (legacy path only — the backend parses snippets server-side) ─

function stripJsonComments(content: string): string {
  let out = "";
  let inString = false;
  let escaped = false;
  let inLineComment = false;
  let inBlockComment = false;

  for (let i = 0; i < content.length; i++) {
    const ch = content[i];
    const next = content[i + 1] ?? "";

    if (inLineComment) {
      if (ch === "\n") { inLineComment = false; out += ch; }
      continue;
    }
    if (inBlockComment) {
      if (ch === "*" && next === "/") { inBlockComment = false; i++; }
      else if (ch === "\n") out += ch;
      continue;
    }
    if (inString) {
      out += ch;
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === "\"") inString = false;
      continue;
    }
    if (ch === "\"") { inString = true; out += ch; continue; }
    if (ch === "/" && next === "/") { inLineComment = true; i++; continue; }
    if (ch === "/" && next === "*") { inBlockComment = true; i++; continue; }
    out += ch;
  }
  return out;
}

function parseSnippetFileContent(content: string, sourceFile: string): VscodeSnippet[] {
  let data: unknown;
  try {
    data = JSON.parse(content);
  } catch {
    data = JSON.parse(stripJsonComments(content));
  }
  if (!data || typeof data !== "object") return [];

  const result: VscodeSnippet[] = [];
  for (const [name, raw] of Object.entries(data as Record<string, unknown>)) {
    if (!raw || typeof raw !== "object") continue;
    const entry = raw as Record<string, unknown>;
    const prefixRaw = entry.prefix;
    const bodyRaw = entry.body;

    const prefixes =
      typeof prefixRaw === "string" ? [prefixRaw]
      : Array.isArray(prefixRaw) ? prefixRaw.filter((p): p is string => typeof p === "string")
      : [];
    const body =
      typeof bodyRaw === "string" ? bodyRaw
      : Array.isArray(bodyRaw) ? bodyRaw.map(String).join("\n")
      : "";

    for (const prefix of prefixes) {
      if (!prefix.trim() || !body.trim()) continue;
      result.push({
        name: name || sourceFile,
        prefix: prefix.trim(),
        body,
        description: String(entry.description ?? ""),
        scope: String(entry.scope ?? ""),
        sourceFile,
      });
    }
  }
  return result;
}

// ── Template & scope helpers ──────────────────────────────────────────────────

/** Returns true if the snippet's scope applies to markdown files. */
export function isMarkdownScope(scope: string): boolean {
  if (!scope.trim()) return true;
  return scope.split(",").some((s) => {
    const n = s.trim().toLowerCase();
    return n === "markdown" || n === "md";
  });
}

/**
 * Convert a VSCode snippet body to a CodeMirror snippet template.
 *
 * - `$N` shorthand → `${N}` (CodeMirror/LSP standard)
 * - `${N:default}` already correct — kept as-is
 * - VSCode uppercase variable references are stripped
 * - Escaped `\$` preserved through a sentinel
 */
export function normalizeSnippetTemplate(body: string): string {
  let t = body.replace(/\\\$/g, DOLLAR_SENTINEL);
  t = t.replace(/\$([0-9]+)/g, "${$1}");                    // $N → ${N}
  t = t.replace(/\$\{[A-Z_][A-Z0-9_]*:([^}]*)\}/g, "$1"); // ${VAR:default} → default
  t = t.replace(/\$\{[A-Z_][A-Z0-9_]*\}/g, "");            // ${VAR} → ""
  t = t.replace(/\$[A-Z_][A-Z0-9_]*/g, "");                // $VAR → ""
  return t.replaceAll(DOLLAR_SENTINEL, "\\$");
}

// ── CodeMirror integration helpers ───────────────────────────────────────────

/**
 * Build a deduplicated list of CodeMirror `Completion` objects from raw snippets.
 * Deduplication key: prefix + body + sourceFile (same snippet from two sources → one entry).
 */
export function buildSnippetCompletions(snippets: VscodeSnippet[]): Completion[] {
  const completions: Completion[] = [];
  const seen = new Set<string>();

  for (const s of snippets) {
    if (!isMarkdownScope(s.scope)) continue;
    const key = `${s.prefix}\0${s.body}\0${s.sourceFile}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const template = normalizeSnippetTemplate(s.body);
    if (!template.trim()) continue;
    completions.push(snippetCompletion(template, {
      label: s.prefix,
      detail: s.description || s.name,
      type: "keyword",
      info: s.sourceFile,
    }));
  }
  return completions;
}

/**
 * Create a CodeMirror `CompletionSource` from a list of snippet completions.
 * Returns a no-op source when the list is empty to avoid unnecessary processing.
 */
export function makeSnippetSource(completions: Completion[]): CompletionSource {
  if (completions.length === 0) return () => null;
  return completeFromList(completions);
}

/**
 * Build a prefix → normalized-template map for Tab-key expansion.
 * When multiple snippets share a prefix, the first one wins.
 */
export function buildSnippetPrefixMap(snippets: VscodeSnippet[]): Map<string, string> {
  const byPrefix = new Map<string, string>();
  for (const s of snippets) {
    if (!isMarkdownScope(s.scope)) continue;
    const prefix = s.prefix.trim();
    if (!prefix || byPrefix.has(prefix)) continue;
    byPrefix.set(prefix, normalizeSnippetTemplate(s.body));
  }
  return byPrefix;
}
