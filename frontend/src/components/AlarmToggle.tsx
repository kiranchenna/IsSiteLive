import { useState } from "react";
import { isAlarmEnabled, setAlarmEnabled } from "../lib/alarm";

export function AlarmToggle() {
  const [enabled, setEnabled] = useState(isAlarmEnabled());

  const toggle = () => {
    const next = !enabled;
    setAlarmEnabled(next);
    setEnabled(next);
  };

  return (
    <button
      type="button"
      className={`toggle-btn toggle-btn-sm ${enabled ? "on" : "off"}`}
      title="Plays a looping siren on failure until you click Stop, in addition to the one-off notification sound"
      onClick={toggle}
    >
      {enabled ? "Alarm on failure: on" : "Alarm on failure: off"}
    </button>
  );
}
