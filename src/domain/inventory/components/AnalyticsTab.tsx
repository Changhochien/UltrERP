/** Analytics tab — monthly demand chart, sales history table, top customer card. */

import { useTranslation } from "react-i18next";

import { SectionCard } from "@/components/layout/PageLayout";
import { PlanningSupportCard } from "../components/PlanningSupportCard";
import { useProductMonthlyDemand } from "../hooks/useProductMonthlyDemand";
import { useProductSalesHistory } from "../hooks/useProductSalesHistory";
import { useProductTopCustomer } from "../hooks/useProductTopCustomer";
import { useStockHistory } from "../hooks/useStockHistory";
import { MonthlyDemandChart } from "../components/MonthlyDemandChart";
import { SalesHistoryTable } from "../components/SalesHistoryTable";
import { TopCustomerCard } from "../components/TopCustomerCard";
import { AnalyticsSummaryCard } from "../components/AnalyticsSummaryCard";
import type { WarehouseStockInfo } from "../types";

interface AnalyticsTabProps {
  productId: string;
  warehouses: WarehouseStockInfo[];
}

export function AnalyticsTab({ productId, warehouses }: AnalyticsTabProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail.analyticsTab" });
  const { items: demandItems, loading: demandLoading, error: demandError } = useProductMonthlyDemand(productId);
  const { items: salesItems, loading: salesLoading, error: salesError } = useProductSalesHistory(productId);
  const { customer: topCustomer, loading: customerLoading, error: customerError } = useProductTopCustomer(productId);

  const stockId = warehouses[0]?.stock_id;
  const { avgDailyUsage, leadTimeDays, safetyStock } = useStockHistory(stockId ?? "");

  const loading = demandLoading || salesLoading || customerLoading;
  const error = demandError || salesError || customerError;

  if (loading && !demandItems.length) {
    return (
      <div className="space-y-4">
        <div className="h-48 animate-pulse rounded-xl bg-muted" />
        <div className="h-32 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <AnalyticsSummaryCard
        avgDailyUsage={avgDailyUsage}
        leadTimeDays={leadTimeDays}
        reorderPoint={warehouses[0]?.reorder_point ?? 0}
        safetyStock={safetyStock}
        loading={loading}
      />

      <PlanningSupportCard productId={productId} />

      {/* Monthly demand chart */}
      <SectionCard title={t("monthlyDemand.title")}>
        <MonthlyDemandChart data={demandItems} />
      </SectionCard>

      {/* Sales history + Top customer side by side on larger screens */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SectionCard title={t("salesHistory.title")}>
            <SalesHistoryTable items={salesItems} />
          </SectionCard>
        </div>
        <div>
          <TopCustomerCard customer={topCustomer} loading={customerLoading} />
        </div>
      </div>
    </div>
  );
}
