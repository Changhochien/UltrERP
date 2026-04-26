/**
 * Chart of Accounts management page (Epic 26).
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  FolderTree,
  Plus,
  RefreshCw,
  Snowflake,
  Upload,
  X,
} from "lucide-react";

import type { Account, AccountType, AccountFormData } from "@/domain/accounting/types";
import {
  useAccountTree,
  useCreateAccount,
  useDeleteAccount,
  useDisableAccount,
  useFreezeAccount,
  useSeedStarterChart,
  useUnfreezeAccount,
  useUpdateAccount,
} from "@/domain/accounting/hooks/useAccounts";
import { AccountBadge, AccountTree } from "@/domain/accounting/components/AccountTree";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";

const ACCOUNT_TYPES_BY_ROOT: Record<string, AccountType[]> = {
  Asset: [
    "Root Asset",
    "Bank",
    "Cash",
    "Receivable",
    "Inventory",
    "Current Asset",
    "Fixed Asset",
    "Non-Current Asset",
    "Prepayment",
    "Tax Asset",
  ],
  Liability: [
    "Root Liability",
    "Payable",
    "Credit Card",
    "Current Liability",
    "Non-Current Liability",
    "Tax Liability",
  ],
  Equity: [
    "Root Equity",
    "Retained Earnings",
    "Shareholders Equity",
  ],
  Income: [
    "Root Income",
    "Sales",
    "Service Revenue",
    "Other Income",
  ],
  Expense: [
    "Root Expense",
    "Cost of Goods Sold",
    "Expense",
    "Depreciation",
    "Tax Expense",
  ],
};

export function ChartOfAccountsPage() {
  const { t } = useTranslation();
  const { error: toastError } = useToast();

  const [showDisabled, setShowDisabled] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isSeedDialogOpen, setIsSeedDialogOpen] = useState(false);
  const [formData, setFormData] = useState<Partial<AccountFormData>>({});
  const [rootTypeForCreate, setRootTypeForCreate] = useState<string>("Asset");

  const { tree, isLoading, refetch } = useAccountTree(showDisabled);
  const { createAccount, isCreating } = useCreateAccount();
  const { updateAccount, isUpdating } = useUpdateAccount();
  const { freezeAccount, isFreezing } = useFreezeAccount();
  const { unfreezeAccount, isUnfreezing } = useUnfreezeAccount();
  const { disableAccount, isDisabling } = useDisableAccount();
  const { deleteAccount, isDeleting } = useDeleteAccount();
  const { seedChart, isSeeding } = useSeedStarterChart();

  const handleSelect = (account: Account) => {
    setSelectedAccount(account);
    setFormData({
      account_number: account.account_number,
      account_name: account.account_name,
      account_type: account.account_type,
      is_group: account.is_group,
      is_frozen: account.is_frozen,
      is_disabled: account.is_disabled,
    });
  };

  const handleEdit = (account: Account) => {
    setSelectedAccount(account);
    setFormData({
      account_number: account.account_number,
      account_name: account.account_name,
      account_type: account.account_type,
      is_group: account.is_group,
    });
    setIsEditDialogOpen(true);
  };

  const handleCreate = () => {
    setFormData({
      account_number: "",
      account_name: "",
      account_type: ACCOUNT_TYPES_BY_ROOT[rootTypeForCreate][1] || ACCOUNT_TYPES_BY_ROOT[rootTypeForCreate][0],
      is_group: false,
    });
    setIsCreateDialogOpen(true);
  };

  const handleDelete = (account: Account) => {
    setSelectedAccount(account);
    setIsDeleteDialogOpen(true);
  };

  const handleSaveCreate = async () => {
    if (!formData.account_number || !formData.account_name || !formData.account_type) {
      toastError(t("accounting.fillRequiredFields"));
      return;
    }

    try {
      await createAccount({
        account_number: formData.account_number!,
        account_name: formData.account_name!,
        root_type: rootTypeForCreate as AccountFormData["root_type"],
        account_type: formData.account_type as AccountFormData["account_type"],
        is_group: formData.is_group ?? false,
        parent_id: selectedAccount?.is_group ? selectedAccount.id : undefined,
      });
      setIsCreateDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedAccount) return;

    try {
      await updateAccount(selectedAccount.id, {
        account_number: formData.account_number,
        account_name: formData.account_name,
        account_type: formData.account_type as AccountFormData["account_type"],
        is_group: formData.is_group,
      });
      setIsEditDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleSaveDelete = async () => {
    if (!selectedAccount) return;

    try {
      await deleteAccount(selectedAccount.id, selectedAccount.account_name);
      setIsDeleteDialogOpen(false);
      setSelectedAccount(null);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleSeed = async () => {
    try {
      await seedChart();
      setIsSeedDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleFreeze = async (account: Account) => {
    try {
      await freezeAccount(account.id, account.account_name);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleUnfreeze = async (account: Account) => {
    try {
      await unfreezeAccount(account.id, account.account_name);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleDisable = async (account: Account) => {
    try {
      await disableAccount(account.id, account.account_name);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const isWorking = isCreating || isUpdating || isFreezing || isUnfreezing || isDisabling || isDeleting || isSeeding;

  return (
    <div className="flex h-full gap-6">
      {/* Tree Panel */}
      <div className="flex flex-1 flex-col rounded-lg border bg-card">
        <div className="flex items-center justify-between border-b p-4">
          <div className="flex items-center gap-2">
            <FolderTree className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">{t("accounting.chartOfAccounts")}</h2>
            {tree && (
              <span className="text-sm text-muted-foreground">
                ({tree.total_accounts} {t("accounting.accounts")})
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <Switch
                id="show-disabled"
                checked={showDisabled}
                onCheckedChange={setShowDisabled}
              />
              <Label htmlFor="show-disabled" className="text-sm">
                {t("accounting.showDisabled")}
              </Label>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={handleCreate}>
                  {t("accounting.createAccount")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setIsSeedDialogOpen(true)}>
                  <Upload className="mr-2 h-4 w-4" />
                  {t("accounting.seedStarterChart")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : tree && tree.roots.length > 0 ? (
            <AccountTree
              tree={tree.roots}
              onSelect={handleSelect}
              onEdit={handleEdit}
              onFreeze={handleFreeze}
              onUnfreeze={handleUnfreeze}
              onDisable={handleDisable}
              onDelete={handleDelete}
              selectedId={selectedAccount?.id}
              showDisabled={showDisabled}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <FolderTree className="mb-4 h-12 w-12 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                {t("accounting.noAccounts")}
              </p>
              <Button
                variant="link"
                onClick={() => setIsSeedDialogOpen(true)}
                className="mt-2"
              >
                {t("accounting.seedStarterChart")}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedAccount && (
        <div className="w-80 shrink-0 rounded-lg border bg-card p-4">
          <h3 className="mb-4 text-lg font-semibold">{t("accounting.accountDetails")}</h3>

          <div className="space-y-4">
            <div className="flex items-center gap-2 rounded-lg bg-muted/50 p-3">
              <AccountBadge account={selectedAccount} />
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-muted-foreground">{t("accounting.rootType")}</div>
              <div>{selectedAccount.root_type}</div>

              <div className="text-muted-foreground">{t("accounting.accountType")}</div>
              <div>{selectedAccount.account_type}</div>

              <div className="text-muted-foreground">{t("accounting.reportType")}</div>
              <div>{selectedAccount.report_type}</div>

              <div className="text-muted-foreground">{t("accounting.isGroup")}</div>
              <div>{selectedAccount.is_group ? t("common.yes") : t("common.no")}</div>

              <div className="text-muted-foreground">{t("accounting.isFrozen")}</div>
              <div>
                {selectedAccount.is_frozen ? (
                  <span className="flex items-center gap-1 text-amber-600">
                    <Snowflake className="h-4 w-4" /> {t("accounting.frozen")}
                  </span>
                ) : (
                  t("common.no")
                )}
              </div>

              <div className="text-muted-foreground">{t("accounting.isDisabled")}</div>
              <div>
                {selectedAccount.is_disabled ? (
                  <span className="flex items-center gap-1 text-red-600">
                    <X className="h-4 w-4" /> {t("accounting.disabled")}
                  </span>
                ) : (
                  t("common.no")
                )}
              </div>
            </div>

            {selectedAccount.parent_number && (
              <div className="border-t pt-4">
                <div className="text-sm text-muted-foreground">
                  {t("accounting.parentAccount")}
                </div>
                <div className="mt-1 font-mono text-sm">
                  {selectedAccount.parent_number}
                </div>
              </div>
            )}

            <div className="border-t pt-4">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => handleEdit(selectedAccount)}
              >
                {t("common.edit")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.createAccount")}</DialogTitle>
            <DialogDescription>{t("accounting.createAccountDescription")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t("accounting.rootType")} *</Label>
              <Select
                value={rootTypeForCreate}
                onValueChange={setRootTypeForCreate}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Asset">{t("accounting.asset")}</SelectItem>
                  <SelectItem value="Liability">{t("accounting.liability")}</SelectItem>
                  <SelectItem value="Equity">{t("accounting.equity")}</SelectItem>
                  <SelectItem value="Income">{t("accounting.income")}</SelectItem>
                  <SelectItem value="Expense">{t("accounting.expense")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="account-number">{t("accounting.accountNumber")} *</Label>
              <Input
                id="account-number"
                value={formData.account_number || ""}
                onChange={(e) =>
                  setFormData({ ...formData, account_number: e.target.value })
                }
                placeholder="e.g., 1100"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="account-name">{t("accounting.accountName")} *</Label>
              <Input
                id="account-name"
                value={formData.account_name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, account_name: e.target.value })
                }
                placeholder="e.g., Cash"
              />
            </div>

            <div className="space-y-2">
              <Label>{t("accounting.accountType")} *</Label>
              <Select
                value={formData.account_type || ""}
                onValueChange={(v) => setFormData({ ...formData, account_type: v as AccountType })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("accounting.selectType")} />
                </SelectTrigger>
                <SelectContent>
                  {ACCOUNT_TYPES_BY_ROOT[rootTypeForCreate]?.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="is-group"
                checked={formData.is_group ?? false}
                onCheckedChange={(v) => setFormData({ ...formData, is_group: v })}
              />
              <Label htmlFor="is-group">{t("accounting.isGroup")}</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSaveCreate} disabled={isWorking}>
              {isCreating && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.editAccount")}</DialogTitle>
            <DialogDescription>
              {selectedAccount?.account_number} - {selectedAccount?.account_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-number">{t("accounting.accountNumber")}</Label>
              <Input
                id="edit-number"
                value={formData.account_number || ""}
                onChange={(e) =>
                  setFormData({ ...formData, account_number: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-name">{t("accounting.accountName")}</Label>
              <Input
                id="edit-name"
                value={formData.account_name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, account_name: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label>{t("accounting.accountType")}</Label>
              <Select
                value={formData.account_type || ""}
                onValueChange={(v) => setFormData({ ...formData, account_type: v as AccountType })}
                disabled={selectedAccount?.is_group}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {selectedAccount &&
                    ACCOUNT_TYPES_BY_ROOT[selectedAccount.root_type]?.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSaveEdit} disabled={isWorking}>
              {isUpdating && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.deleteAccount")}</DialogTitle>
            <DialogDescription>
              {t("accounting.deleteAccountConfirm", {
                name: selectedAccount?.account_name,
              })}
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-medium">{t("accounting.cannotUndo")}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {t("accounting.deleteWarning")}
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" onClick={handleSaveDelete} disabled={isWorking}>
              {isDeleting && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Seed Dialog */}
      <Dialog open={isSeedDialogOpen} onOpenChange={setIsSeedDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.seedStarterChart")}</DialogTitle>
            <DialogDescription>
              {t("accounting.seedStarterChartDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <p className="text-sm text-muted-foreground">
              {t("accounting.seedStarterChartNote")}
            </p>
            <div className="rounded-lg border p-4">
              <h4 className="font-medium">{t("accounting.accountsToCreate")}:</h4>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>• 5 Root Accounts (Asset, Liability, Equity, Income, Expense)</li>
                <li>• 11 Essential Ledger Accounts</li>
              </ul>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSeedDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSeed} disabled={isWorking}>
              {isSeeding && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              <Upload className="mr-2 h-4 w-4" />
              {t("accounting.seedChart")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
