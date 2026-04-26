/**
 * Ledger Table Component (Epic 26.2)
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  GLEntryWithAccount,
  VOUCHER_TYPE_LABELS,
  VoucherType,
} from "@/domain/accounting/types";
import { useAccountLedger } from "@/domain/accounting/hooks/useLedger";
import {
  buildJournalEntryDetailPath,
  buildAccountDetailPath,
} from "@/lib/routes";

interface LedgerTableProps {
  accountId?: string;
  journalEntryId?: string;
  showVoucherDetails?: boolean;
  initialFromDate?: string;
  initialToDate?: string;
}

export function LedgerTable({
  accountId,
  journalEntryId,
  showVoucherDetails = false,
  initialFromDate,
  initialToDate,
}: LedgerTableProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Date filters
  const [fromDate, setFromDate] = useState<string>(initialFromDate || "");
  const [toDate, setToDate] = useState<string>(initialToDate || "");

  // Fetch ledger
  const { data: ledger, refetch } = useAccountLedger({
    accountId,
    journalEntryId,
    fromDate: fromDate || undefined,
    toDate: toDate || undefined,
  });

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "decimal",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  if (accountId && !ledger) {
    return (
      <div className="text-center py-4">
        <div className="text-muted-foreground">{t("common.loading")}</div>
      </div>
    );
  }

  // Ledger entries (from account ledger or journal entry GL entries)
  const entries: GLEntryWithAccount[] = ledger?.summary?.entries || [];

  return (
    <div className="space-y-4">
      {/* Filters (only show for account ledger) */}
      {accountId && (
        <div className="flex gap-4">
          <div className="flex-1">
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full px-3 py-2 border rounded"
              placeholder={t("accounting.fromDate")}
            />
          </div>
          <div className="flex-1">
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full px-3 py-2 border rounded"
              placeholder={t("accounting.toDate")}
            />
          </div>
          <Button variant="outline" onClick={() => refetch()}>
            {t("common.filter")}
          </Button>
        </div>
      )}

      {/* Summary (only for account ledger) */}
      {ledger && (
        <div className="grid grid-cols-4 gap-4 p-4 bg-muted rounded-lg">
          <div>
            <div className="text-sm text-muted-foreground">
              {t("accounting.openingBalance")}
            </div>
            <div className="text-lg font-semibold">
              {formatCurrency(ledger.summary.opening_balance)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">
              {t("accounting.totalDebit")}
            </div>
            <div className="text-lg font-semibold text-blue-600">
              {formatCurrency(ledger.summary.total_debit)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">
              {t("accounting.totalCredit")}
            </div>
            <div className="text-lg font-semibold text-red-600">
              {formatCurrency(ledger.summary.total_credit)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">
              {t("accounting.closingBalance")}
            </div>
            <div className="text-lg font-semibold">
              {formatCurrency(ledger.summary.closing_balance)}
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      {entries.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          {t("accounting.noLedgerEntries")}
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-3">
                  {t("accounting.postingDate")}
                </th>
                {showVoucherDetails && (
                  <>
                    <th className="text-left p-3">
                      {t("accounting.voucherType")}
                    </th>
                    <th className="text-left p-3">
                      {t("accounting.voucherNumber")}
                    </th>
                  </>
                )}
                {!accountId && (
                  <th className="text-left p-3">
                    {t("accounting.account")}
                  </th>
                )}
                <th className="text-left p-3">
                  {t("accounting.remark")}
                </th>
                <th className="text-right p-3">
                  {t("accounting.debit")}
                </th>
                <th className="text-right p-3">
                  {t("accounting.credit")}
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-t hover:bg-muted/50"
                >
                  <td className="p-3">
                    {formatDate(entry.posting_date)}
                  </td>
                  {showVoucherDetails && (
                    <>
                      <td className="p-3">
                        {VOUCHER_TYPE_LABELS[entry.voucher_type as VoucherType] ||
                          entry.voucher_type}
                      </td>
                      <td className="p-3">
                        {entry.journal_entry_id ? (
                          <button
                            className="text-primary hover:underline"
                            onClick={() =>
                              navigate(
                                buildJournalEntryDetailPath(entry.journal_entry_id!)
                              )
                            }
                          >
                            {entry.voucher_number}
                          </button>
                        ) : (
                          entry.voucher_number
                        )}
                      </td>
                    </>
                  )}
                  {!accountId && (
                    <td className="p-3">
                      <div>
                        <button
                          className="text-primary hover:underline"
                          onClick={() =>
                            navigate(buildAccountDetailPath(entry.account_id))
                          }
                        >
                          {entry.account_number} - {entry.account_name}
                        </button>
                      </div>
                    </td>
                  )}
                  <td className="p-3 text-muted-foreground">
                    {entry.remark || "-"}
                  </td>
                  <td className="p-3 text-right">
                    {entry.debit > 0 ? formatCurrency(entry.debit) : "-"}
                  </td>
                  <td className="p-3 text-right">
                    {entry.credit > 0 ? formatCurrency(entry.credit) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
