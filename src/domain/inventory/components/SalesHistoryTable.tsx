import { useTranslation } from "react-i18next";

import { parseBackendDate } from "@/lib/time";
import type { SalesHistoryItem } from "../hooks/useProductSalesHistory";

interface SalesHistoryTableProps {
  items: SalesHistoryItem[];
}

function formatDate(dateStr: string): string {
  return parseBackendDate(dateStr).toLocaleDateString("zh-TW", {
    timeZone: "Asia/Taipei",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function SalesHistoryTable({ items }: SalesHistoryTableProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.salesHistory",
  });

  if (items.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-muted-foreground">
        <p className="text-sm">{t("empty")}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <th className="pb-2 pr-4 font-medium">{t("columns.date")}</th>
            <th className="pb-2 pr-4 font-medium">{t("columns.quantity")}</th>
            <th className="pb-2 pr-4 font-medium">{t("columns.reason")}</th>
            <th className="pb-2 font-medium">{t("columns.actor")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {items.map((item, i) => (
            <tr key={i} className="text-sm">
              <td className="py-2 pr-4 text-muted-foreground">
                {formatDate(item.date)}
              </td>
              <td
                className={`py-2 pr-4 font-medium ${
                  item.quantity_change > 0
                    ? "text-success"
                    : "text-destructive"
                }`}
              >
                {item.quantity_change > 0 ? "+" : ""}
                {item.quantity_change}
              </td>
              <td className="py-2 pr-4 text-muted-foreground">
                {t(`reasonLabels.${item.reason_code}`, { defaultValue: item.reason_code })}
              </td>
              <td className="py-2 text-muted-foreground">{item.actor_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
