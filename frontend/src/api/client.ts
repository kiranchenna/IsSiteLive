import type {
  Account,
  AlertChannel,
  CheckRunDetail,
  Flow,
  PaginatedRuns,
  Site,
  SiteStatus,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:28743";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // sites
  listSites: () => request<Site[]>("/api/sites"),
  createSite: (data: Partial<Site>) =>
    request<Site>("/api/sites", { method: "POST", body: JSON.stringify(data) }),
  updateSite: (id: number, data: Partial<Site>) =>
    request<Site>(`/api/sites/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSite: (id: number) => request<void>(`/api/sites/${id}`, { method: "DELETE" }),
  runNow: (id: number) => request<{ status: string }>(`/api/sites/${id}/run-now`, { method: "POST" }),

  // flow
  getFlow: (siteId: number) => request<Flow>(`/api/sites/${siteId}/flow`),
  upsertFlow: (siteId: number, data: { steps_json: unknown[]; watch_patterns_json: unknown[] }) =>
    request<Flow>(`/api/sites/${siteId}/flow`, { method: "PUT", body: JSON.stringify(data) }),

  // accounts
  listAccounts: (siteId: number) => request<Account[]>(`/api/sites/${siteId}/accounts`),
  createAccount: (siteId: number, data: { label: string; username: string; password: string }) =>
    request<Account>(`/api/sites/${siteId}/accounts`, { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id: number, data: Partial<Account> & { password?: string }) =>
    request<Account>(`/api/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAccount: (id: number) => request<void>(`/api/accounts/${id}`, { method: "DELETE" }),

  // alert channels
  listAlertChannels: () => request<AlertChannel[]>("/api/alert-channels"),
  createAlertChannel: (data: Partial<AlertChannel>) =>
    request<AlertChannel>("/api/alert-channels", { method: "POST", body: JSON.stringify(data) }),
  updateAlertChannel: (id: number, data: Partial<AlertChannel>) =>
    request<AlertChannel>(`/api/alert-channels/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAlertChannel: (id: number) => request<void>(`/api/alert-channels/${id}`, { method: "DELETE" }),
  getSiteAlertChannels: (siteId: number) => request<number[]>(`/api/sites/${siteId}/alert-channels`),
  setSiteAlertChannels: (siteId: number, alertChannelIds: number[]) =>
    request<void>(`/api/sites/${siteId}/alert-channels`, {
      method: "PUT",
      body: JSON.stringify({ alert_channel_ids: alertChannelIds }),
    }),

  // runs
  listRuns: (siteId: number, limit = 50, offset = 0) =>
    request<PaginatedRuns>(`/api/sites/${siteId}/runs?limit=${limit}&offset=${offset}`),
  getRun: (id: number) => request<CheckRunDetail>(`/api/runs/${id}`),
  dashboardStatus: () => request<SiteStatus[]>("/api/dashboard/status"),

  // flow recording
  startRecording: (siteId: number, accountId: number) =>
    request<{ session_id: string }>(`/api/sites/${siteId}/recordings`, {
      method: "POST",
      body: JSON.stringify({ account_id: accountId }),
    }),
  getRecordingSteps: (sessionId: string) =>
    request<{ steps: Record<string, unknown>[] }>(`/api/recordings/${sessionId}/steps`),
  stopRecording: (sessionId: string) =>
    request<void>(`/api/recordings/${sessionId}`, { method: "DELETE" }),
};

export { BASE as API_BASE };
export const WS_BASE = BASE.replace(/^http/, "ws");
