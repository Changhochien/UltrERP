/** Top customers card — ranked list of customers by revenue. */

import { ChevronLeft, ChevronRight } from "lucide-react";
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
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Skeleton } from "../../../components/ui/skeleton";
import { formatBackendCalendarDate } from "../../../lib/time";
import { useTopCustomers } from "../hooks/useDashboard";

function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function shiftAnchorDate(anchorDate: string, monthStep: number): string {
  const [year, month] = anchorDate.slice(0, 7).split("-").map(Number);
  const shifted = new Date(year, month - 1 + monthStep, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}-01`;
}

export function TopCustomersCard() {
  const { t } = useTranslation("dashboard");
  const { data, isLoading, error, refetch, period, setPeriod, anchorDate, setAnchorDate } = useTopCustomers("month");
  const periodStepMonths = period === "month" ? 1 : period === "quarter" ? 3 : 12;

  if (isLoading) {
    return (
      <SectionCard title={t("topCustomers.title")} description={t("topCustomers.description")}>
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
      <SectionCard title={t("topCustomers.title")} description={t("topCustomers.description")}>
        <SurfaceMessage tone="danger">{error}</SurfaceMessage>
        <button onClick={refetch} className="mt-2 text-sm text-primary hover:underline">
          {t("retry")}
        </button>
      </SectionCard>
    );
  }

  if (!data) return null;

  const listedRevenueTotal = data.customers.reduce((sum, customer) => sum + Number(customer.total_revenue), 0);
  const periodRange = t("topCustomers.periodRange", {
    start: formatBackendCalendarDate(data.start_date, "yyyy-MM-dd"),
    end: formatBackendCalendarDate(data.end_date, "yyyy-MM-dd"),
  });

  return (
    <SectionCard title={t("topCustomers.title")} description={t("topCustomers.description")}>
      <Tabs value={period} onValueChange={(v) => setPeriod(v as "month" | "quarter" | "year")} className="mb-4">
        <TabsList>
          <TabsTrigger value="month">{t("topCustomers.month")}</TabsTrigger>
          <TabsTrigger value="quarter">{t("topCustomers.quarter")}</TabsTrigger>
          <TabsTrigger value="year">{t("topCustomers.year")}</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={t("topCustomers.previousPeriod")}
          onClick={() => setAnchorDate(shiftAnchorDate(anchorDate, -periodStepMonths))}
        >
          <ChevronLeft className="size-4" />
        </Button>
        <Input
          id="top-customers-anchor-month"
          type="month"
          value={anchorDate.slice(0, 7)}
          aria-label={t("topCustomers.anchorMonth")}
          className="h-8 w-full sm:w-44"
          onChange={(event) => {
            if (!event.target.value) return;
            setAnchorDate(`${event.target.value}-01`);
          }}
        />
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={t("topCustomers.nextPeriod")}
          onClick={() => setAnchorDate(shiftAnchorDate(anchorDate, periodStepMonths))}
        >
          <ChevronRight className="size-4" />
        </Button>
      </div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
        <span>{periodRange}</span>
        <span>{t("topCustomers.topTotal", { count: data.customers.length, amount: formatTWD(listedRevenueTotal) })}</span>
      </div>
      <Table data-testid="top-customers-table">
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>{t("topCustomers.company")}</TableHead>
            <TableHead className="text-right">{t("topCustomers.revenue")}</TableHead>
            <TableHead className="text-right">{t("topCustomers.invoices")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.customers.map((customer, index) => (
            <TableRow key={customer.customer_id}>
              <TableCell className="font-medium">{index + 1}</TableCell>
              <TableCell>
                <div className="font-medium">{customer.company_name}</div>
                <div className="text-xs text-muted-foreground">
                  {t("topCustomers.lastInvoice", {
                    date: formatBackendCalendarDate(customer.last_invoice_date, "yyyy-MM-dd"),
                  })}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="font-mono">{formatTWD(customer.total_revenue)}</div>
                <div className="text-xs text-muted-foreground">
                  {t("topCustomers.avgInvoice", {
                    amount: formatTWD(
                      customer.invoice_count > 0
                        ? Number(customer.total_revenue) / customer.invoice_count
                        : 0,
                    ),
                  })}
                </div>
              </TableCell>
              <TableCell className="text-right">{customer.invoice_count}</TableCell>
            </TableRow>
          ))}
          {data.customers.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                {t("topCustomers.noData")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </SectionCard>
  );
}
