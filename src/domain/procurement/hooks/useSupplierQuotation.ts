/** Supplier Quotation data fetching hooks. */

import { useCallback, useEffect, useState } from "react";

import {
  createAward,
  createSupplierQuotation,
  getRFQAward,
  getSupplierQuotation,
  listSupplierQuotations,
  updateSupplierQuotation,
} from "../../../lib/api/procurement";
import type {
  AwardCreatePayload,
  AwardResponse,
  SupplierQuotationCreatePayload,
  SupplierQuotationResponse,
  SupplierQuotationUpdatePayload,
} from "../types";

// ---------------------------------------------------------------------------
// Shared fetch hook
// ---------------------------------------------------------------------------

function useFetch<T>(fetcher: () => Promise<T>, deps: React.DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useSupplierQuotationList(params?: {
  rfq_id?: string;
  status?: string;
  q?: string;
  page?: number;
}) {
  const { data, loading, error, refetch } = useFetch(
    () => listSupplierQuotations(params),
    [params?.rfq_id, params?.status, params?.q, params?.page],
  );
  return { data, loading, error, refetch };
}

export function useSupplierQuotation(quotationId: string | undefined) {
  const { data, loading, error, refetch } = useFetch(
    () => (quotationId ? getSupplierQuotation(quotationId) : Promise.resolve(null)),
    [quotationId],
  );
  return { sq: data, loading, error, refetch };
}

export function useCreateSupplierQuotation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: SupplierQuotationCreatePayload): Promise<SupplierQuotationResponse> => {
      setLoading(true);
      setError(null);
      try {
        return await createSupplierQuotation(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create quotation");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { create, loading, error };
}

export function useUpdateSupplierQuotation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback(
    async (quotationId: string, payload: SupplierQuotationUpdatePayload): Promise<SupplierQuotationResponse> => {
      setLoading(true);
      setError(null);
      try {
        return await updateSupplierQuotation(quotationId, payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to update quotation");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { update, loading, error };
}

export function useAward() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const award = useCallback(async (payload: AwardCreatePayload): Promise<AwardResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await createAward(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to award quotation");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { award, loading, error };
}

export function useRFQAward(rfqId: string | undefined) {
  const { data, loading, error, refetch } = useFetch(
    () => (rfqId ? getRFQAward(rfqId) : Promise.resolve(null)),
    [rfqId],
  );
  return { award: data, loading, error, refetch };
}
