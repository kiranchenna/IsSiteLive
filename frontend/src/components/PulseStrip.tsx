type PulseState = "up" | "down" | "checking" | "unknown";

const BEAT = "l20,0 l4,-12 l4,24 l4,-12 l68,0";
const UP_PATH = `M0,20 ${BEAT} ${BEAT} ${BEAT}`;
const DOWN_PATH = "M0,20 l30,0 l5,10 l5,-10 l260,0";
const UNKNOWN_PATH = "M0,20 l300,0";

const PATHS: Record<PulseState, string> = { up: UP_PATH, down: DOWN_PATH, checking: UP_PATH, unknown: UNKNOWN_PATH };
const COLOR: Record<PulseState, string> = {
  up: "var(--color-up)",
  down: "var(--color-down)",
  checking: "var(--color-warn)",
  unknown: "var(--color-text-faint)",
};
const ANIMATED: Record<PulseState, boolean> = { up: true, down: false, checking: true, unknown: false };

export function PulseStrip({ state }: { state: PulseState }) {
  return (
    <div className="pulse-strip" style={{ overflow: "hidden" }}>
      <svg
        className={ANIMATED[state] ? "pulse-svg animate" : "pulse-svg"}
        width="300%"
        height="40"
        viewBox="0 0 300 40"
        preserveAspectRatio="none"
      >
        <path
          d={PATHS[state]}
          fill="none"
          stroke={COLOR[state]}
          strokeWidth={state === "unknown" ? 1 : 2}
          strokeDasharray={state === "unknown" ? "2 4" : state === "checking" ? "6 4" : undefined}
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity={state === "down" ? 0.85 : 1}
        />
      </svg>
    </div>
  );
}
