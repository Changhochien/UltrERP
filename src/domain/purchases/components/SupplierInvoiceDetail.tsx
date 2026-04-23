/** Supplier Invoice Detail Component with Procurement Lineage (Story 24-4).

Displays supplier invoice details with procurement lineage trace and
mismatch indicators for three-way-match readiness.

Note: This is a readiness component - no AP posting workflow is implemented.
*/

import { useEffect, useState } from "react";
import { fetchSupplierInvoiceWithLineage } from "../../../lib/api/purchases";
import type { SupplierInvoiceWithLineage, SupplierInvoiceLineWithLineage } from "../types";
import { LineageTrace, MismatchStatusBadge } from "./LineageTrace";

interface SupplierInvoiceDetailProps {
  invoiceId: string;
  onBack?: () => void;
}

export function SupplierInvoiceDetail({ invoiceId, onBack }: SupplierInvoiceDetailProps) {
  const [invoice, setInvoice] = useState<SupplierInvoiceWithLineage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInvoice() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchSupplierInvoiceWithLineage(invoiceId);
        setInvoice(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load invoice");
      } finally {
        setLoading(false);
      }
    }
    loadInvoice();
  }, [invoiceId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading invoice...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded">
        {error}
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="p-4 bg-gray-50 text-gray-700 rounded">
        Invoice not found
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          {onBack && (
            <button
              onClick={onBack}
              className="text-sm text-blue-600 hover:text-blue-800 mb-2"
            >
              ← Back to list
            </button>
          )}
          <h2 className="text-xl font-semibold">{invoice.invoice_number}</h2>
          <p className="text-gray-500">
            {invoice.supplier_name} • {invoice.invoice_date}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold">
            {invoice.currency_code} {invoice.total_amount}
          </div>
          <StatusBadge status={invoice.status} />
        </div>
      </div>

      {/* PO Linkage (if available) */}
      {invoice.purchase_order_id && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
          <div className="text-sm text-indigo-700 font-medium mb-1">
            Linked Purchase Order
          </div>
          <a
            href={`/procurement/purchase-orders/${invoice.purchase_order_id}`}
            className="text-indigo-600 hover:text-indigo-800 hover:underline"
          >
            {invoice.purchase_order_id}
          </a>
        </div>
      )}

      {/* Lines with Lineage */}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">#</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Item</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Qty</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Unit Price</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">Total</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Mismatch</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Lineage</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {invoice.lines.map((line) => (
              <InvoiceLineRow key={line.id} line={line} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="flex justify-end">
        <div className="w-64 space-y-2">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>{invoice.currency_code} {invoice.subtotal_amount}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Tax</span>
            <span>{invoice.currency_code} {invoice.tax_amount}</span>
          </div>
          <div className="flex justify-between font-semibold text-lg border-t pt-2">
            <span>Total</span>
            <span>{invoice.currency_code} {invoice.total_amount}</span>
          </div>
        </div>
      </div>

      {/* Readiness Notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div className="font-medium text-amber-800">Three-Way-Match Readiness</div>
            <div className="text-sm text-amber-700 mt-1">
              Mismatch indicators shown here are readiness signals for later invoice controls.
              No AP posting workflow or final three-way-match approval gate is implemented in this release.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface InvoiceLineRowProps {
  line: SupplierInvoiceLineWithLineage;
}

function InvoiceLineRow({ line }: InvoiceLineRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className="hover:bg-gray-50">
        <td className="px-4 py-3 text-sm text-gray-600">{line.line_number}</td>
        <td className="px-4 py-3">
          <div className="font-medium">{line.product_name || line.product_code_snapshot || "—"}</div>
          <div className="text-sm text-gray-500">{line.description}</div>
        </td>
        <td className="px-4 py-3 text-right text-sm">{line.quantity}</td>
        <td className="px-4 py-3 text-right text-sm">{line.unit_price}</td>
        <td className="px-4 py-3 text-right text-sm font-medium">{line.total_amount}</td>
        <td className="px-4 py-3">
          <MismatchStatusBadge status={line.mismatch_status} />
        </td>
        <td className="px-4 py-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {expanded ? "Hide" : "Show"} Trace
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={7} className="px-4 py-3 bg-gray-50">
            <LineageTrace
              lineage={line.lineage}
              mismatchSummary={line.mismatch_summary}
              compact={false}
            />
          </td>
        </tr>
      )}
    </>
  );
}

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
    open: { label: "Open", bg: "bg-blue-50", text: "text-blue-700" },
    paid: { label: "Paid", bg: "bg-green-50", text: "text-green-700" },
    voided: { label: "Voided", bg: "bg-gray-50", text: "text-gray-700" },
  };

  const config = statusConfig[status] || statusConfig.open;

  return (
    <span className={`inline-block px-2 py-1 ${config.bg} ${config.text} rounded text-sm font-medium mt-1`}>
      {config.label}
    </span>
  );
}
