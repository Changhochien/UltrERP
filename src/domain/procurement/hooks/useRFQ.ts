/** RFQ data fetching hooks. */

import { useCallback, useEffect, useState } from "react";

import {
  createRFQ,
  getRFQ,
  getRFQComparison,
  listRFQs,
  submitRFQ,
  updateRFQ,
} from "../../../lib/api/procurement";
import type {
  RFQCreatePayload,
  RFQResponse,
  RFQUpdatePayload,
} from "../types";

// ---------------------------------------------------------------------------
// Shared fetch hook for RFQ operations
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

export function useRFQList(initialParams?: { status?: string; q?: string; page?: number }) {
  const [params, setParams] = useState(initialParams ?? {});
  const { data, loading, error, refetch } = useFetch(
    () => listRFQs(params),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [params],
  );
  return { data, loading, error, params, setParams, refetch };
}

export function useRFQ(rfqId: string | undefined) {
  const { data, loading, error, refetch } = useFetch(
    () => (rfqId ? getRFQ(rfqId) : Promise.resolve(null)),
    [rfqId],
  );
  return { rfq: data, loading, error, refetch };
}

export function useRFQComparison(rfqId: string | undefined) {
  const { data, loading, error, refetch } = useFetch(
    () => (rfqId ? getRFQComparison(rfqId) : Promise.resolve(null)),
    [rfqId],
  );
  return { data, loading, error, refetch };
}

export function useCreateRFQ() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(async (payload: RFQCreatePayload): Promise<RFQResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await createRFQ(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create RFQ");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { create, loading, error };
}

export function useUpdateRFQ() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback(async (rfqId: string, payload: RFQUpdatePayload): Promise<RFQResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await updateRFQ(rfqId, payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update RFQ");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { update, loading, error };
}

export function useSubmitRFQ() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (rfqId: string): Promise<RFQResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await submitRFQ(rfqId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit RFQ");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { submit, loading, error };
}
