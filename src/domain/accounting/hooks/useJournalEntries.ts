/**
 * React hooks for journal entry management (Epic 26.2).
 */

import { useCallback, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

import type {
  JournalEntry,
  JournalEntryDetail,
  JournalEntryListResponse,
  JournalEntryReverseResponse,
  JournalEntrySubmitResponse,
} from "@/domain/accounting/types";
import {
  createJournalEntry,
  fetchJournalEntries,
  fetchJournalEntry,
  reverseJournalEntry,
  submitJournalEntry,
  updateJournalEntry,
} from "@/lib/api/accounting";
import { useToast } from "@/hooks/useToast";

interface UseJournalEntriesOptions {
  page?: number;
  pageSize?: number;
  status?: string;
  voucherType?: string;
  fromDate?: string;
  toDate?: string;
}

interface UseJournalEntriesResult {
  entries: JournalEntry[];
  isLoading: boolean;
  error: Error | null;
  total: number;
  refetch: () => void;
}

function useAsyncData<T>(
  fetchFn: () => Promise<T>,
  deps: React.DependencyList = []
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetch = useCallback(() => {
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

  useEffect(() => {
    const cleanup = fetch();
    return cleanup;
  }, [fetch]);

  const refetch = useCallback(() => {
    fetch();
  }, [fetch]);

  return { data, error, isLoading, refetch };
}

export function useJournalEntries(options: UseJournalEntriesOptions = {}) {
  const { page = 1, pageSize = 20, status, voucherType, fromDate, toDate } = options;

  const fetchFn = useCallback(
    () =>
      fetchJournalEntries({
        page,
        pageSize,
        status,
        voucherType,
        fromDate,
        toDate,
      }),
    [page, pageSize, status, voucherType, fromDate, toDate]
  );

  const { data, error, isLoading, refetch } = useAsyncData(fetchFn);

  const entries = data?.items ?? [];
  const total = data?.total ?? 0;

  return { entries, isLoading, error, total, refetch };
}

export function useJournalEntry(journalEntryId: string | undefined) {
  const { t } = useTranslation();
  const toast = useToast();

  const fetchFn = useCallback(
    () => (journalEntryId ? fetchJournalEntry(journalEntryId) : Promise.resolve(null)),
    [journalEntryId]
  );

  const { data, error, isLoading, refetch } = useAsyncData(fetchFn);

  const submitEntry = useCallback(
    async (id: string): Promise<JournalEntrySubmitResponse> => {
      const result = await submitJournalEntry(id);
      return result;
    },
    []
  );

  const reverseEntry = useCallback(
    async (
      id: string,
      options?: { reversalDate?: string; cancelReason?: string }
    ): Promise<JournalEntryReverseResponse> => {
      const result = await reverseJournalEntry(id, options);
      return result;
    },
    []
  );

  const updateEntry = useCallback(
    async (
      id: string,
      data: Parameters<typeof updateJournalEntry>[1]
    ): Promise<JournalEntry> => {
      const result = await updateJournalEntry(id, data);
      return result;
    },
    []
  );

  return {
    entry: data,
    isLoading,
    error,
    refetch,
    submitEntry,
    reverseEntry,
    updateEntry,
    isSubmitting: false,
    isReversing: false,
  };
}

export function useCreateJournalEntry(
  onSuccess?: (entry: JournalEntry) => void
) {
  const { t } = useTranslation();
  const toast = useToast();

  const create = useCallback(
    async (data: Parameters<typeof createJournalEntry>[0]): Promise<JournalEntry> => {
      const entry = await createJournalEntry(data);
      onSuccess?.(entry);
      return entry;
    },
    [onSuccess]
  );

  return { createEntry: create, isLoading: false };
}
