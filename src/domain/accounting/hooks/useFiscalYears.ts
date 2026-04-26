/**
 * React hooks for fiscal year management (Epic 26).
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";

import type {
  CreateFiscalYearRequest,
  FiscalYear,
  FiscalYearFormData,
  UpdateFiscalYearRequest,
} from "@/domain/accounting/types";
import {
  closeFiscalYear,
  createFiscalYear,
  fetchFiscalYears,
  fetchOpenFiscalYears,
  reopenFiscalYear,
  updateFiscalYear,
} from "@/lib/api/accounting";
import { ApiError } from "@/lib/api/errors";
import { useToast } from "@/hooks/useToast";

// Simple async data hook
function useAsyncData<T>(
  fetchFn: () => Promise<T>,
  deps: React.DependencyList = []
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchFn()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const refetch = useCallback(() => {
    setIsLoading(true);
    setError(null);

    fetchFn()
      .then((result) => {
        setData(result);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err : new Error(String(err)));
        setIsLoading(false);
      });
  }, [fetchFn]);

  return { data, error, isLoading, refetch };
}

export function useFiscalYears(page = 1, pageSize = 50) {
  const { data, error, isLoading, execute } = useAsyncData(
    () => fetchFiscalYears(page, pageSize),
    [page, pageSize]
  );

  const refetch = useCallback(() => execute(), [execute]);

  return {
    fiscalYears: data ?? null,
    isLoading,
    error,
    refetch,
  };
}

export function useOpenFiscalYears() {
  const { data, error, isLoading, execute } = useAsyncData(() =>
    fetchOpenFiscalYears()
  );

  const refetch = useCallback(() => execute(), [execute]);

  return {
    openFiscalYears: data ?? [],
    isLoading,
    error,
    refetch,
  };
}

export function useCreateFiscalYear() {
  const { t } = useTranslation();
  const toast = useToast();

  const create = useCallback(
    async (data: CreateFiscalYearRequest): Promise<FiscalYear> => {
      return createFiscalYear(data);
    },
    []
  );

  const createFiscalYearFn = useCallback(
    async (data: FiscalYearFormData) => {
      try {
        const fiscalYear = await create({
          label: data.label,
          start_date: data.start_date.toISOString().split("T")[0],
          end_date: data.end_date.toISOString().split("T")[0],
          is_default: data.is_default,
        });
        toast.success(t("accounting.fiscalYearCreated", { label: fiscalYear.label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toast.error(message);
        throw err;
      }
    },
    [create, t, toast]
  );

  return {
    createFiscalYear: createFiscalYearFn,
    isLoading: false,
    error: null,
  };
}

export function useUpdateFiscalYear() {
  const { t } = useTranslation();
  const toast = useToast();

  const update = useCallback(
    async (
      fiscalYearId: string,
      data: UpdateFiscalYearRequest
    ): Promise<FiscalYear> => {
      return updateFiscalYear(fiscalYearId, data);
    },
    []
  );

  const updateFiscalYearFn = useCallback(
    async (fiscalYearId: string, data: UpdateFiscalYearRequest) => {
      try {
        const fiscalYear = await update(fiscalYearId, data);
        toast.success(t("accounting.fiscalYearUpdated", { label: fiscalYear.label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toast.error(message);
        throw err;
      }
    },
    [update, t, toast]
  );

  return {
    updateFiscalYear: updateFiscalYearFn,
    isLoading: false,
    error: null,
  };
}

export function useCloseFiscalYear() {
  const { t } = useTranslation();
  const toast = useToast();

  const close = useCallback(
    async (
      fiscalYearId: string,
      closureNotes?: string
    ): Promise<FiscalYear> => {
      return closeFiscalYear(fiscalYearId, closureNotes);
    },
    []
  );

  const closeFiscalYearFn = useCallback(
    async (fiscalYearId: string, label: string, closureNotes?: string) => {
      try {
        const fiscalYear = await close(fiscalYearId, closureNotes);
        toast.success(t("accounting.fiscalYearClosed", { label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toast.error(message);
        throw err;
      }
    },
    [close, t, toast]
  );

  return {
    closeFiscalYear: closeFiscalYearFn,
    isLoading: false,
    error: null,
  };
}

export function useReopenFiscalYear() {
  const { t } = useTranslation();
  const toast = useToast();

  const reopen = useCallback(
    async (fiscalYearId: string): Promise<FiscalYear> => {
      return reopenFiscalYear(fiscalYearId);
    },
    []
  );

  const reopenFiscalYearFn = useCallback(
    async (fiscalYearId: string, label: string) => {
      try {
        const fiscalYear = await reopen(fiscalYearId);
        toast.success(t("accounting.fiscalYearReopened", { label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toast.error(message);
        throw err;
      }
    },
    [reopen, t, toast]
  );

  return {
    reopenFiscalYear: reopenFiscalYearFn,
    isLoading: false,
    error: null,
  };
}
