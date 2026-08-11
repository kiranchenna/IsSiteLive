import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";

type StatusFilter = "all" | "success" | "fail";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All runs" },
  { value: "success", label: "Only success" },
  { value: "fail", label: "Only fail" },
];

export function DownloadReportModal({ siteId, onClose }: { siteId: number; onClose: () => void }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const download = () => {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (status !== "all") params.set("status", status);
    const query = params.toString();
    const url = `${API_BASE}/api/sites/${siteId}/report.xlsx${query ? `?${query}` : ""}`;

    const link = document.createElement("a");
    link.href = url;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="row-between" style={{ marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Download report</h3>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Close ✕
          </button>
        </div>

        <div className="field-row">
          <div className="field">
            <label>From (optional)</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="field">
            <label>To (optional)</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label>Status</label>
          <div className="stack" style={{ gap: 6 }}>
            {STATUS_OPTIONS.map((opt) => (
              <label key={opt.value} className="checkbox-row" style={{ marginBottom: 0 }}>
                <input type="radio" name="report-status-filter" checked={status === opt.value} onChange={() => setStatus(opt.value)} />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <button type="button" className="btn btn-primary" style={{ marginTop: 4 }} onClick={download}>
          Download
        </button>
      </div>
    </div>
  );
}
