const LABELS = { up: "Up", down: "Down", checking: "Checking", unknown: "No data" } as const;
const CLASSES = { up: "badge-up", down: "badge-down", checking: "badge-checking", unknown: "badge-unknown" } as const;

export function StatusBadge({ state }: { state: "up" | "down" | "checking" | "unknown" }) {
  return <span className={`badge ${CLASSES[state]}`}>{LABELS[state]}</span>;
}
