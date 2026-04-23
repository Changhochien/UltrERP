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
  RFQComparisonResponse,
  RFQCreatePayload,
  RFQListResponse,
  RFQResponse,
  RFQUpdatePayload,
} from "../types";

export function useRFQList(initialParams?: { status?: string; q?: string; page?: number }) {
  const [data, setData] = useState<RFQListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState(initialParams ?? {});

  const fetch = useCallback(
    (overrides?: typeof params) => {
      const p = { ...params, ...overrides };
      setLoading(true);
      setError(null);
      listRFQs(p)
        .then(setData)
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to load RFQs"))
        .finally(() => setLoading(false));
    },
    [params],
  );

  useEffect(() => { fetch(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, params, setParams, refetch: fetch };
}

export function useRFQ(rfqId: string | undefined) {
  const [rfq, setRfq] = useState<RFQResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    if (!rfqId) return;
    setLoading(true);
    setError(null);
    getRFQ(rfqId)
      .then(setRfq)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load RFQ"))
      .finally(() => setLoading(false));
  }, [rfqId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { rfq, loading, error, refetch: fetch };
}

export function useRFQComparison(rfqId: string | undefined) {
  const [data, setData] = useState<RFQComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    if (!rfqId) return;
    setLoading(true);
    setError(null);
    getRFQComparison(rfqId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load comparison"))
      .finally(() => setLoading(false));
  }, [rfqId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
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
      const msg = err instanceof Error ? err.message : "Failed to create RFQ";
      setError(msg);
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
      const msg = err instanceof Error ? err.message : "Failed to update RFQ";
      setError(msg);
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
      const msg = err instanceof Error ? err.message : "Failed to submit RFQ";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { submit, loading, error };
}
