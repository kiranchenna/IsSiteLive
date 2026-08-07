import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { Site } from "../../types";

export function SitesPage() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = () => api.listSites().then(setSites).catch((e) => setError(String(e)));

  useEffect(() => {
    reload();
  }, []);

  const remove = async (id: number) => {
    if (!confirm("Remove this site? Its accounts, flow, and run history will be deleted too.")) return;
    await api.deleteSite(id);
    reload();
  };

  return (
    <>
      <div className="row-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Sites</h1>
        <Link to="/sites/new" className="btn btn-primary">
          + Add site
        </Link>
      </div>
      <p className="page-subtitle">Manage what's being watched and how often.</p>

      {error && <p className="error-text">{error}</p>}

      {!sites ? (
        <p className="text-muted">Loading…</p>
      ) : sites.length === 0 ? (
        <div className="empty-state">
          <h3>No sites yet</h3>
          <p>Add one to start checking whether it's actually working end to end.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Interval</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sites.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link to={`/sites/${s.id}`}>{s.name}</Link>
                  </td>
                  <td className="mono text-muted">{s.base_url}</td>
                  <td className="mono">{formatInterval(s.check_interval_seconds)}</td>
                  <td>
                    <span className={`chip`}>{s.is_active ? "Monitored" : "Paused"}</span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(s.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </>
  );
}

function formatInterval(seconds: number): string {
  if (seconds % 3600 === 0) return `${seconds / 3600}h`;
  if (seconds % 60 === 0) return `${seconds / 60}m`;
  return `${seconds}s`;
}
