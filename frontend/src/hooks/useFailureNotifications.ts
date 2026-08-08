import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { isAlarmEnabled, raiseAlarm } from "../lib/alarm";
import { isEnabled, notifyFailure } from "../lib/notifications";

const POLL_INTERVAL_MS = 15000;
const STORAGE_KEY = "issitelive-last-seen-runs";

function loadLastSeen(): Map<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? new Map(Object.entries(JSON.parse(raw))) : new Map();
  } catch {
    return new Map();
  }
}

function saveLastSeen(map: Map<string, string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(map)));
  } catch {
    // ignore storage errors (e.g. private browsing quota)
  }
}

/**
 * Polls dashboard status and fires a browser notification the moment a NEW run resolves
 * as "fail" -- keyed off last_run_at + last_status per (site, account) so it fires once per
 * real check failure (matching the backend's "every failed run alerts" semantics), not once
 * per poll, and never floods notifications for failures that were already there before this
 * loaded.
 *
 * Status is part of the key, not just last_run_at, because last_run_at is the run's
 * started_at and never changes when it resolves -- a run that's still "running" during one
 * poll and has finished as "fail" by the next would otherwise look identical on the second
 * poll (same started_at) and the failure would be silently swallowed. This matters for any
 * check slow enough to be caught mid-flight by the 15s poll (a few seconds is fine; several
 * minutes, as with a real login timeout, reliably hits this).
 *
 * The seen-run map is persisted to localStorage (not just an in-memory ref) so a page
 * reload -- or just closing and reopening the tab -- doesn't silently reset the baseline
 * and swallow the very next failure as if it were nothing new. It also means a failure
 * that happened while the tab was closed is still reported once you come back.
 */
export function useFailureNotifications(): void {
  const navigate = useNavigate();
  const lastSeen = useRef<Map<string, string>>(loadLastSeen());
  const seededBaseline = useRef(lastSeen.current.size > 0);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const sites = await api.dashboardStatus();
        if (cancelled) return;

        let changed = false;
        for (const site of sites) {
          for (const account of site.accounts) {
            const key = `${site.site_id}-${account.account_id}`;
            const previous = lastSeen.current.get(key);
            const current = account.last_run_at ? `${account.last_run_at}|${account.last_status}` : null;
            if (current && current !== previous) {
              lastSeen.current.set(key, current);
              changed = true;
              if (seededBaseline.current && account.last_status === "fail") {
                notifyFailure(site.site_id, account.account_id, site.site_name, account.label, account.error_summary, () =>
                  navigate(`/sites/${site.site_id}`)
                );
                raiseAlarm({
                  key,
                  siteId: site.site_id,
                  siteName: site.site_name,
                  accountLabel: account.label,
                  summary: account.error_summary,
                });
              }
            }
          }
        }
        if (changed) saveLastSeen(lastSeen.current);
        seededBaseline.current = true;
      } catch {
        // a failed poll just tries again next interval; notifications are best-effort
      }
    };

    const shouldPoll = () => isEnabled() || isAlarmEnabled();

    if (shouldPoll()) poll();
    const interval = setInterval(() => {
      if (shouldPoll()) poll();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
