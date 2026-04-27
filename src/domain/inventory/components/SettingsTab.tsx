/** Settings tab — per-warehouse ROP override, safety factor, lead time, supplier info. */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import { ProductSuppliersPanel } from "./ProductSuppliersPanel";
import { useProductDetail } from "../hooks/useProductDetail";
import { useStockHistory } from "../hooks/useStockHistory";
import { useUpdateStockSettings } from "../hooks/useUpdateStockSettings";
import type { WarehouseStockInfo } from "../types";

interface WarehouseSettings {
  warehouseId: string;
  stockId: string;
  warehouseName: string;
  reorderPoint: number;
  safetyFactor: number;
  leadTimeDays: number;
  reviewCycleDays: number;
}

interface SettingsTabProps {
  productId: string;
  warehouseFilterId?: string;
  onSaveSuccess?: () => void | Promise<void>;
}

interface WarehouseSettingsCardProps {
  warehouse: WarehouseStockInfo;
  settings: WarehouseSettings;
  hasOverride: boolean;
  saving: boolean;
  updateSettings: (warehouseId: string, field: keyof WarehouseSettings, value: number) => void;
  onSave: (warehouse: WarehouseStockInfo) => Promise<void>;
}

function computePreview(
  avgDailyUsage: number | null,
  settings: WarehouseSettings,
  currentStock: number,
) {
  if (avgDailyUsage == null || settings.leadTimeDays <= 0) {
    return null;
  }

  const safetyStock = avgDailyUsage * settings.safetyFactor * settings.leadTimeDays;
  const computedRop = Math.ceil((avgDailyUsage * settings.leadTimeDays) + safetyStock);
  const targetStock = Math.ceil(
    (avgDailyUsage * (settings.leadTimeDays + settings.reviewCycleDays)) + safetyStock,
  );
  const suggestedOrderQty = Math.max(0, targetStock - currentStock);

  return {
    safetyStock,
    computedRop,
    targetStock,
    suggestedOrderQty,
  };
}

function WarehouseSettingsCard({
  warehouse,
  settings,
  hasOverride,
  saving,
  updateSettings,
  onSave,
}: WarehouseSettingsCardProps) {
  const { t } = useTranslation("inventory");
  const { avgDailyUsage } = useStockHistory(warehouse.stock_id);
  const preview = computePreview(avgDailyUsage, settings, warehouse.current_stock);

  return (
    <SectionCard
      title={warehouse.warehouse_name}
      actions={
        hasOverride ? (
          <span className="text-xs text-muted-foreground">{t("manualOverride")}</span>
        ) : undefined
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              {t("reorderPoint")}
            </label>
            <input
              type="number"
              min={0}
              value={settings.reorderPoint}
              onChange={(e) =>
                updateSettings(warehouse.warehouse_id, "reorderPoint", Number(e.target.value))
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
              value={settings.leadTimeDays}
              onChange={(e) =>
                updateSettings(warehouse.warehouse_id, "leadTimeDays", Number(e.target.value))
              }
              className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              {t("reviewCycle")}
            </label>
            <input
              type="number"
              min={0}
              value={settings.reviewCycleDays}
              onChange={(e) =>
                updateSettings(warehouse.warehouse_id, "reviewCycleDays", Number(e.target.value))
              }
              className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              {t("safetyFactor", { value: settings.safetyFactor.toFixed(1) })}
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={settings.safetyFactor}
              onChange={(e) =>
                updateSettings(warehouse.warehouse_id, "safetyFactor", Number(e.target.value))
              }
              className="w-full accent-primary"
            />
          </div>
        </div>

        <div className="space-y-2 rounded-lg bg-muted/50 px-3 py-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground">{t("computedRop")}</span>
            <span className="font-mono font-semibold tabular-nums">
              {preview ? preview.computedRop.toLocaleString() : "—"}
            </span>
            <span className="text-xs text-muted-foreground">
              ({avgDailyUsage?.toFixed(1) ?? "—"} × {settings.leadTimeDays}) + safety stock
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2 text-xs text-muted-foreground sm:grid-cols-3">
            <div>
              {t("safetyStock")}:{" "}
              <span className="font-mono text-foreground">
                {preview ? preview.safetyStock.toFixed(1) : "—"}
              </span>
            </div>
            <div>
              {t("targetStock")}:{" "}
              <span className="font-mono text-foreground">
                {preview ? preview.targetStock.toLocaleString() : "—"}
              </span>
            </div>
            <div>
              {t("suggestedOrderQty")}:{" "}
              <span className="font-mono text-foreground">
                {preview ? preview.suggestedOrderQty.toLocaleString() : "—"}
              </span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {t("previewNote", { currentStock: warehouse.current_stock })}
          </p>
        </div>

        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={() => void onSave(warehouse)}
            disabled={saving || !hasOverride}
            className="gap-1.5"
          >
            <Save size={14} />
            {saving ? t("saving") : t("save")}
          </Button>
        </div>
      </div>
    </SectionCard>
  );
}

export function SettingsTab({ productId, warehouseFilterId, onSaveSuccess }: SettingsTabProps) {
  const { t } = useTranslation("inventory");
  const { product, loading: productLoading, reload } = useProductDetail(productId);
  const { update, submitting: saving } = useUpdateStockSettings();

  const [warehouseSettings, setWarehouseSettings] = useState<Record<string, WarehouseSettings>>({});
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const warehouses: WarehouseStockInfo[] = (product?.warehouses ?? []).filter((warehouse) => {
    if (!warehouseFilterId) {
      return true;
    }
    return warehouse.warehouse_id === warehouseFilterId;
  });

  const getDefaultSettings = (warehouse: WarehouseStockInfo): WarehouseSettings => ({
    warehouseId: warehouse.warehouse_id,
    stockId: warehouse.stock_id,
    warehouseName: warehouse.warehouse_name,
    reorderPoint: warehouse.reorder_point,
    safetyFactor: warehouse.safety_factor > 0 ? warehouse.safety_factor : 0.5,
    leadTimeDays: warehouse.lead_time_days > 0 ? warehouse.lead_time_days : 7,
    reviewCycleDays: warehouse.review_cycle_days ?? 0,
  });

  const getSettings = (warehouse: WarehouseStockInfo): WarehouseSettings =>
    warehouseSettings[warehouse.warehouse_id] ?? getDefaultSettings(warehouse);

  const updateSettings = (
    warehouseId: string,
    field: keyof WarehouseSettings,
    value: number,
  ) => {
    setWarehouseSettings((prev) => {
      const warehouse = warehouses.find((item) => item.warehouse_id === warehouseId);
      if (!warehouse) return prev;

      const current = prev[warehouseId] ?? getDefaultSettings(warehouse);
      return {
        ...prev,
        [warehouseId]: { ...current, [field]: value },
      };
    });
  };

  const hasOverride = (warehouseId: string) => {
    const draft = warehouseSettings[warehouseId];
    if (!draft) return false;

    const warehouse = warehouses.find((item) => item.warehouse_id === warehouseId);
    if (!warehouse) return false;

    const defaults = getDefaultSettings(warehouse);
    return (
      defaults.reorderPoint !== draft.reorderPoint
      || defaults.safetyFactor !== draft.safetyFactor
      || defaults.leadTimeDays !== draft.leadTimeDays
      || defaults.reviewCycleDays !== draft.reviewCycleDays
    );
  };

  const handleSave = async (warehouse: WarehouseStockInfo) => {
    const settings = warehouseSettings[warehouse.warehouse_id] ?? getSettings(warehouse);
    const result = await update(settings.stockId, {
      reorder_point: settings.reorderPoint,
      safety_factor: settings.safetyFactor,
      lead_time_days: settings.leadTimeDays,
      review_cycle_days: settings.reviewCycleDays,
    });

    if (!result) return;

    setWarehouseSettings((prev) => {
      const next = { ...prev };
      delete next[warehouse.warehouse_id];
      return next;
    });
    await reload();
    if (onSaveSuccess) {
      await onSaveSuccess();
      return;
    }

    setSavedMessage(t("saved", { warehouse: warehouse.warehouse_name }));
    setTimeout(() => setSavedMessage(null), 3000);
  };

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

      {warehouses.map((warehouse) => (
        <WarehouseSettingsCard
          key={warehouse.warehouse_id}
          warehouse={warehouse}
          settings={getSettings(warehouse)}
          hasOverride={hasOverride(warehouse.warehouse_id)}
          saving={saving}
          updateSettings={updateSettings}
          onSave={handleSave}
        />
      ))}
      <ProductSuppliersPanel productId={productId} />
    </div>
  );
}
