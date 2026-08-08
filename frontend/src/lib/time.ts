// The backend sends naive UTC timestamps with no offset suffix; without this,
// `new Date(iso)` would be parsed as local time and skew every displayed time.
function parseUtc(iso: string): Date {
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(iso);
  return new Date(hasOffset ? iso : `${iso}Z`);
}

export function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const diffMs = Date.now() - parseUtc(iso).getTime();
  const sec = Math.max(0, Math.floor(diffMs / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

export function timeUntil(iso: string | null): string {
  if (!iso) return "not scheduled";
  const diffMs = parseUtc(iso).getTime() - Date.now();
  const sec = Math.max(0, Math.floor(diffMs / 1000));
  if (sec < 60) return `in ${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `in ${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `in ${hr}h`;
  const day = Math.floor(hr / 24);
  return `in ${day}d`;
}

export function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatDateTime(iso: string): string {
  return parseUtc(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
