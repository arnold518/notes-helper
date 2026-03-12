import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";
import MarkdownEditor from "./MarkdownEditor";

interface Props {
  mappingPath: string;
  projectId: string;
}

export default function MappingView({ mappingPath, projectId }: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"saved" | "unsaved" | "saving">("saved");
  const [loadError, setLoadError] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setContent(null);
    setLoadError(null);
    setSaveStatus("saved");
    api.readFile(mappingPath).then(setContent).catch((e) => setLoadError(e.message));
  }, [mappingPath]);

  function handleChange(value: string) {
    setContent(value);
    setSaveStatus("unsaved");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setSaveStatus("saving");
      api.writeFile(mappingPath, value)
        .then(() => setSaveStatus("saved"))
        .catch(console.error);
    }, 800);
  }

  const fileName = mappingPath.split("/").pop() ?? mappingPath;
  const saveLabel = saveStatus === "saving" ? "Saving…" : saveStatus === "unsaved" ? "Unsaved" : "Saved";

  return (
    <div className="mapping-view">
      <div className="mapping-view-header">
        <span className="mapping-view-title" title={mappingPath}>{fileName}</span>
        <span className="mapping-view-save">{saveLabel}</span>
      </div>
      <div className="mapping-view-body">
        {loadError ? (
          <div className="error-msg" style={{ gridColumn: "1 / -1" }}>{loadError}</div>
        ) : content === null ? (
          <div className="loading" style={{ gridColumn: "1 / -1" }}>Loading…</div>
        ) : (
          <>
            <div className="mapping-view-editor">
              <MarkdownEditor
                value={content}
                onChange={handleChange}
                height="100%"
                projectId={projectId}
              />
            </div>
            <div className="mapping-view-preview">
              <MappingPreview content={content} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MappingPreview({ content }: { content: string }) {
  return (
    <div
      className="mapping-preview"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: renderMappingMarkdown(content) }}
    />
  );
}

function renderMappingMarkdown(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];
  let inTable = false;
  let tableHead = true;

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.startsWith("## ")) {
      if (inTable) { out.push("</tbody></table>"); inTable = false; }
      out.push(`<h2>${escHtml(line.slice(3))}</h2>`);
      tableHead = true;
      continue;
    }
    if (line.startsWith("# ")) {
      if (inTable) { out.push("</tbody></table>"); inTable = false; }
      out.push(`<h1>${escHtml(line.slice(2))}</h1>`);
      continue;
    }

    if (line.startsWith("|")) {
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^-+$/.test(c))) continue;
      if (!inTable) {
        out.push('<table class="mapping-table"><thead>');
        inTable = true;
        tableHead = true;
      }
      if (tableHead) {
        out.push("<tr>" + cells.map((c) => `<th>${renderInline(c)}</th>`).join("") + "</tr></thead><tbody>");
        tableHead = false;
      } else {
        out.push("<tr>" + cells.map((c) => `<td>${renderInline(c)}</td>`).join("") + "</tr>");
      }
      continue;
    }

    if (inTable) { out.push("</tbody></table>"); inTable = false; tableHead = true; }
    if (line === "") {
      out.push("<br>");
    } else {
      out.push(`<p>${renderInline(line)}</p>`);
    }
  }

  if (inTable) out.push("</tbody></table>");
  return out.join("\n");
}

function renderInline(s: string): string {
  return escHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
