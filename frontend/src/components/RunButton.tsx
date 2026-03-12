import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";
import type { Project } from "../types/project";

interface Props {
  projectId: string;
  action: "match" | "generate" | "edit" | "sync-map" | "sync-map-all";
  label: string;
  activeJobId?: string | null;
  userPrompt?: string;
  itemId?: string;
  editTarget?: "excerpt" | "document";
  editContent?: string;
  onJobStart?: (jobId: string) => void;
  onJobFinish?: () => void;
  disabled?: boolean;
  /** If provided, called instead of starting the job internally. Parent handles dispatch. */
  onRun?: () => void;
  onDone: (updatedProject: Project) => void;
}

export default function RunButton({
  projectId, action, label,
  activeJobId, userPrompt, itemId,
  editTarget, editContent,
  onJobStart, onJobFinish, disabled = false,
  onRun, onDone,
}: Props) {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;
  const activeJobIdRef = useRef(activeJobId);
  activeJobIdRef.current = activeJobId;

  function startPolling(jobId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const job = await api.pollJob(jobId);
        if (job.status === "done") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setStatus("done");
          const updated = await api.getProject(projectId);
          onDoneRef.current(updated);
          onJobFinish?.();
          setTimeout(() => setStatus("idle"), 2000);
        } else if (job.status === "error") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setStatus("error");
          setError(job.error || "Unknown error");
          onJobFinish?.();
        }
      } catch (e: any) {
        const msg = String(e?.message || "");
        if (msg.includes("HTTP 404") && msg.includes("Job not found")) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          try {
            const updated = await api.getProject(projectId);
            onDoneRef.current(updated);
          } catch {
            // Ignore refresh failure; primary goal is to stop stale polling loop.
          }
          setStatus("idle");
          onJobFinish?.();
          return;
        }
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setStatus("error");
        setError(e.message);
        onJobFinish?.();
      }
    }, 3000);
  }

  // When the item changes, reset local state and re-sync with whatever job is active for the new item.
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setError(null);
    const jobId = activeJobIdRef.current;
    if (jobId) {
      setStatus("running");
      startPolling(jobId);
    } else {
      setStatus("idle");
    }
  }, [itemId]);

  // When a job starts or finishes for the current item, sync status.
  useEffect(() => {
    if (activeJobId && status !== "running") {
      setStatus("running");
      startPolling(activeJobId);
    }
  }, [activeJobId]);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  async function run() {
    if (disabled) return;
    if (onRun) {
      setError(null);
      onRun();
      return;
    }
    setStatus("running");
    setError(null);
    try {
      let job_id = "";
      if (action === "match") {
        const opts = { userPrompt: userPrompt || undefined, itemId: itemId || undefined };
        ({ job_id } = await api.startMatch(projectId, opts));
      } else if (action === "generate") {
        const opts = { userPrompt: userPrompt || undefined, itemId: itemId || undefined };
        ({ job_id } = await api.startGenerate(projectId, opts));
      } else if (action === "sync-map") {
        if (!itemId) throw new Error("sync-map requires itemId");
        ({ job_id } = await api.syncMap(projectId, itemId));
      } else if (action === "sync-map-all") {
        ({ job_id } = await api.syncMapAll(projectId));
      } else {
        if (!itemId) throw new Error("Edit requires itemId");
        ({ job_id } = await api.startEdit(projectId, {
          userPrompt: userPrompt || undefined,
          itemId,
          target: editTarget || "excerpt",
          content: editContent,
        }));
      }
      onJobStart?.(job_id);
      startPolling(job_id);
    } catch (e: any) {
      setStatus("error");
      setError(e.message);
    }
  }

  return (
    <span>
      <button
        onClick={run}
        disabled={disabled || status === "running"}
        className={status === "error" ? "btn-danger" : "btn-primary"}
      >
        {status === "running"
          ? action === "match" ? "Matching…" : action === "generate" ? "Generating…" : (action === "sync-map" || action === "sync-map-all") ? "Syncing…" : "Editing…"
          : status === "done" ? "Done ✓" : label}
      </button>
      {error && <span style={{ color: "red", fontSize: 12, marginLeft: 8 }}>{error}</span>}
    </span>
  );
}
