/**
 * React hooks for ledger queries (Epic 26.2).
 */

import { useCallback, useState, useEffect } from "react";

import type {
  AccountRootType,
  AccountType,
  LedgerSummaryResponse,
} from "@/domain/accounting/types";
import {
  fetchAccountLedger,
  fetchGeneralLedger,
} from "@/lib/api/accounting";

interface UseLedgerOptions {
  accountId?: string;
  journalEntryId?: string;
  fromDate?: string;
  toDate?: string;
  page?: number;
  pageSize?: number;
  voucherType?: string;
  includeReversed?: boolean;
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

export function useGeneralLedger(options: UseLedgerOptions = {}) {
  const {
    page = 1,
    pageSize = 50,
    accountId,
    fromDate,
    toDate,
    voucherType,
    includeReversed = false,
  } = options;

  const fetchFn = useCallback(
    () =>
      fetchGeneralLedger({
        page,
        pageSize,
        accountId,
        fromDate,
        toDate,
        voucherType,
        includeReversed,
      }),
    [page, pageSize, accountId, fromDate, toDate, voucherType, includeReversed]
  );

  return useAsyncData(fetchFn);
}

export function useAccountLedger(options: {
  accountId?: string;
  journalEntryId?: string;
  fromDate?: string;
  toDate?: string;
}) {
  const { accountId, journalEntryId, fromDate, toDate } = options;

  // If journalEntryId is provided, fetch GL entries for that journal entry
  const fetchFn = useCallback(async (): Promise<LedgerSummaryResponse | null> => {
    if (journalEntryId) {
      // Fetch GL entries filtered by journal entry
      const result = await fetchGeneralLedger({
        journalEntryId,
        page: 1,
        pageSize: 100,
      });

      // Convert to a ledger summary-like structure
      if (result.items.length === 0) {
        return null;
      }

      // Calculate totals from entries
      const totalDebit = result.items.reduce((sum, e) => sum + e.debit, 0);
      const totalCredit = result.items.reduce((sum, e) => sum + e.credit, 0);

      // Get account from first entry
      const firstEntry = result.items[0];

      return {
        account: {
          id: firstEntry.account_id,
          tenant_id: firstEntry.tenant_id,
          parent_id: null,
          parent_number: null,
          account_number: firstEntry.account_number,
          account_name: firstEntry.account_name,
          root_type: firstEntry.account_root_type as AccountRootType,
          report_type: "Balance Sheet",
          account_type: firstEntry.account_type as AccountType,
          is_group: false,
          is_frozen: false,
          is_disabled: false,
          sort_order: 0,
          currency_code: null,
          created_at: "",
          updated_at: "",
        },
        summary: {
          account_id: firstEntry.account_id,
          account_number: firstEntry.account_number,
          account_name: firstEntry.account_name,
          opening_balance: 0,
          total_debit: totalDebit,
          total_credit: totalCredit,
          closing_balance: 0,
          entries: result.items,
        },
      };
    }

    if (accountId) {
      return fetchAccountLedger(accountId, { fromDate, toDate });
    }

    return null;
  }, [accountId, journalEntryId, fromDate, toDate]);

  return useAsyncData(fetchFn);
}
