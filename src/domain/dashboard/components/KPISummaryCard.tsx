/** KPI summary card — shows today's revenue, open invoices, pending orders, low-stock. */

import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Skeleton } from "../../../components/ui/skeleton";
import type { KPISummary } from "../types";

function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface KPISummaryCardProps {
  data: KPISummary | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function KPISummaryCard({ data, isLoading, error, onRetry }: KPISummaryCardProps) {
  const { t } = useTranslation("dashboard");

  if (isLoading) {
    return (
      <SectionCard title={t("kpi.title")} description={t("kpi.description")}>
        <div data-testid="kpi-card-loading" className="space-y-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
        </div>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title={t("kpi.title")} description={t("kpi.description")}>
        <SurfaceMessage tone="danger">{error}</SurfaceMessage>
        <Button variant="outline" onClick={onRetry} className="mt-2">
          {t("retry")}
        </Button>
      </SectionCard>
    );
  }

  if (!data) return null;

  return (
    <SectionCard title={t("kpi.title")} description={t("kpi.description")}>
      <div data-testid="kpi-card" className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.todayRevenue")}</span>
          <span className="font-semibold">{formatTWD(data.today_revenue)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.openInvoices")}</span>
          <span className="font-semibold">{data.open_invoice_count}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.openInvoiceAmount")}</span>
          <span className="font-semibold">{formatTWD(data.open_invoice_amount)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.pendingOrders")}</span>
          <span className="font-semibold">{data.pending_order_count}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.pendingOrderRevenue")}</span>
          <span className="font-semibold">{formatTWD(data.pending_order_revenue)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.lowStock")}</span>
          <span className="font-semibold">{data.low_stock_product_count}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">{t("kpi.overdueReceivables")}</span>
          <span className="font-semibold">{formatTWD(data.overdue_receivables_amount)}</span>
        </div>
      </div>
    </SectionCard>
  );
}
