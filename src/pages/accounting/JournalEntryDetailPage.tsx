/**
 * Journal Entry Detail Page (Epic 26.2)
 */

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/useToast";

import {
  JournalEntryStatus,
  JOURNAL_ENTRY_STATUS_COLORS,
  JOURNAL_ENTRY_STATUS_LABELS,
  VOUCHER_TYPE_LABELS,
  VoucherType,
} from "@/domain/accounting/types";
import { useJournalEntry } from "@/domain/accounting/hooks/useJournalEntries";
import { LedgerTable } from "@/domain/accounting/components/LedgerTable";
import {
  buildJournalEntriesPath,
  buildJournalEntryDetailPath,
} from "@/lib/routes";

export function JournalEntryDetailPage() {
  const { t } = useTranslation();
  const { success: toastSuccess, error: toastError } = useToast();
  const navigate = useNavigate();
  const { journalEntryId } = useParams<{ journalEntryId: string }>();

  // Reverse dialog
  const [reverseOpen, setReverseOpen] = useState(false);
  const [reversalDate, setReversalDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [cancelReason, setCancelReason] = useState("");

  // Fetch journal entry
  const {
    entry,
    isLoading,
    error,
    refetch,
    submitEntry,
    reverseEntry,
    isSubmitting,
    isReversing,
  } = useJournalEntry(journalEntryId);

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString();
  };

  // Format datetime
  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString();
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "decimal",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Handle submit
  const handleSubmit = useCallback(async () => {
    if (!journalEntryId) return;
    try {
      const result = await submitEntry(journalEntryId);
      toastSuccess(
        t("accounting.journalEntrySubmitted", {
          voucherNumber: result.journal_entry.voucher_number,
          glEntries: result.gl_entries_created,
        })
      );
    } catch (err: any) {
      toastError(
        err?.detail?.errors?.join(", ") ||
          t("accounting.submitFailed")
      );
    }
  }, [journalEntryId, submitEntry, toastSuccess, toastError, t]);

  // Handle reverse
  const handleReverse = useCallback(async () => {
    if (!journalEntryId) return;
    try {
      const result = await reverseEntry(journalEntryId, {
        reversalDate,
        cancelReason,
      });
      toastSuccess(
        t("accounting.journalEntryReversed", {
          original: result.original_entry.voucher_number,
          reversing: result.reversing_entry.voucher_number,
        })
      );
      setReverseOpen(false);
      refetch();
    } catch (err: any) {
      toastError(
        err?.detail?.errors?.join(", ") ||
          t("accounting.reverseFailed")
      );
    }
  }, [journalEntryId, reversalDate, cancelReason, reverseEntry, toastSuccess, toastError, t, refetch]);

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-8">{t("common.loading")}</div>
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              {error?.message || t("accounting.journalEntryNotFound")}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isDraft = entry.status === "Draft";
  const isSubmitted = entry.status === "Submitted";

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(buildJournalEntriesPath())}
            className="mb-2"
          >
            ← {t("accounting.backToJournalEntries")}
          </Button>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            {entry.voucher_number}
            <span
              className="px-3 py-1 rounded text-sm font-medium"
              style={{
                backgroundColor: `${JOURNAL_ENTRY_STATUS_COLORS[entry.status as JournalEntryStatus]}20`,
                color: JOURNAL_ENTRY_STATUS_COLORS[entry.status as JournalEntryStatus],
              }}
            >
              {JOURNAL_ENTRY_STATUS_LABELS[entry.status as JournalEntryStatus]}
            </span>
          </h1>
          <p className="text-muted-foreground">
            {VOUCHER_TYPE_LABELS[entry.voucher_type as VoucherType]} •{" "}
            {t("accounting.postedOn", { date: formatDate(entry.posting_date) })}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {isDraft && (
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? t("common.submitting") : t("accounting.submitEntry")}
            </Button>
          )}
          {isSubmitted && (
            <Dialog open={reverseOpen} onOpenChange={setReverseOpen}>
              <DialogTrigger>
                <Button variant="destructive" onClick={() => setReverseOpen(true)}>
                  {t("accounting.reverseEntry")}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t("accounting.reverseEntry")}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>{t("accounting.reversalDate")}</Label>
                    <Input
                      type="date"
                      value={reversalDate}
                      onChange={(e) => setReversalDate(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("accounting.cancelReason")}</Label>
                    <Textarea
                      value={cancelReason}
                      onChange={(e) => setCancelReason(e.target.value)}
                      placeholder={t("accounting.enterCancelReason")}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setReverseOpen(false)}
                    >
                      {t("common.cancel")}
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleReverse}
                      disabled={isReversing}
                    >
                      {isReversing
                        ? t("common.reversing")
                        : t("accounting.confirmReverse")}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Entry Details */}
          <Card>
            <CardHeader>
              <CardTitle>{t("accounting.entryDetails")}</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.voucherType")}
                  </dt>
                  <dd className="font-medium">
                    {VOUCHER_TYPE_LABELS[entry.voucher_type as VoucherType]}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.postingDate")}
                  </dt>
                  <dd className="font-medium">{formatDate(entry.posting_date)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.referenceDate")}
                  </dt>
                  <dd className="font-medium">
                    {formatDate(entry.reference_date)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.narration")}
                  </dt>
                  <dd className="font-medium">
                    {entry.narration || "-"}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Lines */}
          <Card>
            <CardHeader>
              <CardTitle>{t("accounting.entryLines")}</CardTitle>
              <CardDescription>
                {t("accounting.linesCount", { count: entry.lines.length })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">
                      {t("accounting.account")}
                    </th>
                    <th className="text-left py-2">
                      {t("accounting.remark")}
                    </th>
                    <th className="text-right py-2">
                      {t("accounting.debit")}
                    </th>
                    <th className="text-right py-2">
                      {t("accounting.credit")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {entry.lines.map((line) => (
                    <tr key={line.id} className="border-b">
                      <td className="py-2">
                        <div className="font-medium">{line.account_name}</div>
                        <div className="text-sm text-muted-foreground">
                          {line.account_number}
                        </div>
                      </td>
                      <td className="py-2 text-muted-foreground">
                        {line.remark || "-"}
                      </td>
                      <td className="py-2 text-right">
                        {line.debit > 0 ? formatCurrency(line.debit) : "-"}
                      </td>
                      <td className="py-2 text-right">
                        {line.credit > 0 ? formatCurrency(line.credit) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="font-bold">
                    <td colSpan={2} className="py-2">
                      {t("accounting.total")}
                    </td>
                    <td className="py-2 text-right">
                      {formatCurrency(entry.total_debit)}
                    </td>
                    <td className="py-2 text-right">
                      {formatCurrency(entry.total_credit)}
                    </td>
                  </tr>
                </tfoot>
              </table>

              {/* Balance indicator */}
              <div className="mt-4 flex items-center gap-2">
                {entry.total_debit === entry.total_credit ? (
                  <span className="text-sm text-green-600">
                    ✓ {t("accounting.balanced")}
                  </span>
                ) : (
                  <span className="text-sm text-red-600">
                    ✗ {t("accounting.notBalanced")}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>{t("accounting.statusHistory")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <dt className="text-sm text-muted-foreground">
                  {t("accounting.createdAt")}
                </dt>
                <dd className="font-medium">
                  {formatDateTime(entry.created_at)}
                </dd>
              </div>

              {entry.submitted_at && (
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.submittedAt")}
                  </dt>
                  <dd className="font-medium">
                    {formatDateTime(entry.submitted_at)}
                  </dd>
                </div>
              )}

              {entry.cancelled_at && (
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.cancelledAt")}
                  </dt>
                  <dd className="font-medium">
                    {formatDateTime(entry.cancelled_at)}
                  </dd>
                </div>
              )}

              {entry.cancel_reason && (
                <div>
                  <dt className="text-sm text-muted-foreground">
                    {t("accounting.cancelReason")}
                  </dt>
                  <dd className="font-medium">{entry.cancel_reason}</dd>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Reversal Links */}
          {(entry.reverses_id || entry.reversed_by_id) && (
            <Card>
              <CardHeader>
                <CardTitle>{t("accounting.reversalChain")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {entry.reverses_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() =>
                      navigate(buildJournalEntryDetailPath(entry.reverses_id!))
                    }
                  >
                    ← {t("accounting.reverses", {
                      voucher: entry.reverses_id,
                    })}
                  </Button>
                )}
                {entry.reversed_by_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() =>
                      navigate(buildJournalEntryDetailPath(entry.reversed_by_id!))
                    }
                  >
                    → {t("accounting.reversedBy", {
                      voucher: entry.reversed_by_id,
                    })}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* GL Entries */}
          {isSubmitted && entry.id && (
            <Card>
              <CardHeader>
                <CardTitle>{t("accounting.glEntries")}</CardTitle>
                <CardDescription>
                  {t("accounting.glEntriesDescription")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <LedgerTable
                  accountId={undefined}
                  journalEntryId={entry.id}
                  showVoucherDetails
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
