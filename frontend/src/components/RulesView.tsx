import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";
import MarkdownEditor from "./MarkdownEditor";

type RulesKind = "match" | "generate" | "map";

interface Props {
  projectId: string;
}

export default function RulesView({ projectId }: Props) {
  const [activeKind, setActiveKind] = useState<RulesKind>("match");
  const [matchContent, setMatchContent] = useState<string | null>(null);
  const [generateContent, setGenerateContent] = useState<string | null>(null);
  const [mapContent, setMapContent] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"saved" | "unsaved" | "saving">("saved");
  const [loadError, setLoadError] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLoadError(null);
    Promise.all([
      api.getRules(projectId, "match"),
      api.getRules(projectId, "generate"),
      api.getRules(projectId, "map"),
    ]).then(([m, g, mp]) => {
      setMatchContent(m.content);
      setGenerateContent(g.content);
      setMapContent(mp.content);
    }).catch((e) => {
      setLoadError(e.message);
    });
  }, [projectId]);

  function handleChange(kind: RulesKind, value: string) {
    if (kind === "match") setMatchContent(value);
    else if (kind === "generate") setGenerateContent(value);
    else setMapContent(value);
    setSaveStatus("unsaved");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setSaveStatus("saving");
      api.putRules(projectId, kind, value)
        .then(() => setSaveStatus("saved"))
        .catch(console.error);
    }, 800);
  }

  const content = activeKind === "match" ? matchContent : activeKind === "generate" ? generateContent : mapContent;

  return (
    <div className="rules-view">
      <div className="rules-sidebar">
        <div className="rules-nav">
          <button
            className={activeKind === "match" ? "rules-nav-item active" : "rules-nav-item"}
            onClick={() => setActiveKind("match")}
          >
            Match Rules
          </button>
          <button
            className={activeKind === "generate" ? "rules-nav-item active" : "rules-nav-item"}
            onClick={() => setActiveKind("generate")}
          >
            Generate Rules
          </button>
          <button
            className={activeKind === "map" ? "rules-nav-item active" : "rules-nav-item"}
            onClick={() => setActiveKind("map")}
          >
            Map Rules
          </button>
        </div>
        <div className="rules-save-status">
          {saveStatus === "saving" ? "Saving…" : saveStatus === "unsaved" ? "Unsaved" : "Saved"}
        </div>
      </div>
      <div className="rules-editor-pane">
        {loadError ? (
          <div className="error-msg">{loadError}</div>
        ) : content === null ? (
          <div className="loading">Loading…</div>
        ) : (
          <MarkdownEditor
            value={content}
            onChange={(v) => handleChange(activeKind, v)}
            height="100%"
            projectId={projectId}
          />
        )}
      </div>
    </div>
  );
}
