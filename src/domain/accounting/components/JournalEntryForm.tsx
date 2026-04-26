/**
 * Journal Entry Form Component (Epic 26.2)
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

import {
  CreateJournalEntryRequest,
  JournalEntryFormData,
  VoucherType,
  VOUCHER_TYPE_LABELS,
} from "@/domain/accounting/types";
import { useAccountTree, useFlattenedAccounts } from "@/domain/accounting/hooks/useAccounts";
import { useCreateJournalEntry } from "@/domain/accounting/hooks/useJournalEntries";

interface JournalEntryFormProps {
  initialData?: JournalEntryFormData;
  onSuccess: (entry: any) => void;
  onCancel: () => void;
}

export function JournalEntryForm({
  initialData,
  onSuccess,
  onCancel,
}: JournalEntryFormProps) {
  const { t } = useTranslation();
  const toast = useToast();

  // Fetch accounts
  const { tree } = useAccountTree();
  const accounts = useFlattenedAccounts(tree);

  // Form state
  const [formData, setFormData] = useState<JournalEntryFormData>({
    voucher_type: initialData?.voucher_type || "Journal Entry",
    posting_date: initialData?.posting_date || new Date(),
    reference_date: initialData?.reference_date || null,
    narration: initialData?.narration || "",
    lines: initialData?.lines || [
      { account_id: "", debit: 0, credit: 0, remark: "" },
      { account_id: "", debit: 0, credit: 0, remark: "" },
    ],
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  // Create entry
  const { createEntry } = useCreateJournalEntry();

  // Calculate totals
  const totalDebit = formData.lines.reduce((sum, line) => sum + (line.debit || 0), 0);
  const totalCredit = formData.lines.reduce((sum, line) => sum + (line.credit || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  // Add line
  const addLine = useCallback(() => {
    setFormData((prev) => ({
      ...prev,
      lines: [...prev.lines, { account_id: "", debit: 0, credit: 0, remark: "" }],
    }));
  }, []);

  // Remove line
  const removeLine = useCallback(
    (index: number) => {
      if (formData.lines.length <= 2) {
        toast.error(t("accounting.atLeastTwoLines"));
        return;
      }
      setFormData((prev) => ({
        ...prev,
        lines: prev.lines.filter((_, i) => i !== index),
      }));
    },
    [formData.lines.length, toast, t]
  );

  // Update line
  const updateLine = useCallback(
    (index: number, field: string, value: number | string) => {
      setFormData((prev) => {
        const newLines = [...prev.lines];
        newLines[index] = { ...newLines[index], [field]: value };

        // If updating debit to non-zero, clear credit
        if (field === "debit" && typeof value === "number" && value > 0) {
          newLines[index].credit = 0;
        }
        // If updating credit to non-zero, clear debit
        if (field === "credit" && typeof value === "number" && value > 0) {
          newLines[index].debit = 0;
        }

        return { ...prev, lines: newLines };
      });
    },
    []
  );

  // Validate form
  const validate = useCallback((): string[] => {
    const validationErrors: string[] = [];

    if (formData.lines.length < 2) {
      validationErrors.push(t("accounting.atLeastTwoLines"));
    }

    for (let i = 0; i < formData.lines.length; i++) {
      const line = formData.lines[i];
      if (!line.account_id) {
        validationErrors.push(t("accounting.lineAccountRequired", { line: i + 1 }));
      }
      if (line.debit === 0 && line.credit === 0) {
        validationErrors.push(t("accounting.lineAmountRequired", { line: i + 1 }));
      }
      if (line.debit > 0 && line.credit > 0) {
        validationErrors.push(t("accounting.lineSingleAmount", { line: i + 1 }));
      }
    }

    if (!isBalanced) {
      validationErrors.push(
        t("accounting.entryMustBeBalanced", {
          debit: totalDebit.toFixed(2),
          credit: totalCredit.toFixed(2),
        })
      );
    }

    return validationErrors;
  }, [formData, isBalanced, totalDebit, totalCredit, t]);

  // Handle submit
  const handleSubmit = useCallback(async () => {
    const validationErrors = validate();
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors([]);

    try {
      const payload: CreateJournalEntryRequest = {
        voucher_type: formData.voucher_type,
        posting_date: formData.posting_date.toISOString().split("T")[0],
        reference_date: formData.reference_date?.toISOString().split("T")[0] || null,
        narration: formData.narration || null,
        lines: formData.lines.map((line) => ({
          account_id: line.account_id,
          debit: line.debit,
          credit: line.credit,
          remark: line.remark || null,
        })),
      };

      const result = await createEntry(payload);
      onSuccess(result);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t("accounting.createFailed");
      setErrors([errorMessage]);
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validate, createEntry, onSuccess, t]);

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "decimal",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Get ledger accounts only (non-group)
  const ledgerAccounts = accounts.filter((acc) => !acc.is_group);

  return (
    <div className="space-y-6">
      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-destructive/10 text-destructive p-3 rounded">
          <ul className="list-disc list-inside">
            {errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Header */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t("accounting.voucherType")}
          </label>
          <Select
            value={formData.voucher_type}
            onValueChange={(value) =>
              setFormData((prev) => ({ ...prev, voucher_type: value as VoucherType }))
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(VOUCHER_TYPE_LABELS) as VoucherType[]).map((type) => (
                <SelectItem key={type} value={type}>
                  {VOUCHER_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t("accounting.postingDate")}
          </label>
          <Popover>
            <PopoverTrigger>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !formData.posting_date && "text-muted-foreground"
                )}
              >
                {formData.posting_date?.toLocaleDateString() || "Select date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={formData.posting_date}
                onSelect={(date) =>
                  setFormData((prev) => ({ ...prev, posting_date: date || new Date() }))
                }
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Narration */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          {t("accounting.narration")}
        </label>
        <Textarea
          value={formData.narration}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, narration: e.target.value }))
          }
          placeholder={t("accounting.narrationPlaceholder")}
          rows={2}
        />
      </div>

      {/* Lines */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">
            {t("accounting.entryLines")}
          </label>
          <Button type="button" variant="outline" size="sm" onClick={addLine}>
            {t("accounting.addLine")}
          </Button>
        </div>

        <div className="border rounded-lg">
          {/* Header */}
          <div className="grid grid-cols-12 gap-2 p-3 bg-muted text-sm font-medium">
            <div className="col-span-5">{t("accounting.account")}</div>
            <div className="col-span-4">{t("accounting.remark")}</div>
            <div className="col-span-1 text-right">{t("accounting.debit")}</div>
            <div className="col-span-1 text-right">{t("accounting.credit")}</div>
            <div className="col-span-1"></div>
          </div>

          {/* Line rows */}
          {formData.lines.map((line, index) => (
            <div
              key={index}
              className="grid grid-cols-12 gap-2 p-3 border-t items-center"
            >
              <div className="col-span-5">
                <Select
                  value={line.account_id}
                  onValueChange={(value) => updateLine(index, "account_id", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t("accounting.selectAccount")} />
                  </SelectTrigger>
                  <SelectContent>
                    {ledgerAccounts.map((acc) => (
                      <SelectItem key={acc.id} value={acc.id}>
                        {acc.account_number} - {acc.account_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-4">
                <Input
                  value={line.remark}
                  onChange={(e) => updateLine(index, "remark", e.target.value)}
                  placeholder={t("accounting.remarkOptional")}
                />
              </div>
              <div className="col-span-1">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.debit || ""}
                  onChange={(e) =>
                    updateLine(index, "debit", parseFloat(e.target.value) || 0)
                  }
                  className="text-right"
                />
              </div>
              <div className="col-span-1">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.credit || ""}
                  onChange={(e) =>
                    updateLine(index, "credit", parseFloat(e.target.value) || 0)
                  }
                  className="text-right"
                />
              </div>
              <div className="col-span-1 text-center">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeLine(index)}
                  disabled={formData.lines.length <= 2}
                >
                  ×
                </Button>
              </div>
            </div>
          ))}

          {/* Totals */}
          <div className="grid grid-cols-12 gap-2 p-3 bg-muted border-t font-medium">
            <div className="col-span-9 text-right">
              {t("accounting.total")}
            </div>
            <div className="col-span-1 text-right">{formatCurrency(totalDebit)}</div>
            <div className="col-span-1 text-right">{formatCurrency(totalCredit)}</div>
            <div className="col-span-1"></div>
          </div>
        </div>

        {/* Balance indicator */}
        <div
          className={`text-sm ${isBalanced ? "text-green-600" : "text-red-600"}`}
        >
          {isBalanced ? (
            <span>✓ {t("accounting.entryIsBalanced")}</span>
          ) : (
            <span>
              ✗ {t("accounting.difference")}: {formatCurrency(Math.abs(totalDebit - totalCredit))}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? t("common.submitting") : t("accounting.createSubmit")}
        </Button>
      </div>
    </div>
  );
}
