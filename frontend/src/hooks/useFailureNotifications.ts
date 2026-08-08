import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { isEnabled, notifyFailure } from "../lib/notifications";

const POLL_INTERVAL_MS = 15000;

/**
 * Polls dashboard status and fires a browser notification the moment a NEW run resolves
 * as "fail" -- keyed off last_run_at per (site, account) so it fires once per real check
 * failure (matching the backend's "every failed run alerts" semantics), not once per poll,
 * and never floods notifications for failures that were already there before this loaded.
 */
export function useFailureNotifications(): void {
  const navigate = useNavigate();
  const lastSeen = useRef<Map<string, string>>(new Map());
  const seededBaseline = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const sites = await api.dashboardStatus();
        if (cancelled) return;

        for (const site of sites) {
          for (const account of site.accounts) {
            const key = `${site.site_id}-${account.account_id}`;
            const previous = lastSeen.current.get(key);
            if (account.last_run_at && account.last_run_at !== previous) {
              lastSeen.current.set(key, account.last_run_at);
              if (seededBaseline.current && account.last_status === "fail") {
                notifyFailure(site.site_id, account.account_id, site.site_name, account.label, account.error_summary, () =>
                  navigate(`/sites/${site.site_id}`)
                );
              }
            }
          }
        }
        seededBaseline.current = true;
      } catch {
        // a failed poll just tries again next interval; notifications are best-effort
      }
    };

    if (isEnabled()) poll();
    const interval = setInterval(() => {
      if (isEnabled()) poll();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
