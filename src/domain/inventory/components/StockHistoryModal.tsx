/** Modal overlay displaying stock history trend chart for a specific stock item. */

import { X } from "lucide-react";
import { useStockHistory } from "../hooks/useStockHistory";
import { StockTrendChart } from "./StockTrendChart";

interface StockHistoryModalProps {
  stockId: string;
  productName: string;
  warehouseName: string;
  onClose: () => void;
}

export function StockHistoryModal({
  stockId,
  productName,
  warehouseName,
  onClose,
}: StockHistoryModalProps) {
  const {
    history,
    currentStock,
    reorderPoint,
    avgDailyUsage,
    safetyStock,
    loading,
    error,
  } = useStockHistory(stockId, { granularity: "raw" });

  return (
    <div
      className="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-background p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">{productName}</h2>
            <p className="text-sm text-muted-foreground">{warehouseName}</p>
            <p className="mt-1 text-sm">
              <span className={currentStock < reorderPoint ? "font-semibold text-destructive" : ""}>
                Stock: {currentStock}
              </span>
              <span className="mx-2 text-muted-foreground">·</span>
              <span className="text-muted-foreground">ROP: {reorderPoint}</span>
              {avgDailyUsage != null && (
                <>
                  <span className="mx-2 text-muted-foreground">·</span>
                  <span className="text-muted-foreground">Usage: {avgDailyUsage.toFixed(1)}/day</span>
                </>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
            aria-label="Close modal"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex h-64 items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {/* Chart */}
        {!loading && (
          <StockTrendChart
            points={history}
            reorderPoint={reorderPoint}
            safetyStock={safetyStock ?? undefined}
            avgDailyUsage={avgDailyUsage ?? undefined}
          />
        )}
      </div>
    </div>
  );
}