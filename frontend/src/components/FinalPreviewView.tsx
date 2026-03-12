import PreviewIframe from "./PreviewIframe";

interface Props {
  content: string;
  mkdocsRoot: string;
  outputPath: string;
  autoPreviewKey: number;
  onExport: () => void;
  exporting: boolean;
  exportStatus: "idle" | "saved" | "error";
  exportMessage: string;
}

export default function FinalPreviewView({
  content,
  mkdocsRoot,
  outputPath,
  autoPreviewKey,
  onExport,
  exporting,
  exportStatus,
  exportMessage,
}: Props) {
  return (
    <div className="final-view">
      <div className="final-panel">
        <div className="final-panel-header">
          <div className="final-panel-header-row">
            <span>Final Markdown</span>
            <button
              type="button"
              className="btn-primary final-export-btn"
              onClick={onExport}
              disabled={exporting || !outputPath.trim()}
              title={outputPath ? `Export to ${outputPath}` : "No output path configured"}
            >
              {exporting ? "Exporting…" : "Export"}
            </button>
          </div>
          <div className="final-output-path">{outputPath || "No output file path configured"}</div>
          {exportStatus !== "idle" && (
            <div
              className={`final-export-status ${exportStatus === "error" ? "final-export-status-error" : "final-export-status-saved"}`}
            >
              {exportMessage}
            </div>
          )}
        </div>
        <div className="final-panel-body">
          <textarea
            className="final-markdown-textarea"
            value={content}
            readOnly
          />
        </div>
      </div>

      <div className="final-panel">
        <div className="final-panel-header">MkDocs Preview</div>
        <div className="final-panel-body">
          <PreviewIframe
            content={content}
            mkdocsRoot={mkdocsRoot}
            autoPreviewKey={autoPreviewKey}
          />
        </div>
      </div>
    </div>
  );
}
