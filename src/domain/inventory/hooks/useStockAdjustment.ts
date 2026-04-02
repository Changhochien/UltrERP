/** Hook for stock adjustment submission and reason codes. */

import { useCallback, useEffect, useState } from "react";
import type { ReasonCodeItem, StockAdjustmentResponse } from "../types";
import { fetchReasonCodes, submitAdjustment } from "../../../lib/api/inventory";

export function useReasonCodes() {
  const [codes, setCodes] = useState<ReasonCodeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReasonCodes()
      .then((data) =>
        setCodes(data.items.filter((c) => c.user_selectable)),
      )
      .catch(() => setCodes([]))
      .finally(() => setLoading(false));
  }, []);

  return { codes, loading };
}

export function useStockAdjustment() {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<StockAdjustmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (payload: {
      product_id: string;
      warehouse_id: string;
      quantity_change: number;
      reason_code: string;
      notes?: string;
    }) => {
      setSubmitting(true);
      setError(null);
      setResult(null);

      try {
        const resp = await submitAdjustment(payload);
        if (resp.ok) {
          setResult(resp.data);
          return resp.data;
        }
        const detail = resp.error.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : detail.message;
        setError(msg);
        return null;
      } catch {
        setError("Network error — please try again.");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { submit, submitting, result, error, clearError: () => setError(null) };
}
