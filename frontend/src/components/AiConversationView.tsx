import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { AiConversationMessage, AiConversationThread } from "../types/project";

interface Props {
  projectId: string;
  onProjectMaybeChanged?: () => void;
}

function formatDate(iso: string): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function findRunningJobId(thread: AiConversationThread | null): string | null {
  if (!thread) return null;
  for (let index = thread.messages.length - 1; index >= 0; index -= 1) {
    const message = thread.messages[index];
    if (message.role === "assistant" && message.status === "running" && message.jobId) {
      return message.jobId;
    }
  }
  return null;
}

export default function AiConversationView({ projectId, onProjectMaybeChanged }: Props) {
  const [thread, setThread] = useState<AiConversationThread | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const loadThread = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
      setError(null);
    }
    try {
      const next = await api.getAiConversation(projectId);
      setThread(next);
      setActiveJobId(findRunningJobId(next));
      if (!silent) {
        setError(null);
      }
    } catch (e: any) {
      if (!silent) {
        setError(e.message || "Failed to load AI conversation");
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [projectId]);

  useEffect(() => {
    loadThread(false).catch(() => {});
  }, [loadThread]);

  useEffect(() => {
    const timer = setInterval(() => {
      loadThread(true).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [loadThread]);

  useEffect(() => {
    if (!activeJobId) return;
    const timer = setInterval(async () => {
      try {
        const job = await api.pollJob(activeJobId);
        if (job.status === "done" || job.status === "error") {
          setActiveJobId(null);
          await loadThread(false);
          onProjectMaybeChanged?.();
        }
      } catch {
        setActiveJobId(null);
        await loadThread(false);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [activeJobId, loadThread, onProjectMaybeChanged]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread?.messages.length]);

  const hasRunningMessage = useMemo(
    () => thread?.messages.some((entry) => entry.role === "assistant" && entry.status === "running") ?? false,
    [thread],
  );

  async function handleSubmit() {
    const trimmed = message.trim();
    if (!trimmed || submitting || hasRunningMessage) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.startAiCommand(projectId, { message: trimmed });
      setMessage("");
      setActiveJobId(result.job_id);
      await loadThread(false);
    } catch (e: any) {
      setError(e.message || "Failed to start AI command");
    } finally {
      setSubmitting(false);
    }
  }

  function renderMessage(entry: AiConversationMessage) {
    return (
      <div
        key={entry.id}
        className={`ai-chat-message ai-chat-message-${entry.role} ai-chat-message-${entry.status}`}
      >
        <div className="ai-chat-message-top">
          <span className="ai-chat-message-role">{entry.role === "user" ? "You" : "AI"}</span>
          <span className={`ai-chat-message-status ai-chat-message-status-${entry.status}`}>
            {entry.status}
          </span>
          <span className="ai-chat-message-time">{formatDate(entry.updatedAt || entry.createdAt)}</span>
        </div>
        <div className="ai-chat-message-body">
          {entry.content || (entry.status === "running" ? "Working…" : "(empty)")}
        </div>
        {entry.changedFiles.length > 0 && (
          <div className="ai-chat-message-files">
            <div className="ai-chat-message-files-title">Changed files</div>
            <div className="ai-chat-message-files-list">
              {entry.changedFiles.map((path) => (
                <code key={path} className="ai-chat-file-chip">{path}</code>
              ))}
            </div>
          </div>
        )}
        {entry.error && (
          <div className="ai-chat-message-error-text">{entry.error}</div>
        )}
      </div>
    );
  }

  return (
    <div className="ai-chat-view">
      <div className="ai-chat-header">
        <span>AI Conversation</span>
        <button className="btn-secondary" onClick={() => loadThread(false).catch(() => {})}>Refresh</button>
      </div>

      <div className="ai-chat-scroll">
        {loading && <div className="ai-logs-empty">Loading conversation...</div>}
        {!loading && error && <div className="ai-logs-error">{error}</div>}
        {!loading && !error && (!thread || thread.messages.length === 0) && (
          <div className="ai-logs-empty">No conversation yet. Ask the AI to inspect or edit the project.</div>
        )}
        {!loading && !error && thread && thread.messages.map(renderMessage)}
        <div ref={endRef} />
      </div>

      <div className="ai-chat-composer">
        <textarea
          className="prompt-textarea ai-chat-textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask the AI to inspect, explain, or edit project files…"
          rows={4}
          disabled={submitting || hasRunningMessage}
        />
        <div className="ai-chat-composer-actions">
          <div className="ai-chat-composer-hint">
            {hasRunningMessage ? "One AI command is still running." : "The AI can inspect and edit project files."}
          </div>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={!message.trim() || submitting || hasRunningMessage}
          >
            {submitting ? "Starting…" : "Run AI Command"}
          </button>
        </div>
      </div>
    </div>
  );
}
