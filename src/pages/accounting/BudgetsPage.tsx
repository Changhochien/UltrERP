/**
 * Budgets Page (Epic 26 - Story 26-6)
 * Budget management and allocation
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Pencil, FileText, CheckCircle, AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/useToast";

interface Budget {
  id: string;
  budget_number: string;
  budget_name: string;
  fiscal_year: string;
  status: string;
  total_amount: string;
  scope_type: string | null;
  expense_action: string;
}

interface BudgetPeriod {
  id: string;
  period_name: string;
  allocated_amount: string;
}

export function BudgetsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [periods, setPeriods] = useState<BudgetPeriod[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const loadBudgets = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/v1/accounting/budgets", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data);
      }
    } catch (error) {
      console.error("Failed to load budgets:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadBudgetPeriods = async (budgetId: string) => {
    try {
      const response = await fetch(`/api/v1/accounting/budgets/${budgetId}/periods`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPeriods(data);
      }
    } catch (error) {
      console.error("Failed to load periods:", error);
    }
  };

  const handleCreateBudget = async (data: any) => {
    try {
      const response = await fetch("/api/v1/accounting/budgets", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        toast({ title: "Success", description: "Budget created" });
        loadBudgets();
        setShowCreateDialog(false);
      } else {
        toast({ title: "Error", description: "Failed to create budget", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to create budget", variant: "destructive" });
    }
  };

  const handleSubmitBudget = async (budgetId: string) => {
    try {
      const response = await fetch(`/api/v1/accounting/budgets/${budgetId}/submit`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });

      if (response.ok) {
        toast({ title: "Success", description: "Budget submitted" });
        loadBudgets();
      } else {
        toast({ title: "Error", description: "Failed to submit budget", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to submit budget", variant: "destructive" });
    }
  };

  const handleAllocate = async (budgetId: string, distributionType: string) => {
    try {
      const response = await fetch(`/api/v1/accounting/budgets/${budgetId}/allocate`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ distribution_type: distributionType })
      });

      if (response.ok) {
        toast({ title: "Success", description: "Budget allocated to periods" });
        loadBudgetPeriods(budgetId);
      } else {
        toast({ title: "Error", description: "Failed to allocate budget", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to allocate budget", variant: "destructive" });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "draft":
        return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">Draft</span>;
      case "submitted":
        return <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">Submitted</span>;
      case "cancelled":
        return <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">Cancelled</span>;
      default:
        return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs">{status}</span>;
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case "warn":
        return <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800">
          <AlertTriangle className="mr-1 h-3 w-3" /> Warn
        </span>;
      case "stop":
        return <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
          <CheckCircle className="mr-1 h-3 w-3" /> Block
        </span>;
      default:
        return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs">Ignore</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("routes.budgets.label", "Budgets")}
          </h1>
          <p className="text-muted-foreground">
            {t("routes.budgets.description", "Create and manage budgets with period allocation")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadBudgets} variant="outline" size="sm">
            Refresh
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Budget
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Budgets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{budgets.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Submitted</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {budgets.filter(b => b.status === "submitted").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Draft</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">
              {budgets.filter(b => b.status === "draft").length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">Budget List</TabsTrigger>
          <TabsTrigger value="details">Budget Details</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left text-sm font-medium">Budget #</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">Name</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">Year</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">Amount</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">Control</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">Status</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {budgets.map((budget) => (
                  <tr key={budget.id} className="border-b">
                    <td className="px-4 py-2 text-sm font-mono">{budget.budget_number}</td>
                    <td className="px-4 py-2 text-sm">{budget.budget_name}</td>
                    <td className="px-4 py-2 text-sm">{budget.fiscal_year}</td>
                    <td className="px-4 py-2 text-right text-sm">
                      {parseFloat(budget.total_amount).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {getActionBadge(budget.expense_action)}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {getStatusBadge(budget.status)}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <div className="flex justify-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setSelectedBudget(budget);
                            loadBudgetPeriods(budget.id);
                          }}
                        >
                          <FileText className="h-4 w-4" />
                        </Button>
                        {budget.status === "draft" && (
                          <Button
                            size="sm"
                            onClick={() => handleSubmitBudget(budget.id)}
                          >
                            Submit
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {budgets.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                      No budgets created yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="details">
          {selectedBudget ? (
            <Card>
              <CardHeader>
                <CardTitle>{selectedBudget.budget_name}</CardTitle>
                <CardDescription>{selectedBudget.budget_number}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label>Fiscal Year</Label>
                    <p className="text-sm">{selectedBudget.fiscal_year}</p>
                  </div>
                  <div>
                    <Label>Total Amount</Label>
                    <p className="text-sm">{parseFloat(selectedBudget.total_amount).toLocaleString()}</p>
                  </div>
                  <div>
                    <Label>Expense Control</Label>
                    <p className="text-sm">{selectedBudget.expense_action}</p>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <p className="text-sm">{getStatusBadge(selectedBudget.status)}</p>
                  </div>
                </div>

                {selectedBudget.status === "submitted" && periods.length > 0 && (
                  <>
                    <div className="pt-4">
                      <h3 className="text-sm font-medium mb-2">Period Allocation</h3>
                      <div className="rounded-md border">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b bg-muted/50">
                              <th className="px-4 py-2 text-left text-sm">Period</th>
                              <th className="px-4 py-2 text-right text-sm">Allocated</th>
                            </tr>
                          </thead>
                          <tbody>
                            {periods.map((period) => (
                              <tr key={period.id} className="border-b">
                                <td className="px-4 py-2 text-sm">{period.period_name}</td>
                                <td className="px-4 py-2 text-right text-sm">
                                  {parseFloat(period.allocated_amount).toLocaleString()}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                )}

                {selectedBudget.status === "draft" && (
                  <div className="pt-4 flex gap-2">
                    <Button onClick={() => handleAllocate(selectedBudget.id, "equal")}>
                      Allocate Equally (12 months)
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-md border p-8 text-center text-muted-foreground">
              Select a budget to view details
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
