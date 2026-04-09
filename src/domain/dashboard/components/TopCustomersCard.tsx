/** Top customers card — ranked list of customers by revenue. */

import { useTranslation } from "react-i18next";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "../../../components/ui/tabs";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Skeleton } from "../../../components/ui/skeleton";
import { useTopCustomers } from "../hooks/useDashboard";

function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function TopCustomersCard() {
  const { t } = useTranslation("common");
  const { data, isLoading, error, refetch, period, setPeriod } = useTopCustomers("month");

  if (isLoading) {
    return (
      <SectionCard title={t("dashboard.topCustomers.title")} description={t("dashboard.topCustomers.description")}>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title={t("dashboard.topCustomers.title")} description={t("dashboard.topCustomers.description")}>
        <SurfaceMessage tone="danger">{error}</SurfaceMessage>
        <button onClick={refetch} className="mt-2 text-sm text-primary hover:underline">
          {t("common.retry")}
        </button>
      </SectionCard>
    );
  }

  if (!data) return null;

  return (
    <SectionCard title={t("dashboard.topCustomers.title")} description={t("dashboard.topCustomers.description")}>
      <Tabs value={period} onValueChange={(v) => setPeriod(v as "month" | "quarter" | "year")} className="mb-4">
        <TabsList>
          <TabsTrigger value="month">{t("dashboard.topCustomers.month")}</TabsTrigger>
          <TabsTrigger value="quarter">{t("dashboard.topCustomers.quarter")}</TabsTrigger>
          <TabsTrigger value="year">{t("dashboard.topCustomers.year")}</TabsTrigger>
        </TabsList>
      </Tabs>
      <Table data-testid="top-customers-table">
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>{t("dashboard.topCustomers.company")}</TableHead>
            <TableHead className="text-right">{t("dashboard.topCustomers.revenue")}</TableHead>
            <TableHead className="text-right">{t("dashboard.topCustomers.invoices")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.customers.map((customer, index) => (
            <TableRow key={customer.customer_id}>
              <TableCell className="font-medium">{index + 1}</TableCell>
              <TableCell>{customer.company_name}</TableCell>
              <TableCell className="text-right font-mono">{formatTWD(customer.total_revenue)}</TableCell>
              <TableCell className="text-right">{customer.invoice_count}</TableCell>
            </TableRow>
          ))}
          {data.customers.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                {t("dashboard.topCustomers.noData")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </SectionCard>
  );
}
