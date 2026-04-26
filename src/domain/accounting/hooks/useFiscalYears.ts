/**
 * React hooks for fiscal year management (Epic 26).
 */

import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

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
import { useAsync, useAsyncFn } from "@/lib/hooks/useAsync";
import { ApiError } from "@/lib/api/errors";

export function useFiscalYears(page = 1, pageSize = 50) {
  const { data, error, isLoading, execute } = useAsync(
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
  const { data, error, isLoading, execute } = useAsync(() =>
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
  const [state, create] = useAsyncFn(
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
    [create, t]
  );

  return {
    createFiscalYear: createFiscalYearFn,
    ...state,
  };
}

export function useUpdateFiscalYear() {
  const { t } = useTranslation();
  const [state, update] = useAsyncFn(
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
    [update, t]
  );

  return {
    updateFiscalYear: updateFiscalYearFn,
    ...state,
  };
}

export function useCloseFiscalYear() {
  const { t } = useTranslation();
  const [state, close] = useAsyncFn(
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
    [close, t]
  );

  return {
    closeFiscalYear: closeFiscalYearFn,
    ...state,
  };
}

export function useReopenFiscalYear() {
  const { t } = useTranslation();
  const [state, reopen] = useAsyncFn(
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
    [reopen, t]
  );

  return {
    reopenFiscalYear: reopenFiscalYearFn,
    ...state,
  };
}
