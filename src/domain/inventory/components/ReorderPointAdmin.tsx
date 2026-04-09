/** Reorder point calculator admin — compute preview and apply selected rows. */

import { useCallback, useMemo, useState } from "react";

import { SlidersHorizontal, CheckCircle2, AlertCircle, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import { DataTable, DataTableToolbar } from "@/components/layout/DataTable";
import { useReorderPointAdmin } from "../hooks/useReorderPointAdmin";
import { useWarehouses } from "../hooks/useWarehouses";
import type { ReorderPointPreviewRow } from "../types";

const LOOKBACK_OPTIONS = [
  { value: 30, label: "30d" },
  { value: 60, label: "60d" },
  { value: 90, label: "90d" },
  { value: 180, label: "180d" },
  { value: 365, label: "1yr" },
] as const;

function SafetyFactorSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium">Safety Factor</span>
      <input
        type="range"
        min={0}
        max={100}
        value={value * 100}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="flex-1 accent-primary"
        aria-label="Safety factor"
      />
      <span className="w-10 text-right font-mono text-sm tabular-nums">{value.toFixed(1)}</span>
    </div>
  );
}

function num(value: number | null | undefined, fallback = "—"): string {
  if (value == null) return fallback;
  return value.toFixed(1);
}

function leadTimeSourceLabel(source: string | null | undefined): string {
  switch (source) {
    case "actual": return "Historical";
    case "supplier_default": return "Supplier default";
    case "fallback_7d": return "7d fallback";
    default: return source ?? "—";
  }
}

interface CandidateRow extends ReorderPointPreviewRow {
  _checked: boolean;
}

function ReorderPointAdmin() {
  const [safetyFactor, setSafetyFactor] = useState(0.5);
  const [lookbackDays, setLookbackDays] = useState<30 | 60 | 90 | 180 | 365>(90);
  const [warehouseId, setWarehouseId] = useState("");
  const [activeTab, setActiveTab] = useState<"candidates" | "skipped">("candidates");
  const [candidateRows, setCandidateRows] = useState<CandidateRow[]>([]);

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
    await computeReorderPoints({
      safetyFactor,
      lookbackDays,
      lookbackDaysLeadTime: 180,
      warehouseId: warehouseId || undefined,
    });
  }, [computeReorderPoints, safetyFactor, lookbackDays, warehouseId]);

  const handleSelectAll = useCallback((checked: boolean) => {
    setCandidateRows((rows) => rows.map((r) => ({ ...r, _checked: checked })));
  }, []);

  const handleSelectRow = useCallback((stockId: string, checked: boolean) => {
    setCandidateRows((rows) =>
      rows.map((r) => (r.stock_id === stockId ? { ...r, _checked: checked } : r)),
    );
  }, []);

  const selectedCount = useMemo(
    () => candidateRows.filter((r) => r._checked).length,
    [candidateRows],
  );

  const selectedStockIds = useMemo(
    () => candidateRows.filter((r) => r._checked).map((r) => r.stock_id),
    [candidateRows],
  );

  const handleApply = useCallback(async () => {
    if (selectedStockIds.length === 0) return;
    await applyReorderPoints(selectedStockIds, {
      safetyFactor,
      lookbackDays,
      lookbackDaysLeadTime: 180,
      warehouseId: warehouseId || undefined,
    });
    setCandidateRows([]);
  }, [applyReorderPoints, selectedStockIds, safetyFactor, lookbackDays, warehouseId]);

  // Sync candidates into local checkbox state
  const syncedCandidates = useMemo(() => {
    if (candidates.length === 0 && candidateRows.length === 0) return [];
    if (candidates.length === 0) return [];
    // Preserve checkbox state from candidateRows
    const checkedMap = new Map(candidateRows.map((r) => [r.stock_id, r._checked]));
    return candidates.map((c) => ({
      ...c,
      _checked: checkedMap.get(c.stock_id) ?? false,
    }));
  }, [candidates, candidateRows]);

  const candidateColumns = [
    {
      id: "checkbox",
      header: (
        <input
          type="checkbox"
          className="accent-primary"
          onChange={(e) => handleSelectAll(e.target.checked)}
          checked={syncedCandidates.length > 0 && syncedCandidates.every((r) => r._checked)}
          ref={(el) => {
            if (el) el.indeterminate = syncedCandidates.some((r) => r._checked) && !syncedCandidates.every((r) => r._checked);
          }}
          aria-label="Select all rows"
        />
      ),
      cell: (row: CandidateRow) => (
        <input
          type="checkbox"
          className="accent-primary"
          checked={row._checked}
          onChange={(e) => handleSelectRow(row.stock_id, e.target.checked)}
          aria-label={`Select ${row.product_name}`}
        />
      ),
      className: "w-8",
      headerClassName: "w-8",
    },
    {
      id: "product_name",
      header: "Product",
      cell: (row: CandidateRow) => <span className="font-medium">{row.product_name}</span>,
    },
    {
      id: "warehouse_name",
      header: "Warehouse",
      cell: (row: CandidateRow) => row.warehouse_name,
    },
    {
      id: "current_reorder_point",
      header: "Current ROP",
      cell: (row: CandidateRow) => (
        <span className="font-mono text-sm tabular-nums">{num(row.current_reorder_point)}</span>
      ),
    },
    {
      id: "computed_reorder_point",
      header: "Computed ROP",
      cell: (row: CandidateRow) =>
        row.computed_reorder_point != null ? (
          <span className="font-mono text-sm font-semibold tabular-nums text-primary">
            {num(row.computed_reorder_point)}
          </span>
        ) : (
          "—"
        ),
    },
    {
      id: "avg_daily_usage",
      header: "Avg Daily Usage",
      cell: (row: CandidateRow) => (
        <span className="font-mono text-sm tabular-nums">{num(row.avg_daily_usage)}</span>
      ),
    },
    {
      id: "lead_time_days",
      header: "Lead Time (d)",
      cell: (row: CandidateRow) => (
        <span className="font-mono text-sm tabular-nums">{num(row.lead_time_days)}</span>
      ),
    },
    {
      id: "safety_stock",
      header: "Safety Stock",
      cell: (row: CandidateRow) => (
        <span className="font-mono text-sm tabular-nums">{num(row.safety_stock)}</span>
      ),
    },
    {
      id: "demand_basis",
      header: "Demand Basis",
      cell: (row: CandidateRow) =>
        row.demand_basis ? (
          <Badge variant="outline" className="normal-case tracking-normal">{row.demand_basis}</Badge>
        ) : (
          "—"
        ),
    },
    {
      id: "movement_count",
      header: "Movements",
      cell: (row: CandidateRow) =>
        row.movement_count != null ? (
          <span className="font-mono text-sm tabular-nums">{row.movement_count}</span>
        ) : (
          "—"
        ),
    },
    {
      id: "lead_time_source",
      header: "LT Source",
      cell: (row: CandidateRow) => (
        <span className="text-xs text-muted-foreground">
          {leadTimeSourceLabel(row.lead_time_source)}
        </span>
      ),
    },
    {
      id: "quality_note",
      header: "Quality Note",
      cell: (row: CandidateRow) =>
        row.quality_note ? (
          <span className="text-xs text-muted-foreground">{row.quality_note}</span>
        ) : (
          "—"
        ),
    },
  ];

  const skippedColumns = [
    {
      id: "product_name",
      header: "Product",
      cell: (row: ReorderPointPreviewRow) => <span className="font-medium">{row.product_name}</span>,
    },
    {
      id: "warehouse_name",
      header: "Warehouse",
      cell: (row: ReorderPointPreviewRow) => row.warehouse_name,
    },
    {
      id: "current_reorder_point",
      header: "Current ROP",
      cell: (row: ReorderPointPreviewRow) => (
        <span className="font-mono text-sm tabular-nums">{num(row.current_reorder_point)}</span>
      ),
    },
    {
      id: "skip_reason",
      header: "Skip Reason",
      cell: (row: ReorderPointPreviewRow) =>
        row.skip_reason ? (
          <Badge variant="outline" className="normal-case tracking-normal text-muted-foreground">
            {row.skip_reason}
          </Badge>
        ) : (
          "—"
        ),
    },
    {
      id: "quality_note",
      header: "Note",
      cell: (row: ReorderPointPreviewRow) =>
        row.quality_note ? (
          <span className="text-xs text-muted-foreground">{row.quality_note}</span>
        ) : (
          "—"
        ),
    },
  ];

  const showPreview = candidates.length > 0 || skipped.length > 0;
  const hasResults = candidates.length > 0 || skipped.length > 0;

  return (
    <SectionCard
      title="Reorder Point Calculator"
      description="Preview computed reorder points from demand history, then apply selected rows."
      actions={
        showPreview ? (
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="normal-case tracking-normal">
              {candidates.length} candidates · {skipped.length} skipped
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { clearResults(); setCandidateRows([]); }}
            >
              Clear
            </Button>
          </div>
        ) : undefined
      }
    >
      {/* ── Parameter controls ── */}
      <div className="mb-5 rounded-xl border border-border/70 bg-muted/20 p-4">
        <div className="mb-4 flex flex-wrap items-center gap-6">
          {/* Safety factor */}
          <div className="min-w-52 flex-1">
            <SafetyFactorSlider value={safetyFactor} onChange={setSafetyFactor} />
          </div>

          {/* Lookback days */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Lookback</span>
            <div className="flex rounded-lg border border-border bg-background p-0.5">
              {LOOKBACK_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setLookbackDays(opt.value)}
                  className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                    lookbackDays === opt.value
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-pressed={lookbackDays === opt.value}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Warehouse filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="rop-warehouse" className="text-sm font-medium">Warehouse</label>
            <select
              id="rop-warehouse"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
              className="h-8 rounded-lg border border-input bg-background px-2 text-sm"
            >
              <option value="">All warehouses</option>
              {warehouses.map((wh) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => void handlePreview()}
            disabled={loading}
            className="gap-2"
          >
            <SlidersHorizontal className="size-4" />
            {loading ? "Computing…" : "Preview"}
          </Button>

          {hasResults && (
            <Button
              variant="default"
              onClick={() => void handleApply()}
              disabled={applying || selectedCount === 0}
              className="gap-2"
            >
              <CheckCircle2 className="size-4" />
              {applying ? "Applying…" : `Apply Selected (${selectedCount})`}
            </Button>
          )}
        </div>
      </div>

      {/* ── Error feedback ── */}
      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Apply success ── */}
      {applyResult && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-success/20 bg-success/8 px-4 py-3 text-sm text-success">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
          <span>
            Applied {applyResult.updated_count} rows · {applyResult.skipped_count} skipped
          </span>
        </div>
      )}

      {/* ── Results tabs ── */}
      {showPreview && (
        <div className="space-y-4">
          {/* Tab bar */}
          <div className="flex items-center gap-1 border-b border-border/70">
            <button
              type="button"
              onClick={() => setActiveTab("candidates")}
              className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === "candidates"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Candidate Rows
              <Badge variant="outline" className="normal-case tracking-normal">{candidates.length}</Badge>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("skipped")}
              className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === "skipped"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              Skipped Rows
              <Badge variant="outline" className="normal-case tracking-normal">{skipped.length}</Badge>
            </button>
          </div>

          {/* Candidate table */}
          {activeTab === "candidates" && (
            <DataTable
              tableClassName="min-w-[900px]"
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              columns={candidateColumns as any}
              data={syncedCandidates}
              loading={loading}
              loadingRowCount={5}
              emptyTitle="No candidate rows."
              emptyDescription="No products met eligibility criteria for the selected scope."
              toolbar={
                <DataTableToolbar>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Info className="size-3.5" />
                    <span>
                      {syncedCandidates.length > 0
                        ? `${syncedCandidates.length} candidate rows · check rows to include in apply`
                        : "Run Preview to see candidate rows"}
                    </span>
                  </div>
                </DataTableToolbar>
              }
              getRowId={(row) => String(row.stock_id)}
            />
          )}

          {/* Skipped table */}
          {activeTab === "skipped" && (
            <DataTable
              tableClassName="min-w-[600px]"
              columns={skippedColumns}
              data={skipped}
              loading={loading}
              loadingRowCount={5}
              emptyTitle="No skipped rows."
              emptyDescription="All evaluated rows had sufficient data."
              toolbar={
                <DataTableToolbar>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Info className="size-3.5" />
                    <span>Skipped rows were not eligible and will not be modified.</span>
                  </div>
                </DataTableToolbar>
              }
              getRowId={(row) => String(row.stock_id)}
            />
          )}
        </div>
      )}

      {/* ── Empty state (no preview run yet) ── */}
      {!showPreview && !loading && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <SlidersHorizontal className="mb-3 size-10 text-muted-foreground/40" />
          <p className="text-sm font-medium">Set parameters and click Preview</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Computed ROP = Safety Stock + (Lead Time × Avg Daily Usage)
          </p>
        </div>
      )}
    </SectionCard>
  );
}

export { ReorderPointAdmin };
export default ReorderPointAdmin;
