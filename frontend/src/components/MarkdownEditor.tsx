import { useEffect, useMemo, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { autocompletion, snippet } from "@codemirror/autocomplete";
import { indentUnit } from "@codemirror/language";
import { markdown } from "@codemirror/lang-markdown";
import { oneDark } from "@codemirror/theme-one-dark";
import { RangeSetBuilder } from "@codemirror/state";
import { Prec } from "@codemirror/state";
import { Decoration, type DecorationSet, EditorView, ViewPlugin, type ViewUpdate, keymap } from "@codemirror/view";
import {
  buildSnippetCompletions,
  buildSnippetPrefixMap,
  loadProjectSnippets,
  makeSnippetSource,
} from "../lib/snippets";
import type { VscodeSnippet } from "../types/project";

interface Props {
  value: string;
  onChange: (val: string) => void;
  height?: string;
  placeholder?: string;
  projectId?: string;
}

const TAB_WIDTH = 4;

// ── Wrap-indent decoration ────────────────────────────────────────────────────

function lineIndentColumns(line: string): number {
  let cols = 0;
  for (const ch of line) {
    if (ch === "\t") cols += TAB_WIDTH;
    else if (ch === " ") cols += 1;
    else break;
  }
  return cols;
}

function buildWrapIndentDecorations(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  for (const range of view.visibleRanges) {
    let pos = range.from;
    while (pos <= range.to) {
      const line = view.state.doc.lineAt(pos);
      const indent = lineIndentColumns(line.text);
      if (indent > 0) {
        builder.add(
          line.from,
          line.from,
          Decoration.line({ attributes: { style: `--cm-wrap-indent: ${indent}ch` } }),
        );
      }
      if (line.to >= range.to) break;
      pos = line.to + 1;
    }
  }
  return builder.finish();
}

const wrapIndentPlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    constructor(view: EditorView) {
      this.decorations = buildWrapIndentDecorations(view);
    }
    update(update: ViewUpdate) {
      if (update.docChanged || update.viewportChanged) {
        this.decorations = buildWrapIndentDecorations(update.view);
      }
    }
  },
  { decorations: (v) => v.decorations },
);

const wrapIndentTheme = EditorView.baseTheme({
  ".cm-content": { tabSize: String(TAB_WIDTH) },
  ".cm-line": {
    "--cm-wrap-indent": "0ch",
    textIndent: "calc(var(--cm-wrap-indent) * -1)",
    paddingLeft: "var(--cm-wrap-indent)",
  },
});

// ── Component ─────────────────────────────────────────────────────────────────

export default function MarkdownEditor({ value, onChange, height = "150px", placeholder, projectId }: Props) {
  const [workspaceSnippets, setWorkspaceSnippets] = useState<VscodeSnippet[]>([]);

  useEffect(() => {
    let active = true;
    if (!projectId) {
      setWorkspaceSnippets([]);
      return () => { active = false; };
    }
    loadProjectSnippets(projectId).then((snippets) => {
      if (active) setWorkspaceSnippets(snippets);
    });
    return () => { active = false; };
  }, [projectId]);

  const snippetSource = useMemo(
    () => makeSnippetSource(buildSnippetCompletions(workspaceSnippets)),
    [workspaceSnippets],
  );

  const tabExpandExtension = useMemo(() => {
    const byPrefix = buildSnippetPrefixMap(workspaceSnippets);

    return Prec.high(keymap.of([{
      key: "Tab",
      run(view) {
        if (byPrefix.size === 0) return false;
        const sel = view.state.selection.main;
        if (!sel.empty) return false;
        const line = view.state.doc.lineAt(sel.from);
        const before = line.text.slice(0, sel.from - line.from);
        const match = before.match(/(\S+)$/);
        if (!match) return false;
        const template = byPrefix.get(match[1]);
        if (!template) return false;
        snippet(template)(view, null, sel.from - match[1].length, sel.from);
        return true;
      },
    }]));
  }, [workspaceSnippets]);

  const extensions = useMemo(
    () => [
      markdown(),
      indentUnit.of(" ".repeat(TAB_WIDTH)),
      EditorView.lineWrapping,
      wrapIndentTheme,
      wrapIndentPlugin,
      tabExpandExtension,
      autocompletion({ override: [snippetSource], activateOnTyping: true }),
    ],
    [snippetSource, tabExpandExtension],
  );

  return (
    <CodeMirror
      value={value}
      height={height}
      basicSetup={{ autocompletion: false }}
      extensions={extensions}
      theme={oneDark}
      onChange={onChange}
      placeholder={placeholder}
      style={{ fontSize: 13, borderRadius: 4, overflow: "hidden" }}
    />
  );
}
