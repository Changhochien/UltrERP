/** Owner Dashboard page — KPI overview for business owners. */

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader } from "../../components/layout/PageLayout";
import { RevenueCard } from "../dashboard/components/RevenueCard";
import { KPISummaryCard } from "../dashboard/components/KPISummaryCard";
import { ARAgingCard } from "../dashboard/components/ARAgingCard";
import { APAgingCard } from "../dashboard/components/APAgingCard";
import { CashFlowCard } from "../dashboard/components/CashFlowCard";
import { GrossMarginCard } from "../dashboard/components/GrossMarginCard";
import { TopCustomersCard } from "../dashboard/components/TopCustomersCard";
import { RevenueTrendChart } from "../dashboard/components/RevenueTrendChart";
import {
  useRevenueSummary,
  useARAging,
  useAPAging,
  useCashFlow,
  useGrossMargin,
  useRevenueTrend,
} from "../dashboard/hooks/useDashboard";
import { useKPISummary } from "../dashboard/hooks/useKPISummary";

export function OwnerDashboardPage() {
  const { t } = useTranslation("common");

  const revenueSummary = useRevenueSummary();
  const kpiSummary = useKPISummary();
  const arAging = useARAging();
  const apAging = useAPAging();
  const cashFlow = useCashFlow();
  const grossMargin = useGrossMargin();

  const [revenuePeriod, setRevenuePeriod] = useState<"month" | "quarter" | "year">("month");
  const revenueTrend = useRevenueTrend(revenuePeriod);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("routes.workspace.label")}
        title={t("routes.ownerDashboard.label")}
        description={t("routes.ownerDashboard.description")}
      />

      {/* KPI Summary row */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPISummaryCard
          data={kpiSummary.data}
          isLoading={kpiSummary.isLoading}
          error={kpiSummary.error}
          onRetry={() => void kpiSummary.refetch()}
        />
        <RevenueCard
          data={revenueSummary.data}
          isLoading={revenueSummary.isLoading}
          error={revenueSummary.error}
        />
        <GrossMarginCard
          data={grossMargin.data}
          isLoading={grossMargin.isLoading}
          error={grossMargin.error}
        />
        <CashFlowCard
          data={cashFlow.data}
          isLoading={cashFlow.isLoading}
          error={cashFlow.error}
          onRetry={() => void cashFlow.refetch()}
        />
      </section>

      {/* Revenue trend chart */}
      <section>
        <RevenueTrendChart
          data={revenueTrend.data?.items ?? []}
          isLoading={revenueTrend.isLoading}
          isLoadingMore={revenueTrend.isLoadingMore}
          error={revenueTrend.error}
          onRetry={() => void revenueTrend.refetch()}
          period={revenuePeriod}
          onPeriodChange={setRevenuePeriod}
          hasMore={revenueTrend.hasMore}
          onLoadMore={revenueTrend.loadMore}
        />
      </section>

      {/* Aging reports */}
      <section className="grid gap-4 lg:grid-cols-2">
        <ARAgingCard
          data={arAging.data}
          isLoading={arAging.isLoading}
          error={arAging.error}
          onRetry={() => void arAging.refetch()}
        />
        <APAgingCard
          data={apAging.data}
          isLoading={apAging.isLoading}
          error={apAging.error}
          onRetry={() => void apAging.refetch()}
        />
      </section>

      {/* Top customers */}
      <section>
        <TopCustomersCard />
      </section>
    </div>
  );
}
