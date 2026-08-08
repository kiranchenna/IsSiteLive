import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { type ActiveAlert, stopAlarm, subscribeAlarm } from "../lib/alarm";

export function AlertBanner() {
  const [alerts, setAlerts] = useState<ActiveAlert[]>([]);
  const navigate = useNavigate();

  useEffect(() => subscribeAlarm(setAlerts), []);

  if (alerts.length === 0) return null;

  const headline =
    alerts.length === 1
      ? `${alerts[0].siteName} is down`
      : `${alerts.length} sites are down`;

  return (
    <div
      role="alert"
      className="sticky inset-x-0 top-0 z-50 flex items-center gap-3 bg-down px-4 py-2.5 text-bg shadow-lg animate-brand-pulse"
    >
      <span className="text-lg leading-none">🔔</span>
      <button
        type="button"
        className="flex-1 truncate text-left text-[13px] font-semibold underline-offset-2 hover:underline"
        onClick={() => navigate(`/sites/${alerts[0].siteId}`)}
      >
        {headline}
        {alerts.length === 1 && alerts[0].summary ? ` — ${alerts[0].summary}` : ""}
      </button>
      <button
        type="button"
        className="shrink-0 rounded-md border border-bg/30 bg-bg/10 px-3 py-1.5 text-[13px] font-semibold text-bg hover:bg-bg/20"
        onClick={stopAlarm}
      >
        Stop sound
      </button>
    </div>
  );
}
