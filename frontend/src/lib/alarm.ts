import { playAlertSound, SIREN_CYCLE_SECONDS } from "./notifications";

const STORAGE_KEY = "issitelive-alarm-enabled";
// Slightly under one full siren cycle so the next wail starts right as the last one fades,
// instead of leaving an audible gap of silence between repeats.
const LOOP_INTERVAL_MS = (SIREN_CYCLE_SECONDS - 0.05) * 1000;

export interface ActiveAlert {
  key: string;
  siteId: number;
  siteName: string;
  accountLabel: string;
  summary: string | null;
}

/** Default-on: absence of the key means "never touched the toggle," not "opted out." */
export function isAlarmEnabled(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== "false";
}

export function setAlarmEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
  if (!enabled) stopAlarm();
}

let activeAlerts: ActiveAlert[] = [];
let loopHandle: number | null = null;
const listeners = new Set<(alerts: ActiveAlert[]) => void>();

function emit(): void {
  for (const listener of listeners) listener(activeAlerts);
}

/** Subscribes to the current alert list; called immediately with the current value. */
export function subscribeAlarm(listener: (alerts: ActiveAlert[]) => void): () => void {
  listeners.add(listener);
  listener(activeAlerts);
  return () => listeners.delete(listener);
}

/**
 * Raises (or refreshes) an alarm for a failing site/account and starts the looping siren if
 * it isn't already running. The loop keeps playing -- across every subsequent failed poll --
 * until stopAlarm() is called, so it can't be missed by someone away from a background tab.
 */
export function raiseAlarm(alert: ActiveAlert): void {
  if (!isAlarmEnabled()) return;

  activeAlerts = [...activeAlerts.filter((a) => a.key !== alert.key), alert];
  emit();

  if (loopHandle === null) {
    playAlertSound();
    loopHandle = window.setInterval(playAlertSound, LOOP_INTERVAL_MS);
  }
}

/** Stops the siren and clears every active alert -- the sole job of the banner's "Stop" button. */
export function stopAlarm(): void {
  activeAlerts = [];
  emit();
  if (loopHandle !== null) {
    clearInterval(loopHandle);
    loopHandle = null;
  }
}
