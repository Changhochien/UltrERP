/**
 * Fiscal Years management page (Epic 26).
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Calendar,
  Check,
  Clock,
  Edit,
  Lock,
  Plus,
  RefreshCw,
  Unlock,
  X,
} from "lucide-react";

import type { FiscalYear, FiscalYearFormData, FiscalYearStatus } from "@/domain/accounting/types";
import {
  useCloseFiscalYear,
  useCreateFiscalYear,
  useFiscalYears,
  useReopenFiscalYear,
  useUpdateFiscalYear,
} from "@/domain/accounting/hooks/useFiscalYears";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/DatePicker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";

const STATUS_COLORS: Record<FiscalYearStatus, { bg: string; text: string }> = {
  Draft: { bg: "bg-gray-100", text: "text-gray-700" },
  Open: { bg: "bg-green-100", text: "text-green-700" },
  Closed: { bg: "bg-red-100", text: "text-red-700" },
  Archived: { bg: "bg-gray-100", text: "text-gray-500" },
};

export function FiscalYearsPage() {
  const { t } = useTranslation();
  const { error: toastError } = useToast();

  const [page, setPage] = useState(1);
  const [selectedFiscalYear, setSelectedFiscalYear] = useState<FiscalYear | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isCloseDialogOpen, setIsCloseDialogOpen] = useState(false);
  const [formData, setFormData] = useState<Partial<FiscalYearFormData>>({});
  const [closureNotes, setClosureNotes] = useState("");

  const { fiscalYears, isLoading, refetch } = useFiscalYears(page);
  const { createFiscalYear, isCreating } = useCreateFiscalYear();
  const { updateFiscalYear, isUpdating } = useUpdateFiscalYear();
  const { closeFiscalYear, isClosing } = useCloseFiscalYear();
  const { reopenFiscalYear, isReopening } = useReopenFiscalYear();

  const handleCreate = () => {
    const currentYear = new Date().getFullYear();
    setFormData({
      label: `FY${currentYear}`,
      start_date: new Date(currentYear, 0, 1),
      end_date: new Date(currentYear, 11, 31),
      is_default: false,
    });
    setIsCreateDialogOpen(true);
  };

  const handleEdit = (fy: FiscalYear) => {
    setSelectedFiscalYear(fy);
    setFormData({
      label: fy.label,
      start_date: new Date(fy.start_date),
      end_date: new Date(fy.end_date),
      is_default: fy.is_default,
    });
    setIsEditDialogOpen(true);
  };

  const handleClose = (fy: FiscalYear) => {
    setSelectedFiscalYear(fy);
    setClosureNotes("");
    setIsCloseDialogOpen(true);
  };

  const handleSaveCreate = async () => {
    if (!formData.label || !formData.start_date || !formData.end_date) {
      toastError(t("accounting.fillRequiredFields"));
      return;
    }

    if (formData.start_date >= formData.end_date) {
      toastError(t("accounting.endDateAfterStartDate"));
      return;
    }

    try {
      await createFiscalYear(formData as FiscalYearFormData);
      setIsCreateDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedFiscalYear) return;

    if (!formData.label || !formData.start_date || !formData.end_date) {
      toastError(t("accounting.fillRequiredFields"));
      return;
    }

    try {
      await updateFiscalYear(selectedFiscalYear.id, {
        label: formData.label,
        start_date: formData.start_date.toISOString().split("T")[0],
        end_date: formData.end_date.toISOString().split("T")[0],
        is_default: formData.is_default,
      });
      setIsEditDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleSaveClose = async () => {
    if (!selectedFiscalYear) return;

    try {
      await closeFiscalYear(
        selectedFiscalYear.id,
        selectedFiscalYear.label,
        closureNotes || undefined
      );
      setIsCloseDialogOpen(false);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const handleReopen = async (fy: FiscalYear) => {
    try {
      await reopenFiscalYear(fy.id, fy.label);
      refetch();
    } catch {
      // Error handled in hook
    }
  };

  const isWorking = isCreating || isUpdating || isClosing || isReopening;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{t("accounting.fiscalYears")}</h1>
          {fiscalYears && (
            <span className="text-sm text-muted-foreground">
              ({fiscalYears.total} {t("accounting.total")})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
          <Button onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            {t("accounting.createFiscalYear")}
          </Button>
        </div>
      </div>

      {/* List */}
      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : fiscalYears && fiscalYears.items.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-sm">
                <th className="px-4 py-3 font-medium">{t("accounting.label")}</th>
                <th className="px-4 py-3 font-medium">{t("accounting.startDate")}</th>
                <th className="px-4 py-3 font-medium">{t("accounting.endDate")}</th>
                <th className="px-4 py-3 font-medium">{t("accounting.status")}</th>
                <th className="px-4 py-3 font-medium">{t("accounting.isDefault")}</th>
                <th className="px-4 py-3 font-medium">{t("accounting.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {fiscalYears.items.map((fy) => (
                <tr key={fy.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-medium">{fy.label}</span>
                      {fy.is_default && (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary">
                          {t("accounting.default")}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {new Date(fy.start_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {new Date(fy.end_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium ${
                        STATUS_COLORS[fy.status].bg
                      } ${STATUS_COLORS[fy.status].text}`}
                    >
                      {fy.status === "Open" && <Clock className="h-3 w-3" />}
                      {fy.status === "Closed" && <Lock className="h-3 w-3" />}
                      {fy.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {fy.is_default ? (
                      <Check className="h-4 w-4 text-green-600" />
                    ) : (
                      <X className="h-4 w-4 text-muted-foreground" />
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <Edit className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleEdit(fy)}>
                          <Edit className="mr-2 h-4 w-4" />
                          {t("common.edit")}
                        </DropdownMenuItem>
                        {fy.status === "Open" && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleClose(fy)}
                              className="text-amber-600"
                            >
                              <Lock className="mr-2 h-4 w-4" />
                              {t("accounting.close")}
                            </DropdownMenuItem>
                          </>
                        )}
                        {fy.status === "Closed" && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleReopen(fy)}
                              className="text-green-600"
                            >
                              <Unlock className="mr-2 h-4 w-4" />
                              {t("accounting.reopen")}
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Calendar className="mb-4 h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {t("accounting.noFiscalYears")}
            </p>
            <Button variant="link" onClick={handleCreate} className="mt-2">
              {t("accounting.createFirstFiscalYear")}
            </Button>
          </div>
        )}
      </div>

      {/* Pagination */}
      {fiscalYears && fiscalYears.total > fiscalYears.page_size && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {t("accounting.showing", {
              from: (page - 1) * fiscalYears.page_size + 1,
              to: Math.min(page * fiscalYears.page_size, fiscalYears.total),
              total: fiscalYears.total,
            })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
            >
              {t("common.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page * fiscalYears.page_size >= fiscalYears.total}
            >
              {t("common.next")}
            </Button>
          </div>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.createFiscalYear")}</DialogTitle>
            <DialogDescription>
              {t("accounting.createFiscalYearDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="fy-label">{t("accounting.label")} *</Label>
              <Input
                id="fy-label"
                value={formData.label || ""}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                placeholder="e.g., FY2026"
              />
              <p className="text-xs text-muted-foreground">
                {t("accounting.labelFormat")}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("accounting.startDate")} *</Label>
                <DatePicker
                  value={formData.start_date}
                  onChange={(date) => setFormData({ ...formData, start_date: date ?? null })}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("accounting.endDate")} *</Label>
                <DatePicker
                  value={formData.end_date}
                  onChange={(date) => setFormData({ ...formData, end_date: date ?? null })}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="fy-default"
                checked={formData.is_default ?? false}
                onCheckedChange={(v) => setFormData({ ...formData, is_default: v })}
              />
              <Label htmlFor="fy-default">{t("accounting.setAsDefault")}</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSaveCreate} disabled={isWorking}>
              {isCreating && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.editFiscalYear")}</DialogTitle>
            <DialogDescription>
              {selectedFiscalYear?.label}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-fy-label">{t("accounting.label")}</Label>
              <Input
                id="edit-fy-label"
                value={formData.label || ""}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("accounting.startDate")}</Label>
                <DatePicker
                  value={formData.start_date}
                  onChange={(date) => setFormData({ ...formData, start_date: date ?? null })}
                  disabled={selectedFiscalYear?.status !== "Draft"}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("accounting.endDate")}</Label>
                <DatePicker
                  value={formData.end_date}
                  onChange={(date) => setFormData({ ...formData, end_date: date ?? null })}
                  disabled={selectedFiscalYear?.status !== "Draft"}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="edit-fy-default"
                checked={formData.is_default ?? false}
                onCheckedChange={(v) => setFormData({ ...formData, is_default: v })}
              />
              <Label htmlFor="edit-fy-default">{t("accounting.setAsDefault")}</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleSaveEdit} disabled={isWorking}>
              {isUpdating && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close Dialog */}
      <Dialog open={isCloseDialogOpen} onOpenChange={setIsCloseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("accounting.closeFiscalYear")}</DialogTitle>
            <DialogDescription>
              {t("accounting.closeFiscalYearConfirm", { label: selectedFiscalYear?.label })}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              {t("accounting.closeWarning")}
            </p>

            <div className="space-y-2">
              <Label htmlFor="closure-notes">{t("accounting.closureNotes")}</Label>
              <textarea
                id="closure-notes"
                className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={closureNotes}
                onChange={(e) => setClosureNotes(e.target.value)}
                placeholder={t("accounting.closureNotesPlaceholder")}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCloseDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" onClick={handleSaveClose} disabled={isWorking}>
              {isClosing && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              <Lock className="mr-2 h-4 w-4" />
              {t("accounting.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
