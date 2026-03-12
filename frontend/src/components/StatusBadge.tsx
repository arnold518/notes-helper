import type { EntryStatus } from "../types/project";

const STATUS_COLORS: Record<EntryStatus, string> = {
  pending: "#888",
  matched: "#2196F3",
  generated: "#9C27B0",
  approved: "#4CAF50",
};

const STATUS_LABELS: Record<EntryStatus, string> = {
  pending: "pending",
  matched: "matched",
  generated: "generated",
  approved: "approved ✓",
};

interface Props {
  status: EntryStatus;
}

export default function StatusBadge({ status }: Props) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        background: STATUS_COLORS[status],
        color: "#fff",
        letterSpacing: "0.02em",
      }}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
