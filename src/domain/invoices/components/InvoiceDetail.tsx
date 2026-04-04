/** Invoice detail with payment summary section. */

import { useEffect } from "react";

import {
  eguiStatusColor,
  paymentStatusColor,
  paymentStatusLabel,
  useInvoice,
} from "../hooks/useInvoices";
import { rememberTrackedEguiInvoice } from "../../../lib/desktop/eguiMonitor";
import PaymentHistory from "../../payments/components/PaymentHistory";

interface InvoiceDetailProps {
  invoiceId: string;
  onBack: () => void;
}

export function InvoiceDetail({ invoiceId, onBack }: InvoiceDetailProps) {
  const {
    invoice,
    loading,
    error,
    eguiError,
    refreshEgui,
    refreshingEgui,
  } = useInvoice(invoiceId);

  const egui = invoice?.egui_submission;

  useEffect(() => {
    if (!invoice || !egui) {
      return;
    }

    rememberTrackedEguiInvoice(invoice);
  }, [egui, invoice]);

  if (loading) return <p>Loading invoice…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
  if (!invoice) return <p>Invoice not found.</p>;

  const ps = invoice.payment_status;

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

  return (
    <section aria-label="Invoice detail">
      <button type="button" onClick={onBack} style={{ marginBottom: 12 }}>
        ← Back
      </button>
      <h2>Invoice {invoice.invoice_number}</h2>

      <dl>
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

      {egui && (
        <div
          data-testid="egui-status"
          style={{
            marginTop: 16,
            padding: 12,
            border: "1px solid #dbeafe",
            borderRadius: 8,
            background: "#f8fbff",
          }}
        >
          <h3>eGUI Status</h3>
          <dl>
            <dt>Status</dt>
            <dd>
              <span
                style={{
                  color: eguiStatusColor(egui.status),
                  fontWeight: 700,
                }}
              >
                {egui.status}
              </span>
            </dd>
            <dt>Submission Window</dt>
            <dd>{egui.deadline_label}</dd>
            <dt>Deadline</dt>
            <dd>{formatOperationalTimestamp(egui.deadline_at)}</dd>
            <dt>Last Synced</dt>
            <dd>{formatOperationalTimestamp(egui.last_synced_at)}</dd>
            {egui.last_error_message && (
              <>
                <dt>Last Error</dt>
                <dd style={{ color: "#b91c1c" }}>{egui.last_error_message}</dd>
              </>
            )}
          </dl>
          <button
            type="button"
            onClick={() => {
              void refreshEgui();
            }}
            disabled={refreshingEgui}
            style={{ marginTop: 12 }}
          >
            {refreshingEgui ? "Refreshing…" : "Refresh eGUI status"}
          </button>
          {eguiError && (
            <p data-testid="egui-refresh-error" style={{ color: "#b91c1c", marginTop: 8 }}>
              {eguiError}
            </p>
          )}
        </div>
      )}

      {/* Payment Summary */}
      {ps && (
        <div
          data-testid="payment-summary"
          style={{
            marginTop: 16,
            padding: 12,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
          }}
        >
          <h3>Payment Summary</h3>
          <dl>
            <dt>Total Amount</dt>
            <dd>{invoice.currency_code} {invoice.total_amount}</dd>
            <dt>Amount Paid</dt>
            <dd>{invoice.currency_code} {invoice.amount_paid}</dd>
            <dt>Outstanding</dt>
            <dd>{invoice.currency_code} {invoice.outstanding_balance}</dd>
            <dt>Payment Status</dt>
            <dd>
              <span
                style={{
                  color: paymentStatusColor(ps),
                  fontWeight: 600,
                }}
              >
                {paymentStatusLabel(ps)}
              </span>
            </dd>
            {invoice.due_date && (
              <>
                <dt>Due Date</dt>
                <dd>{invoice.due_date}</dd>
              </>
            )}
            {invoice.days_overdue != null && invoice.days_overdue > 0 && (
              <>
                <dt>Days Overdue</dt>
                <dd style={{ color: "#dc2626", fontWeight: 600 }}>
                  {invoice.days_overdue}
                </dd>
              </>
            )}
          </dl>
        </div>
      )}

      <PaymentHistory invoiceId={invoiceId} />
    </section>
  );
}
