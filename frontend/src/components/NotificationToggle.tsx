import { useState } from "react";
import { disableNotifications, enableNotifications, getPermission, isEnabled } from "../lib/notifications";

export function NotificationToggle() {
  const [permission, setPermission] = useState(getPermission());
  const [enabled, setEnabled] = useState(isEnabled());

  if (permission === "unsupported") return null;

  if (permission === "denied") {
    return (
      <span className="chip" title="Blocked in your browser's site settings">
        Notifications blocked
      </span>
    );
  }

  const toggle = async () => {
    if (enabled) {
      disableNotifications();
      setEnabled(false);
      return;
    }
    const result = await enableNotifications();
    setPermission(result);
    setEnabled(result === "granted");
  };

  return (
    <button className={`toggle-btn toggle-btn-sm ${enabled ? "on" : "off"}`} onClick={toggle}>
      {enabled ? "Notifications on" : "Enable notifications"}
    </button>
  );
}
