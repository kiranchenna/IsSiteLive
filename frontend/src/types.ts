export type RunStatus = "running" | "success" | "fail";
export type AlertChannelType = "slack" | "email" | "whatsapp";

export interface Site {
  id: number;
  name: string;
  base_url: string;
  is_active: boolean;
  check_interval_seconds: number;
  created_at: string;
  next_run_at: string | null;
}

export interface Account {
  id: number;
  site_id: number;
  label: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface FlowStep {
  type: string;
  [key: string]: unknown;
}

export interface Flow {
  id: number;
  site_id: number;
  steps_json: FlowStep[];
  watch_patterns_json: { pattern: string }[];
}

export interface AlertChannel {
  id: number;
  type: AlertChannelType;
  label: string;
  config_json: Record<string, unknown>;
  is_default: boolean;
  created_at: string;
}

export interface StepResult {
  id: number;
  step_index: number;
  step_type: string;
  status: RunStatus;
  http_status: number | null;
  message: string | null;
  screenshot_path: string | null;
}

export interface CheckRun {
  id: number;
  site_id: number;
  account_id: number;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_summary: string | null;
}

export interface CheckRunDetail extends CheckRun {
  step_results: StepResult[];
}

export interface SiteStatusAccount {
  account_id: number;
  label: string;
  last_status: RunStatus | "unknown";
  last_run_at: string | null;
  error_summary: string | null;
}

export interface SiteStatus {
  site_id: number;
  site_name: string;
  is_active: boolean;
  next_run_at: string | null;
  accounts: SiteStatusAccount[];
}
