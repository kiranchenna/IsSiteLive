const STORAGE_KEY = "issitelive-notifications-enabled";

export function isSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function getPermission(): NotificationPermission | "unsupported" {
  return isSupported() ? Notification.permission : "unsupported";
}

export function isEnabled(): boolean {
  return isSupported() && Notification.permission === "granted" && localStorage.getItem(STORAGE_KEY) === "true";
}

export async function enableNotifications(): Promise<NotificationPermission | "unsupported"> {
  if (!isSupported()) return "unsupported";
  const permission = await Notification.requestPermission();
  localStorage.setItem(STORAGE_KEY, permission === "granted" ? "true" : "false");
  return permission;
}

export function disableNotifications(): void {
  localStorage.setItem(STORAGE_KEY, "false");
}

// A single, reused AudioContext -- browsers only let a *fresh* one start in the "running"
// state right after a real user gesture (like clicking "Enable notifications"). Creating a
// new one later, from a background timer when a failure is detected, would start suspended
// and silently produce no sound. Reusing one primed context sidesteps that entirely.
let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  try {
    if (!audioCtx) {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioCtx = new Ctor();
    }
    return audioCtx;
  } catch {
    return null;
  }
}

/** Call from a real click handler (e.g. the "Enable notifications" button) so the audio
 * context starts primed and ready, instead of only being created later from a timer. */
export function primeAlertSound(): void {
  const ctx = getAudioContext();
  if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
}

let unlockArmed = false;

/**
 * Primes the alert sound off the *first* click/keypress/tap anywhere on the page, not just
 * the "Enable notifications" button. Necessary because permission + the enabled flags persist
 * across reloads: if sound was already "on" from a previous visit, the page loads enabled but
 * no fresh click ever fires, so the AudioContext would otherwise stay uncreated (or suspended)
 * until the first real failure -- by which point there's no user gesture backing it, so
 * browsers refuse to ever let it play. Primes unconditionally (cheap, plays nothing by itself)
 * so it covers both the one-off notification sound and the looping failure alarm. Call once
 * at app startup.
 */
export function armAudioUnlock(): void {
  if (unlockArmed || typeof document === "undefined") return;
  unlockArmed = true;

  const unlock = () => primeAlertSound();

  document.addEventListener("pointerdown", unlock, { once: true, capture: true });
  document.addEventListener("keydown", unlock, { once: true, capture: true });

  // Some browsers auto-suspend a long-idle AudioContext to save power while the tab is
  // hidden; re-resume it whenever the tab regains focus so a failure detected while it was
  // backgrounded doesn't land on a silently-suspended context.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") primeAlertSound();
  });
}

/** How long one up-down siren wail takes, in seconds -- exported so the alarm loop can pace
 * its repeat interval to butt up against this with no audible silence in between. */
export const SIREN_CYCLE_SECONDS = 1.0;

/** Synthesizes a rising/falling siren wail (sawtooth sweep, like a real alarm) -- no external
 * sound file to source or license, and it plays regardless of the OS's per-app notification
 * sound settings, since it isn't routed through the OS notification system at all. */
export function playAlertSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === "suspended") ctx.resume().catch(() => {});

  const now = ctx.currentTime;
  const half = SIREN_CYCLE_SECONDS / 2;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sawtooth";

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.3, now + 0.06);
  gain.gain.setValueAtTime(0.3, now + SIREN_CYCLE_SECONDS - 0.08);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + SIREN_CYCLE_SECONDS);

  osc.frequency.setValueAtTime(520, now);
  osc.frequency.linearRampToValueAtTime(1046, now + half);
  osc.frequency.linearRampToValueAtTime(520, now + SIREN_CYCLE_SECONDS);

  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + SIREN_CYCLE_SECONDS + 0.05);
}

export function notifyFailure(
  siteId: number,
  accountId: number,
  siteName: string,
  accountLabel: string,
  summary: string | null,
  onClick: () => void
): void {
  if (!isEnabled()) return;

  playAlertSound();

  const notification = new Notification(`${siteName} is down`, {
    body: `${accountLabel}: ${summary ?? "Check failed"}`,
    tag: `issitelive-fail-${siteId}-${accountId}`,
    icon: "/favicon.svg",
  });
  notification.onclick = () => {
    window.focus();
    onClick();
    notification.close();
  };
}
