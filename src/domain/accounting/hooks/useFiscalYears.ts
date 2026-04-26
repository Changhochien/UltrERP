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
  const { data, error, isLoading, refetch } = useAsyncData(
    () => fetchFiscalYears(page, pageSize),
    [page, pageSize]
  );

  return {
    fiscalYears: data ?? null,
    isLoading,
    error,
    refetch,
  };
}

export function useOpenFiscalYears() {
  const { data, error, isLoading, refetch } = useAsyncData(() =>
    fetchOpenFiscalYears()
  );

  return {
    openFiscalYears: data ?? [],
    isLoading,
    error,
    refetch,
  };
}

export function useCreateFiscalYear() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const [isCreating, setIsCreating] = useState(false);

  const create = useCallback(
    async (data: CreateFiscalYearRequest): Promise<FiscalYear> => {
      return createFiscalYear(data);
    },
    []
  );

  const createFiscalYearFn = useCallback(
    async (data: FiscalYearFormData) => {
      setIsCreating(true);
      try {
        const fiscalYear = await create({
          label: data.label,
          start_date: (data.start_date ?? new Date()).toISOString().split("T")[0],
          end_date: (data.end_date ?? new Date()).toISOString().split("T")[0],
          is_default: data.is_default,
        });
        toastSuccess(t("accounting.fiscalYearCreated", { label: fiscalYear.label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toastError(message);
        throw err;
      } finally {
        setIsCreating(false);
      }
    },
    [create, t, toastSuccess, toastError]
  );

  return {
    createFiscalYear: createFiscalYearFn,
    isCreating,
    error: null,
  };
}

export function useUpdateFiscalYear() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const [isUpdating, setIsUpdating] = useState(false);

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
      setIsUpdating(true);
      try {
        const fiscalYear = await update(fiscalYearId, data);
        toastSuccess(t("accounting.fiscalYearUpdated", { label: fiscalYear.label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toastError(message);
        throw err;
      } finally {
        setIsUpdating(false);
      }
    },
    [update, t, toastSuccess, toastError]
  );

  return {
    updateFiscalYear: updateFiscalYearFn,
    isUpdating,
    error: null,
  };
}

export function useCloseFiscalYear() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const [isClosing, setIsClosing] = useState(false);

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
      setIsClosing(true);
      try {
        const fiscalYear = await close(fiscalYearId, closureNotes);
        toastSuccess(t("accounting.fiscalYearClosed", { label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toastError(message);
        throw err;
      } finally {
        setIsClosing(false);
      }
    },
    [close, t, toastSuccess, toastError]
  );

  return {
    closeFiscalYear: closeFiscalYearFn,
    isClosing,
    error: null,
  };
}

export function useReopenFiscalYear() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const [isReopening, setIsReopening] = useState(false);

  const reopen = useCallback(
    async (fiscalYearId: string): Promise<FiscalYear> => {
      return reopenFiscalYear(fiscalYearId);
    },
    []
  );

  const reopenFiscalYearFn = useCallback(
    async (fiscalYearId: string, label: string) => {
      setIsReopening(true);
      try {
        const fiscalYear = await reopen(fiscalYearId);
        toastSuccess(t("accounting.fiscalYearReopened", { label }));
        return fiscalYear;
      } catch (err) {
        const error = err as ApiError;
        const message = typeof error.detail === "string"
          ? error.detail
          : error.detail?.errors?.[0]?.message ?? t("common.error");
        toastError(message);
        throw err;
      } finally {
        setIsReopening(false);
      }
    },
    [reopen, t, toastSuccess, toastError]
  );

  return {
    reopenFiscalYear: reopenFiscalYearFn,
    isReopening,
    error: null,
  };
}
