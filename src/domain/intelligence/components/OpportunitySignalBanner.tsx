import { AlertTriangle, Info, TrendingUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../../../components/ui/button";
import type { OpportunitySignal } from "../types";

interface OpportunitySignalBannerProps {
  signals: OpportunitySignal[];
  deferredSignalTypes?: string[];
}

const SEVERITY_STYLES = {
  alert: "border-red-500 bg-red-500 text-white",
  warning: "border-amber-400 bg-amber-100 text-amber-950",
  info: "border-sky-300 bg-sky-100 text-sky-950",
} as const;

function severityIcon(severity: OpportunitySignal["severity"]) {
  if (severity === "alert") return AlertTriangle;
  if (severity === "warning") return TrendingUp;
  return Info;
}

export function OpportunitySignalBanner({ signals, deferredSignalTypes = [] }: OpportunitySignalBannerProps) {
  const { t } = useTranslation("common", { keyPrefix: "intelligence.marketOpportunities" });
  const [expandedHeadlines, setExpandedHeadlines] = useState<Record<string, boolean>>({});

  if (signals.length === 0 && deferredSignalTypes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3" data-testid="opportunity-signal-stack">
      {signals.map((signal) => {
        const isExpanded = expandedHeadlines[signal.headline] ?? false;
        const Icon = severityIcon(signal.severity);

        return (
          <article
            key={signal.headline}
            data-testid="opportunity-signal-banner"
            className={`rounded-2xl border px-4 py-3 shadow-sm ${SEVERITY_STYLES[signal.severity]}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <Icon className="mt-0.5 h-5 w-5" />
                <div className="space-y-1">
                  <h3 className="font-semibold">{signal.headline}</h3>
                  <p className="text-sm opacity-90">{signal.detail}</p>
                  <p className="text-xs opacity-90">
                    {t("affectedCustomers", {
                      count: signal.affected_customer_count,
                      defaultValue: `${signal.affected_customer_count} customers affected`,
                    })}
                  </p>
                </div>
              </div>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() =>
                  setExpandedHeadlines((current) => ({
                    ...current,
                    [signal.headline]: !isExpanded,
                  }))
                }
              >
                {t(isExpanded ? "hideDetail" : "showDetail", {
                  defaultValue: isExpanded ? "Hide detail" : "Show detail",
                })}
              </Button>
            </div>
            {isExpanded ? (
              <div className="mt-3 space-y-2 text-sm opacity-95">
                <p>
                  <span className="font-semibold">{t("action", { defaultValue: "Recommended action" })}: </span>
                  {signal.recommended_action}
                </p>
                <p>
                  <span className="font-semibold">Source period: </span>
                  {signal.source_period}
                </p>
                {signal.support_counts ? (
                  <p>
                    <span className="font-semibold">Support: </span>
                    {Object.entries(signal.support_counts)
                      .map(([key, value]) => `${key}=${value}`)
                      .join(", ")}
                  </p>
                ) : null}
              </div>
            ) : null}
          </article>
        );
      })}
      {deferredSignalTypes.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          {t("deferred", {
            value: deferredSignalTypes.join(", "),
            defaultValue: `Deferred in v1: ${deferredSignalTypes.join(", ")}`,
          })}
        </p>
      ) : null}
    </div>
  );
}