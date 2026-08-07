import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { API_BASE, api } from "../api/client";
import { formatDateTime, formatDuration } from "../lib/time";
import type { Account, AlertChannel, CheckRun, CheckRunDetail, Flow, Site } from "../types";

const DEFAULT_STEPS = [
  { type: "navigate", url: "https://example.com" },
  { type: "click", selector: "#sign-in" },
  { type: "fill", selector: "#username", value: "{{username}}" },
  { type: "fill", selector: "#password", value: "{{password}}" },
  { type: "click", selector: "#submit" },
  { type: "wait_for_selector", selector: "#dashboard", timeout_ms: 15000 },
  { type: "assert_selector_absent", selector: ".error-banner" },
];

const INTERVAL_PRESETS = [
  { label: "5 min", value: 300 },
  { label: "15 min", value: 900 },
  { label: "30 min", value: 1800 },
  { label: "1 hour", value: 3600 },
];

export function SiteDetail() {
  const params = useParams();
  const navigate = useNavigate();
  const isNew = params.id === "new";
  const siteId = isNew ? null : Number(params.id);

  if (isNew) return <NewSiteForm onCreated={(id) => navigate(`/sites/${id}`)} />;
  if (siteId) return <ExistingSite siteId={siteId} />;
  return null;
}

function NewSiteForm({ onCreated }: { onCreated: (id: number) => void }) {
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [interval, setInterval] = useState(300);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const site = await api.createSite({ name, base_url: baseUrl, check_interval_seconds: interval });
      onCreated(site.id);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="page-title">Add a site</h1>
      <p className="page-subtitle">You'll add the login flow and accounts next.</p>
      <form className="card" onSubmit={submit} style={{ maxWidth: 480 }}>
        <div className="field">
          <label>Site name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="TinyMedic" required />
        </div>
        <div className="field">
          <label>Base URL</label>
          <input
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://tinymedic.com"
            required
          />
        </div>
        <div className="field">
          <label>Check interval</label>
          <select value={interval} onChange={(e) => setInterval(Number(e.target.value))}>
            {INTERVAL_PRESETS.map((p) => (
              <option key={p.value} value={p.value}>
                Every {p.label}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create site"}
        </button>
      </form>
    </>
  );
}

function ExistingSite({ siteId }: { siteId: number }) {
  const [site, setSite] = useState<Site | null>(null);
  const [flow, setFlow] = useState<Flow | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [allChannels, setAllChannels] = useState<AlertChannel[]>([]);
  const [siteChannelIds, setSiteChannelIds] = useState<number[]>([]);
  const [runs, setRuns] = useState<CheckRun[]>([]);
  const [runningNow, setRunningNow] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reloadRuns = () => api.listRuns(siteId).then(setRuns).catch(() => {});

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.listSites().then((sites) => sites.find((s) => s.id === siteId) ?? null),
      api.getFlow(siteId).catch(() => null),
      api.listAccounts(siteId),
      api.listAlertChannels(),
      api.getSiteAlertChannels(siteId),
      api.listRuns(siteId),
    ])
      .then(([s, f, accs, channels, channelIds, r]) => {
        if (cancelled) return;
        setSite(s);
        setFlow(f);
        setAccounts(accs);
        setAllChannels(channels);
        setSiteChannelIds(channelIds);
        setRuns(r);
      })
      .catch((e) => !cancelled && setError(String(e)));

    const interval = setInterval(reloadRuns, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  if (error) return <p className="error-text">{error}</p>;
  if (!site) return <p className="text-muted">Loading…</p>;

  const runNow = async () => {
    setRunningNow(true);
    try {
      await api.runNow(siteId);
      setTimeout(reloadRuns, 3000);
    } finally {
      setRunningNow(false);
    }
  };

  return (
    <>
      <div className="row-between" style={{ marginBottom: 4 }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: 2 }}>
            {site.name}
          </h1>
          <p className="mono text-faint" style={{ margin: 0, fontSize: 12.5 }}>
            {site.base_url}
          </p>
        </div>
        <button className="btn btn-primary" onClick={runNow} disabled={runningNow}>
          {runningNow ? "Running…" : "Run now"}
        </button>
      </div>
      <p className="page-subtitle" />

      <div className="stack">
        <SiteSettingsCard site={site} onUpdated={setSite} />
        <AccountsCard siteId={siteId} accounts={accounts} onChange={setAccounts} />
        <FlowCard siteId={siteId} flow={flow} onSaved={setFlow} />
        <AlertChannelsCard siteId={siteId} allChannels={allChannels} initialSelected={siteChannelIds} />
        <RunHistoryCard runs={runs} />
      </div>
    </>
  );
}

function SiteSettingsCard({ site, onUpdated }: { site: Site; onUpdated: (s: Site) => void }) {
  const [interval, setInterval] = useState(site.check_interval_seconds);
  const [isActive, setIsActive] = useState(site.is_active);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.updateSite(site.id, { check_interval_seconds: interval, is_active: isActive });
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  };

  const dirty = interval !== site.check_interval_seconds || isActive !== site.is_active;

  return (
    <div className="card">
      <div className="card-header">
        <h3>Settings</h3>
      </div>
      <div className="field-row">
        <div className="field">
          <label>Check interval</label>
          <select value={interval} onChange={(e) => setInterval(Number(e.target.value))}>
            {INTERVAL_PRESETS.map((p) => (
              <option key={p.value} value={p.value}>
                Every {p.label}
              </option>
            ))}
            {!INTERVAL_PRESETS.some((p) => p.value === interval) && (
              <option value={interval}>Every {interval}s (custom)</option>
            )}
          </select>
        </div>
        <div className="field">
          <label>&nbsp;</label>
          <div className="checkbox-row" style={{ marginTop: 8 }}>
            <input
              type="checkbox"
              id="active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <label htmlFor="active">Actively monitored</label>
          </div>
        </div>
      </div>
      {dirty && (
        <button className="btn btn-sm" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
      )}
    </div>
  );
}

function AccountsCard({
  siteId,
  accounts,
  onChange,
}: {
  siteId: number;
  accounts: Account[];
  onChange: (a: Account[]) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const account = await api.createAccount(siteId, { label, username, password });
      onChange([...accounts, account]);
      setLabel("");
      setUsername("");
      setPassword("");
      setShowForm(false);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    await api.deleteAccount(id);
    onChange(accounts.filter((a) => a.id !== id));
  };

  const toggleActive = async (account: Account) => {
    const updated = await api.updateAccount(account.id, { is_active: !account.is_active });
    onChange(accounts.map((a) => (a.id === account.id ? updated : a)));
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3>Demo accounts ({accounts.length})</h3>
        <button className="btn btn-sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add account"}
        </button>
      </div>

      {accounts.length === 0 && !showForm && (
        <p className="text-muted" style={{ margin: 0 }}>
          No accounts yet — add a demo login so checks can exercise the real sign-in flow.
        </p>
      )}

      {accounts.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Username</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td>{a.label}</td>
                  <td className="mono">{a.username}</td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => toggleActive(a)}>
                      {a.is_active ? "Active" : "Paused"}
                    </button>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(a.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <form onSubmit={add} style={{ marginTop: accounts.length ? 16 : 0 }}>
          <div className="field-row">
            <div className="field">
              <label>Label</label>
              <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="demo-readonly" required />
            </div>
            <div className="field">
              <label>Username</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div className="field">
              <label>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
          </div>
          <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save account"}
          </button>
        </form>
      )}
    </div>
  );
}

function FlowCard({ siteId, flow, onSaved }: { siteId: number; flow: Flow | null; onSaved: (f: Flow) => void }) {
  const [stepsText, setStepsText] = useState(
    JSON.stringify(flow?.steps_json ?? DEFAULT_STEPS, null, 2)
  );
  const [watchText, setWatchText] = useState(
    JSON.stringify(flow?.watch_patterns_json ?? [{ pattern: "*/api/*" }], null, 2)
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setError(null);
    let steps, watch;
    try {
      steps = JSON.parse(stepsText);
      watch = JSON.parse(watchText);
    } catch {
      setError("Steps and watch patterns must be valid JSON.");
      return;
    }
    setSaving(true);
    try {
      const saved = await api.upsertFlow(siteId, { steps_json: steps, watch_patterns_json: watch });
      onSaved(saved);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3>Login flow</h3>
      </div>
      <p className="text-muted" style={{ marginTop: -6, marginBottom: 14 }}>
        Steps run in order against a headless browser. Use <code className="mono">{"{{username}}"}</code> and{" "}
        <code className="mono">{"{{password}}"}</code> in <code className="mono">fill</code> steps.
      </p>
      <div className="field">
        <label>Steps (JSON)</label>
        <textarea rows={12} value={stepsText} onChange={(e) => setStepsText(e.target.value)} />
      </div>
      <div className="field">
        <label>AJAX URL patterns to watch for 4xx/5xx responses</label>
        <textarea rows={3} value={watchText} onChange={(e) => setWatchText(e.target.value)} />
      </div>
      {error && <p className="error-text">{error}</p>}
      <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
        {saving ? "Saving…" : "Save flow"}
      </button>
    </div>
  );
}

function AlertChannelsCard({
  siteId,
  allChannels,
  initialSelected,
}: {
  siteId: number;
  allChannels: AlertChannel[];
  initialSelected: number[];
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set(initialSelected));
  const [useDefaults, setUseDefaults] = useState(initialSelected.length === 0);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSelected(new Set(initialSelected));
    setUseDefaults(initialSelected.length === 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSelected.join(",")]);

  const toggle = (id: number) => {
    setUseDefaults(false);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.setSiteAlertChannels(siteId, useDefaults ? [] : Array.from(selected));
    } finally {
      setSaving(false);
    }
  };

  const defaults = allChannels.filter((c) => c.is_default);

  return (
    <div className="card">
      <div className="card-header">
        <h3>Alerts</h3>
      </div>
      <div className="checkbox-row" style={{ marginBottom: 12 }}>
        <input
          type="checkbox"
          id="use-defaults"
          checked={useDefaults}
          onChange={(e) => setUseDefaults(e.target.checked)}
        />
        <label htmlFor="use-defaults">
          Use default channels
          {defaults.length > 0 && (
            <span className="text-faint"> ({defaults.map((c) => c.label).join(", ")})</span>
          )}
        </label>
      </div>

      {!useDefaults && (
        <div className="stack" style={{ gap: 8, marginBottom: 12 }}>
          {allChannels.length === 0 && (
            <p className="text-muted" style={{ margin: 0 }}>
              No alert channels configured yet. Add one under Alert Channels.
            </p>
          )}
          {allChannels.map((c) => (
            <div className="checkbox-row" key={c.id}>
              <input type="checkbox" id={`ch-${c.id}`} checked={selected.has(c.id)} onChange={() => toggle(c.id)} />
              <label htmlFor={`ch-${c.id}`}>
                {c.label} <span className="chip">{c.type}</span>
              </label>
            </div>
          ))}
        </div>
      )}

      <button className="btn btn-sm" onClick={save} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </button>
    </div>
  );
}

function RunHistoryCard({ runs }: { runs: CheckRun[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<CheckRunDetail | null>(null);

  const toggle = async (run: CheckRun) => {
    if (expandedId === run.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(run.id);
    setDetail(null);
    const d = await api.getRun(run.id);
    setDetail(d);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3>Run history</h3>
      </div>
      {runs.length === 0 && <p className="text-muted">No checks have run yet.</p>}
      <div>
        {runs.map((run) => (
          <div key={run.id}>
            <div className={`run-row ${expandedId === run.id ? "expanded" : ""}`} onClick={() => toggle(run)}>
              <span className={`run-dot ${run.status === "success" ? "up" : "down"}`} />
              <span className="run-time">{formatDateTime(run.started_at)}</span>
              <span className="run-summary">{run.status === "success" ? "Passed" : run.error_summary ?? "Failed"}</span>
              <span className="run-duration">{formatDuration(run.duration_ms)}</span>
            </div>
            {expandedId === run.id && (
              <div className="run-detail">
                {!detail ? (
                  <p className="text-muted">Loading…</p>
                ) : (
                  <>
                    {detail.step_results.map((s) => (
                      <div key={s.id} className={`step-line ${s.status}`}>
                        <span className="mono">{s.step_index}</span>
                        <span>{s.step_type}</span>
                        {s.http_status && <span className="mono">HTTP {s.http_status}</span>}
                        {s.message && <span className="text-muted">{s.message}</span>}
                      </div>
                    ))}
                    {detail.step_results.some((s) => s.screenshot_path) && (
                      <a
                        className="screenshot-link"
                        href={`${API_BASE}${detail.step_results.find((s) => s.screenshot_path)?.screenshot_path}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View screenshot
                      </a>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
