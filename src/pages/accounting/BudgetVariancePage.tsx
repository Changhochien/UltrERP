/**
 * Budget Variance Page (Epic 26 - Story 26-6)
 * Budget vs Actual Variance Reporting
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FileDown, TrendingDown, TrendingUp, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/useToast";

interface Budget {
  id: string;
  budget_number: string;
  budget_name: string;
  fiscal_year: string;
}

interface VarianceRow {
  account_id: string;
  account_number: string;
  account_name: string;
  allocated: string;
  actual: string;
  variance: string;
  variance_percent: string;
}

interface VarianceReport {
  budget: Budget;
  period: { from_date: string; to_date: string };
  summary: {
    total_allocated: string;
    total_actual: string;
    total_variance: string;
    variance_percent: string;
  };
  rows: VarianceRow[];
}

export function BudgetVariancePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selectedBudgetId, setSelectedBudgetId] = useState<string>("");
  const [fromDate, setFromDate] = useState("2026-01-01");
  const [toDate, setToDate] = useState("2026-12-31");
  const [report, setReport] = useState<VarianceReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadBudgets = async () => {
    try {
      const response = await fetch("/api/v1/accounting/budgets?status=submitted", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data);
        if (data.length > 0 && !selectedBudgetId) {
          setSelectedBudgetId(data[0].id);
        }
      }
    } catch (error) {
      console.error("Failed to load budgets:", error);
    }
  };

  const generateReport = async () => {
    if (!selectedBudgetId) {
      toast({ title: "Error", description: "Please select a budget", variant: "destructive" });
      return;
    }

    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        from_date: fromDate,
        to_date: toDate,
      });

      const response = await fetch(
        `/api/v1/accounting/budgets/${selectedBudgetId}/variance?${params}`,
        {
          headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setReport(data);
      } else {
        toast({ title: "Error", description: "Failed to generate report", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to generate report", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  const exportCSV = () => {
    if (!report) return;

    const headers = ["Account Number", "Account Name", "Budgeted", "Actual", "Variance", "Variance %"];
    const rows = report.rows.map(row => [
      row.account_number,
      row.account_name,
      row.allocated,
      row.actual,
      row.variance,
      row.variance_percent,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `budget-variance-${report.budget.budget_number}.csv`;
    a.click();
  };

  const getVarianceColor = (variance: string) => {
    const value = parseFloat(variance);
    if (value > 0) return "text-green-600";  // Under budget
    if (value < 0) return "text-red-600";     // Over budget
    return "text-gray-600";
  };

  const getVarianceIcon = (variance: string) => {
    const value = parseFloat(variance);
    if (value > 0) return <TrendingUp className="h-4 w-4 text-green-600" />;
    if (value < 0) return <TrendingDown className="h-4 w-4 text-red-600" />;
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("routes.budgetVariance.label", "Budget Variance")}
          </h1>
          <p className="text-muted-foreground">
            {t("routes.budgetVariance.description", "Compare actual spending against budget")}
          </p>
        </div>
        {report && (
          <Button onClick={exportCSV} variant="outline">
            <FileDown className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Report Parameters</CardTitle>
          <CardDescription>Select budget and date range</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="budget">Budget</Label>
              <select
                id="budget"
                className="w-full rounded-md border border-input bg-background px-3 py-2"
                value={selectedBudgetId}
                onChange={(e) => setSelectedBudgetId(e.target.value)}
                onClick={loadBudgets}
              >
                <option value="">Select budget...</option>
                {budgets.map((budget) => (
                  <option key={budget.id} value={budget.id}>
                    {budget.budget_name} ({budget.fiscal_year})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="from-date">From Date</Label>
              <Input
                id="from-date"
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="to-date">To Date</Label>
              <Input
                id="to-date"
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
              />
            </div>

            <div className="flex items-end">
              <Button onClick={generateReport} disabled={isLoading || !selectedBudgetId}>
                {isLoading ? "Generating..." : "Generate Report"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {report && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Budgeted</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {parseFloat(report.summary.total_allocated).toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Actual</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {parseFloat(report.summary.total_actual).toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Variance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold flex items-center gap-2 ${getVarianceColor(report.summary.total_variance)}`}>
                  {getVarianceIcon(report.summary.total_variance)}
                  {parseFloat(report.summary.total_variance).toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Variance %</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold flex items-center gap-2 ${getVarianceColor(report.summary.total_variance)}`}>
                  {getVarianceIcon(report.summary.total_variance)}
                  {parseFloat(report.summary.variance_percent).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Variance by Account</CardTitle>
              <CardDescription>
                {report.budget.budget_name} | {report.period.from_date} to {report.period.to_date}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-2 text-left text-sm font-medium">Account</th>
                      <th className="px-4 py-2 text-right text-sm font-medium">Budgeted</th>
                      <th className="px-4 py-2 text-right text-sm font-medium">Actual</th>
                      <th className="px-4 py-2 text-right text-sm font-medium">Variance</th>
                      <th className="px-4 py-2 text-right text-sm font-medium">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.rows.map((row) => {
                      const variance = parseFloat(row.variance);
                      return (
                        <tr key={row.account_id} className="border-b">
                          <td className="px-4 py-2">
                            <div className="text-sm font-mono">{row.account_number}</div>
                            <div className="text-xs text-muted-foreground">{row.account_name}</div>
                          </td>
                          <td className="px-4 py-2 text-right text-sm">
                            {parseFloat(row.allocated).toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-right text-sm">
                            {parseFloat(row.actual).toLocaleString()}
                          </td>
                          <td className={`px-4 py-2 text-right text-sm font-medium flex items-center justify-end gap-1 ${getVarianceColor(row.variance)}`}>
                            {getVarianceIcon(row.variance)}
                            {variance.toLocaleString()}
                          </td>
                          <td className={`px-4 py-2 text-right text-sm ${getVarianceColor(row.variance)}`}>
                            {parseFloat(row.variance_percent).toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                    {report.rows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                          No data for the selected period
                        </td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr className="bg-muted/50 font-bold">
                      <td className="px-4 py-2">Total</td>
                      <td className="px-4 py-2 text-right">
                        {parseFloat(report.summary.total_allocated).toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {parseFloat(report.summary.total_actual).toLocaleString()}
                      </td>
                      <td className={`px-4 py-2 text-right flex items-center justify-end gap-1 ${getVarianceColor(report.summary.total_variance)}`}>
                        {getVarianceIcon(report.summary.total_variance)}
                        {parseFloat(report.summary.total_variance).toLocaleString()}
                      </td>
                      <td className={`px-4 py-2 text-right ${getVarianceColor(report.summary.total_variance)}`}>
                        {parseFloat(report.summary.variance_percent).toFixed(1)}%
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {!report && (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          <AlertCircle className="mx-auto h-8 w-8 mb-4 opacity-50" />
          <p>Select a budget and date range to generate a variance report</p>
        </div>
      )}
    </div>
  );
}
