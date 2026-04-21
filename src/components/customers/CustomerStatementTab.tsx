/** Customer account statement tab for the customer detail page. */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../ui/button";
import { DatePicker } from "../ui/DatePicker";
import {
  parseDatePickerInputValue,
  serializeDatePickerValue,
} from "../ui/date-picker-utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { SurfaceMessage } from "../layout/PageLayout";
import { getCustomerStatement, type CustomerStatementResponse, type StatementLine } from "../../lib/api/customers";
import { appTodayISO } from "../../lib/time";

interface CustomerStatementTabProps {
  customerId: string;
  customerName: string;
}

function twelveMonthsAgo(): string {
  const d = parseDatePickerInputValue(appTodayISO()) ?? new Date();
  d.setMonth(d.getMonth() - 12);
  return serializeDatePickerValue(d);
}

function today(): string {
  return appTodayISO();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

function formatCurrency(amount: string, currency = "TWD"): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return `${currency} 0.00`;
  return `${currency} ${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function computeSummary(lines: StatementLine[]) {
  const unpaidInvoices = lines.filter(
    (l) => l.type === "invoice" && parseFloat(l.balance) > 0
  );
  const oldestUnpaid = unpaidInvoices.length > 0 ? unpaidInvoices[0] : null;
  // Average days to pay: for paid invoices, compute invoice_date to payment_date delta
  const paidInvoices = lines.filter((l) => l.type === "invoice" && parseFloat(l.balance) === 0);
  let avgDays: number | null = null;
  if (paidInvoices.length > 0) {
    let totalDays = 0;
    let count = 0;
    for (const inv of paidInvoices) {
      const invDate = new Date(inv.date).getTime();
      // Find corresponding payment
      const payment = lines.find(
        (l) =>
          l.type === "payment" &&
          l.reference.includes(inv.reference.replace("Invoice ", "")) &&
          new Date(l.date).getTime() >= invDate
      );
      if (payment) {
        const days = Math.round(
          (new Date(payment.date).getTime() - invDate) / (1000 * 60 * 60 * 24)
        );
        totalDays += days;
        count++;
      }
    }
    avgDays = count > 0 ? Math.round(totalDays / count) : null;
  }
  return { oldestUnpaid, avgDays };
}

export function CustomerStatementTab({ customerId, customerName }: CustomerStatementTabProps) {
  const { t } = useTranslation("common");
  const [fromDate, setFromDate] = useState(twelveMonthsAgo);
  const [toDate, setToDate] = useState(today);
  const [data, setData] = useState<CustomerStatementResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCustomerStatement(customerId, fromDate, toDate);
      setData(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [customerId, fromDate, toDate]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleExportCSV = () => {
    if (!data) return;
    const headers = [
      t("customer.detail.statement.table.date"),
      t("customer.detail.statement.table.type"),
      t("customer.detail.statement.table.reference"),
      t("customer.detail.statement.table.description"),
      t("customer.detail.statement.table.debit"),
      t("customer.detail.statement.table.credit"),
      t("customer.detail.statement.table.balance"),
    ];
    const rows = data.lines.map((line) => [
      line.date,
      line.type === "invoice"
        ? t("customer.detail.statement.invoiceType")
        : t("customer.detail.statement.paymentType"),
      line.reference,
      line.description,
      line.debit,
      line.credit,
      line.balance,
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${customerName}_statement_${fromDate}_${toDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const { oldestUnpaid, avgDays } = computeSummary(data?.lines ?? []);

  return (
    <div className="space-y-4">
      {/* Summary box */}
      {data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-xl border p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("customer.detail.statement.summary.totalOutstanding")}
            </p>
            <p className="mt-1 text-xl font-semibold">
              {formatCurrency(data.current_balance, data.currency_code)}
            </p>
          </div>
          <div className="rounded-xl border p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("customer.detail.statement.summary.oldestUnpaid")}
            </p>
            {oldestUnpaid ? (
              <p className="mt-1 text-xl font-semibold">
                {formatDate(oldestUnpaid.date)} / {formatCurrency(oldestUnpaid.balance, data.currency_code)}
              </p>
            ) : (
              <p className="mt-1 text-muted-foreground">—</p>
            )}
          </div>
          <div className="rounded-xl border p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("customer.detail.statement.summary.avgDaysToPay")}
            </p>
            {avgDays !== null ? (
              <p className="mt-1 text-xl font-semibold">{avgDays} days</p>
            ) : (
              <p className="mt-1 text-muted-foreground">—</p>
            )}
          </div>
        </div>
      )}

      {/* Filter row */}
      <div className="flex items-center gap-3">
        <div className="flex items-end gap-2">
          <label className="flex flex-col gap-1 text-sm font-medium" htmlFor="customer-statement-from-date">
            {t("customer.detail.statement.filter.from")}
            <DatePicker
              id="customer-statement-from-date"
              aria-label={t("customer.detail.statement.filter.from")}
              placeholder={t("customer.detail.statement.filter.from")}
              value={parseDatePickerInputValue(fromDate)}
              onChange={(value) => setFromDate(serializeDatePickerValue(value))}
              className="w-[10rem]"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium" htmlFor="customer-statement-to-date">
            {t("customer.detail.statement.filter.to")}
            <DatePicker
              id="customer-statement-to-date"
              aria-label={t("customer.detail.statement.filter.to")}
              placeholder={t("customer.detail.statement.filter.to")}
              value={parseDatePickerInputValue(toDate)}
              onChange={(value) => setToDate(serializeDatePickerValue(value))}
              className="w-[10rem]"
            />
          </label>
        </div>
        <Button size="sm" variant="outline" onClick={() => void load()}>
          Refresh
        </Button>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" onClick={() => window.print()}>
            {t("customer.detail.statement.actions.print")}
          </Button>
          <Button size="sm" variant="outline" onClick={handleExportCSV}>
            {t("customer.detail.statement.actions.exportCSV")}
          </Button>
        </div>
      </div>

      {/* Table */}
      {loading && <p>{t("common.loading")}</p>}
      {error && <SurfaceMessage tone="danger">{error}</SurfaceMessage>}
      {!loading && !error && data && (
        <>
          {data.lines.length === 0 ? (
            <SurfaceMessage tone="default">{t("customer.detail.statement.empty")}</SurfaceMessage>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("customer.detail.statement.table.date")}</TableHead>
                  <TableHead>{t("customer.detail.statement.table.type")}</TableHead>
                  <TableHead>{t("customer.detail.statement.table.reference")}</TableHead>
                  <TableHead>{t("customer.detail.statement.table.description")}</TableHead>
                  <TableHead className="text-right">
                    {t("customer.detail.statement.table.debit")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("customer.detail.statement.table.credit")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("customer.detail.statement.table.balance")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* Opening balance row */}
                <TableRow className="bg-muted/30">
                  <TableCell colSpan={4} className="font-medium text-muted-foreground">
                    Opening Balance
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">—</TableCell>
                  <TableCell className="text-right text-muted-foreground">—</TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(data.opening_balance, data.currency_code)}
                  </TableCell>
                </TableRow>
                {data.lines.map((line, i) => (
                  <TableRow key={i}>
                    <TableCell>{formatDate(line.date)}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          line.type === "invoice"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {line.type === "invoice"
                          ? t("customer.detail.statement.invoiceType")
                          : t("customer.detail.statement.paymentType")}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{line.reference}</TableCell>
                    <TableCell>{line.description}</TableCell>
                    <TableCell className="text-right">
                      {line.debit !== "0.00" ? formatCurrency(line.debit, data.currency_code) : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {line.credit !== "0.00" ? formatCurrency(line.credit, data.currency_code) : "—"}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(line.balance, data.currency_code)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </>
      )}
    </div>
  );
}
