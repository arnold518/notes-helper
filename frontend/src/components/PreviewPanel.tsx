import type { Item, Project } from "../types/project";
import ExcerptPreview from "./ExcerptPreview";
import PreviewIframe from "./PreviewIframe";
import ReferencePanel from "./ReferencePanel";

type PanelTab = "excerpt" | "document" | "reference";

interface Props {
  item: Item | null;
  project: Project;
  activeTab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
  autoPreviewKey?: number;
  onOpenReferences?: () => void;
  onAppendToExcerpt?: (block: string) => void;
}

export default function PreviewPanel({
  item,
  project,
  activeTab,
  onTabChange,
  autoPreviewKey = 0,
  onOpenReferences,
  onAppendToExcerpt,
}: Props) {
  return (
    <div className="preview-panel">
      <div className="panel-tabs">
        <button
          className={`panel-tab${activeTab === "reference" ? " panel-tab-active" : ""}`}
          onClick={() => onTabChange("reference")}
        >
          Reference
        </button>
        <button
          className={`panel-tab${activeTab === "excerpt" ? " panel-tab-active" : ""}`}
          onClick={() => onTabChange("excerpt")}
        >
          Preview Excerpt
        </button>
        <button
          className={`panel-tab${activeTab === "document" ? " panel-tab-active" : ""}`}
          onClick={() => onTabChange("document")}
        >
          Preview Document
        </button>
      </div>
      <div className="panel-content">
        {activeTab === "reference" ? (
          <ReferencePanel
            project={project}
            excerpt={item?.excerpt ?? ""}
            onOpenReferences={onOpenReferences}
            onAppendToExcerpt={onAppendToExcerpt}
            canAppendToExcerpt={!!item}
          />
        ) : item ? (
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
