import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Plus, Power, Save, Trash2, X } from "lucide-react";

import { SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Checkbox } from "../../components/ui/checkbox";
import { Field, FieldError, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { useOptionalAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import {
  createPaymentTermsTemplate,
  fetchPaymentTermsTemplates,
  updatePaymentTermsTemplate,
  type PaymentTermsTemplate,
  type PaymentTermsTemplateCreate,
  type PaymentTermsTemplateDetailPayload,
} from "../../lib/api/paymentTerms";

let detailKeyCounter = 0;

function createDetailKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  detailKeyCounter += 1;
  return `terms-detail-${detailKeyCounter}`;
}

interface DetailFormState {
  key: string;
  invoicePortion: string;
  creditDays: string;
  creditMonths: string;
  discountPercent: string;
  discountValidityDays: string;
  modeOfPayment: string;
  description: string;
}

interface TemplateFormState {
  templateName: string;
  description: string;
  legacyCode: string;
  allocateBasedOnTerms: boolean;
  isActive: boolean;
  details: DetailFormState[];
}

function newDetail(): DetailFormState {
  return {
    key: createDetailKey(),
    invoicePortion: "100.00",
    creditDays: "30",
    creditMonths: "0",
    discountPercent: "",
    discountValidityDays: "",
    modeOfPayment: "",
    description: "",
  };
}

const EMPTY_TEMPLATE_FORM: TemplateFormState = {
  templateName: "",
  description: "",
  legacyCode: "",
  allocateBasedOnTerms: true,
  isActive: true,
  details: [newDetail()],
};

function cloneEmptyForm(): TemplateFormState {
  return { ...EMPTY_TEMPLATE_FORM, details: [newDetail()] };
}

function toFormState(template: PaymentTermsTemplate): TemplateFormState {
  return {
    templateName: template.template_name,
    description: template.description ?? "",
    legacyCode: template.legacy_code ?? "",
    allocateBasedOnTerms: template.allocate_payment_based_on_payment_terms,
    isActive: template.is_active,
    details: template.details.length > 0
      ? template.details
        .slice()
        .sort((left, right) => left.row_number - right.row_number)
        .map((detail) => ({
          key: detail.id,
          invoicePortion: detail.invoice_portion,
          creditDays: String(detail.credit_days),
          creditMonths: String(detail.credit_months),
          discountPercent: detail.discount_percent ?? "",
          discountValidityDays: detail.discount_validity_days == null ? "" : String(detail.discount_validity_days),
          modeOfPayment: detail.mode_of_payment ?? "",
          description: detail.description ?? "",
        }))
      : [newDetail()],
  };
}

function parseOptionalInteger(value: string, fieldName: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`${fieldName} must be a whole number greater than or equal to zero.`);
  }
  return parsed;
}

function parseTermsDetails(details: DetailFormState[]): PaymentTermsTemplateDetailPayload[] {
  if (details.length === 0) {
    throw new Error("Add at least one payment term row.");
  }

  let totalPortion = 0;
  const payload = details.map((detail, index) => {
    const invoicePortion = Number(detail.invoicePortion);
    if (!Number.isFinite(invoicePortion) || invoicePortion <= 0) {
      throw new Error("Invoice portion must be greater than zero for every row.");
    }
    totalPortion += invoicePortion;

    const creditDays = parseOptionalInteger(detail.creditDays, "Credit days") ?? 0;
    const creditMonths = parseOptionalInteger(detail.creditMonths, "Credit months") ?? 0;
    const discountValidityDays = parseOptionalInteger(detail.discountValidityDays, "Discount validity days");
    const discountPercent = detail.discountPercent.trim();
    const parsedDiscountPercent = discountPercent ? Number(discountPercent) : null;
    if (parsedDiscountPercent != null && (!Number.isFinite(parsedDiscountPercent) || parsedDiscountPercent < 0)) {
      throw new Error("Discount percent must be a valid number greater than or equal to zero.");
    }

    return {
      row_number: index + 1,
      invoice_portion: invoicePortion.toFixed(2),
      credit_days: creditDays,
      credit_months: creditMonths,
      discount_percent: discountPercent || null,
      discount_validity_days: discountValidityDays,
      mode_of_payment: detail.modeOfPayment.trim() || null,
      description: detail.description.trim() || null,
    };
  });

  if (Math.abs(totalPortion - 100) > 0.01) {
    throw new Error("Invoice portions must add up to 100%.");
  }

  return payload;
}

function buildPayload(form: TemplateFormState): PaymentTermsTemplateCreate {
  const templateName = form.templateName.trim();
  if (!templateName) {
    throw new Error("Template name is required.");
  }

  return {
    template_name: templateName,
    description: form.description.trim() || null,
    legacy_code: form.legacyCode.trim() || null,
    allocate_payment_based_on_payment_terms: form.allocateBasedOnTerms,
    details: parseTermsDetails(form.details),
  };
}

function summarizeDetails(template: PaymentTermsTemplate): string {
  if (template.details.length === 0) {
    return "No schedule rows";
  }
  return template.details
    .slice()
    .sort((left, right) => left.row_number - right.row_number)
    .map((detail) => `${detail.invoice_portion}% / ${detail.credit_days}d`)
    .join(", ");
}

export function PaymentTermsPanel() {
  const { t } = useTranslation("settings");
  const auth = useOptionalAuth();
  const { success: showSuccessToast, error: showErrorToast } = useToast();
  const canEdit = auth?.user ? ["owner", "admin", "finance"].includes(auth.user.role) : true;

  const [templates, setTemplates] = useState<PaymentTermsTemplate[]>([]);
  const [form, setForm] = useState<TemplateFormState>(cloneEmptyForm);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const editingTemplate = useMemo(
    () => templates.find((template) => template.id === editingTemplateId) ?? null,
    [editingTemplateId, templates],
  );

  async function refresh() {
    setLoading(true);
    setLoadError(null);
    const result = await fetchPaymentTermsTemplates({ includeInactive: true });
    if (result.ok) {
      setTemplates(result.data.items);
    } else {
      setLoadError(result.error);
    }
    setLoading(false);
  }

  useEffect(() => {
    void refresh();
  }, []);

  function resetForm() {
    setEditingTemplateId(null);
    setForm(cloneEmptyForm());
    setFormError(null);
  }

  function updateDetail(key: string, patch: Partial<DetailFormState>) {
    setForm((current) => ({
      ...current,
      details: current.details.map((detail) => detail.key === key ? { ...detail, ...patch } : detail),
    }));
  }

  function removeDetail(key: string) {
    setForm((current) => ({
      ...current,
      details: current.details.length === 1
        ? current.details
        : current.details.filter((detail) => detail.key !== key),
    }));
  }

  async function handleSubmit() {
    setFormError(null);
    let payload: PaymentTermsTemplateCreate;
    try {
      payload = buildPayload(form);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Review the payment terms details.");
      return;
    }

    const saveKey = editingTemplateId ? `edit:${editingTemplateId}` : "new-template";
    setSavingKey(saveKey);
    const result = editingTemplateId
      ? await updatePaymentTermsTemplate(editingTemplateId, { ...payload, is_active: form.isActive })
      : await createPaymentTermsTemplate(payload);
    setSavingKey(null);

    if (!result.ok) {
      setFormError(result.error);
      showErrorToast("Payment terms save failed", result.error);
      return;
    }

    showSuccessToast(
      editingTemplateId ? "Payment terms updated" : "Payment terms created",
      `${result.data.template_name} is available for commercial defaults.`,
    );
    resetForm();
    await refresh();
  }

  async function handleToggleActive(template: PaymentTermsTemplate) {
    setSavingKey(`toggle:${template.id}`);
    const result = await updatePaymentTermsTemplate(template.id, { is_active: !template.is_active });
    setSavingKey(null);
    if (!result.ok) {
      showErrorToast("Payment terms update failed", result.error);
      return;
    }
    await refresh();
  }

  function handleEdit(template: PaymentTermsTemplate) {
    setEditingTemplateId(template.id);
    setForm(toFormState(template));
    setFormError(null);
  }

  if (loading) {
    return (
      <SectionCard
        title={t("paymentTerms.title", { defaultValue: "Payment Terms Templates" })}
        description={t("paymentTerms.description", {
          defaultValue: "Build reusable payment schedules for customers, suppliers, orders, and invoices.",
        })}
      >
        <p className="text-sm text-muted-foreground">Loading payment terms...</p>
      </SectionCard>
    );
  }

  return (
    <div className="space-y-6">
      {!canEdit ? (
        <SurfaceMessage tone="warning">
          Your role can view payment terms templates but cannot edit them.
        </SurfaceMessage>
      ) : null}
      {loadError ? <SurfaceMessage tone="danger">{loadError}</SurfaceMessage> : null}

      <SectionCard
        title={t("paymentTerms.title", { defaultValue: "Payment Terms Templates" })}
        description={t("paymentTerms.description", {
          defaultValue: "Build reusable payment schedules for customers, suppliers, orders, and invoices.",
        })}
        actions={<span className="text-sm text-muted-foreground">{templates.length} templates</span>}
      >
        <div className="space-y-5">
          <div className="grid gap-4 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_160px]">
            <Field>
              <FieldLabel htmlFor="payment-terms-name">Template name</FieldLabel>
              <Input
                id="payment-terms-name"
                value={form.templateName}
                onChange={(event) => setForm((current) => ({ ...current, templateName: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="payment-terms-legacy-code">Legacy code</FieldLabel>
              <Input
                id="payment-terms-legacy-code"
                value={form.legacyCode}
                onChange={(event) => setForm((current) => ({ ...current, legacyCode: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <div className="flex flex-col justify-end gap-3">
              <label className="flex items-center gap-2 text-sm text-foreground">
                <Checkbox
                  checked={form.allocateBasedOnTerms}
                  onCheckedChange={(checked) => setForm((current) => ({ ...current, allocateBasedOnTerms: Boolean(checked) }))}
                  disabled={!canEdit}
                  aria-label="Allocate by payment terms"
                />
                Allocate schedule
              </label>
              <label className="flex items-center gap-2 text-sm text-foreground">
                <Checkbox
                  checked={form.isActive}
                  onCheckedChange={(checked) => setForm((current) => ({ ...current, isActive: Boolean(checked) }))}
                  disabled={!canEdit || !editingTemplateId}
                  aria-label="Payment terms active"
                />
                Active
              </label>
            </div>
            <Field className="lg:col-span-3">
              <FieldLabel htmlFor="payment-terms-description">Description</FieldLabel>
              <Textarea
                id="payment-terms-description"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                disabled={!canEdit}
                rows={2}
              />
            </Field>
          </div>

          <div className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold">Schedule rows</h3>
                <p className="text-xs text-muted-foreground">Invoice portions must total 100%.</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setForm((current) => ({ ...current, details: [...current.details, newDetail()] }))}
                disabled={!canEdit}
              >
                <Plus className="mr-2 size-4" />
                Add row
              </Button>
            </div>

            <div className="space-y-3">
              {form.details.map((detail, index) => (
                <div key={detail.key} className="grid gap-3 rounded-xl border border-border/70 p-3 md:grid-cols-[70px_100px_100px_100px_100px_100px_minmax(0,1fr)_auto] md:items-end">
                  <div className="text-xs font-semibold uppercase text-muted-foreground">#{index + 1}</div>
                  <Field>
                    <FieldLabel htmlFor={`portion-${detail.key}`}>Portion %</FieldLabel>
                    <Input
                      id={`portion-${detail.key}`}
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={detail.invoicePortion}
                      onChange={(event) => updateDetail(detail.key, { invoicePortion: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`days-${detail.key}`}>Days</FieldLabel>
                    <Input
                      id={`days-${detail.key}`}
                      type="number"
                      min="0"
                      value={detail.creditDays}
                      onChange={(event) => updateDetail(detail.key, { creditDays: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`months-${detail.key}`}>Months</FieldLabel>
                    <Input
                      id={`months-${detail.key}`}
                      type="number"
                      min="0"
                      value={detail.creditMonths}
                      onChange={(event) => updateDetail(detail.key, { creditMonths: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`discount-${detail.key}`}>Discount %</FieldLabel>
                    <Input
                      id={`discount-${detail.key}`}
                      type="number"
                      min="0"
                      step="0.01"
                      value={detail.discountPercent}
                      onChange={(event) => updateDetail(detail.key, { discountPercent: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`discount-days-${detail.key}`}>Discount days</FieldLabel>
                    <Input
                      id={`discount-days-${detail.key}`}
                      type="number"
                      min="0"
                      value={detail.discountValidityDays}
                      onChange={(event) => updateDetail(detail.key, { discountValidityDays: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`mode-${detail.key}`}>Payment mode</FieldLabel>
                    <Input
                      id={`mode-${detail.key}`}
                      value={detail.modeOfPayment}
                      onChange={(event) => updateDetail(detail.key, { modeOfPayment: event.target.value })}
                      disabled={!canEdit}
                    />
                  </Field>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeDetail(detail.key)}
                    disabled={!canEdit || form.details.length === 1}
                    aria-label="Remove payment terms row"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {formError ? <FieldError>{formError}</FieldError> : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={!canEdit || savingKey === "new-template" || (editingTemplateId ? savingKey === `edit:${editingTemplateId}` : false)}
            >
              <Save className="mr-2 size-4" />
              {savingKey ? "Saving..." : editingTemplate ? "Save template" : "Create template"}
            </Button>
            {editingTemplate ? (
              <Button type="button" variant="outline" onClick={resetForm} disabled={!canEdit}>
                <X className="mr-2 size-4" />
                Cancel edit
              </Button>
            ) : null}
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Template Directory"
        description="Review active and inactive payment terms templates."
      >
        {templates.length === 0 ? (
          <SurfaceMessage tone="default">No payment terms templates have been created.</SurfaceMessage>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Legacy code</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.map((template) => (
                <TableRow key={template.id}>
                  <TableCell>
                    <div className="font-medium">{template.template_name}</div>
                    {template.description ? <div className="text-xs text-muted-foreground">{template.description}</div> : null}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{summarizeDetails(template)}</TableCell>
                  <TableCell>
                    <Badge variant={template.is_active ? "success" : "outline"} className="normal-case tracking-normal">
                      {template.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell>{template.legacy_code ?? "-"}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" size="sm" onClick={() => handleEdit(template)} disabled={!canEdit}>
                        <Pencil className="mr-2 size-4" />
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => void handleToggleActive(template)}
                        disabled={!canEdit || savingKey === `toggle:${template.id}`}
                      >
                        <Power className="mr-2 size-4" />
                        {template.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>
    </div>
  );
}

export default PaymentTermsPanel;