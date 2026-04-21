/** Invoice detail with payment summary section. */

import { startTransition, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { SectionCard } from "../../../components/layout/PageLayout";
import { Breadcrumb } from "../../../components/ui/Breadcrumb";
import { Button } from "../../../components/ui/button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  paymentStatusLabel,
  useInvoice,
} from "../hooks/useInvoices";
import { getCustomer } from "../../../lib/api/customers";
import { rememberTrackedEguiInvoice } from "../../../lib/desktop/eguiMonitor";
import {
  buildInvoicePrintPreviewContext,
  clearInvoicePrintPreviewMeasurement,
  finishInvoicePrintPreviewMeasurement,
  loadInvoicePrintPreviewModal,
  prefetchInvoicePrintPreviewModal,
  startInvoicePrintPreviewMeasurement,
  validatePrintReady,
  type InvoicePrintPreviewContext,
  type InvoicePrintPreviewMeasurement,
} from "../../../lib/print/invoices";
import { INVOICES_ROUTE } from "../../../lib/routes";
import PaymentHistory from "../../payments/components/PaymentHistory";

type InvoicePrintPreviewModalComponent = Awaited<ReturnType<typeof loadInvoicePrintPreviewModal>>["default"];

interface InvoiceDetailProps {
  invoiceId: string;
  onBack: () => void;
}

export function InvoiceDetail({ invoiceId, onBack }: InvoiceDetailProps) {
  const navigate = useNavigate();
  const { t } = useTranslation("common");
  const {
    invoice,
    loading,
    error,
    eguiError,
    refreshEgui,
    refreshingEgui,
  } = useInvoice(invoiceId);
  const [printPreviewOpen, setPrintPreviewOpen] = useState(false);
  const [printPreviewLoading, setPrintPreviewLoading] = useState(false);
  const [printPreviewError, setPrintPreviewError] = useState<string | null>(null);
  const [printPreviewContext, setPrintPreviewContext] = useState<InvoicePrintPreviewContext | null>(null);
  const [printPreviewAttempt, setPrintPreviewAttempt] = useState(0);
  const [pendingPrintPreviewOpen, setPendingPrintPreviewOpen] = useState(false);
  const [PrintPreviewModalComponent, setPrintPreviewModalComponent] = useState<InvoicePrintPreviewModalComponent | null>(null);
  const previewMeasurementRef = useRef<InvoicePrintPreviewMeasurement | null>(null);
  const previewInvoiceIdRef = useRef<string | null>(null);

  const egui = invoice?.egui_submission;

  useEffect(() => {
    if (!invoice || !egui) {
      return;
    }

    rememberTrackedEguiInvoice(invoice);
  }, [egui, invoice]);

  useEffect(() => {
    if (!invoice) {
      previewInvoiceIdRef.current = null;
      setPrintPreviewOpen(false);
      setPrintPreviewLoading(false);
      setPrintPreviewError(null);
      setPrintPreviewContext(null);
      setPendingPrintPreviewOpen(false);
      setPrintPreviewModalComponent(null);
      clearInvoicePrintPreviewMeasurement(previewMeasurementRef.current);
      previewMeasurementRef.current = null;
      return;
    }

    let active = true;

    if (previewInvoiceIdRef.current !== invoice.id) {
      previewInvoiceIdRef.current = invoice.id;
      setPendingPrintPreviewOpen(false);
      clearInvoicePrintPreviewMeasurement(previewMeasurementRef.current);
      previewMeasurementRef.current = null;
    }

    setPrintPreviewOpen(false);
    setPrintPreviewLoading(true);
    setPrintPreviewError(null);
    setPrintPreviewContext(null);
    void loadInvoicePrintPreviewModal()
      .then((module) => {
        if (!active) {
          return;
        }

        setPrintPreviewModalComponent(() => module.default);
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setPrintPreviewModalComponent(null);
        setPrintPreviewError("Unable to load print preview.");
      });

    void (async () => {
      try {
        const customer = await getCustomer(invoice.customer_id);
        if (!active) {
          return;
        }

        if (!customer) {
          setPrintPreviewError((current) => current ?? "Unable to prepare print preview.");
          return;
        }

        setPrintPreviewContext(buildInvoicePrintPreviewContext(customer));
      } catch {
        if (!active) {
          return;
        }

        setPrintPreviewError((current) => current ?? "Unable to prepare print preview.");
      } finally {
        if (active) {
          setPrintPreviewLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [invoice?.customer_id, invoice?.id, printPreviewAttempt]);

  useEffect(() => {
    if (!pendingPrintPreviewOpen || !PrintPreviewModalComponent || !printPreviewContext) {
      return;
    }

    setPendingPrintPreviewOpen(false);
    startTransition(() => {
      setPrintPreviewOpen(true);
    });
  }, [PrintPreviewModalComponent, pendingPrintPreviewOpen, printPreviewContext]);

  useEffect(() => {
    if (!printPreviewError) {
      return;
    }

    setPendingPrintPreviewOpen(false);
    clearInvoicePrintPreviewMeasurement(previewMeasurementRef.current);
    previewMeasurementRef.current = null;
  }, [printPreviewError]);

  if (loading) return <p>Loading invoice…</p>;
  if (error) return <p className="text-sm text-destructive">Error: {error}</p>;
  if (!invoice) return <p>Invoice not found.</p>;

  const ps = invoice.payment_status;
  const printPreviewValidationError = validatePrintReady(invoice);
  const previewPreparationPending = !printPreviewError
    && (!PrintPreviewModalComponent || !printPreviewContext || printPreviewLoading);
  const printPreviewDisabledReason = printPreviewValidationError
    ?? (previewPreparationPending ? "Preparing print preview…" : null);
  const printPreviewButtonLabel = printPreviewError
    ? "Retry Preview"
    : (previewPreparationPending ? "Preparing Preview…" : "Print Preview");

  const formatOperationalTimestamp = (value: string | null | undefined): string => {
    if (!value) {
      return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString();
  };

  const handleOpenPrintPreview = () => {
    if (printPreviewValidationError || printPreviewOpen || previewMeasurementRef.current) {
      return;
    }

    previewMeasurementRef.current = startInvoicePrintPreviewMeasurement({
      invoiceId: invoice.id,
      lineCount: invoice.lines.length,
    });

    if (PrintPreviewModalComponent && printPreviewContext && !printPreviewLoading && !printPreviewError) {
      startTransition(() => {
        setPrintPreviewOpen(true);
      });
      return;
    }

    setPendingPrintPreviewOpen(true);
    if (printPreviewError) {
      setPrintPreviewAttempt((attempt) => attempt + 1);
      return;
    }

    startTransition(() => {
      setPrintPreviewOpen(true);
    });
  };

  const handleClosePrintPreview = () => {
    clearInvoicePrintPreviewMeasurement(previewMeasurementRef.current);
    previewMeasurementRef.current = null;
    setPrintPreviewOpen(false);
  };

  const handlePrintPreviewReady = () => {
    finishInvoicePrintPreviewMeasurement(previewMeasurementRef.current);
    previewMeasurementRef.current = null;
  };

  return (
    <section aria-label="Invoice detail" className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <Breadcrumb
            items={[
              { label: t("routes.invoices.label"), href: INVOICES_ROUTE },
              { label: invoice.invoice_number },
            ]}
          />
          <Button type="button" variant="outline" onClick={onBack}>
            Back
          </Button>
          <h2>Invoice {invoice.invoice_number}</h2>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <Button
            type="button"
            onClick={handleOpenPrintPreview}
            onFocus={() => {
              prefetchInvoicePrintPreviewModal();
            }}
            onMouseEnter={() => {
              prefetchInvoicePrintPreviewModal();
            }}
            disabled={Boolean(printPreviewDisabledReason)}
            title={printPreviewDisabledReason ?? printPreviewError ?? "Open invoice print preview"}
          >
            {printPreviewButtonLabel}
          </Button>
          {printPreviewError ? (
            <p data-testid="print-preview-error" className="text-sm text-destructive">
              {printPreviewError}
            </p>
          ) : null}
        </div>
      </div>

      <SectionCard title="Invoice Summary" description="Commercial totals and issuance metadata for this invoice.">
        <dl className="gap-y-4">
          <dt>Date</dt>
          <dd>{invoice.invoice_date}</dd>
          <dt>Status</dt>
          <dd>{invoice.status}</dd>
          <dt>Currency</dt>
          <dd>{invoice.currency_code}</dd>
          <dt>Subtotal</dt>
          <dd>{invoice.currency_code} {invoice.subtotal_amount}</dd>
          <dt>Tax</dt>
          <dd>{invoice.currency_code} {invoice.tax_amount}</dd>
          <dt>Total</dt>
          <dd>{invoice.currency_code} {invoice.total_amount}</dd>
        </dl>
      </SectionCard>

      {invoice.order_id ? (
        <SectionCard title="Linked Order" description="The sales order this invoice was issued against.">
          <div className="flex items-center justify-between">
            <dl className="gap-y-4">
              <dt>Order ID</dt>
              <dd className="font-mono text-sm">{invoice.order_id}</dd>
            </dl>
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(`/orders/${invoice.order_id}`)}
            >
              View Order
            </Button>
          </div>
        </SectionCard>
      ) : null}

      {egui ? (
        <SectionCard title="eGUI Status" description="Submission window, sync timestamps, and retry information for eGUI tracking.">
          <div data-testid="egui-status" className="space-y-4">
            <dl className="gap-y-4">
              <dt>Status</dt>
              <dd>
                <StatusBadge status={egui.status} label={egui.status} />
              </dd>
              <dt>Submission Window</dt>
              <dd>{egui.deadline_label}</dd>
              <dt>Deadline</dt>
              <dd>{formatOperationalTimestamp(egui.deadline_at)}</dd>
              <dt>Last Synced</dt>
              <dd>{formatOperationalTimestamp(egui.last_synced_at)}</dd>
              {egui.last_error_message ? (
                <>
                  <dt>Last Error</dt>
                  <dd className="text-destructive">{egui.last_error_message}</dd>
                </>
              ) : null}
            </dl>
            <div className="flex flex-col items-start gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void refreshEgui();
                }}
                disabled={refreshingEgui}
              >
                {refreshingEgui ? "Refreshing…" : "Refresh eGUI status"}
              </Button>
              {eguiError ? (
                <p data-testid="egui-refresh-error" className="text-sm text-destructive">
                  {eguiError}
                </p>
              ) : null}
            </div>
          </div>
        </SectionCard>
      ) : null}

      {ps ? (
        <SectionCard title="Payment Summary" description="Current payment posture, due date, and collections status for this invoice.">
          <div data-testid="payment-summary">
            <dl className="gap-y-4">
              <dt>Total Amount</dt>
              <dd>{invoice.currency_code} {invoice.total_amount}</dd>
              <dt>Amount Paid</dt>
              <dd>{invoice.currency_code} {invoice.amount_paid}</dd>
              <dt>Outstanding</dt>
              <dd>{invoice.currency_code} {invoice.outstanding_balance}</dd>
              <dt>Payment Status</dt>
              <dd>
                <StatusBadge status={ps} label={paymentStatusLabel(ps)} />
              </dd>
              {invoice.due_date ? (
                <>
                  <dt>Due Date</dt>
                  <dd>{invoice.due_date}</dd>
                </>
              ) : null}
              {invoice.days_overdue != null && invoice.days_overdue > 0 ? (
                <>
                  <dt>Days Overdue</dt>
                  <dd className="font-semibold text-destructive">{invoice.days_overdue}</dd>
                </>
              ) : null}
            </dl>
          </div>
        </SectionCard>
      ) : null}

			<PaymentHistory invoiceId={invoiceId} />

      {printPreviewOpen && printPreviewContext && PrintPreviewModalComponent && (
          <PrintPreviewModalComponent
            invoice={invoice}
            customer={printPreviewContext.customer}
            seller={printPreviewContext.seller}
            onClose={handleClosePrintPreview}
            onPreviewReady={handlePrintPreviewReady}
          />
      )}
    </section>
  );
}
