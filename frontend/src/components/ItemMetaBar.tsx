import { useState, useEffect, useRef } from "react";
import type React from "react";
import { api } from "../api/client";
import type { Item, Project } from "../types/project";

type SaveStatus = "saved" | "unsaved" | "saving";

interface Props {
  item: Item | null;
  project: Project;
  numberPrefix: string;
  onUpdate: (patch: Partial<Item>) => void;
  onSaveStatusChange?: (s: SaveStatus) => void;
  flushRef?: React.MutableRefObject<(() => void) | null>;
}

interface AdmonitionType {
  type: string;
  color: string;
}

function encodeKindType(kind: string, type: string): string {
  return `${kind}:${type}`;
}

function decodeKindType(value: string): { kind: Item["kind"]; type: string } {
  const colon = value.indexOf(":");
  return {
    kind: value.slice(0, colon) as Item["kind"],
    type: value.slice(colon + 1),
  };
}

export default function ItemMetaBar({ item, project, numberPrefix, onUpdate, onSaveStatusChange, flushRef }: Props) {
  const [admonitionTypes, setAdmonitionTypes] = useState<AdmonitionType[]>([]);
  const [content, setContent] = useState(item?.content ?? "");
  const [localNumber, setLocalNumber] = useState(item?.number ?? 0);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const numberTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch admonition types from mkdocs root
  useEffect(() => {
    if (!project.mkdocsRoot) return;
    api.getMkdocsConfig(project.mkdocsRoot)
      .then(setAdmonitionTypes)
      .catch(() => setAdmonitionTypes([]));
  }, [project.mkdocsRoot]);

  // Sync local state when selected item changes
  useEffect(() => {
    setContent(item?.content ?? "");
    setLocalNumber(item?.number ?? 0);
  }, [item?.id]);

  // Sync localNumber when autonumber is re-enabled (backend may have assigned a new number)
  useEffect(() => {
    if (item?.autonumber) setLocalNumber(item.number);
  }, [item?.autonumber, item?.number]);

  function handleKindTypeChange(value: string) {
    if (!item) return;
    onUpdate(decodeKindType(value));
  }

  function flush() {
    const patch: Partial<Item> = {};
    if (saveTimer.current) {
      clearTimeout(saveTimer.current);
      saveTimer.current = null;
      patch.content = content;
    }
    if (numberTimer.current) {
      clearTimeout(numberTimer.current);
      numberTimer.current = null;
      patch.number = localNumber;
    }
    if (Object.keys(patch).length > 0) onUpdate(patch);
  }

  useEffect(() => {
    if (flushRef) flushRef.current = flush;
    return () => { if (flushRef) flushRef.current = null; };
  });

  function handleContentChange(val: string) {
    setContent(val);
    onSaveStatusChange?.("unsaved");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      onUpdate({ content: val });
    }, 600);
  }

  if (!item) {
    return <div className="item-meta-bar item-meta-bar-empty">No item selected</div>;
  }

  const currentValue = encodeKindType(item.kind, item.type);

  return (
    <div className="item-meta-bar">
      {item.kind === "admonition" && (
        <>
          <button
            className={`meta-autonumber-btn${item.autonumber ? " meta-autonumber-on" : ""}`}
            title={item.autonumber ? "Autonumber on — click to set manually" : "Manual number — click to autonumber"}
            onClick={() => onUpdate({ autonumber: !item.autonumber })}
          >auto</button>
          {item.autonumber ? (
            <span className="meta-number-badge">
              {numberPrefix ? `${numberPrefix}.${item.number}` : String(item.number)}
            </span>
          ) : (
            <input
              className="meta-number-input"
              type="number"
              min={0}
              value={localNumber}
              onChange={(e) => {
                const n = parseInt(e.target.value, 10) || 0;
                setLocalNumber(n);
                onSaveStatusChange?.("unsaved");
                if (numberTimer.current) clearTimeout(numberTimer.current);
                numberTimer.current = setTimeout(() => onUpdate({ number: n }), 600);
              }}
            />
          )}
        </>
      )}
      <button
        className={`meta-approve-btn${item.status === "approved" ? " meta-approve-btn-on" : ""}`}
        title={item.status === "approved" ? "Approved — click to unapprove" : "Click to approve"}
        onClick={() => onUpdate({ status: item.status === "approved" ? "pending" : "approved" })}
      >{item.status === "approved" ? "✓ approved" : "approve"}</button>
      <select
        className="meta-type-select"
        value={currentValue}
        onChange={(e) => handleKindTypeChange(e.target.value)}
      >
        <optgroup label="Section">
          <option value="section:h1"># Heading 1</option>
          <option value="section:h2">## Heading 2</option>
          <option value="section:h3">### Heading 3</option>
        </optgroup>
        <optgroup label="Text">
          <option value="text:">Plain text</option>
        </optgroup>
        {admonitionTypes.length > 0 && (
          <optgroup label="Admonition">
            {admonitionTypes.map((a) => (
              <option key={a.type} value={`admonition:${a.type}`}>
                {a.type}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <input
        className="meta-content-input"
        type="text"
        value={content}
        onChange={(e) => handleContentChange(e.target.value)}
        placeholder="Entry description…"
      />
    </div>
  );
}
