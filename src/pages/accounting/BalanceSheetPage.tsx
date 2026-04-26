/**
 * Balance Sheet Report Page (Epic 26.3).
 */

import { useState, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ToastService } from "@/components/ui/toast";
import { useApiErrorToast } from "@/hooks/useApiErrorToast";
import { EMPTY_REASON_LABELS } from "@/domain/accounting/types";

import {
  fetchBalanceSheet,
  exportBalanceSheetCSV,
  downloadBlob,
  formatCurrency,
  BalanceSheetResponse,
} from "@/lib/api/reports";

function formatDateForInput(date: Date | null): string {
  if (!date) return "";
  return date.toISOString().split("T")[0];
}

export function BalanceSheetPage() {
  const { t } = useTranslation();
  const errorToast = useApiErrorToast();

  // Date selection
  const [asOfDate, setAsOfDate] = useState<Date | null>(new Date());

  // Report state
  const [report, setReport] = useState<BalanceSheetResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Fetch report
  const fetchReport = useCallback(async () => {
    if (!asOfDate) {
      ToastService.error("Please select a date");
      return;
    }

    setIsLoading(true);
    try {
      const data = await fetchBalanceSheet({
        as_of_date: formatDateForInput(asOfDate),
      });
      setReport(data);
    } catch (error) {
      errorToast(error, "Failed to load Balance Sheet");
    } finally {
      setIsLoading(false);
    }
  }, [asOfDate, errorToast]);

  // Export CSV
  const handleExport = useCallback(async () => {
    if (!asOfDate) return;

    setIsExporting(true);
    try {
      const blob = await exportBalanceSheetCSV({
        as_of_date: formatDateForInput(asOfDate),
      });
      downloadBlob(
        blob,
        `balance_sheet_${formatDateForInput(asOfDate)}.csv`
      );
      ToastService.success("Report exported successfully");
    } catch (error) {
      errorToast(error, "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  }, [asOfDate, errorToast]);

  // Check if balanced
  const isBalanced = useMemo(() => {
    if (!report) return null;
    const assets = parseFloat(report.total_assets);
    const liabilitiesAndEquity = parseFloat(report.total_liabilities_and_equity);
    const diff = Math.abs(assets - liabilitiesAndEquity);
    return diff < 0.01;
  }, [report]);

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t("Balance Sheet")}
          </h1>
          <p className="text-muted-foreground">
            {t("Assets, liabilities, and equity as of a specific date")}
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
            {/* Date selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">As of Date</label>
              <DatePicker date={asOfDate} onChange={setAsOfDate} />
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button onClick={fetchReport} disabled={isLoading || !asOfDate}>
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
                    No ledger entries were found up to this date.
                    All totals will show zero values.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-2 gap-6">
            {/* Assets Section */}
            <Card className="col-span-2">
              <CardHeader>
                <CardTitle>ASSETS</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {report.metadata.as_of_date}
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
                    {report.asset_rows.map((row, index) => (
                      <TableRow
                        key={`${row.account_id}-${index}`}
                        className={
                          row.is_subtotal ? "font-semibold bg-muted/50" : ""
                        }
                      >
                        <TableCell
                          className="font-mono text-sm"
                          style={{
                            paddingLeft: `${row.indent_level * 16 + 12}px`,
                          }}
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
                        Total Assets
                      </TableCell>
                      <TableCell className="text-right font-bold font-mono">
                        {formatCurrency(report.total_assets)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Liabilities Section */}
            <Card>
              <CardHeader>
                <CardTitle>LIABILITIES</CardTitle>
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
                    {report.liability_rows.map((row, index) => (
                      <TableRow
                        key={`${row.account_id}-${index}`}
                        className={
                          row.is_subtotal ? "font-semibold bg-muted/50" : ""
                        }
                      >
                        <TableCell
                          className="font-mono text-sm"
                          style={{
                            paddingLeft: `${row.indent_level * 16 + 12}px`,
                          }}
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
                        Total Liabilities
                      </TableCell>
                      <TableCell className="text-right font-bold font-mono">
                        {formatCurrency(report.total_liabilities)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Equity Section */}
            <Card>
              <CardHeader>
                <CardTitle>EQUITY</CardTitle>
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
                    {report.equity_rows.map((row, index) => (
                      <TableRow
                        key={`${row.account_id}-${index}`}
                        className={
                          row.is_subtotal ? "font-semibold bg-muted/50" : ""
                        }
                      >
                        <TableCell
                          className="font-mono text-sm"
                          style={{
                            paddingLeft: `${row.indent_level * 16 + 12}px`,
                          }}
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
                        Total Equity
                      </TableCell>
                      <TableCell className="text-right font-bold font-mono">
                        {formatCurrency(report.total_equity)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          {/* Total Liabilities and Equity */}
          <Card
            className={
              isBalanced
                ? "border-green-200 bg-green-50"
                : "border-red-200 bg-red-50"
            }
          >
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold">Total Liabilities and Equity</span>
                <div className="text-right">
                  <span className="text-2xl font-bold font-mono">
                    {formatCurrency(report.total_liabilities_and_equity)}
                  </span>
                  {!isBalanced && (
                    <p className="text-red-600 text-sm mt-1">
                      Warning: Balance sheet is not balanced!
                    </p>
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
              <p className="text-lg">Select a date and generate the report</p>
              <p className="text-sm mt-1">
                The Balance Sheet will show your company's assets, liabilities, and
                equity at a specific point in time.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
