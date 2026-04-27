import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import type { OpportunityStatus, OpportunitySummary } from "@/domain/crm/types";

const STATUS_ORDER: OpportunityStatus[] = [
  "open",
  "replied",
  "quotation",
  "converted",
  "closed",
  "lost",
];

export interface OpportunityPipelineSummaryProps {
  items: OpportunitySummary[];
}

export function OpportunityPipelineSummary({ items }: OpportunityPipelineSummaryProps) {
  const { t } = useTranslation("crm");
  const counts = useMemo(() => {
    return STATUS_ORDER.reduce<Record<OpportunityStatus, number>>((acc, status) => {
      acc[status] = items.filter((item) => item.status === status).length;
      return acc;
    }, {
      open: 0,
      replied: 0,
      quotation: 0,
      converted: 0,
      closed: 0,
      lost: 0,
    });
  }, [items]);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {STATUS_ORDER.map((status) => (
        <div key={status} className="rounded-xl border border-border/70 bg-muted/20 px-4 py-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            {t(`crm.opportunities.statusValues.${status}`)}
          </p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{counts[status]}</p>
        </div>
      ))}
    </div>
  );
}

export default OpportunityPipelineSummary;