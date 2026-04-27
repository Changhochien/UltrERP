/**
 * Journal Entries List Page (Epic 26.2)
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/useToast";

import {
  JournalEntry,
  JournalEntryStatus,
  JOURNAL_ENTRY_STATUS_COLORS,
  JOURNAL_ENTRY_STATUS_LABELS,
  VOUCHER_TYPE_LABELS,
  VoucherType,
} from "@/domain/accounting/types";
import { useJournalEntries } from "@/domain/accounting/hooks/useJournalEntries";
import { JournalEntryForm } from "@/domain/accounting/components/JournalEntryForm";
import { buildJournalEntryDetailPath } from "@/lib/routes";

export function JournalEntriesPage() {
  const { t } = useTranslation();
  const { success: toastSuccess } = useToast();
  const navigate = useNavigate();

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [voucherTypeFilter, setVoucherTypeFilter] = useState<string>("");

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false);

  // Fetch journal entries
  const { entries, isLoading, total } = useJournalEntries({
    page,
    pageSize,
    status: statusFilter || undefined,
    voucherType: voucherTypeFilter || undefined,
  });

  // Handle create success
  const handleCreateSuccess = useCallback(
    (entry: JournalEntry) => {
      setCreateOpen(false);
      toastSuccess(
        t("accounting.journalEntryCreated", {
          voucherNumber: entry.voucher_number,
        })
      );
      navigate(buildJournalEntryDetailPath(entry.id));
    },
    [t, toastSuccess, navigate]
  );

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

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">
            {t("accounting.journalEntries")}
          </h1>
          <p className="text-muted-foreground">
            {t("accounting.journalEntriesDescription")}
          </p>
        </div>

        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger>
            <Button onClick={() => setCreateOpen(true)}>
              {t("accounting.newJournalEntry")}
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{t("accounting.createJournalEntry")}</DialogTitle>
            </DialogHeader>
            <JournalEntryForm
              onSuccess={handleCreateSuccess}
              onCancel={() => setCreateOpen(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="w-48">
              <Select
                value={statusFilter}
                onValueChange={(value) => {
                  setStatusFilter(value);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={t("accounting.allStatuses")}
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t("accounting.allStatuses")}</SelectItem>
                  {(Object.keys(JOURNAL_ENTRY_STATUS_LABELS) as JournalEntryStatus[]).map(
                    (status) => (
                      <SelectItem key={status} value={status}>
                        {JOURNAL_ENTRY_STATUS_LABELS[status]}
                      </SelectItem>
                    )
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="w-48">
              <Select
                value={voucherTypeFilter}
                onValueChange={(value) => {
                  setVoucherTypeFilter(value);
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={t("accounting.allVoucherTypes")}
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t("accounting.allVoucherTypes")}</SelectItem>
                  {(Object.keys(VOUCHER_TYPE_LABELS) as VoucherType[]).map(
                    (type) => (
                      <SelectItem key={type} value={type}>
                        {VOUCHER_TYPE_LABELS[type]}
                      </SelectItem>
                    )
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Entries Table */}
      <Card>
        <CardHeader>
          <CardTitle>{t("accounting.journalEntries")}</CardTitle>
          <CardDescription>
            {t("accounting.totalEntries", { count: total })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">{t("loading")}</div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t("accounting.noJournalEntries")}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("accounting.voucherNumber")}</TableHead>
                    <TableHead>{t("accounting.voucherType")}</TableHead>
                    <TableHead>{t("accounting.postingDate")}</TableHead>
                    <TableHead className="text-right">{t("accounting.debit")}</TableHead>
                    <TableHead className="text-right">{t("accounting.credit")}</TableHead>
                    <TableHead>{t("accounting.status")}</TableHead>
                    <TableHead>{t("accounting.narration")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => (
                    <TableRow
                      key={entry.id}
                      className="cursor-pointer"
                      onClick={() =>
                        navigate(buildJournalEntryDetailPath(entry.id))
                      }
                    >
                      <TableCell className="font-medium">
                        {entry.voucher_number}
                      </TableCell>
                      <TableCell>
                        {VOUCHER_TYPE_LABELS[entry.voucher_type as VoucherType]}
                      </TableCell>
                      <TableCell>{formatDate(entry.posting_date)}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(entry.total_debit)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(entry.total_credit)}
                      </TableCell>
                      <TableCell>
                        <span
                          className="px-2 py-1 rounded text-xs font-medium"
                          style={{
                            backgroundColor: `${JOURNAL_ENTRY_STATUS_COLORS[entry.status as JournalEntryStatus]}20`,
                            color: JOURNAL_ENTRY_STATUS_COLORS[entry.status as JournalEntryStatus],
                          }}
                        >
                          {JOURNAL_ENTRY_STATUS_LABELS[entry.status as JournalEntryStatus]}
                        </span>
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {entry.narration || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {total > pageSize && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    {t("accounting.showingEntries", {
                      start: (page - 1) * pageSize + 1,
                      end: Math.min(page * pageSize, total),
                      total,
                    })}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      {t("previous")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page * pageSize >= total}
                    >
                      {t("next")}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
