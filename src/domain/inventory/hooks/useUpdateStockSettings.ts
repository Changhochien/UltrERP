import { useCallback, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";
import type { InventoryStock, ReplenishmentPolicy } from "../types";

export interface UpdateStockSettingsPayload {
  reorder_point?: number;
  safety_factor?: number;
  lead_time_days?: number;
  policy_type?: ReplenishmentPolicy;
  target_stock_qty?: number;
  on_order_qty?: number;
  in_transit_qty?: number;
  reserved_qty?: number;
  planning_horizon_days?: number;
  review_cycle_days?: number;
}

export function useUpdateStockSettings() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback(
    async (
      stockId: string,
      payload: UpdateStockSettingsPayload,
    ): Promise<InventoryStock | null> => {
      setSubmitting(true);
      setError(null);
      try {
        const resp = await apiFetch(
          `/api/v1/inventory/stocks/${encodeURIComponent(stockId)}`,
          {
            method: "PATCH",
            body: JSON.stringify(payload),
          },
        );
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          setError((body as { detail?: string }).detail ?? "Failed to update settings");
          return null;
        }
        return (await resp.json()) as InventoryStock;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update settings");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { update, submitting, error, clearError: () => setError(null) };
}
