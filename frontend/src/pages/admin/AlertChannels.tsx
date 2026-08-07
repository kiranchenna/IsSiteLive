import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { AlertChannel, AlertChannelType } from "../../types";

export function AlertChannelsPage() {
  const [channels, setChannels] = useState<AlertChannel[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = () => api.listAlertChannels().then(setChannels).catch((e) => setError(String(e)));

  useEffect(() => {
    reload();
  }, []);

  const remove = async (id: number) => {
    await api.deleteAlertChannel(id);
    reload();
  };

  const toggleDefault = async (channel: AlertChannel) => {
    await api.updateAlertChannel(channel.id, { is_default: !channel.is_default });
    reload();
  };

  return (
    <>
      <div className="row-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Alert channels</h1>
        <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add channel"}
        </button>
      </div>
      <p className="page-subtitle">
        Channels marked "default" notify any site that hasn't picked its own channels. WhatsApp support is coming later.
      </p>

      {error && <p className="error-text">{error}</p>}

      {showForm && (
        <NewChannelForm
          onCreated={() => {
            setShowForm(false);
            reload();
          }}
        />
      )}

      {!channels ? (
        <p className="text-muted">Loading…</p>
      ) : channels.length === 0 ? (
        <div className="empty-state">
          <h3>No alert channels yet</h3>
          <p>Add a Slack webhook or email recipients so failures actually reach someone.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Type</th>
                  <th>Destination</th>
                  <th>Default</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {channels.map((c) => (
                  <tr key={c.id}>
                    <td>{c.label}</td>
                    <td>
                      <span className="chip">{c.type}</span>
                    </td>
                    <td className="mono text-muted">{destinationSummary(c)}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => toggleDefault(c)}>
                        {c.is_default ? "Yes" : "No"}
                      </button>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(c.id)}>
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

function destinationSummary(c: AlertChannel): string {
  if (c.type === "slack") return String(c.config_json.webhook_url ?? "");
  if (c.type === "email") return (c.config_json.recipients as string[] | undefined)?.join(", ") ?? "";
  return "";
}

function NewChannelForm({ onCreated }: { onCreated: () => void }) {
  const [type, setType] = useState<AlertChannelType>("slack");
  const [label, setLabel] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [recipients, setRecipients] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const config_json =
        type === "slack"
          ? { webhook_url: webhookUrl }
          : { recipients: recipients.split(",").map((r) => r.trim()).filter(Boolean) };
      await api.createAlertChannel({ type, label, config_json, is_default: isDefault });
      onCreated();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit} style={{ maxWidth: 480 }}>
      <div className="field-row">
        <div className="field">
          <label>Type</label>
          <select value={type} onChange={(e) => setType(e.target.value as AlertChannelType)}>
            <option value="slack">Slack</option>
            <option value="email">Email</option>
          </select>
        </div>
        <div className="field">
          <label>Label</label>
          <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="team-slack" required />
        </div>
      </div>

      {type === "slack" ? (
        <div className="field">
          <label>Slack webhook URL</label>
          <input
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/…"
            required
          />
        </div>
      ) : (
        <div className="field">
          <label>Recipient emails (comma-separated)</label>
          <input
            type="text"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="ops@example.com, oncall@example.com"
            required
          />
        </div>
      )}

      <div className="checkbox-row" style={{ marginBottom: 14 }}>
        <input type="checkbox" id="is-default" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
        <label htmlFor="is-default">Use as default for sites without their own channels</label>
      </div>

      {error && <p className="error-text">{error}</p>}
      <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>
        {busy ? "Saving…" : "Save channel"}
      </button>
    </form>
  );
}
