/** Reorder point calculator admin — compute preview and apply selected rows. */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { SlidersHorizontal, CheckCircle2, AlertCircle, Info } from "lucide-react";

import { SectionCard } from "@/components/layout/PageLayout";
import { DataTable, DataTableToolbar } from "@/components/layout/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LabeledInfoPopover } from "@/components/ui/info-popover";
import { useTranslation } from "react-i18next";

import { useReorderPointAdmin } from "../hooks/useReorderPointAdmin";
import { useWarehouses } from "../hooks/useWarehouses";
import type { ReorderPointPreviewRow } from "../types";
import { SettingsTab } from "./SettingsTab";

const LOOKBACK_OPTIONS = [
  { value: 30, label: "30d" },
  { value: 60, label: "60d" },
  { value: 90, label: "90d" },
  { value: 180, label: "180d" },
  { value: 365, label: "1yr" },
] as const;

interface SummaryCardProps {
  label: string;
  value: string;
  hint: string;
  tone?: "default" | "success" | "warning";
}

function SummaryCard({ label, value, hint, tone = "default" }: SummaryCardProps) {
  const toneClass = tone === "warning"
    ? "border-warning/40 bg-warning/10"
    : tone === "success"
      ? "border-success/30 bg-success/10"
      : "border-border/70 bg-muted/20";

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-foreground">{value}</p>
      <p className="mt-2 text-sm text-muted-foreground">{hint}</p>
    </div>
  );
}

function DetailMetric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">{label}</dt>
      <dd className="font-mono text-sm tabular-nums text-foreground">{value}</dd>
    </div>
  );
}

function LookbackSelector({
  value,
  onChange,
  label,
}: {
  value: (typeof LOOKBACK_OPTIONS)[number]["value"];
  onChange: (nextValue: (typeof LOOKBACK_OPTIONS)[number]["value"]) => void;
  label: string;
}) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex flex-wrap rounded-lg border border-border bg-background p-0.5">
        {LOOKBACK_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
              value === option.value
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
            aria-pressed={value === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function WarehouseFilter({
  value,
  onChange,
  label,
  allWarehousesLabel,
  warehouses,
}: {
  value: string;
  onChange: (nextValue: string) => void;
  label: string;
  allWarehousesLabel: string;
  warehouses: Array<{ id: string; name: string }>;
}) {
  return (
    <div className="space-y-2 min-w-[220px]">
      <label htmlFor="rop-warehouse" className="block text-sm font-medium">{label}</label>
      <select
        id="rop-warehouse"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
      >
        <option value="">{allWarehousesLabel}</option>
        {warehouses.map((warehouse) => (
          <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>
        ))}
      </select>
    </div>
  );
}

function SafetyFactorSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (nextValue: number) => void;
}) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.reorderPointAdmin.safetyFactorPopover" });

  return (
    <div className="space-y-2">
      <LabeledInfoPopover
        alwaysVisible
        label={t("title")}
        title={t("title")}
        formula={t("formula")}
        triggerClassName="relative top-0.5"
      >
        <p className="text-sm leading-relaxed">{t("body")}</p>
      </LabeledInfoPopover>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={100}
          value={value * 100}
          onChange={(event) => onChange(Number(event.target.value) / 100)}
          className="flex-1 accent-primary"
          aria-label="Safety factor"
        />
        <span className="w-14 text-right font-mono text-sm tabular-nums">{Math.round(value * 100)}%</span>
      </div>
    </div>
  );
}

function num(value: number | null | undefined, fallback = "—"): string {
  if (value == null) {
    return fallback;
  }
  return value.toFixed(1);
}

function normalizeDemandBasis(value: string | null | undefined): string {
  return (value ?? "sales_reservation").toLowerCase();
}

interface CandidateRow extends ReorderPointPreviewRow {
  _checked: boolean;
}

function ReorderPointAdmin() {
  const { t } = useTranslation("common", { keyPrefix: "inventory.reorderPointAdmin" });
  const [safetyFactor, setSafetyFactor] = useState(0.5);
  const [lookbackDays, setLookbackDays] = useState<30 | 60 | 90 | 180 | 365>(90);
  const [warehouseId, setWarehouseId] = useState("");
  const [activeTab, setActiveTab] = useState<"candidates" | "skipped">("candidates");
  const [candidateRows, setCandidateRows] = useState<CandidateRow[]>([]);
  const [detailRow, setDetailRow] = useState<ReorderPointPreviewRow | null>(null);
  const [settingsRow, setSettingsRow] = useState<ReorderPointPreviewRow | null>(null);

  const { warehouses } = useWarehouses();
  const {
    candidates,
    skipped,
    loading,
    applying,
    error,
    applyResult,
    computeReorderPoints,
    applyReorderPoints,
    clearResults,
  } = useReorderPointAdmin();

  const handlePreview = useCallback(async () => {
    setActiveTab("candidates");
    setDetailRow(null);
    setSettingsRow(null);
    await computeReorderPoints({
      safetyFactor,
      lookbackDays,
      lookbackDaysLeadTime: 180,
      warehouseId: warehouseId || undefined,
    });
  }, [computeReorderPoints, safetyFactor, lookbackDays, warehouseId]);

  const runPreviewWithLookback = useCallback(async (nextLookbackDays: 30 | 60 | 90 | 180 | 365) => {
    setLookbackDays(nextLookbackDays);
    setActiveTab("candidates");
    setDetailRow(null);
    setSettingsRow(null);
    await computeReorderPoints({
      safetyFactor,
      lookbackDays: nextLookbackDays,
      lookbackDaysLeadTime: 180,
      warehouseId: warehouseId || undefined,
    });
  }, [computeReorderPoints, safetyFactor, warehouseId]);

  const handleSelectAll = useCallback((checked: boolean) => {
    setCandidateRows((rows) => rows.map((row) => ({ ...row, _checked: checked })));
  }, []);

  const handleSelectRow = useCallback((stockId: string, checked: boolean) => {
    setCandidateRows((rows) =>
      rows.map((row) => (row.stock_id === stockId ? { ...row, _checked: checked } : row)),
    );
  }, []);

  useEffect(() => {
    setCandidateRows((rows) => {
      if (candidates.length === 0) {
        return [];
      }

      const checkedMap = new Map(rows.map((row) => [row.stock_id, row._checked]));
      return candidates.map((candidate) => ({
        ...candidate,
        _checked: checkedMap.get(candidate.stock_id) ?? false,
      }));
    });
  }, [candidates]);

  useEffect(() => {
    if (!detailRow) {
      return;
    }

    const activeRows = activeTab === "candidates" ? candidateRows : skipped;
    if (!activeRows.some((row) => row.stock_id === detailRow.stock_id)) {
      setDetailRow(null);
    }
  }, [activeTab, candidateRows, skipped, detailRow]);

  const selectedCount = useMemo(
    () => candidateRows.filter((row) => row._checked).length,
    [candidateRows],
  );

  const insufficientHistoryCount = useMemo(
    () => skipped.filter((row) => row.skip_reason === "insufficient_history").length,
    [skipped],
  );

  const zeroDemandCount = useMemo(
    () => skipped.filter((row) => row.skip_reason === "insufficient_history" && (row.movement_count ?? 0) === 0).length,
    [skipped],
  );

  const singleDemandCount = useMemo(
    () => skipped.filter((row) => row.skip_reason === "insufficient_history" && (row.movement_count ?? 0) === 1).length,
    [skipped],
  );

  const selectedStockIds = useMemo(
    () => candidateRows.filter((row) => row._checked).map((row) => row.stock_id),
    [candidateRows],
  );

  const detailCandidate = useMemo(
    () => (detailRow ? candidateRows.find((row) => row.stock_id === detailRow.stock_id) ?? null : null),
    [candidateRows, detailRow],
  );

  const leadTimeReviewCount = useMemo(
    () => skipped.filter((row) => row.skip_reason === "lead_time_unconfigured").length,
    [skipped],
  );

  const candidateReviewCount = useMemo(
    () => candidateRows.filter((row) => row.lead_time_confidence === "low" || Boolean(row.quality_note)).length,
    [candidateRows],
  );

  const isMaxLookback = lookbackDays >= 365;

  const handleApply = useCallback(async () => {
    if (selectedStockIds.length === 0) {
      return;
    }

    await applyReorderPoints(selectedStockIds, {
      safetyFactor,
      lookbackDays,
      lookbackDaysLeadTime: 180,
      warehouseId: warehouseId || undefined,
    });
    setCandidateRows([]);
    setDetailRow(null);
    setSettingsRow(null);
  }, [applyReorderPoints, selectedStockIds, safetyFactor, lookbackDays, warehouseId]);

  const getSkipReasonLabel = useCallback(
    (skipReason: string | null | undefined) => {
      if (!skipReason) {
        return "—";
      }
      return t(`skipReasonLabel.${skipReason}`, { defaultValue: skipReason });
    },
    [t],
  );

  const getLeadTimeStatusLabel = useCallback(
    (row: ReorderPointPreviewRow) => {
      if (row.skip_reason === "lead_time_unconfigured") {
        return t("leadTimeStatus.needsSetup");
      }

      switch (row.lead_time_source) {
        case "actual":
          return t("leadTimeStatus.actual");
        case "manual_override":
          return t("leadTimeStatus.manual");
        case "supplier_default":
          return t("leadTimeStatus.supplier");
        case "fallback_7d":
          return t("leadTimeStatus.needsSetup");
        default:
          return t("leadTimeStatus.unknown");
      }
    },
    [t],
  );

  const getLeadTimeVariant = useCallback((row: ReorderPointPreviewRow) => {
    if (row.skip_reason === "lead_time_unconfigured") {
      return "warning" as const;
    }
    if (row.lead_time_source === "manual_override" || row.lead_time_confidence === "high") {
      return "success" as const;
    }
    if (row.lead_time_confidence === "medium") {
      return "info" as const;
    }
    if (row.lead_time_confidence === "low" || row.lead_time_source === "supplier_default") {
      return "warning" as const;
    }
    return "outline" as const;
  }, []);

  const getReviewNote = useCallback(
    (row: ReorderPointPreviewRow) => {
      const notes: string[] = [];

      if (row.skip_reason === "lead_time_unconfigured") {
        notes.push(t("qualityMessage.leadTimeMissing"));
      } else if (row.skip_reason === "insufficient_history") {
        notes.push(
          t("qualityMessage.insufficientHistory", {
            count: row.movement_count ?? 0,
            days: lookbackDays,
          }),
        );
      } else if (row.skip_reason === "source_unresolved") {
        notes.push(t("qualityMessage.sourceUnresolved"));
      } else if (row.lead_time_source === "supplier_default") {
        notes.push(t("qualityMessage.supplierDefault"));
      } else if (
        row.lead_time_source === "actual"
        && row.lead_time_sample_count
        && row.lead_time_sample_count > 0
        && row.lead_time_confidence
        && row.lead_time_confidence !== "high"
      ) {
        notes.push(
          t("qualityMessage.lowConfidenceHistory", {
            count: row.lead_time_sample_count,
            confidence: t(`leadTimeConfidence.${row.lead_time_confidence}`),
          }),
        );
      }

      if (row.policy_type === "continuous" && (!row.target_stock_qty || row.target_stock_qty <= 0)) {
        notes.push(t("qualityMessage.continuousPolicyFallback"));
      }

      if (
        row.policy_type === "periodic"
        && (!row.target_stock_qty || row.target_stock_qty <= 0)
        && (!row.effective_horizon_days || row.effective_horizon_days <= 0)
      ) {
        notes.push(t("qualityMessage.periodicPolicyFallback"));
      }

      return notes.join(" ");
    },
    [lookbackDays, t],
  );

  const candidateColumns = [
    {
      id: "checkbox",
      header: (
        <input
          type="checkbox"
          className="accent-primary"
          onChange={(event) => handleSelectAll(event.target.checked)}
          checked={candidateRows.length > 0 && candidateRows.every((row) => row._checked)}
          ref={(element) => {
            if (element) {
              element.indeterminate = candidateRows.some((row) => row._checked) && !candidateRows.every((row) => row._checked);
            }
          }}
          aria-label={t("col.product")}
        />
      ),
      cell: (row: CandidateRow) => (
        <input
          type="checkbox"
          className="accent-primary"
          checked={row._checked}
          onClick={(event) => event.stopPropagation()}
          onChange={(event) => handleSelectRow(row.stock_id, event.target.checked)}
          aria-label={t("col.product")}
        />
      ),
      className: "w-8",
      headerClassName: "w-8",
    },
    {
      id: "product",
      header: t("compactCol.product"),
      cell: (row: CandidateRow) => (
        <div className="space-y-1">
          <p className="font-medium text-foreground">{row.product_name}</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">{row.warehouse_name}</span>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t(`policy.${row.policy_type ?? "continuous"}`, {
                defaultValue: row.policy_type ?? "continuous",
              })}
            </Badge>
          </div>
        </div>
      ),
    },
    {
      id: "stock",
      header: t("compactCol.stock"),
      cell: (row: CandidateRow) => (
        <div className="space-y-1">
          <p className="font-mono text-sm font-semibold tabular-nums text-foreground">{num(row.inventory_position)}</p>
          <p className="text-xs text-muted-foreground">
            {t("col.currentQty")}: {num(row.current_quantity)}
          </p>
        </div>
      ),
    },
    {
      id: "recommendation",
      header: t("compactCol.recommendation"),
      cell: (row: CandidateRow) => (
        <div className="space-y-1">
          <p className="font-mono text-sm font-semibold tabular-nums text-primary">{num(row.computed_reorder_point)}</p>
          <p className="text-xs text-muted-foreground">
            {t("col.suggestedOrderQty")}: {num(row.suggested_order_qty)}
          </p>
        </div>
      ),
    },
    {
      id: "lead_time",
      header: t("compactCol.leadTime"),
      cell: (row: CandidateRow) => (
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
              {row.lead_time_days && row.lead_time_days > 0 ? num(row.lead_time_days) : t("notSet")}
            </span>
            <Badge variant={getLeadTimeVariant(row)} className="normal-case tracking-normal">
              {getLeadTimeStatusLabel(row)}
            </Badge>
          </div>
          {row.lead_time_confidence ? (
            <p className="text-xs text-muted-foreground">
              {t("leadTimeConfidenceLabel", {
                value: t(`leadTimeConfidence.${row.lead_time_confidence}`),
              })}
            </p>
          ) : null}
        </div>
      ),
    },
    {
      id: "note",
      header: t("compactCol.note"),
      cell: (row: CandidateRow) => (
        <div className="space-y-1 text-xs">
          <p className="line-clamp-2 text-foreground">
            {getReviewNote(row) || t("candidateReasonHint", { count: row.movement_count ?? 0 })}
          </p>
          <p className="text-muted-foreground">
            {t(`demandBasisLabel.${normalizeDemandBasis(row.demand_basis)}`, {
              defaultValue: row.demand_basis ?? "sales_reservation",
            })}
          </p>
        </div>
      ),
    },
    {
      id: "actions",
      header: t("col.actions"),
      cell: (row: CandidateRow) => (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-auto px-2 py-1 text-xs"
          onClick={(event) => {
            event.stopPropagation();
            setSettingsRow(row);
          }}
        >
          {t("openSettings")}
        </Button>
      ),
    },
  ];

  const skippedColumns = [
    {
      id: "product",
      header: t("compactCol.product"),
      cell: (row: ReorderPointPreviewRow) => (
        <div className="space-y-1">
          <p className="font-medium text-foreground">{row.product_name}</p>
          <p className="text-xs text-muted-foreground">{row.warehouse_name}</p>
        </div>
      ),
    },
    {
      id: "reason",
      header: t("col.skipReason"),
      cell: (row: ReorderPointPreviewRow) => (
        <Badge variant="warning" className="normal-case tracking-normal">
          {getSkipReasonLabel(row.skip_reason)}
        </Badge>
      ),
    },
    {
      id: "note",
      header: t("compactCol.note"),
      cell: (row: ReorderPointPreviewRow) => (
        <p className="text-xs text-muted-foreground">{row.quality_note ?? "—"}</p>
      ),
    },
    {
      id: "actions",
      header: t("col.actions"),
      cell: (row: ReorderPointPreviewRow) => (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-auto px-2 py-1 text-xs"
          onClick={(event) => {
            event.stopPropagation();
            setSettingsRow(row);
          }}
        >
          {t("openSettings")}
        </Button>
      ),
    },
  ];

  const showPreview = candidates.length > 0 || skipped.length > 0;

  return (
    <SectionCard
      title={t("title")}
      description={t("description")}
      actions={
        showPreview ? (
          <div className="flex items-center gap-3">
            {candidates.length === 0 ? (
              <div className="mb-4 rounded-2xl border border-warning/30 bg-warning/8 p-4">
                <p className="text-sm font-semibold text-foreground">{t("guidanceTitleNoCandidates")}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {isMaxLookback
                    ? t("guidanceBodyMaxLookback", {
                        lookbackDays,
                        insufficientHistoryCount,
                        leadTimeReviewCount,
                        zeroDemandCount,
                        singleDemandCount,
                      })
                    : t("guidanceBodyNoCandidates", {
                        lookbackDays,
                        insufficientHistoryCount,
                        leadTimeReviewCount,
                      })}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {!isMaxLookback && lookbackDays < 180 ? (
                    <Button type="button" variant="outline" size="sm" onClick={() => void runPreviewWithLookback(180)}>
                      {t("guidanceTryLookback", { label: "180d" })}
                    </Button>
                  ) : null}
                  {!isMaxLookback && lookbackDays < 365 ? (
                    <Button type="button" variant="outline" size="sm" onClick={() => void runPreviewWithLookback(365)}>
                      {t("guidanceTryLookback", { label: "1yr" })}
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}

            <Badge variant="outline" className="normal-case tracking-normal">
              {t("candidatesCount", { count: candidates.length })} · {t("skippedCount", { count: skipped.length })}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                clearResults();
                setCandidateRows([]);
                setDetailRow(null);
                setSettingsRow(null);
              }}
            >
              {t("clear")}
            </Button>
          </div>
        ) : undefined
      }
    >
      {showPreview ? (
        <div className="mb-5 rounded-2xl border border-border/70 bg-muted/20 p-4">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_auto_minmax(220px,0.9fr)_auto] xl:items-end">
            <div className="min-w-0">
              <SafetyFactorSlider value={safetyFactor} onChange={setSafetyFactor} />
            </div>

            <LookbackSelector value={lookbackDays} onChange={setLookbackDays} label={t("lookback")} />

            <WarehouseFilter
              value={warehouseId}
              onChange={setWarehouseId}
              label={t("warehouse")}
              allWarehousesLabel={t("allWarehouses")}
              warehouses={warehouses}
            />

            <Button onClick={() => void handlePreview()} disabled={loading} className="h-10 gap-2 xl:w-auto">
              <SlidersHorizontal className="size-4" />
              {loading ? t("computing") : t("preview")}
            </Button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {leadTimeReviewCount > 0 ? (
              <Badge variant="warning" className="normal-case tracking-normal">
                {t("leadTimeMissingCount", { count: leadTimeReviewCount })}
              </Badge>
            ) : null}
            <p className="text-sm text-muted-foreground">{t("rerunPreviewHint")}</p>
          </div>
        </div>
      ) : (
        <div className="mb-5 grid items-start gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(280px,0.85fr)]">
          <div className="rounded-2xl border border-border/70 bg-muted/20 p-4">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_auto_minmax(220px,0.9fr)] xl:items-end">
              <div className="min-w-0">
                <SafetyFactorSlider value={safetyFactor} onChange={setSafetyFactor} />
              </div>

              <LookbackSelector value={lookbackDays} onChange={setLookbackDays} label={t("lookback")} />

              <WarehouseFilter
                value={warehouseId}
                onChange={setWarehouseId}
                label={t("warehouse")}
                allWarehousesLabel={t("allWarehouses")}
                warehouses={warehouses}
              />
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button onClick={() => void handlePreview()} disabled={loading} className="gap-2">
                <SlidersHorizontal className="size-4" />
                {loading ? t("computing") : t("preview")}
              </Button>
              <p className="text-sm text-muted-foreground">{t("setParamsAndClick")}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
            <div className="flex items-start gap-2">
              <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t("rulesTitle")}</p>
                  <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">
                    <li>{t("rulesDemand")}</li>
                    <li>{t("rulesLeadTime")}</li>
                    <li>{t("rulesApply")}</li>
                  </ul>
                </div>

                <div className="space-y-2 rounded-xl border border-border/70 bg-background/70 p-3 text-sm text-foreground">
                  <p><span className="font-medium">{t("formulaRopTitle")}</span> {t("formulaRopBody")}</p>
                  <p><span className="font-medium">{t("formulaInventoryTitle")}</span> {t("formulaInventoryBody")}</p>
                  <p><span className="font-medium">{t("formulaOrderTitle")}</span> {t("formulaOrderBody")}</p>
                </div>

                <div className="rounded-xl border border-warning/40 bg-warning/10 p-3">
                  <p className="text-sm font-medium text-foreground">{t("leadTimePolicyTitle")}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{t("leadTimePolicyBody")}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error ? (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {settingsRow ? (
        <div className="mb-4 rounded-xl border border-border/70 bg-background p-4 shadow-sm">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold">{t("settingsInlineTitle")}</h3>
              <p className="text-sm text-muted-foreground">
                {t("settingsInlineHint", {
                  product: settingsRow.product_name,
                  warehouse: settingsRow.warehouse_name,
                })}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setSettingsRow(null)}>
              {t("closeSettings")}
            </Button>
          </div>
          <SettingsTab productId={settingsRow.product_id} />
        </div>
      ) : null}

      {applyResult ? (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-success/20 bg-success/8 px-4 py-3 text-sm text-success">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
          <span>{t("applied", { updated: applyResult.updated_count, skipped: applyResult.skipped_count })}</span>
        </div>
      ) : null}

      {showPreview ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard
              label={t("summary.candidates")}
              value={candidates.length.toLocaleString()}
              hint={t("summary.candidatesHint")}
            />
            <SummaryCard
              label={t("summary.selected")}
              value={selectedCount.toLocaleString()}
              hint={t("summary.selectedHint")}
              tone={selectedCount > 0 ? "success" : "default"}
            />
            <SummaryCard
              label={t("summary.skipped")}
              value={skipped.length.toLocaleString()}
              hint={t("summary.skippedHint")}
            />
            <SummaryCard
              label={t("summary.leadTimeReview")}
              value={leadTimeReviewCount.toLocaleString()}
              hint={t("summary.leadTimeReviewHint")}
              tone={leadTimeReviewCount > 0 ? "warning" : "default"}
            />
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2 border-b border-border/70 pb-2">
              <button
                type="button"
                onClick={() => setActiveTab("candidates")}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "candidates"
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                }`}
              >
                {t("candidates")}
                <span className={`rounded-full px-2 py-0.5 text-xs ${
                  activeTab === "candidates" ? "bg-background/15 text-background" : "bg-background text-foreground"
                }`}>{candidates.length}</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("skipped")}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "skipped"
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                }`}
              >
                {t("skipped")}
                <span className={`rounded-full px-2 py-0.5 text-xs ${
                  activeTab === "skipped" ? "bg-background/15 text-background" : "bg-background text-foreground"
                }`}>{skipped.length}</span>
              </button>
            </div>

            {activeTab === "candidates" ? (
              <DataTable
                tableClassName="min-w-[780px]"
                columns={candidateColumns as any}
                data={candidateRows}
                loading={loading}
                loadingRowCount={5}
                emptyTitle={t("noCandidatesTitle")}
                emptyDescription={t("noCandidatesDesc")}
                toolbar={
                  <DataTableToolbar>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-foreground">{t("candidateToolbarTitle")}</p>
                      <p className="text-sm text-muted-foreground">
                        {selectedCount > 0
                          ? t("candidateToolbarSelected", { count: selectedCount })
                          : t("candidateToolbarHint")}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {candidateReviewCount > 0 ? (
                        <Badge variant="warning" className="normal-case tracking-normal">
                          {t("reviewNeededCount", { count: candidateReviewCount })}
                        </Badge>
                      ) : null}
                      <Button
                        variant="default"
                        onClick={() => void handleApply()}
                        disabled={applying || selectedCount === 0}
                        className="gap-2"
                      >
                        <CheckCircle2 className="size-4" />
                        {applying ? t("applying") : `${t("apply")} ${t("selectedCount", { count: selectedCount })}`}
                      </Button>
                    </div>
                  </DataTableToolbar>
                }
                getRowId={(row) => String(row.stock_id)}
                getRowClassName={(row) => (row._checked ? "bg-primary/5 hover:bg-primary/5" : undefined)}
                onRowClick={(row) => setDetailRow(row)}
                rowLabel={(row) => t("rowDetailAria", { product: row.product_name })}
              />
            ) : (
              <DataTable
                tableClassName="min-w-[620px]"
                columns={skippedColumns}
                data={skipped}
                loading={loading}
                loadingRowCount={5}
                emptyTitle={t("noSkippedTitle")}
                emptyDescription={t("noSkippedDesc")}
                toolbar={
                  <DataTableToolbar>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-foreground">{t("skippedToolbarTitle")}</p>
                      <p className="text-sm text-muted-foreground">{t("skippedToolbarHint")}</p>
                    </div>
                    {leadTimeReviewCount > 0 ? (
                      <Badge variant="warning" className="normal-case tracking-normal">
                        {t("leadTimeMissingCount", { count: leadTimeReviewCount })}
                      </Badge>
                    ) : null}
                  </DataTableToolbar>
                }
                getRowId={(row) => String(row.stock_id)}
                onRowClick={(row) => setDetailRow(row)}
                rowLabel={(row) => t("rowDetailAria", { product: row.product_name })}
              />
            )}

            {detailRow ? (
              <div className="rounded-2xl border border-border/70 bg-card/80 p-4 shadow-sm">
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        {activeTab === "candidates" ? t("detailCandidateLabel") : t("detailSkippedLabel")}
                      </p>
                      <h3 className="mt-1 text-lg font-semibold text-foreground">{detailRow.product_name}</h3>
                      <p className="text-sm text-muted-foreground">{detailRow.warehouse_name}</p>
                    </div>
                    <Badge variant={detailRow.skip_reason ? "warning" : "success"} className="normal-case tracking-normal">
                      {detailRow.skip_reason ? getSkipReasonLabel(detailRow.skip_reason) : t("detailReadyLabel")}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="normal-case tracking-normal">
                      {t(`policy.${detailRow.policy_type ?? "continuous"}`, {
                        defaultValue: detailRow.policy_type ?? "continuous",
                      })}
                    </Badge>
                    <Badge variant={getLeadTimeVariant(detailRow)} className="normal-case tracking-normal">
                      {getLeadTimeStatusLabel(detailRow)}
                    </Badge>
                    {detailRow.lead_time_confidence ? (
                      <Badge variant="outline" className="normal-case tracking-normal">
                        {t(`leadTimeConfidence.${detailRow.lead_time_confidence}`)}
                      </Badge>
                    ) : null}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t("detailDemandTitle")}</p>
                      <dl className="mt-3 grid gap-3">
                        <DetailMetric label={t("col.avgDailyUsage")} value={num(detailRow.avg_daily_usage)} />
                        <DetailMetric label={t("col.movements")} value={detailRow.movement_count ?? "—"} />
                        <DetailMetric
                          label={t("col.demandBasis")}
                          value={t(`demandBasisLabel.${normalizeDemandBasis(detailRow.demand_basis)}`, {
                            defaultValue: detailRow.demand_basis ?? "sales_reservation",
                          })}
                        />
                        <DetailMetric label={t("detailLookback")} value={`${lookbackDays}d`} />
                      </dl>
                    </div>

                    <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t("detailStockTitle")}</p>
                      <dl className="mt-3 grid gap-3">
                        <DetailMetric label={t("col.currentQty")} value={num(detailRow.current_quantity)} />
                        <DetailMetric label={t("col.onOrder")} value={num(detailRow.on_order_qty)} />
                        <DetailMetric label={t("col.inTransit")} value={num(detailRow.in_transit_qty)} />
                        <DetailMetric label={t("col.reserved")} value={num(detailRow.reserved_qty)} />
                        <DetailMetric label={t("col.inventoryPosition")} value={num(detailRow.inventory_position)} />
                      </dl>
                    </div>

                    <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t("detailRecommendationTitle")}</p>
                      <dl className="mt-3 grid gap-3">
                        <DetailMetric label={t("col.currentRop")} value={num(detailRow.current_reorder_point)} />
                        <DetailMetric label={t("col.computedRop")} value={num(detailRow.computed_reorder_point)} />
                        <DetailMetric label={t("col.safetyStock")} value={num(detailRow.safety_stock)} />
                        <DetailMetric label={t("col.targetStock")} value={num(detailRow.target_stock_level)} />
                        <DetailMetric label={t("col.suggestedOrderQty")} value={num(detailRow.suggested_order_qty)} />
                      </dl>
                    </div>

                    <div className="rounded-xl border border-border/70 bg-muted/20 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t("detailDecisionTitle")}</p>
                      <dl className="mt-3 grid gap-3">
                        <DetailMetric
                          label={t("col.leadTime")}
                          value={detailRow.lead_time_days && detailRow.lead_time_days > 0 ? num(detailRow.lead_time_days) : t("notSet")}
                        />
                        <DetailMetric label={t("col.ltSource")} value={getLeadTimeStatusLabel(detailRow)} />
                        <DetailMetric label={t("col.reviewCycle")} value={num(detailRow.review_cycle_days)} />
                        <DetailMetric label={t("col.planningHorizon")} value={num(detailRow.planning_horizon_days)} />
                        <DetailMetric label={t("col.effectiveHorizon")} value={num(detailRow.effective_horizon_days)} />
                      </dl>
                    </div>
                  </div>

                  <div className={`rounded-xl border px-4 py-3 text-sm ${detailRow.skip_reason ? "border-warning/40 bg-warning/10" : "border-border/70 bg-muted/20"}`}>
                    <p className="font-medium text-foreground">
                      {detailRow.skip_reason ? getSkipReasonLabel(detailRow.skip_reason) : t("detailReviewNote")}
                    </p>
                    <p className="mt-1 text-muted-foreground">{getReviewNote(detailRow) || t("detailNoQualityNote")}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {detailCandidate ? (
                      <Button
                        type="button"
                        variant={detailCandidate._checked ? "secondary" : "outline"}
                        size="sm"
                        onClick={() => handleSelectRow(detailCandidate.stock_id, !detailCandidate._checked)}
                      >
                        {detailCandidate._checked ? t("unselectRow") : t("selectRow")}
                      </Button>
                    ) : null}
                    <Button type="button" variant="ghost" size="sm" onClick={() => setSettingsRow(detailRow)}>
                      {t("openSettings")}
                    </Button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {!showPreview && !loading ? (
        <div className="rounded-2xl border border-dashed border-border/70 bg-muted/15 p-5">
          <div className="flex items-start gap-3">
            <SlidersHorizontal className="mt-0.5 size-5 shrink-0 text-muted-foreground/60" />
            <div>
              <p className="text-sm font-medium">{t("setParamsAndClick")}</p>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{t("formula")}</p>
            </div>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}

export { ReorderPointAdmin };
export default ReorderPointAdmin;