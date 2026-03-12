import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { AiLogDetail, AiLogSummary } from "../types/project";

interface Props {
  projectId: string;
}

function formatDate(iso: string): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return "-";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export default function AiLogsView({ projectId }: Props) {
  const [logs, setLogs] = useState<AiLogSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AiLogDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadList = useCallback(async (silent = false) => {
    if (!silent) {
      setLoadingList(true);
      setListError(null);
    }
    try {
      const next = await api.listAiLogs(projectId, 500);
      setLogs(next);
      setSelectedId((prev) => {
        if (prev && next.some((l) => l.id === prev)) return prev;
        return next[0]?.id ?? null;
      });
      if (!silent) {
        setListError(null);
      }
    } catch (e: any) {
      if (!silent) {
        setListError(e.message || "Failed to load AI logs");
        setLogs([]);
        setSelectedId(null);
      }
    } finally {
      if (!silent) {
        setLoadingList(false);
      }
    }
  }, [projectId]);

  useEffect(() => {
    loadList(false).catch(() => {});
  }, [loadList]);

  useEffect(() => {
    const timer = setInterval(() => {
      loadList(true).catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [loadList]);

  const loadDetail = useCallback(async (logId: string, silent = false) => {
    if (!silent) {
      setLoadingDetail(true);
      setDetailError(null);
    }
    try {
      const d = await api.getAiLog(projectId, logId);
      setDetail(d);
      if (!silent) {
        setDetailError(null);
      }
    } catch (e: any) {
      if (!silent) {
        setDetail(null);
        setDetailError(e.message || "Failed to load log detail");
      }
    } finally {
      if (!silent) {
        setLoadingDetail(false);
      }
    }
  }, [projectId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    loadDetail(selectedId, false).catch(() => {});
  }, [selectedId, loadDetail]);

  useEffect(() => {
    if (!selectedId) return;
    const timer = setInterval(() => {
      loadDetail(selectedId, true).catch(() => {});
    }, 2000);
    return () => clearInterval(timer);
  }, [selectedId, loadDetail]);

  const selectedSummary = useMemo(
    () => logs.find((l) => l.id === selectedId) ?? null,
    [logs, selectedId],
  );

  return (
    <div className="ai-logs-view">
      <div className="ai-logs-nav">
        <div className="ai-logs-nav-header">
          <span>AI Agent Logs</span>
          <button className="btn-secondary" onClick={() => loadList(false).catch(() => {})}>Refresh</button>
        </div>

        <div className="ai-logs-list">
          {loadingList && <div className="ai-logs-empty">Loading logs...</div>}
          {!loadingList && listError && <div className="ai-logs-error">{listError}</div>}
          {!loadingList && !listError && logs.length === 0 && (
            <div className="ai-logs-empty">No logs yet. Run Match/Generate/Prepare first.</div>
          )}
          {!loadingList && !listError && logs.map((log) => (
            <button
              key={log.id}
              className={`ai-log-item ${log.id === selectedId ? "ai-log-item-active" : ""}`}
              onClick={() => setSelectedId(log.id)}
            >
              <div className="ai-log-item-top">
                <span className="ai-log-item-run">{log.runType || "agent"}</span>
                <span className={`ai-log-item-status ai-log-item-status-${log.status || "unknown"}`}>
                  {log.status || "unknown"}
                </span>
              </div>
              <div className="ai-log-item-meta">
                {log.provider || "provider?"}
                {log.model ? ` • ${log.model}` : ""}
              </div>
              <div className="ai-log-item-meta">{formatDate(log.startedAt)}</div>
              {log.error && <div className="ai-log-item-error">{log.error}</div>}
            </button>
          ))}
        </div>
      </div>

      <div className="ai-logs-detail">
        <div className="ai-logs-detail-header">
          {selectedSummary ? `Log ${selectedSummary.id}` : "Log Details"}
        </div>
        <div className="ai-logs-detail-scroll">
          {!selectedId && <div className="ai-logs-empty">Select a log entry.</div>}
          {selectedId && loadingDetail && <div className="ai-logs-empty">Loading detail...</div>}
          {selectedId && !loadingDetail && detailError && <div className="ai-logs-error">{detailError}</div>}
          {selectedId && !loadingDetail && !detailError && detail && (
            <>
              <div className="ai-log-card">
                <div className="ai-log-meta-grid">
                  <div><strong>Run</strong>: {detail.runType || "agent"}</div>
                  <div><strong>Status</strong>: {detail.status || "-"}</div>
                  <div><strong>Provider</strong>: {detail.provider || "-"}</div>
                  <div><strong>Model</strong>: {detail.model || "(CLI default)"}</div>
                  <div><strong>Reasoning</strong>: {detail.reasoningEffort || "-"}</div>
                  <div><strong>Duration</strong>: {formatDuration(detail.durationMs)}</div>
                  <div><strong>Started</strong>: {formatDate(detail.startedAt)}</div>
                  <div><strong>Finished</strong>: {formatDate(detail.finishedAt)}</div>
                  <div className="ai-log-meta-full"><strong>CWD</strong>: {detail.cwd || "-"}</div>
                  <div className="ai-log-meta-full"><strong>Command</strong>: {(detail.command || []).join(" ") || "-"}</div>
                </div>
              </div>

              <div className="ai-log-card">
                <div className="ai-log-section-title">Prompt</div>
                <pre className="ai-log-code">{detail.prompt || ""}</pre>
              </div>

              <div className="ai-log-card">
                <div className="ai-log-section-title">STDOUT</div>
                <pre className="ai-log-code">{detail.stdout || ""}</pre>
              </div>

              <div className="ai-log-card">
                <div className="ai-log-section-title">STDERR</div>
                <pre className="ai-log-code">{detail.stderr || ""}</pre>
              </div>

              {detail.error && (
                <div className="ai-log-card ai-log-card-error">
                  <div className="ai-log-section-title">Error</div>
                  <pre className="ai-log-code">{detail.error}</pre>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
