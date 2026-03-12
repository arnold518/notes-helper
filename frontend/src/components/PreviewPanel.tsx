import type { Item, Project } from "../types/project";
import ExcerptPreview from "./ExcerptPreview";
import PreviewIframe from "./PreviewIframe";

type PanelTab = "excerpt" | "document";

interface Props {
  item: Item | null;
  project: Project;
  activeTab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
  autoPreviewKey?: number;
}

export default function PreviewPanel({ item, project, activeTab, onTabChange, autoPreviewKey = 0 }: Props) {
  return (
    <div className="preview-panel">
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
        {item ? (
          activeTab === "excerpt" ? (
            <ExcerptPreview excerpt={item.excerpt} />
          ) : (
            <PreviewIframe
              content={item.document}
              mkdocsRoot={project.mkdocsRoot}
              outputPath={project.outputPath}
              autoPreviewKey={autoPreviewKey}
            />
          )
        ) : (
          <div className="no-selection">Select an item to preview</div>
        )}
      </div>
    </div>
  );
}
