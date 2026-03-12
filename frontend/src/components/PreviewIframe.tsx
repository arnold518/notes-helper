import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

interface Props {
  content: string;
  mkdocsRoot: string;
  outputPath?: string;
  autoPreviewKey?: number;
}

export default function PreviewIframe({ content, mkdocsRoot, outputPath, autoPreviewKey = 0 }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.preview(content, mkdocsRoot, outputPath);
      const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:7999";
      setUrl(`${apiBase}${res.url}?t=${Date.now()}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [content, mkdocsRoot, outputPath]);

  useEffect(() => {
    if (autoPreviewKey <= 0) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.preview(content, mkdocsRoot, outputPath);
        if (cancelled) return;
        const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:7999";
        setUrl(`${apiBase}${res.url}?t=${Date.now()}`);
      } catch (e: any) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [autoPreviewKey]);

  return (
    <div style={{ position: "relative", flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
      <button
        onClick={handlePreview}
        disabled={loading}
        className="btn-secondary"
        style={{ position: "absolute", top: 8, right: 8, zIndex: 10 }}
      >
        {loading ? "Building…" : "Preview"}
      </button>
      {error && <p style={{ color: "red", fontSize: 12, margin: "4px 0" }}>{error}</p>}
      {url ? (
        <iframe
          src={url}
          style={{ flex: 1, width: "100%", border: "none", background: "#fff" }}
          title="MkDocs Preview"
        />
      ) : (
        <div className="no-selection">Click Preview to render the document</div>
      )}
    </div>
  );
}
