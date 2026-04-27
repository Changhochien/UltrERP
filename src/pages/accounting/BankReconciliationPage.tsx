/**
 * Bank Reconciliation Page (Epic 26 - Story 26-5)
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Upload, FileText, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/useToast";

interface BankAccount {
  id: string;
  account_name: string;
  account_number: string;
  bank_name: string | null;
  current_balance: string;
  currency_code: string;
}

interface BankTransaction {
  id: string;
  transaction_date: string;
  description: string;
  reference_number: string | null;
  debit: string;
  credit: string;
  status: string;
}

export function BankReconciliationPage() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("unmatched");

  const loadAccounts = async () => {
    try {
      const response = await fetch("/api/v1/accounting/bank-accounts", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAccounts(data);
        if (data.length > 0 && !selectedAccount) {
          setSelectedAccount(data[0].id);
        }
      }
    } catch (error) {
      console.error("Failed to load accounts:", error);
    }
  };

  const loadTransactions = async () => {
    if (!selectedAccount) return;
    try {
      const response = await fetch(`/api/v1/accounting/bank-transactions?bank_account_id=${selectedAccount}&status=${activeTab}`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTransactions(data.items || data);
      }
    } catch (error) {
      console.error("Failed to load transactions:", error);
    }
  };

  const handleImport = async () => {
    if (!importFile || !selectedAccount) {
      toastError("Error", "Please select a file and bank account");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch(`/api/v1/accounting/bank-transactions/import?bank_account_id=${selectedAccount}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` },
        body: formData,
      });

      if (response.ok) {
        toastSuccess("Success", "Transactions imported successfully");
        loadTransactions();
        setImportFile(null);
      } else {
        const error = await response.json();
        toastError("Import Failed", error.message || "Failed to import transactions");
      }
    } catch (error) {
      toastError("Error", "Failed to import transactions");
    } finally {
      setIsLoading(false);
    }
  };

  const unmatchedCount = transactions.filter(t => t.status === "unmatched").length;
  const matchedCount = transactions.filter(t => t.status === "matched" || t.status === "suggested").length;
  const reconciledCount = transactions.filter(t => t.status === "reconciled").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("routes.bankReconciliation.label", { defaultValue: "Bank Reconciliation" })}
          </h1>
          <p className="text-muted-foreground">
            {t("routes.bankReconciliation.description", { defaultValue: "Import bank statements and reconcile with ledger" })}
          </p>
        </div>
        <Button onClick={loadAccounts} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          {t("refresh", { defaultValue: "Refresh" })}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Unmatched</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{unmatchedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Suggested</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{matchedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Reconciled</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{reconciledCount}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="unmatched">Unmatched</TabsTrigger>
          <TabsTrigger value="matched">Matched</TabsTrigger>
          <TabsTrigger value="reconciled">Reconciled</TabsTrigger>
          <TabsTrigger value="import">Import</TabsTrigger>
        </TabsList>

        <TabsContent value="unmatched" className="space-y-4">
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left text-sm font-medium">Date</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">Description</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">Reference</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">Debit</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">Credit</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.filter(t => t.status === "unmatched").map((tx) => (
                  <tr key={tx.id} className="border-b">
                    <td className="px-4 py-2 text-sm">{tx.transaction_date}</td>
                    <td className="px-4 py-2 text-sm">{tx.description}</td>
                    <td className="px-4 py-2 text-sm">{tx.reference_number || "-"}</td>
                    <td className="px-4 py-2 text-right text-sm">
                      {parseFloat(tx.debit) > 0 ? tx.debit : "-"}
                    </td>
                    <td className="px-4 py-2 text-right text-sm">
                      {parseFloat(tx.credit) > 0 ? tx.credit : "-"}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <Button size="sm" variant="outline">
                        <FileText className="mr-1 h-3 w-3" />
                        Match
                      </Button>
                    </td>
                  </tr>
                ))}
                {transactions.filter(t => t.status === "unmatched").length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      No unmatched transactions
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="matched">
          <div className="rounded-md border p-8 text-center text-muted-foreground">
            Matched transactions will appear here
          </div>
        </TabsContent>

        <TabsContent value="reconciled">
          <div className="rounded-md border p-8 text-center text-muted-foreground">
            Reconciled transactions will appear here
          </div>
        </TabsContent>

        <TabsContent value="import" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Import Bank Statement</CardTitle>
              <CardDescription>Upload a CSV file with bank transactions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bank-account">Bank Account</Label>
                <select
                  id="bank-account"
                  className="w-full rounded-md border border-input bg-background px-3 py-2"
                  value={selectedAccount || ""}
                  onChange={(e) => setSelectedAccount(e.target.value)}
                >
                  <option value="">Select bank account...</option>
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.account_name} - {acc.account_number}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="csv-file">CSV File</Label>
                <Input
                  id="csv-file"
                  type="file"
                  accept=".csv"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                />
                <p className="text-xs text-muted-foreground">
                  Expected format: date, description, reference, debit, credit
                </p>
              </div>

              <Button onClick={handleImport} disabled={isLoading || !importFile || !selectedAccount}>
                {isLoading ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Import Transactions
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
