import type { AdjustmentHistoryItem } from "../types";
import { useTranslation } from "react-i18next";
import { parseBackendDate } from "@/lib/time";

interface AdjustmentTimelineProps {
  history: AdjustmentHistoryItem[];
}

export function AdjustmentTimeline({ history }: AdjustmentTimelineProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.adjustmentTimeline",
  });

  if (history.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
        {t("empty")}
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
            <div className="timeline-item-reason">
              {t(`reasons.${item.reason_code}`, { defaultValue: item.reason_code })}
            </div>
            <div style={{ fontSize: 12, color: "var(--inv-muted)" }}>
              {t("byActor", { actorId: item.actor_id })}
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
