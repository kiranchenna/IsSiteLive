export function StatusBadge({ state }: { state: "up" | "down" | "unknown" }) {
  const label = state === "up" ? "Up" : state === "down" ? "Down" : "No data";
  const cls = state === "up" ? "badge-up" : state === "down" ? "badge-down" : "badge-unknown";
  return <span className={`badge ${cls}`}>{label}</span>;
}
