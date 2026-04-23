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
  SupplierQuotationListResponse,
  SupplierQuotationResponse,
  SupplierQuotationUpdatePayload,
} from "../types";

export function useSupplierQuotationList(params?: {
  rfq_id?: string;
  status?: string;
  q?: string;
  page?: number;
}) {
  const [data, setData] = useState<SupplierQuotationListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(null);
    listSupplierQuotations(params)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load quotations"))
      .finally(() => setLoading(false));
  }, [params?.rfq_id, params?.status, params?.q, params?.page]);

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

export function useSupplierQuotation(quotationId: string | undefined) {
  const [sq, setSq] = useState<SupplierQuotationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    if (!quotationId) return;
    setLoading(true);
    setError(null);
    getSupplierQuotation(quotationId)
      .then(setSq)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load quotation"))
      .finally(() => setLoading(false));
  }, [quotationId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { sq, loading, error, refetch: fetch };
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
        const msg = err instanceof Error ? err.message : "Failed to create quotation";
        setError(msg);
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
        const msg = err instanceof Error ? err.message : "Failed to update quotation";
        setError(msg);
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
      const msg = err instanceof Error ? err.message : "Failed to award quotation";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { award, loading, error };
}

export function useRFQAward(rfqId: string | undefined) {
  const [award, setAward] = useState<AwardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    if (!rfqId) return;
    setLoading(true);
    setError(null);
    getRFQAward(rfqId)
      .then((data) => setAward(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load award"))
      .finally(() => setLoading(false));
  }, [rfqId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { award, loading, error, refetch: fetch };
}
