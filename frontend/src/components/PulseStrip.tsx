type PulseState = "up" | "down" | "unknown";

const BEAT = "l20,0 l4,-12 l4,24 l4,-12 l68,0";
const UP_PATH = `M0,20 ${BEAT} ${BEAT} ${BEAT}`;
const DOWN_PATH = "M0,20 l30,0 l5,10 l5,-10 l260,0";
const UNKNOWN_PATH = "M0,20 l300,0";

const COLOR: Record<PulseState, string> = {
  up: "var(--color-up)",
  down: "var(--color-down)",
  unknown: "var(--color-text-faint)",
};

export function PulseStrip({ state }: { state: PulseState }) {
  const path = state === "up" ? UP_PATH : state === "down" ? DOWN_PATH : UNKNOWN_PATH;
  return (
    <div className="pulse-strip" style={{ overflow: "hidden" }}>
      <svg
        className={state === "up" ? "pulse-svg animate" : "pulse-svg"}
        width="300%"
        height="40"
        viewBox="0 0 300 40"
        preserveAspectRatio="none"
      >
        <path
          d={path}
          fill="none"
          stroke={COLOR[state]}
          strokeWidth={state === "unknown" ? 1 : 2}
          strokeDasharray={state === "unknown" ? "2 4" : undefined}
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity={state === "down" ? 0.85 : 1}
        />
      </svg>
    </div>
  );
}
