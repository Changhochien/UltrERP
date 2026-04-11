/** Settings tab — per-warehouse ROP override, safety factor, lead time, supplier info. */

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import { useProductDetail } from "../hooks/useProductDetail";
import { useStockHistory } from "../hooks/useStockHistory";
import { useWarehouseContext } from "../context/WarehouseContext";
import { useUpdateStockSettings } from "../hooks/useUpdateStockSettings";
import type { WarehouseStockInfo } from "../types";

interface WarehouseSettings {
  warehouseId: string;
  stockId: string;
  warehouseName: string;
  reorderPoint: number;
  safetyFactor: number;
  leadTimeDays: number;
}

interface SettingsTabProps {
  productId: string;
}

export function SettingsTab({ productId }: SettingsTabProps) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail.settingsTab" });
  const { product, loading: productLoading } = useProductDetail(productId);
  const { selectedWarehouse } = useWarehouseContext();

  const stockId = selectedWarehouse?.id
    ? product?.warehouses.find((w) => w.warehouse_id === selectedWarehouse.id)?.stock_id
    : product?.warehouses[0]?.stock_id;

  const { avgDailyUsage, leadTimeDays } = useStockHistory(stockId ?? "");

  const { update, submitting: saving } = useUpdateStockSettings();

  // Per-warehouse settings state
  const [warehouseSettings, setWarehouseSettings] = useState<Record<string, WarehouseSettings>>({});
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  // Initialize settings when product loads
  const warehouses: WarehouseStockInfo[] = product?.warehouses ?? [];

  const getSettings = (wh: WarehouseStockInfo): WarehouseSettings => {
    if (warehouseSettings[wh.warehouse_id]) {
      return warehouseSettings[wh.warehouse_id];
    }
    return {
      warehouseId: wh.warehouse_id,
      stockId: wh.stock_id,
      warehouseName: wh.warehouse_name,
      reorderPoint: wh.reorder_point,
      safetyFactor: 0.5,
      leadTimeDays: leadTimeDays ?? 7,
    };
  };

  const updateSettings = (warehouseId: string, field: keyof WarehouseSettings, value: number) => {
    setWarehouseSettings((prev) => {
      const current = prev[warehouseId] ?? getSettings(
        warehouses.find((w) => w.warehouse_id === warehouseId)!,
      );
      return {
        ...prev,
        [warehouseId]: { ...current, [field]: value },
      };
    });
  };

  const hasOverride = (warehouseId: string) => {
    const ws = warehouseSettings[warehouseId];
    if (!ws) return false;
    const original = warehouses.find((w) => w.warehouse_id === warehouseId);
    return (
      original?.reorder_point !== ws.reorderPoint ||
      ws.safetyFactor !== 0.5 ||
      ws.leadTimeDays !== (leadTimeDays ?? 7)
    );
  };

  // Compute live ROP preview
  const computePreview = (ws: WarehouseSettings) => {
    if (!avgDailyUsage || !ws.leadTimeDays) return ws.reorderPoint;
    return Math.ceil(avgDailyUsage * ws.leadTimeDays * (1 + ws.safetyFactor));
  };

  const handleSave = useCallback(async (wh: WarehouseStockInfo) => {
    const ws = warehouseSettings[wh.warehouse_id] ?? getSettings(wh);
    const result = await update(ws.stockId, {
      reorder_point: ws.reorderPoint,
      lead_time_days: ws.leadTimeDays,
    });
    if (result) {
      setSavedMessage(t("saved", { warehouse: wh.warehouse_name }));
      setTimeout(() => setSavedMessage(null), 3000);
    }
  }, [warehouseSettings, warehouses, update]);

  if (productLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {savedMessage && (
        <div className="rounded-lg bg-success/10 px-4 py-2 text-sm text-success">
          {savedMessage}
        </div>
      )}

      {/* Per-warehouse settings */}
      {warehouses.map((wh) => {
        const ws = getSettings(wh);
        const override = hasOverride(wh.warehouse_id);
        const preview = computePreview(ws);

        return (
          <SectionCard
            key={wh.warehouse_id}
            title={wh.warehouse_name}
            actions={
              override ? (
                <span className="text-xs text-muted-foreground">{t("manualOverride")}</span>
              ) : undefined
            }
          >
            <div className="space-y-4">
              {/* Reorder Point */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">
                    {t("reorderPoint")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={ws.reorderPoint}
                    onChange={(e) =>
                      updateSettings(wh.warehouse_id, "reorderPoint", Number(e.target.value))
                    }
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">
                    {t("leadTime")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={ws.leadTimeDays}
                    onChange={(e) =>
                      updateSettings(wh.warehouse_id, "leadTimeDays", Number(e.target.value))
                    }
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">
                    {t("safetyFactor", { value: ws.safetyFactor.toFixed(1) })}
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={ws.safetyFactor}
                    onChange={(e) =>
                      updateSettings(wh.warehouse_id, "safetyFactor", Number(e.target.value))
                    }
                    className="w-full accent-primary"
                  />
                </div>
              </div>

              {/* ROP Preview */}
              <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm">
                <span className="text-muted-foreground">{t("computedRop")}</span>
                <span className="font-mono font-semibold tabular-nums">{preview.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground">
                  ({avgDailyUsage?.toFixed(1) ?? "—" } × {ws.leadTimeDays} × { (1 + ws.safetyFactor).toFixed(1) })
                </span>
              </div>

              {/* Save */}
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={() => void handleSave(wh)}
                  disabled={saving || !override}
                  className="gap-1.5"
                >
                  <Save size={14} />
                  {saving ? t("saving") : t("save")}
                </Button>
              </div>
            </div>
          </SectionCard>
        );
      })}

      {/* Supplier info */}
      <SectionCard title={t("supplierInfo")}>
        <p className="text-sm text-muted-foreground">{t("noSupplierConfigured")}</p>
      </SectionCard>
    </div>
  );
}
