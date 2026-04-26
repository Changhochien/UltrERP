/**
 * Trial Balance Report Page (Epic 26.3).
 */

import { useState, useCallback } from "react";
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
  fetchTrialBalance,
  exportTrialBalanceCSV,
  downloadBlob,
  formatCurrency,
  TrialBalanceResponse,
} from "@/lib/api/reports";

function formatDateForInput(date: Date | null): string {
  if (!date) return "";
  return date.toISOString().split("T")[0];
}

export function TrialBalancePage() {
  const { t } = useTranslation();
  const errorToast = useApiErrorToast();

  // Report mode: "as_of" or "period"
  const [reportMode, setReportMode] = useState<"as_of" | "period">("as_of");

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

  // As-of date
  const [asOfDate, setAsOfDate] = useState<Date | null>(new Date());

  // Wrapper to handle DatePicker's Date | null | undefined
  const handleAsOfDateChange = (date: Date | null | undefined) => {
    setAsOfDate(date ?? null);
  };

  // Report state
  const [report, setReport] = useState<TrialBalanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Fetch report
  const fetchReport = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: { as_of_date?: string; from_date?: string; to_date?: string } = {};

      if (reportMode === "as_of") {
        if (!asOfDate) {
          ToastService.error("Please select a date");
          setIsLoading(false);
          return;
        }
        params.as_of_date = formatDateForInput(asOfDate);
      } else {
        if (!fromDate || !toDate) {
          ToastService.error("Please select start and end dates");
          setIsLoading(false);
          return;
        }
        params.from_date = formatDateForInput(fromDate);
        params.to_date = formatDateForInput(toDate);
      }

      const data = await fetchTrialBalance(params);
      setReport(data);
    } catch (error) {
      errorToast(error, "Failed to load Trial Balance");
    } finally {
      setIsLoading(false);
    }
  }, [reportMode, asOfDate, fromDate, toDate, errorToast]);

  // Export CSV
  const handleExport = useCallback(async () => {
    setIsExporting(true);
    try {
      const params: { as_of_date?: string; from_date?: string; to_date?: string } = {};

      if (reportMode === "as_of") {
        params.as_of_date = formatDateForInput(asOfDate);
      } else {
        params.from_date = formatDateForInput(fromDate);
        params.to_date = formatDateForInput(toDate);
      }

      const blob = await exportTrialBalanceCSV(params);
      const filename = reportMode === "as_of"
        ? `trial_balance_${formatDateForInput(asOfDate)}.csv`
        : `trial_balance_${formatDateForInput(fromDate)}_${formatDateForInput(toDate)}.csv`;
      downloadBlob(blob, filename);
      ToastService.success("Report exported successfully");
    } catch (error) {
      errorToast(error, "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  }, [reportMode, asOfDate, fromDate, toDate, errorToast]);

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

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t("Trial Balance")}
          </h1>
          <p className="text-muted-foreground">
            {t("View all accounts with debit and credit balances")}
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
            {/* Mode selector */}
            <div className="flex flex-col gap-1.5 min-w-[150px]">
              <label className="text-sm font-medium">Report Mode</label>
              <select
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                value={reportMode}
                onChange={(e) => setReportMode(e.target.value as "as_of" | "period")}
              >
                <option value="as_of">As of Date</option>
                <option value="period">Period Range</option>
              </select>
            </div>

            {/* As-of date mode */}
            {reportMode === "as_of" && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">As of Date</label>
                <DatePicker value={asOfDate} onChange={handleAsOfDateChange} />
              </div>
            )}

            {/* Period mode */}
            {reportMode === "period" && (
              <>
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
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">From Date</label>
                  <DatePicker value={fromDate} onChange={setFromDate} placeholder="Start date" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium">To Date</label>
                  <DatePicker value={toDate} onChange={setToDate} placeholder="End date" />
                </div>
              </>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                onClick={fetchReport}
                disabled={
                  isLoading ||
                  (reportMode === "as_of" && !asOfDate) ||
                  (reportMode === "period" && (!fromDate || !toDate))
                }
              >
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

          {/* Trial Balance Table */}
          <Card>
            <CardHeader>
              <CardTitle>Trial Balance</CardTitle>
              <p className="text-sm text-muted-foreground">
                {report.metadata.as_of_date
                  ? `As of ${report.metadata.as_of_date}`
                  : `${report.metadata.from_date} to ${report.metadata.to_date}`}
              </p>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Account</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-[100px]">Type</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.rows.map((row) => (
                    <TableRow key={row.account_id}>
                      <TableCell className="font-mono text-sm">
                        {row.account_number}
                      </TableCell>
                      <TableCell>{row.account_name}</TableCell>
                      <TableCell>
                        <span className="text-xs px-2 py-0.5 rounded bg-muted">
                          {row.root_type}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {parseFloat(row.debit) > 0 ? formatCurrency(row.debit) : "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {parseFloat(row.credit) > 0 ? formatCurrency(row.credit) : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                  {/* Totals Row */}
                  <TableRow className="border-t-2 border-t-foreground font-bold">
                    <TableCell colSpan={3}>TOTAL</TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(report.total_debit)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(report.total_credit)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Balance Status */}
          <Card
            className={
              report.is_balanced
                ? "border-green-200 bg-green-50"
                : "border-red-200 bg-red-50"
            }
          >
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold">Balance Check</span>
                <div className="text-right">
                  {report.is_balanced ? (
                    <span className="text-green-700 font-semibold">
                      ✓ Balanced - Debits equal Credits
                    </span>
                  ) : (
                    <div>
                      <span className="text-red-700 font-semibold">
                        ✗ Out of Balance
                      </span>
                      <p className="text-red-600 text-sm mt-1">
                        Difference: {formatCurrency(
                          Math.abs(
                            parseFloat(report.total_debit) -
                              parseFloat(report.total_credit)
                          )
                        )}
                      </p>
                    </div>
                  )}
                </div>
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
                The Trial Balance shows all accounts with their debit and credit
                balances. Total debits should equal total credits.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
