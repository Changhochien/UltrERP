/**
 * React hooks for account management (Epic 26).
 */

import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";

import type {
  Account,
  AccountTreeNode,
  AccountTreeResponse,
  CreateAccountRequest,
  UpdateAccountRequest,
} from "@/domain/accounting/types";
import {
  createAccount,
  deleteAccount,
  disableAccount,
  fetchAccount,
  fetchAccountTree,
  freezeAccount,
  seedStarterChart,
  unfreezeAccount,
  updateAccount,
} from "@/lib/api/accounting";
import { useToast } from "@/hooks/useToast";

export function useAccountTree(includeDisabled = false) {
  const fetchTree = useCallback(
    () => fetchAccountTree(includeDisabled),
    [includeDisabled]
  );
  const { data, error, isLoading, refetch } = useAsyncData(fetchTree);

  return {
    tree: data ?? null,
    isLoading,
    error,
    refetch,
  };
}

export function useAccount(accountId: string | null) {
  const fetchOne = useCallback(
    () => (accountId ? fetchAccount(accountId) : Promise.resolve(null)),
    [accountId]
  );
  const { data, error, isLoading, refetch } = useAsyncData(fetchOne);

  return {
    account: data,
    isLoading,
    error,
    refetch,
  };
}

export function useCreateAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const create = useCallback(
    async (data: CreateAccountRequest): Promise<Account> => {
      const account = await createAccount(data);
      toast.success(t("accounting.accountCreated", { name: account.account_name }));
      onSuccess?.(account);
      return account;
    },
    [t, toast, onSuccess]
  );

  return { createAccount: create, isLoading: false };
}

export function useUpdateAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const update = useCallback(
    async (accountId: string, data: UpdateAccountRequest): Promise<Account> => {
      const account = await updateAccount(accountId, data);
      toast.success(t("accounting.accountUpdated", { name: account.account_name }));
      onSuccess?.(account);
      return account;
    },
    [t, toast, onSuccess]
  );

  return { updateAccount: update, isLoading: false };
}

export function useFreezeAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const freeze = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      const account = await freezeAccount(accountId);
      toast.success(t("accounting.accountFrozen", { name: accountName }));
      onSuccess?.(account);
      return account;
    },
    [t, toast, onSuccess]
  );

  return { freezeAccount: freeze, isLoading: false };
}

export function useUnfreezeAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const unfreeze = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      const account = await unfreezeAccount(accountId);
      toast.success(t("accounting.accountUnfrozen", { name: accountName }));
      onSuccess?.(account);
      return account;
    },
    [t, toast, onSuccess]
  );

  return { unfreezeAccount: unfreeze, isLoading: false };
}

export function useDisableAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const disable = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      const account = await disableAccount(accountId);
      toast.success(t("accounting.accountDisabled", { name: accountName }));
      onSuccess?.(account);
      return account;
    },
    [t, toast, onSuccess]
  );

  return { disableAccount: disable, isLoading: false };
}

export function useDeleteAccount(onSuccess?: () => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const remove = useCallback(
    async (accountId: string, accountName: string): Promise<void> => {
      await deleteAccount(accountId);
      toast.success(t("accounting.accountDeleted", { name: accountName }));
      onSuccess?.();
    },
    [t, toast, onSuccess]
  );

  return { deleteAccount: remove, isLoading: false };
}

export function useSeedStarterChart(onSuccess?: (result: AccountTreeResponse) => void) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const seed = useCallback(
    async (): Promise<AccountTreeResponse> => {
      const result = await seedStarterChart();
      toast.success(t("accounting.starterChartSeeded", { count: result.total_accounts }));
      onSuccess?.(result);
      return result;
    },
    [t, toast, onSuccess]
  );

  return { seedChart: seed, isLoading: false };
}

/**
 * Flatten an account tree into a list of all accounts.
 */
export function useFlattenedAccounts(tree: AccountTreeResponse | null): Account[] {
  return useMemo(() => {
    if (!tree) return [];

    const result: Account[] = [];

    function traverse(node: AccountTreeNode) {
      result.push(node);
      for (const child of node.children) {
        traverse(child);
      }
    }

    for (const root of tree.roots) {
      traverse(root);
    }

    return result;
  }, [tree]);
}

/**
 * Get accounts grouped by root type.
 */
export function useAccountsByRootType(tree: AccountTreeResponse | null) {
  return useMemo(() => {
    if (!tree) return null;

    const groups: Record<string, AccountTreeNode> = {};
    const accounts: Record<string, Account[]> = {};

    for (const root of tree.roots) {
      groups[root.root_type] = root;
      accounts[root.root_type] = flattenAccounts(root.children);
    }

    return { groups, accounts };
  }, [tree]);
}

function flattenAccounts(nodes: AccountTreeNode[]): Account[] {
  const result: Account[] = [];

  for (const node of nodes) {
    result.push(node);
    if (node.children.length > 0) {
      result.push(...flattenAccounts(node.children));
    }
  }

  return result;
}

// Simple async data hook
import { useState, useEffect } from "react";

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
          setError(err);
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
        setError(err);
        setIsLoading(false);
      });
  }, [fetchFn]);

  return { data, error, isLoading, refetch };
}
