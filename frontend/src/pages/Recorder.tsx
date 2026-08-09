import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, WS_BASE } from "../api/client";
import type { Account, FlowStep } from "../types";

const VIEWPORT = { width: 1280, height: 800 };

type Status = "loading" | "picking-account" | "connecting" | "recording" | "error";

export function Recorder() {
  const { id } = useParams();
  const siteId = Number(id);
  const navigate = useNavigate();

  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [steps, setSteps] = useState<FlowStep[]>([]);
  const [markingSuccess, setMarkingSuccess] = useState(false);
  const [assertValue, setAssertValue] = useState("");
  const [markingAssertion, setMarkingAssertion] = useState(false);
  const [saving, setSaving] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const watchPatternsRef = useRef<{ pattern: string }[]>([]);
  const stoppedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listAccounts(siteId), api.getFlow(siteId).catch(() => null)])
      .then(([accs, flow]) => {
        if (cancelled) return;
        setAccounts(accs);
        if (flow) watchPatternsRef.current = flow.watch_patterns_json;
        if (accs.length === 1) {
          setAccountId(accs[0].id);
        }
        setStatus("picking-account");
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  useEffect(() => {
    return () => {
      stopSession();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function stopSession() {
    if (stoppedRef.current) return;
    stoppedRef.current = true;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
    } else if (sessionIdRef.current) {
      api.stopRecording(sessionIdRef.current).catch(() => {});
    }
    wsRef.current?.close();
  }

  async function startRecording() {
    if (!accountId) return;
    setStatus("connecting");
    setError(null);
    try {
      const { session_id } = await api.startRecording(siteId, accountId);
      sessionIdRef.current = session_id;
      stoppedRef.current = false;

      const seeded = await api.getRecordingSteps(session_id);
      setSteps(seeded.steps as FlowStep[]);

      const ws = new WebSocket(`${WS_BASE}/api/recordings/${session_id}/stream`);
      wsRef.current = ws;

      ws.onopen = () => setStatus("recording");
      ws.onerror = () => setError("Connection to the recording browser dropped.");
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "frame") {
          drawFrame(msg.data);
        } else if (msg.type === "step") {
          setSteps((prev) => (msg.replace_last && prev.length ? [...prev.slice(0, -1), msg.step] : [...prev, msg.step]));
          if (msg.step.type === "wait_for_selector") setMarkingSuccess(false);
          if (msg.step.type === "assert_text_contains") {
            setMarkingAssertion(false);
            setAssertValue("");
          }
        }
      };
    } catch (e) {
      setError(String(e));
      setStatus("picking-account");
    }
  }

  function drawFrame(base64Data: string) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const img = new Image();
    img.onload = () => ctx.drawImage(img, 0, 0, VIEWPORT.width, VIEWPORT.height);
    img.src = `data:image/jpeg;base64,${base64Data}`;
  }

  function toPageCoords(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = VIEWPORT.width / rect.width;
    const scaleY = VIEWPORT.height / rect.height;
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  }

  function send(message: Record<string, unknown>) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = toPageCoords(e);
    send({ type: "mouse", x, y, kind: "down" });
  }

  function handleMouseUp(e: React.MouseEvent<HTMLCanvasElement>) {
    const { x, y } = toPageCoords(e);
    send({ type: "mouse", x, y, kind: "up" });
  }

  const lastMoveRef = useRef(0);
  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const now = performance.now();
    if (now - lastMoveRef.current < 40) return;
    lastMoveRef.current = now;
    const { x, y } = toPageCoords(e);
    send({ type: "mouse", x, y, kind: "move" });
  }

  const NAMED_KEYS = new Set(["Enter", "Tab", "Backspace", "Escape", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Delete"]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLCanvasElement>) {
    e.preventDefault();
    if (NAMED_KEYS.has(e.key)) {
      send({ type: "key", key: e.key, kind: "down" });
    } else if (e.key.length === 1) {
      send({ type: "text", text: e.key });
    }
  }

  function handleKeyUp(e: React.KeyboardEvent<HTMLCanvasElement>) {
    if (NAMED_KEYS.has(e.key)) {
      e.preventDefault();
      send({ type: "key", key: e.key, kind: "up" });
    }
  }

  function markSuccess() {
    setMarkingSuccess(true);
    send({ type: "mark_success" });
  }

  function markAssertion() {
    const value = assertValue.trim();
    if (!value) return;
    setMarkingAssertion(true);
    send({ type: "mark_assertion", value });
  }

  function removeStep(index: number) {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }

  async function saveFlow() {
    setSaving(true);
    try {
      await api.upsertFlow(siteId, {
        steps_json: steps,
        watch_patterns_json: watchPatternsRef.current,
      });
      stopSession();
      navigate(`/sites/${siteId}`);
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  }

  function cancel() {
    stopSession();
    navigate(`/sites/${siteId}`);
  }

  if (status === "loading") return <p className="text-muted">Loading…</p>;

  if (accounts.length === 0) {
    return (
      <div className="empty-state">
        <h3>No demo accounts yet</h3>
        <p>Add a demo account on the site page before recording a login flow.</p>
        <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate(`/sites/${siteId}`)}>
          Back to site
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="row-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title" style={{ marginBottom: 2 }}>
          Record flow
        </h1>
        <button className="btn btn-ghost" onClick={cancel}>
          Cancel
        </button>
      </div>
      <p className="page-subtitle">
        {status === "recording"
          ? "Click and type directly on the page below, exactly as a real user would."
          : "Pick the account to record with, then click through the login, a form submission, or any other flow."}
      </p>

      {error && <p className="error-text">{error}</p>}

      {status === "picking-account" && (
        <div className="card" style={{ maxWidth: 480 }}>
          <div className="field">
            <label>Record using account</label>
            <select value={accountId ?? ""} onChange={(e) => setAccountId(Number(e.target.value))}>
              <option value="" disabled>
                Select an account…
              </option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label} ({a.username})
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={startRecording} disabled={!accountId}>
            Start recording
          </button>
        </div>
      )}

      {(status === "connecting" || status === "recording") && (
        <div className="recorder-shell">
          <div className="recorder-canvas-wrap">
            <canvas
              ref={canvasRef}
              className="recorder-canvas"
              width={VIEWPORT.width}
              height={VIEWPORT.height}
              tabIndex={0}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseMove={handleMouseMove}
              onKeyDown={handleKeyDown}
              onKeyUp={handleKeyUp}
            />
            {status === "connecting" && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  pointerEvents: "none",
                }}
              >
                <span className="text-muted">Connecting…</span>
              </div>
            )}
            {markingSuccess && (
              <div className="chip" style={{ position: "absolute", top: 10, right: 10, pointerEvents: "none" }}>
                Click the element that proves you're logged in
              </div>
            )}
            {markingAssertion && (
              <div className="chip" style={{ position: "absolute", top: 10, right: 10, pointerEvents: "none" }}>
                Click the element that should show "{assertValue}"
              </div>
            )}
          </div>

          <div className="card recorder-steps-panel">
            <div className="card-header">
              <h3>Recorded steps ({steps.length})</h3>
            </div>
            {steps.length === 0 && <p className="text-muted" style={{ margin: 0 }}>Nothing recorded yet — start clicking through the login.</p>}
            {steps.map((step, i) => (
              <div className="recorder-step-row" key={i}>
                <div>
                  <div className="mono text-text">{step.type}</div>
                  {"selector" in step && <div className="text-faint mono">{String(step.selector)}</div>}
                  {"value" in step && <div className="text-muted mono">{String(step.value)}</div>}
                  {"url" in step && <div className="text-muted mono" style={{ wordBreak: "break-all" }}>{String(step.url)}</div>}
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => removeStep(i)}>
                  ×
                </button>
              </div>
            ))}

            <div className="field" style={{ marginTop: 8, marginBottom: 0 }}>
              <label>Verify a value was saved (optional)</label>
              <div className="field-row">
                <input
                  type="text"
                  placeholder="e.g. Order {{unique}}"
                  value={assertValue}
                  onChange={(e) => setAssertValue(e.target.value)}
                  disabled={status !== "recording" || markingAssertion}
                />
                <button
                  className="btn btn-sm"
                  style={{ flex: "0 0 auto" }}
                  onClick={markAssertion}
                  disabled={status !== "recording" || markingAssertion || !assertValue.trim()}
                >
                  Mark element
                </button>
              </div>
            </div>

            <div className="stack" style={{ marginTop: 8, gap: 8 }}>
              <button className="btn btn-sm" onClick={markSuccess} disabled={status !== "recording"}>
                Mark success element
              </button>
              <button className="btn btn-primary btn-sm" onClick={saveFlow} disabled={saving || steps.length === 0}>
                {saving ? "Saving…" : "Save as flow"}
              </button>
            </div>
            <p className="text-faint" style={{ fontSize: 11.5, marginTop: 4 }}>
              This covers navigation, clicks, typed fields, the success check, and verifying a saved value. Use{" "}
              <code>{"{{unique}}"}</code> in the value above so each scheduled run checks its own submission, not a
              leftover from a past one. Add "don't show an error" checks and AJAX watch patterns by hand afterward.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
