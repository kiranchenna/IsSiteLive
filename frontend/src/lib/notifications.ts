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

export function notifyFailure(
  siteId: number,
  accountId: number,
  siteName: string,
  accountLabel: string,
  summary: string | null,
  onClick: () => void
): void {
  if (!isEnabled()) return;
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
