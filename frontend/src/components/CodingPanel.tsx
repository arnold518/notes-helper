import { useState } from "react";
import type { Item, Project } from "../types/project";
import MarkdownEditor from "./MarkdownEditor";
import RunButton from "./RunButton";

type PanelTab = "excerpt" | "document";

interface Props {
  item: Item | null;
  project: Project;
  activeTab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
  matchItemJobId: string | null;
  editExcerptJobId: string | null;
  generateItemJobId: string | null;
  editDocumentJobId: string | null;
  matchPrompt: string;
  generatePrompt: string;
  onMatchPromptChange: (value: string) => void;
  onGeneratePromptChange: (value: string) => void;
  /** Called when user clicks Run Match — parent handles dispatch */
  onRunMatch: () => void;
  onEditExcerptJobStart: (jobId: string) => void;
  /** Called when user clicks Run Generate — parent handles dispatch */
  onRunGenerate: () => void;
  onEditDocumentJobStart: (jobId: string) => void;
  onMatchItemJobFinish: (itemId: string) => void;
  onEditExcerptJobFinish: () => void;
  onGenerateItemJobFinish: (itemId: string) => void;
  onEditDocumentJobFinish: () => void;
  onItemChange: (field: "excerpt" | "document", value: string) => void;
  onProjectUpdate: (p: Project) => void;
}

export default function CodingPanel({
  item, project, activeTab, onTabChange,
  matchItemJobId, editExcerptJobId, generateItemJobId, editDocumentJobId,
  matchPrompt, generatePrompt, onMatchPromptChange, onGeneratePromptChange,
  onRunMatch, onEditExcerptJobStart, onRunGenerate, onEditDocumentJobStart,
  onMatchItemJobFinish, onEditExcerptJobFinish, onGenerateItemJobFinish, onEditDocumentJobFinish,
  onItemChange, onProjectUpdate,
}: Props) {
  const [syncMapJobId, setSyncMapJobId] = useState<string | null>(null);

  if (!item) {
    return (
      <div className="coding-panel">
        <div className="no-selection">Select an item from the nav panel</div>
      </div>
    );
  }

  return (
    <div className="coding-panel">
      <div className="panel-tabs">
        <button
          className={`panel-tab${activeTab === "excerpt" ? " panel-tab-active" : ""}`}
          onClick={() => onTabChange("excerpt")}
        >
          Excerpt
        </button>
        <button
          className={`panel-tab${activeTab === "document" ? " panel-tab-active" : ""}`}
          onClick={() => onTabChange("document")}
        >
          Document
        </button>
      </div>

      <div className="panel-content">
        {activeTab === "excerpt" && (
          <MarkdownEditor
            value={item.excerpt}
            onChange={(v) => onItemChange("excerpt", v)}
            height="100%"
            placeholder="Textbook excerpt will appear here after matching…"
            projectId={project.id}
          />
        )}
        {activeTab === "document" && (
          <MarkdownEditor
            value={item.document}
            onChange={(v) => onItemChange("document", v)}
            height="100%"
            placeholder="Generated markdown will appear here after generation…"
            projectId={project.id}
          />
        )}
      </div>

      <div className="panel-footer">
        {activeTab === "excerpt" && (
          <>
            <textarea
              className="prompt-textarea"
              value={matchPrompt}
              onChange={(e) => onMatchPromptChange(e.target.value)}
              placeholder="Optional: extra instructions…"
              rows={2}
            />
            <div className="panel-footer-actions">
              <RunButton
                projectId={project.id}
                action="match"
                label="Run Match ▶"
                activeJobId={matchItemJobId}
                itemId={item.id}
                onRun={onRunMatch}
                onJobFinish={() => onMatchItemJobFinish(item.id)}
                onDone={onProjectUpdate}
              />
              <RunButton
                projectId={project.id}
                action="edit"
                label="Edit Excerpt ✎"
                activeJobId={editExcerptJobId}
                userPrompt={matchPrompt}
                itemId={item.id}
                editTarget="excerpt"
                editContent={item.excerpt}
                onJobStart={onEditExcerptJobStart}
                onJobFinish={onEditExcerptJobFinish}
                onDone={onProjectUpdate}
              />
              {project.mappingPath && item.excerpt && (
                <RunButton
                  projectId={project.id}
                  action="sync-map"
                  label="Sync Map ⟳"
                  activeJobId={syncMapJobId}
                  itemId={item.id}
                  onJobStart={setSyncMapJobId}
                  onJobFinish={() => setSyncMapJobId(null)}
                  onDone={onProjectUpdate}
                />
              )}
            </div>
          </>
        )}
        {activeTab === "document" && (
          <>
            <textarea
              className="prompt-textarea"
              value={generatePrompt}
              onChange={(e) => onGeneratePromptChange(e.target.value)}
              placeholder="Optional: extra instructions…"
              rows={2}
            />
            <div className="panel-footer-actions">
              <RunButton
                projectId={project.id}
                action="generate"
                label="Run Generate ▶"
                activeJobId={generateItemJobId}
                itemId={item.id}
                onRun={onRunGenerate}
                onJobFinish={() => onGenerateItemJobFinish(item.id)}
                onDone={onProjectUpdate}
              />
              <RunButton
                projectId={project.id}
                action="edit"
                label="Edit Document ✎"
                activeJobId={editDocumentJobId}
                userPrompt={generatePrompt}
                itemId={item.id}
                editTarget="document"
                editContent={item.document}
                onJobStart={onEditDocumentJobStart}
                onJobFinish={onEditDocumentJobFinish}
                onDone={onProjectUpdate}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
