import { useCallback, useEffect, useState } from "react";

import {
  createReorderSuggestionOrders,
  fetchReorderSuggestions,
} from "../../../lib/api/inventory";
import type {
  CreateReorderSuggestionOrdersRequest,
  CreateReorderSuggestionOrdersResponse,
  ReorderSuggestionItem,
} from "../types";

export function useReorderSuggestions(filters?: {
  warehouseId?: string;
}) {
  const [suggestions, setSuggestions] = useState<ReorderSuggestionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchReorderSuggestions({
        warehouseId: filters?.warehouseId,
      });
      if (response.ok) {
        setSuggestions(response.data.items);
        setTotal(response.data.total);
      } else {
        setSuggestions([]);
        setTotal(0);
        setError(response.error);
      }
    } catch (err) {
      setSuggestions([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load reorder suggestions");
    } finally {
      setLoading(false);
    }
  }, [filters?.warehouseId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { suggestions, total, loading, error, reload };
}

export function useCreateReorderSuggestionOrders() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (
      payload: CreateReorderSuggestionOrdersRequest,
    ): Promise<CreateReorderSuggestionOrdersResponse | null> => {
      setSubmitting(true);
      setError(null);
      try {
        const response = await createReorderSuggestionOrders(payload);
        if (response.ok) {
          return response.data;
        }
        setError(response.error);
        return null;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create reorder drafts");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { create, submitting, error };
}