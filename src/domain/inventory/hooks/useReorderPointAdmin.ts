/** Hook for reorder point compute and apply workflow. */

import { useCallback, useState } from "react";

import { apiFetch } from "../../../lib/apiFetch";
import type {
  ReorderPointPreviewRow,
  ReorderPointComputeResponse,
  ReorderPointApplyResponse,
} from "../types";

export interface ReorderPointParams {
  safetyFactor: number;
  lookbackDays: 30 | 60 | 90 | 180 | 365;
  lookbackDaysLeadTime?: number;
  warehouseId?: string;
}

export function useReorderPointAdmin() {
  const [candidates, setCandidates] = useState<ReorderPointPreviewRow[]>([]);
  const [skipped, setSkipped] = useState<ReorderPointPreviewRow[]>([]);
  const [computeParams, setComputeParams] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<ReorderPointApplyResponse | null>(null);

  const computeReorderPoints = useCallback(async (params: ReorderPointParams) => {
    setLoading(true);
    setError(null);
    setApplyResult(null);
    try {
      const body = {
        safety_factor: params.safetyFactor,
        lookback_days: params.lookbackDays,
        lookback_days_lead_time: params.lookbackDaysLeadTime ?? 180,
        warehouse_id: params.warehouseId ?? null,
      };
      const resp = await apiFetch("/api/v1/inventory/reorder-points/compute", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        let msg = "Compute failed";
        try {
          const err = await resp.json();
          // FastAPI validation errors: err.detail is an array of {type, loc, msg, input}
          const detail = (err as { detail?: unknown }).detail;
          if (Array.isArray(detail)) {
            msg = detail.map((e: { msg?: string }) => e.msg ?? String(e)).join("; ");
          } else if (typeof detail === "string") {
            msg = detail;
          }
        } catch {
          // ignore parse error
        }
        setError(msg);
        setCandidates([]);
        setSkipped([]);
        return;
      }
      const data = (await resp.json()) as ReorderPointComputeResponse;
      setCandidates(data.candidate_rows);
      setSkipped(data.skipped_rows);
      setComputeParams(data.parameters);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compute failed");
      setCandidates([]);
      setSkipped([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const applyReorderPoints = useCallback(
    async (selectedStockIds: string[], params: ReorderPointParams) => {
      setApplying(true);
      setError(null);
      try {
        const body = {
          selected_stock_ids: selectedStockIds,
          safety_factor: params.safetyFactor,
          lookback_days: params.lookbackDays,
          lookback_days_lead_time: params.lookbackDaysLeadTime ?? 180,
          warehouse_id: params.warehouseId ?? null,
        };
        const resp = await apiFetch("/api/v1/inventory/reorder-points/apply", {
          method: "PUT",
          body: JSON.stringify(body),
        });
        if (!resp.ok) {
          let msg = "Apply failed";
          try {
            const err = await resp.json();
            const detail = (err as { detail?: unknown }).detail;
            if (Array.isArray(detail)) {
              msg = detail.map((e: { msg?: string }) => e.msg ?? String(e)).join("; ");
            } else if (typeof detail === "string") {
              msg = detail;
            }
          } catch {
            // ignore parse error
          }
          setError(msg);
          return;
        }
        const result = (await resp.json()) as ReorderPointApplyResponse;
        setApplyResult(result);
        // Clear preview after successful apply
        setCandidates([]);
        setSkipped([]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Apply failed");
      } finally {
        setApplying(false);
      }
    },
    [],
  );

  const clearResults = useCallback(() => {
    setCandidates([]);
    setSkipped([]);
    setComputeParams({});
    setApplyResult(null);
    setError(null);
  }, []);

  return {
    candidates,
    skipped,
    computeParams,
    loading,
    applying,
    error,
    applyResult,
    computeReorderPoints,
    applyReorderPoints,
    clearResults,
  };
}
