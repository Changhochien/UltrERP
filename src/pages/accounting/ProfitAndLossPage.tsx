/**
 * Profit and Loss Report Page (Epic 26.3).
 */

import { useState, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/DatePicker";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ToastService } from "@/components/ui/Toast";
import { useApiErrorToast } from "@/hooks/useApiErrorToast";
import { useReportDateRange } from "@/domain/accounting/hooks/useReportDateRange";
import { EMPTY_REASON_LABELS } from "@/domain/accounting/types";

import {
  fetchProfitAndLoss,
  exportProfitAndLossCSV,
  downloadBlob,
  formatCurrency,
  ProfitAndLossResponse,
} from "@/lib/api/reports";

function formatDateForInput(date: Date | null): string {
  if (!date) return "";
  return date.toISOString().split("T")[0];
}

export function ProfitAndLossPage() {
  const { t } = useTranslation();
  const errorToast = useApiErrorToast();

  // Date range selection
  const {
    fromDate,
    toDate,
    setFromDate,
    setToDate,
    presets,
    selectedPreset,
    setSelectedPreset,
  } = useReportDateRange();

  // Report state
  const [report, setReport] = useState<ProfitAndLossResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Fetch report
  const fetchReport = useCallback(async () => {
    if (!fromDate || !toDate) {
      ToastService.error("Please select both start and end dates");
      return;
    }

    setIsLoading(true);
    try {
      const data = await fetchProfitAndLoss({
        from_date: formatDateForInput(fromDate),
        to_date: formatDateForInput(toDate),
      });
      setReport(data);
    } catch (error) {
      errorToast(error, "Failed to load Profit and Loss report");
    } finally {
      setIsLoading(false);
    }
  }, [fromDate, toDate, errorToast]);

  // Export CSV
  const handleExport = useCallback(async () => {
    if (!fromDate || !toDate) return;

    setIsExporting(true);
    try {
      const blob = await exportProfitAndLossCSV({
        from_date: formatDateForInput(fromDate),
        to_date: formatDateForInput(toDate),
      });
      downloadBlob(blob, `profit_and_loss_${formatDateForInput(fromDate)}_${formatDateForInput(toDate)}.csv`);
      ToastService.success("Report exported successfully");
    } catch (error) {
      errorToast(error, "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  }, [fromDate, toDate, errorToast]);

  // Handle preset selection
  const handlePresetSelect = useCallback(
    (preset: string) => {
      setSelectedPreset(preset);
      const range = presets[preset];
      if (range) {
        setFromDate(range.from);
        setToDate(range.to);
      }
    },
    [presets, setSelectedPreset, setFromDate, setToDate]
  );

  // Parse net profit for coloring
  const netProfit = useMemo(() => {
    if (!report) return null;
    const value = parseFloat(report.net_profit);
    return {
      value,
      isPositive: value >= 0,
      formatted: formatCurrency(report.net_profit),
    };
  }, [report]);

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t("Profit and Loss Statement")}
          </h1>
          <p className="text-muted-foreground">
            {t("View income and expenses for a period")}
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Report Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 items-end">
            {/* Preset selector */}
            <div className="flex flex-col gap-1.5 min-w-[150px]">
              <label className="text-sm font-medium">Period</label>
              <select
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                value={selectedPreset}
                onChange={(e) => handlePresetSelect(e.target.value)}
              >
                <option value="custom">Custom Range</option>
                <option value="this_month">This Month</option>
                <option value="last_month">Last Month</option>
                <option value="this_quarter">This Quarter</option>
                <option value="last_quarter">Last Quarter</option>
                <option value="this_year">This Year</option>
                <option value="last_year">Last Year</option>
              </select>
            </div>

            {/* Date range */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">From Date</label>
              <DatePicker
                value={fromDate}
                onChange={setFromDate}
                placeholder="Start date"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">To Date</label>
              <DatePicker
                value={toDate}
                onChange={setToDate}
                placeholder="End date"
              />
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button onClick={fetchReport} disabled={isLoading || !fromDate || !toDate}>
                {isLoading ? "Loading..." : "Generate Report"}
              </Button>
              <Button
                variant="outline"
                onClick={handleExport}
                disabled={isExporting || !report}
              >
                {isExporting ? "Exporting..." : "Export CSV"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Content */}
      {report && (
        <>
          {/* Empty State */}
          {report.metadata.empty_reason && (
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-amber-800 font-medium">
                    {EMPTY_REASON_LABELS[report.metadata.empty_reason]}
                  </p>
                  <p className="text-amber-600 text-sm mt-1">
                    No ledger entries were found for the selected period.
                    All totals will show zero values.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Income Section */}
          <Card>
            <CardHeader>
              <CardTitle>Income</CardTitle>
              <p className="text-sm text-muted-foreground">
                {report.metadata.from_date} to {report.metadata.to_date}
              </p>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Account</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.income_rows.map((row, index) => (
                    <TableRow
                      key={`${row.account_id}-${index}`}
                      className={row.is_subtotal ? "font-semibold bg-muted/50" : ""}
                    >
                      <TableCell
                        className="font-mono text-sm"
                        style={{ paddingLeft: `${row.indent_level * 16 + 12}px` }}
                      >
                        {row.account_number || "—"}
                      </TableCell>
                      <TableCell>{row.account_name}</TableCell>
                      <TableCell
                        className={`text-right font-mono ${
                          row.is_subtotal ? "font-semibold" : ""
                        }`}
                      >
                        {formatCurrency(row.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="border-t-2 border-t-foreground">
                    <TableCell colSpan={2} className="font-bold">
                      Total Income
                    </TableCell>
                    <TableCell className="text-right font-bold font-mono">
                      {formatCurrency(report.income_total)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Expense Section */}
          <Card>
            <CardHeader>
              <CardTitle>Expenses</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Account</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.expense_rows.map((row, index) => (
                    <TableRow
                      key={`${row.account_id}-${index}`}
                      className={row.is_subtotal ? "font-semibold bg-muted/50" : ""}
                    >
                      <TableCell
                        className="font-mono text-sm"
                        style={{ paddingLeft: `${row.indent_level * 16 + 12}px` }}
                      >
                        {row.account_number || "—"}
                      </TableCell>
                      <TableCell>{row.account_name}</TableCell>
                      <TableCell
                        className={`text-right font-mono ${
                          row.is_subtotal ? "font-semibold" : ""
                        }`}
                      >
                        {formatCurrency(row.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="border-t-2 border-t-foreground">
                    <TableCell colSpan={2} className="font-bold">
                      Total Expenses
                    </TableCell>
                    <TableCell className="text-right font-bold font-mono">
                      {formatCurrency(report.expense_total)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Net Profit/Loss */}
          <Card
            className={
              netProfit?.isPositive
                ? "border-green-200 bg-green-50"
                : "border-red-200 bg-red-50"
            }
          >
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <span
                  className={`text-lg font-bold ${
                    netProfit?.isPositive ? "text-green-700" : "text-red-700"
                  }`}
                >
                  {netProfit?.isPositive ? "Net Profit" : "Net Loss"}
                </span>
                <span
                  className={`text-2xl font-bold font-mono ${
                    netProfit?.isPositive ? "text-green-700" : "text-red-700"
                  }`}
                >
                  {netProfit?.formatted}
                </span>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* No Report State */}
      {!report && !isLoading && (
        <Card>
          <CardContent className="pt-12 pb-12">
            <div className="text-center text-muted-foreground">
              <p className="text-lg">Select a date range and generate the report</p>
              <p className="text-sm mt-1">
                The Profit and Loss statement will show income, expenses, and net
                profit/loss based on your GL entries.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
