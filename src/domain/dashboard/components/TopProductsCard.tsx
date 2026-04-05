/** Top selling products card with day/week toggle. */

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { cn } from "../../../lib/utils";
import { useTopProducts } from "../hooks/useDashboard";

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function TopProductsCard() {
  const { t } = useTranslation("common");
  const [period, setPeriod] = useState<"day" | "week">("day");
  const { data, isLoading, error } = useTopProducts(period);

  return (
    <Card data-testid="top-products-card" className="h-full">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>{t("dashboard.topProducts.title")}</CardTitle>
          <p className="text-sm text-muted-foreground">{t("dashboard.topProducts.description")}</p>
        </div>
        <div className="flex items-center gap-2" role="group" aria-label="Period toggle">
          <Button
            type="button"
            size="sm"
            variant={period === "day" ? "default" : "outline"}
            className={cn(period === "day" && "toggle--active")}
            onClick={() => setPeriod("day")}
            aria-pressed={period === "day"}
          >
            {t("dashboard.topProducts.today")}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={period === "week" ? "default" : "outline"}
            className={cn(period === "week" && "toggle--active")}
            onClick={() => setPeriod("week")}
            aria-pressed={period === "week"}
          >
            {t("dashboard.topProducts.thisWeek")}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">

        {isLoading && (
          <div data-testid="top-products-loading" className="space-y-3">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!isLoading && !error && data && data.items.length === 0 && (
          <p className="rounded-xl border border-border/70 bg-muted/35 px-4 py-6 text-sm text-muted-foreground" data-testid="top-products-empty">
            {t("dashboard.topProducts.noData")}
          </p>
        )}

        {!isLoading && !error && data && data.items.length > 0 && (
          <div className="overflow-x-auto">
            <Table data-testid="top-products-table">
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">{t("dashboard.topProducts.rank")}</TableHead>
                <TableHead>{t("dashboard.topProducts.product")}</TableHead>
                <TableHead>{t("dashboard.topProducts.qtySold")}</TableHead>
                <TableHead className="text-right">{t("dashboard.topProducts.revenue")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((item, idx) => (
                <TableRow key={item.product_id}>
                  <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
                  <TableCell className="font-medium">{item.product_name}</TableCell>
                  <TableCell>{Number(item.quantity_sold).toLocaleString("en-US")}</TableCell>
                  <TableCell className="text-right font-medium">{formatTWD(item.revenue)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
