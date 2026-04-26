import { ArrowDownUp } from "lucide-react";
import { useState } from "react";
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
import { useProductAffinity } from "../hooks/useIntelligence";
import type { AffinityPair } from "../types";

type SortKey = "product_a_name" | "product_b_name" | "shared_customer_count" | "overlap_pct" | "affinity_score";
type SortDirection = "asc" | "desc";

interface AffinityMatrixProps {
  minShared?: number;
  limit?: number;
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

function formatScore(value: number): string {
  return value.toFixed(3);
}

function formatComputedAt(value: string, language: string): string {
  const locale = language === "zh-Hant" ? "zh-TW" : "en-US";

  return new Date(value).toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function sortPairs(
  pairs: AffinityPair[],
  sortKey: SortKey,
  direction: SortDirection,
): AffinityPair[] {
  const multiplier = direction === "asc" ? 1 : -1;

  return [...pairs].sort((left, right) => {
    if (sortKey === "product_a_name" || sortKey === "product_b_name") {
      return left[sortKey].localeCompare(right[sortKey], undefined, { sensitivity: "base" }) * multiplier;
    }

    return (left[sortKey] - right[sortKey]) * multiplier;
  });
}

export function AffinityMatrix({ minShared = 2, limit = 50 }: AffinityMatrixProps) {
  const { t, i18n } = useTranslation("intelligence", { keyPrefix: "affinity" });
  const { data, isLoading, error } = useProductAffinity(minShared, limit);
  const [sortKey, setSortKey] = useState<SortKey>("affinity_score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const handleSort = (nextKey: SortKey) => {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === "desc" ? "asc" : "desc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === "product_a_name" || nextKey === "product_b_name" ? "asc" : "desc");
  };

  const sortedPairs = data ? sortPairs(data.pairs, sortKey, sortDirection) : [];

  return (
    <SectionCard
      title={t("title", { defaultValue: "Product Affinity Map" })}
      description={t("description", {
        defaultValue: "Customer-level co-purchase pairs scored by overlap and Jaccard affinity.",
      })}
      actions={(
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{t("minShared", { count: minShared, defaultValue: `Min shared ${minShared}` })}</Badge>
          {data ? (
            <Badge variant="outline">
              {t("topPairs", { count: Math.min(data.total, data.limit), defaultValue: `Top ${Math.min(data.total, data.limit)} pairs` })}
            </Badge>
          ) : null}
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="affinity-matrix-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-44 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load product affinity map." })}
          </SurfaceMessage>
        ) : null}

        {!isLoading && !error && data ? (
          <>
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>
                {t("showing", {
                  shown: sortedPairs.length,
                  total: data.total,
                  defaultValue: `Showing ${sortedPairs.length} of ${data.total} pairs`,
                })}
              </span>
              <span>
                {t("computedAt", {
                  value: formatComputedAt(data.computed_at, i18n.resolvedLanguage ?? i18n.language),
                  defaultValue: `Computed ${formatComputedAt(data.computed_at, i18n.resolvedLanguage ?? i18n.language)}`,
                })}
              </span>
            </div>

            {sortedPairs.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No qualifying product affinities yet." })}
              </SurfaceMessage>
            ) : (
              <Table aria-label={t("title", { defaultValue: "Product Affinity Map" })}>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="-ml-2 h-auto px-2 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground"
                        onClick={() => handleSort("product_a_name")}
                        aria-label={t("sortBy", { label: t("productA", { defaultValue: "Product A" }), defaultValue: "Sort by Product A" })}
                      >
                        {t("productA", { defaultValue: "Product A" })}
                        <ArrowDownUp className="size-3.5" />
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="-ml-2 h-auto px-2 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground"
                        onClick={() => handleSort("product_b_name")}
                        aria-label={t("sortBy", { label: t("productB", { defaultValue: "Product B" }), defaultValue: "Sort by Product B" })}
                      >
                        {t("productB", { defaultValue: "Product B" })}
                        <ArrowDownUp className="size-3.5" />
                      </Button>
                    </TableHead>
                    <TableHead className="text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="ml-auto h-auto px-2 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground"
                        onClick={() => handleSort("shared_customer_count")}
                        aria-label={t("sortBy", { label: t("sharedCustomers", { defaultValue: "Shared Customers" }), defaultValue: "Sort by Shared Customers" })}
                      >
                        {t("sharedCustomers", { defaultValue: "Shared Customers" })}
                        <ArrowDownUp className="size-3.5" />
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="-ml-2 h-auto px-2 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground"
                        onClick={() => handleSort("overlap_pct")}
                        aria-label={t("sortBy", { label: t("overlap", { defaultValue: "Overlap" }), defaultValue: "Sort by Overlap" })}
                      >
                        {t("overlap", { defaultValue: "Overlap" })}
                        <ArrowDownUp className="size-3.5" />
                      </Button>
                    </TableHead>
                    <TableHead className="text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="ml-auto h-auto px-2 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground"
                        onClick={() => handleSort("affinity_score")}
                        aria-label={t("sortBy", { label: t("affinityScore", { defaultValue: "Affinity Score" }), defaultValue: "Sort by Affinity Score" })}
                      >
                        {t("affinityScore", { defaultValue: "Affinity Score" })}
                        <ArrowDownUp className="size-3.5" />
                      </Button>
                    </TableHead>
                    <TableHead>{t("pitchHint", { defaultValue: "Pitch Hint" })}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedPairs.map((pair) => (
                    <TableRow key={`${pair.product_a_id}:${pair.product_b_id}`}>
                      <TableCell className="font-medium">{pair.product_a_name}</TableCell>
                      <TableCell className="font-medium">{pair.product_b_name}</TableCell>
                      <TableCell className="text-right">{pair.shared_customer_count}</TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="h-2 overflow-hidden rounded-full bg-muted/60">
                            <div
                              role="progressbar"
                              aria-valuemin={0}
                              aria-valuemax={100}
                              aria-valuenow={pair.overlap_pct}
                              className="h-full rounded-full bg-primary"
                              style={{ width: `${Math.min(pair.overlap_pct, 100)}%` }}
                            />
                          </div>
                          <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                            <span>{formatPercent(pair.overlap_pct)}</span>
                            {pair.shared_order_count != null ? (
                              <span>
                                {t("sharedOrders", {
                                  count: pair.shared_order_count,
                                  defaultValue: `Shared orders: ${pair.shared_order_count}`,
                                })}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium">{formatScore(pair.affinity_score)}</TableCell>
                      <TableCell className="max-w-[28rem] text-sm text-muted-foreground">{pair.pitch_hint}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}