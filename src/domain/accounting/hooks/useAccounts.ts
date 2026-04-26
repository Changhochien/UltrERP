/**
 * React hooks for account management (Epic 26).
 */

import { useState, useEffect, useCallback, useMemo } from "react";
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
  const { success: toastSuccess } = useToast();
  const [isCreating, setIsCreating] = useState(false);

  const create = useCallback(
    async (data: CreateAccountRequest): Promise<Account> => {
      setIsCreating(true);
      try {
        const account = await createAccount(data);
        toastSuccess(t("accounting.accountCreated", { name: account.account_name }));
        onSuccess?.(account);
        return account;
      } finally {
        setIsCreating(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { createAccount: create, isCreating };
}

export function useUpdateAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isUpdating, setIsUpdating] = useState(false);

  const update = useCallback(
    async (accountId: string, data: UpdateAccountRequest): Promise<Account> => {
      setIsUpdating(true);
      try {
        const account = await updateAccount(accountId, data);
        toastSuccess(t("accounting.accountUpdated", { name: account.account_name }));
        onSuccess?.(account);
        return account;
      } finally {
        setIsUpdating(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { updateAccount: update, isUpdating };
}

export function useFreezeAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isFreezing, setIsFreezing] = useState(false);

  const freeze = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      setIsFreezing(true);
      try {
        const account = await freezeAccount(accountId);
        toastSuccess(t("accounting.accountFrozen", { name: accountName }));
        onSuccess?.(account);
        return account;
      } finally {
        setIsFreezing(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { freezeAccount: freeze, isFreezing };
}

export function useUnfreezeAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isUnfreezing, setIsUnfreezing] = useState(false);

  const unfreeze = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      setIsUnfreezing(true);
      try {
        const account = await unfreezeAccount(accountId);
        toastSuccess(t("accounting.accountUnfrozen", { name: accountName }));
        onSuccess?.(account);
        return account;
      } finally {
        setIsUnfreezing(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { unfreezeAccount: unfreeze, isUnfreezing };
}

export function useDisableAccount(onSuccess?: (account: Account) => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isDisabling, setIsDisabling] = useState(false);

  const disable = useCallback(
    async (accountId: string, accountName: string): Promise<Account> => {
      setIsDisabling(true);
      try {
        const account = await disableAccount(accountId);
        toastSuccess(t("accounting.accountDisabled", { name: accountName }));
        onSuccess?.(account);
        return account;
      } finally {
        setIsDisabling(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { disableAccount: disable, isDisabling };
}

export function useDeleteAccount(onSuccess?: () => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isDeleting, setIsDeleting] = useState(false);

  const remove = useCallback(
    async (accountId: string, accountName: string): Promise<void> => {
      setIsDeleting(true);
      try {
        await deleteAccount(accountId);
        toastSuccess(t("accounting.accountDeleted", { name: accountName }));
        onSuccess?.();
      } finally {
        setIsDeleting(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { deleteAccount: remove, isDeleting };
}

export function useSeedStarterChart(onSuccess?: (result: AccountTreeResponse) => void) {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const [isSeeding, setIsSeeding] = useState(false);

  const seed = useCallback(
    async (): Promise<AccountTreeResponse> => {
      setIsSeeding(true);
      try {
        const result = await seedStarterChart();
        toastSuccess(t("accounting.starterChartSeeded", { count: result.total_accounts }));
        onSuccess?.(result);
        return result;
      } finally {
        setIsSeeding(false);
      }
    },
    [t, toastSuccess, onSuccess]
  );

  return { seedChart: seed, isSeeding };
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
