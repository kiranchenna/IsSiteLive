import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PulseStrip } from "../components/PulseStrip";
import { StatusBadge } from "../components/StatusBadge";
import { timeAgo, timeUntil } from "../lib/time";
import type { SiteStatus } from "../types";

function siteState(site: SiteStatus): "up" | "down" | "checking" | "unknown" {
  if (site.accounts.length === 0) return "unknown";
  if (site.accounts.some((a) => a.last_status === "running")) return "checking";
  if (site.accounts.some((a) => a.last_status === "fail")) return "down";
  if (site.accounts.every((a) => a.last_status === "success")) return "up";
  return "unknown";
}

export function Dashboard() {
  const [sites, setSites] = useState<SiteStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const load = () => {
      api
        .dashboardStatus()
        .then((data) => {
          if (cancelled) return;
          setSites(data);
          const anyChecking = data.some((s) => s.accounts.some((a) => a.last_status === "running"));
          timer = setTimeout(load, anyChecking ? 3000 : 15000);
        })
        .catch((e) => {
          if (cancelled) return;
          setError(String(e));
          timer = setTimeout(load, 15000);
        });
    };
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  if (error) return <p className="error-text">{error}</p>;
  if (!sites) return <p className="text-muted">Loading…</p>;

  if (sites.length === 0) {
    return (
      <div className="empty-state">
        <h3>No sites being watched yet</h3>
        <p>Add a site and its login flow to start checking whether it's actually working.</p>
        <Link to="/sites/new" className="btn btn-primary" style={{ marginTop: 12, display: "inline-block" }}>
          Add a site
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="row-between" style={{ marginBottom: 28 }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle" style={{ margin: 0 }}>
            Live status across {sites.length} site{sites.length === 1 ? "" : "s"}
          </p>
        </div>
        <Link to="/sites/new" className="btn btn-primary">
          + Add site
        </Link>
      </div>

      <div className="site-grid">
        {sites.map((site) => {
          const state = siteState(site);
          const oldestRun = site.accounts
            .map((a) => a.last_run_at)
            .filter(Boolean)
            .sort()
            .pop();
          return (
            <Link to={`/sites/${site.site_id}`} key={site.site_id} className={`site-card ${state === "down" ? "is-down" : ""}`}>
              <div className="site-card-top">
                <div className="site-card-name">{site.site_name}</div>
                <StatusBadge state={state} />
              </div>
              <PulseStrip state={state} />
              <div className="site-card-meta">
                <span>
                  {site.accounts.length} account{site.accounts.length === 1 ? "" : "s"}
                </span>
                <span className="mono">{timeAgo(oldestRun ?? null)}</span>
              </div>
              <div className="text-faint mono" style={{ fontSize: 11, marginTop: 6 }}>
                Next check {timeUntil(site.next_run_at)}
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
