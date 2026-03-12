import type { Item, EntryStatus } from "../types/project";

const STATUS_COLORS: Record<EntryStatus, string> = {
  pending: "#555",
  matched: "#1565C0",
  generated: "#6A1B9A",
  approved: "#2E7D32",
};

interface Props {
  items: Item[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onInsertAfter: (afterId: string) => void;
  onDelete: (id: string) => void;
  numberPrefix: string;
  syncedNumberPrefix: string;
  mappingPath: string;
}

export default function NavPanel({ items, selectedId, onSelect, onInsertAfter, onDelete, numberPrefix, syncedNumberPrefix, mappingPath }: Props) {
  // Group items into sections (section item + following non-section items)
  const groups: Array<{ section: Item | null; children: Item[] }> = [];
  let current: { section: Item | null; children: Item[] } = { section: null, children: [] };

  for (const item of items) {
    if (item.kind === "section") {
      if (current.section !== null || current.children.length > 0) {
        groups.push(current);
      }
      current = { section: item, children: [] };
    } else {
      current.children.push(item);
    }
  }
  groups.push(current);

  function renderChip(item: Item) {
    const isActive = selectedId === item.id;
    const borderColor = STATUS_COLORS[item.status];
    const isUnsynced = !!mappingPath && !!item.excerpt && (
      item.excerpt !== item.syncedExcerpt ||
      item.number !== item.syncedNumber ||
      numberPrefix !== syncedNumberPrefix
    );

    return (
      <div key={item.id} className="nav-chip-row">
        <span
          className={`nav-chip${isActive ? " nav-chip-active" : ""}${item.kind === "section" ? " nav-chip-section" : ""}`}
          style={borderColor && !isActive ? { borderColor } : undefined}
          onClick={() => onSelect(item.id)}
          title={item.content}
        >
          {item.kind === "admonition" && (
            <span className="nav-chip-type">
              {numberPrefix ? `${item.type} ${numberPrefix}.${item.number}` : `${item.type} ${item.number}`}
            </span>
          )}
          {item.kind === "section" && (
            <span className="nav-chip-type">{item.type}</span>
          )}
          <span className="nav-chip-label">{
            item.kind === "admonition"
              ? item.content.slice(0, 20)
              : item.kind === "section"
              ? item.content
              : item.content.slice(0, 24)
          }</span>
          {item.status === "approved" && (
            <span style={{ color: STATUS_COLORS.approved }}> ●</span>
          )}
          {isUnsynced && (
            <span style={{ color: "#c62828" }} title="Map unsynced"> ●</span>
          )}
        </span>
        <div className="nav-chip-actions">
          <button
            className="nav-action-btn"
            title="Insert item after"
            onClick={(e) => { e.stopPropagation(); onInsertAfter(item.id); }}
          >+</button>
          <button
            className="nav-action-btn nav-action-del"
            title="Delete item"
            onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
          >×</button>
        </div>
      </div>
    );
  }

  return (
    <div className="nav-panel">
      {groups.map((group, gi) => (
        <div key={gi} className="nav-section">
          {group.section && renderChip(group.section)}
          <div className="nav-chips">
            {group.children.map((item) => renderChip(item))}
          </div>
        </div>
      ))}
    </div>
  );
}
