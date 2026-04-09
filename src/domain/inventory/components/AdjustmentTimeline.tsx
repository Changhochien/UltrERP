import type { AdjustmentHistoryItem } from "../types";
import { parseBackendDate } from "@/lib/time";

interface AdjustmentTimelineProps {
  history: AdjustmentHistoryItem[];
}

export function AdjustmentTimeline({ history }: AdjustmentTimelineProps) {
  if (history.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
        No adjustment history available.
      </p>
    );
  }

  return (
    <div className="adjustment-timeline">
      {history.map((item) => {
        const isPositive = item.quantity_change > 0;
        const isNeutral = item.quantity_change === 0;
        return (
          <div
            key={item.id}
            className={`timeline-item ${isPositive ? "positive" : isNeutral ? "neutral" : "negative"}`}
          >
            <div className="timeline-item-header">
              <span
                className={`timeline-item-change ${isPositive ? "positive" : "negative"}`}
              >
                {isPositive ? "+" : ""}
                {item.quantity_change}
              </span>
              <span className="timeline-item-date">
                {parseBackendDate(item.created_at).toLocaleDateString("zh-TW", {
                  timeZone: "Asia/Taipei",
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </div>
            <div className="timeline-item-reason">{item.reason_code}</div>
            <div style={{ fontSize: 12, color: "var(--inv-muted)" }}>
              by {item.actor_id}
              {item.notes && (
                <span style={{ fontStyle: "italic" }}> — {item.notes}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
