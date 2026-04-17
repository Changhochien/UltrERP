import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import type { ProspectGapCustomerFilter } from "../types";
import { useCategoryTrends, useProspectGaps } from "../hooks/useIntelligence";

interface ProspectGapTableProps {
  defaultCategory?: string;
}

const customerTypeOptions: Array<{
  value: ProspectGapCustomerFilter;
  labelKey: "filterDealers" | "filterEndUsers" | "filterAll";
  defaultValue: string;
}> = [
  { value: "dealer", labelKey: "filterDealers", defaultValue: "Dealers" },
  { value: "end_user", labelKey: "filterEndUsers", defaultValue: "End Users" },
  { value: "all", labelKey: "filterAll", defaultValue: "All" },
];

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function scoreColor(score: number): string {
  if (score < 0.3) return "bg-destructive";
  if (score <= 0.6) return "bg-amber-500";
  return "bg-emerald-500";
}

export function ProspectGapTable({ defaultCategory = "Supplies" }: ProspectGapTableProps) {
  const { t } = useTranslation("common", { keyPrefix: "intelligence.prospectGaps" });
  const [category, setCategory] = useState("");
  const [customerType, setCustomerType] = useState<ProspectGapCustomerFilter>("dealer");
  const { data: categoryTrendData } = useCategoryTrends("last_12m");
  const availableCategories = categoryTrendData?.trends.map((trend) => trend.category) ?? [];
  const { data, isLoading, error } = useProspectGaps(category, customerType, 20);

  useEffect(() => {
    if (availableCategories.length === 0) {
      return;
    }
    if (!category || !availableCategories.includes(category)) {
      const preferredCategory = availableCategories.includes(defaultCategory)
        ? defaultCategory
        : availableCategories[0];
      setCategory(preferredCategory);
    }
  }, [availableCategories, category, defaultCategory]);

  return (
    <SectionCard
      title={t("title", { defaultValue: "Prospect Gap Analysis" })}
      description={t("description", {
        defaultValue: "Find active non-buyers who look like strong fits for a target category.",
      })}
      actions={(
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{t("categoryLabel", { defaultValue: "Target Category" })}</span>
            <select
              aria-label={t("categoryLabel", { defaultValue: "Target Category" })}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {(availableCategories.length ? availableCategories : category ? [category] : []).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <div
            role="group"
            aria-label={t("customerTypeLabel", { defaultValue: "Customer Type" })}
            className="flex flex-wrap items-center gap-2"
          >
            {customerTypeOptions.map((option) => (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant={customerType === option.value ? "default" : "outline"}
                onClick={() => setCustomerType(option.value)}
              >
                {t(option.labelKey, { defaultValue: option.defaultValue })}
              </Button>
            ))}
          </div>
          {data ? (
            <Badge variant="secondary">
              {t("existingBuyers", {
                count: data.existing_buyers_count,
                defaultValue: `${data.existing_buyers_count} existing buyers`,
              })}
            </Badge>
          ) : null}
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="prospect-gap-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-40 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load prospect gaps." })}
          </SurfaceMessage>
        ) : null}

        {!isLoading && !error && data ? (
          data.prospects.length === 0 ? (
            <SurfaceMessage>
              {t("empty", { defaultValue: "No whitespace prospects for this category yet." })}
            </SurfaceMessage>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("company", { defaultValue: "Company" })}</TableHead>
                  <TableHead>{t("reason", { defaultValue: "Reason" })}</TableHead>
                  <TableHead>{t("lastOrder", { defaultValue: "Last Order" })}</TableHead>
                  <TableHead className="text-right">{t("categoryCount", { defaultValue: "Category Count" })}</TableHead>
                  <TableHead className="text-right">{t("aov", { defaultValue: "AOV" })}</TableHead>
                  <TableHead>{t("affinityScore", { defaultValue: "Affinity Score" })}</TableHead>
                  <TableHead>{t("tags", { defaultValue: "Tags" })}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.prospects.map((prospect) => (
                  <TableRow key={prospect.customer_id} data-testid="prospect-gap-row">
                    <TableCell className="font-medium">{prospect.company_name}</TableCell>
                    <TableCell className="max-w-[22rem] text-sm text-muted-foreground">{prospect.reason}</TableCell>
                    <TableCell>{prospect.last_order_date ?? "—"}</TableCell>
                    <TableCell className="text-right">{prospect.category_count}</TableCell>
                    <TableCell className="text-right">{formatTWD(prospect.avg_order_value)}</TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="h-2 overflow-hidden rounded-full bg-muted/60">
                          <div
                            role="progressbar"
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={prospect.affinity_score * 100}
                            className={`h-full rounded-full ${scoreColor(prospect.affinity_score)}`}
                            style={{ width: `${Math.min(prospect.affinity_score * 100, 100)}%` }}
                          />
                        </div>
                        <div className="text-xs text-muted-foreground">{(prospect.affinity_score * 100).toFixed(1)}%</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        {prospect.tags.map((tag) => (
                          <Badge key={tag} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )
        ) : null}
      </div>
    </SectionCard>
  );
}