import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { InvoiceLineEditor } from "@/domain/invoices/components/InvoiceLineEditor";
import { InvoiceTotalsCard } from "@/domain/invoices/components/InvoiceTotalsCard";
import { CustomerCombobox } from "@/domain/customers/components/CustomerCombobox";
import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { DatePicker } from "../../components/ui/DatePicker";
import {
  parseDatePickerInputValue,
  serializeDatePickerValue,
} from "../../components/ui/date-picker-utils";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import type { CustomerSummary } from "../../domain/customers/types";
import {
  INVOICE_TAX_POLICY_OPTIONS,
  type InvoiceBuyerType,
  type InvoiceCreatePayload,
  type InvoiceDraftLine,
  type InvoiceResponse,
} from "../../domain/invoices/types";
import { useToast } from "../../hooks/useToast";
import { listCustomers } from "../../lib/api/customers";
import { createInvoice } from "../../lib/api/invoices";
import { appTodayISO } from "../../lib/time";
import { INVOICES_ROUTE } from "../../lib/routes";

interface DraftLine extends InvoiceDraftLine {
  id: number;
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function makeDraftLine(id: number): DraftLine {
  return {
    id,
    product_code: "",
    product_id: "",
    description: "",
    quantity: "1",
    unit_price: "0",
    tax_policy_code: "standard",
  };
}

function buildLinePreview(line: InvoiceDraftLine) {
  const quantity = Number(line.quantity);
  const unitPrice = Number(line.unit_price);
  const policy =
    INVOICE_TAX_POLICY_OPTIONS.find((option) => option.code === line.tax_policy_code) ??
    INVOICE_TAX_POLICY_OPTIONS[0];
  const subtotalAmount =
    Number.isFinite(quantity) && Number.isFinite(unitPrice) ? roundMoney(quantity * unitPrice) : 0;
  const taxAmount = roundMoney(subtotalAmount * policy.taxRate);

  return {
    subtotalAmount,
    taxAmount,
    totalAmount: roundMoney(subtotalAmount + taxAmount),
    taxType: policy.taxType,
    taxRate: policy.taxRate,
  };
}

export default function CreateInvoicePage() {
  const { t } = useTranslation("invoice");
const { t: tRoutes } = useTranslation("routes");
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [buyerType, setBuyerType] = useState<InvoiceBuyerType>("b2b");
  const [buyerIdentifier, setBuyerIdentifier] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(appTodayISO);
  const [lines, setLines] = useState<DraftLine[]>([makeDraftLine(1)]);
  const [nextLineId, setNextLineId] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [created, setCreated] = useState<InvoiceResponse | null>(null);

  useEffect(() => {
    let active = true;
    void listCustomers({ status: "active", page_size: 200 }).then((response) => {
      if (active) {
        setCustomers(response.items);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const selectedCustomer = useMemo(
    () => customers.find((customer) => customer.id === customerId) ?? null,
    [customerId, customers],
  );

  useEffect(() => {
    if (buyerType === "b2c") {
      setBuyerIdentifier("");
      return;
    }
    if (selectedCustomer) {
      setBuyerIdentifier(selectedCustomer.normalized_business_number);
    }
  }, [buyerType, selectedCustomer]);

  const linePreviews = useMemo(() => lines.map((line) => buildLinePreview(line)), [lines]);
  const totals = useMemo(() => {
    return linePreviews.reduce(
      (accumulator, preview) => ({
        subtotalAmount: roundMoney(accumulator.subtotalAmount + preview.subtotalAmount),
        taxAmount: roundMoney(accumulator.taxAmount + preview.taxAmount),
        totalAmount: roundMoney(accumulator.totalAmount + preview.totalAmount),
      }),
      { subtotalAmount: 0, taxAmount: 0, totalAmount: 0 },
    );
  }, [linePreviews]);

  const isValid =
    customerId.length > 0 &&
    lines.length > 0 &&
    lines.every((line) => {
      const quantity = Number(line.quantity);
      const unitPrice = Number(line.unit_price);
      return (
        line.description.trim().length > 0 &&
        Number.isFinite(quantity) &&
        quantity > 0 &&
        Number.isFinite(unitPrice) &&
        unitPrice >= 0
      );
    }) &&
    (buyerType === "b2c" || buyerIdentifier.trim().length > 0);

  function updateLine(lineId: number, next: InvoiceDraftLine) {
    setLines((current) =>
      current.map((line) => (line.id === lineId ? { ...line, ...next } : line)),
    );
  }

  function addLine() {
    setLines((current) => [...current, makeDraftLine(nextLineId)]);
    setNextLineId((current) => current + 1);
  }

  function removeLine(lineId: number) {
    setLines((current) => current.filter((line) => line.id !== lineId));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || submitting) {
      return;
    }

    setSubmitting(true);
    setServerErrors([]);
    const payload: InvoiceCreatePayload = {
      customer_id: customerId,
      buyer_type: buyerType,
      buyer_identifier: buyerType === "b2b" ? buyerIdentifier.trim() : null,
      invoice_date: invoiceDate,
      currency_code: "TWD",
      lines: lines.map((line) => ({
        product_id: line.product_id?.trim() || null,
        product_code: line.product_code.trim() || null,
        description: line.description.trim(),
        quantity: line.quantity,
        unit_price: line.unit_price,
        tax_policy_code: line.tax_policy_code,
      })),
    };

    try {
      const result = await createInvoice(payload);
      if (result.ok) {
        showSuccessToast(
          t("createPage.toast.successTitle"),
          t("createPage.toast.successDescription", { invoiceNumber: result.data.invoice_number }),
        );
        setCreated(result.data);
        return;
      }
      setServerErrors(result.errors);
      showErrorToast(
        t("createPage.toast.errorTitle"),
        result.errors[0]?.message ?? t("createPage.toast.errorDescription"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={[
            { label: tRoutes("invoices.label"), href: INVOICES_ROUTE },
            { label: tRoutes("createInvoice.label") },
          ]}
          eyebrow={t("createPage.eyebrow")}
          title={t("createPage.titleCreated")}
          description={t("createPage.descriptionCreated")}
        />
        <SectionCard
          title={t("createPage.createdRecord")}
          description={t("createPage.createdRecordDescription")}
        >
          <div className="space-y-4 text-sm">
            <p>
              <strong>{created.invoice_number}</strong> was issued for {created.currency_code}{" "}
              {created.total_amount}.
            </p>
            <Button
              type="button"
              onClick={() => {
                setCreated(null);
                setCustomerId("");
                setBuyerType("b2b");
                setBuyerIdentifier("");
                setLines([makeDraftLine(1)]);
                setNextLineId(2);
              }}
            >
              {t("createPage.createAnotherInvoice")}
            </Button>
          </div>
        </SectionCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: tRoutes("invoices.label"), href: INVOICES_ROUTE },
          { label: tRoutes("createInvoice.label") },
        ]}
        eyebrow={t("createPage.eyebrow")}
        title={t("createPage.title")}
        description={t("createPage.description")}
      />
      <SectionCard
        title={t("createPage.draftTitle")}
        description={t("createPage.draftDescription")}
      >
        <form onSubmit={handleSubmit} className="grid gap-6">
          {serverErrors.length > 0 ? (
            <SurfaceMessage tone="danger">
              {serverErrors.map((error) => (
                <div key={`${error.field}:${error.message}`}>{error.message}</div>
              ))}
            </SurfaceMessage>
          ) : null}

          <div className="space-y-1.5">
            <label htmlFor="customer-combobox" className="text-sm font-medium">
              {t("createPage.customer")}
            </label>
            <CustomerCombobox
              value={customerId}
              onChange={setCustomerId}
              disabled={submitting}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="space-y-1.5">
              <label htmlFor="buyer-type" className="text-sm font-medium">
                {t("createPage.buyerType")}
              </label>
              <Select
                value={buyerType}
                onValueChange={(v) => setBuyerType(v as InvoiceBuyerType)}
                disabled={submitting}
              >
                <SelectTrigger id="buyer-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="b2b">{t("createPage.b2b")}</SelectItem>
                  <SelectItem value="b2c">{t("createPage.b2c")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="buyer-identifier" className="text-sm font-medium">
                {t("createPage.buyerIdentifier")}
              </label>
              <Input
                id="buyer-identifier"
                type="text"
                value={buyerType === "b2c" ? t("createPage.b2cPlaceholder") : buyerIdentifier}
                onChange={(e) => setBuyerIdentifier(e.target.value)}
                disabled={buyerType === "b2c" || submitting}
                placeholder={buyerType === "b2c" ? t("createPage.b2cPlaceholder") : t("createPage.b2bPlaceholder")}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="invoice-date" className="text-sm font-medium">
                {t("createPage.invoiceDate")}
              </label>
              <DatePicker
                id="invoice-date"
                value={parseDatePickerInputValue(invoiceDate)}
                onChange={(value) => setInvoiceDate(serializeDatePickerValue(value))}
                allowClear={false}
                disabled={submitting}
              />
            </div>
          </div>

          {buyerType === "b2c" ? (
            <SurfaceMessage tone="warning">
              {t("createPage.b2cWarning")}
            </SurfaceMessage>
          ) : null}

          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-base font-semibold tracking-tight">{t("createPage.invoiceLines")}</h3>
              <Button type="button" variant="outline" onClick={addLine}>
                {t("createPage.addLine")}
              </Button>
            </div>
            {lines.map((line, index) => (
              <InvoiceLineEditor
                key={line.id}
                index={index}
                line={line}
                preview={linePreviews[index]}
                currencyCode="TWD"
                canRemove={lines.length > 1}
                onChange={(next) => updateLine(line.id, next)}
                onRemove={() => removeLine(line.id)}
              />
            ))}
          </div>

          <InvoiceTotalsCard
            currencyCode="TWD"
            lineCount={lines.length}
            subtotalAmount={totals.subtotalAmount}
            taxAmount={totals.taxAmount}
            totalAmount={totals.totalAmount}
          />

          {customers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("createPage.noActiveCustomers")}
            </p>
          ) : null}

          <div className="flex gap-3">
            <Button type="submit" disabled={!isValid || submitting || customers.length === 0}>
              {submitting ? t("createPage.creating") : t("createPage.createInvoice")}
            </Button>
          </div>
        </form>
      </SectionCard>
    </div>
  );
}
