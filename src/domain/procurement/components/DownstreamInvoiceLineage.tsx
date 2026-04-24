/** Downstream Invoice Lineage Component (Story 24-4).

Shows supplier invoices linked to procurement documents (PO, GR).
Used by procurement detail views to see downstream invoice references.

Note: This is a readiness component - no AP posting workflow is implemented.
*/

import { useEffect, useState } from "react";
import { fetchPOLineage, fetchGRLineage, POLineageResponse, GRLineageResponse } from "../../../lib/api/procurement";

interface DownstreamInvoiceLineageProps {
  type: "purchase_order" | "goods_receipt_line";
  documentId: string;
  lineId?: string; // Required for goods_receipt_line type
  onInvoiceClick?: (invoiceId: string) => void;
}

interface LinkedInvoice {
  invoice_id: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: string;
  status: string;
  linked_lines: number;
}

export function DownstreamInvoiceLineage({
  type,
  documentId,
  lineId,
  onInvoiceClick,
}: DownstreamInvoiceLineageProps) {
  const [data, setData] = useState<POLineageResponse | GRLineageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadLineage() {
      try {
        setLoading(true);
        setError(null);

        if (type === "purchase_order") {
          const result = await fetchPOLineage(documentId);
          setData(result);
        } else if (type === "goods_receipt_line" && lineId) {
          const result = await fetchGRLineage(documentId, lineId);
          setData(result);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load lineage");
      } finally {
        setLoading(false);
      }
    }

    loadLineage();
  }, [type, documentId, lineId]);

  if (loading) {
    return (
      <div className="p-4 text-gray-500 text-sm">Loading downstream invoices...</div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-600 text-sm">{error}</div>
    );
  }

  const linkedInvoices: LinkedInvoice[] = data?.linked_invoices || [];

  if (linkedInvoices.length === 0) {
    return (
      <div className="p-4 text-gray-500 text-sm italic">
        No supplier invoices linked to this document yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-700">
        Linked Supplier Invoices ({linkedInvoices.length})
      </div>

      <div className="space-y-1">
        {linkedInvoices.map((inv) => (
          <LinkedInvoiceRow
            key={inv.invoice_id}
            invoice={inv}
            onClick={() => onInvoiceClick?.(inv.invoice_id)}
          />
        ))}
      </div>
    </div>
  );
}

interface LinkedInvoiceRowProps {
  invoice: LinkedInvoice;
  onClick?: () => void;
}

function LinkedInvoiceRow({ invoice, onClick }: LinkedInvoiceRowProps) {
  const statusConfig: Record<string, { bg: string; text: string }> = {
    open: { bg: "bg-blue-50", text: "text-blue-700" },
    paid: { bg: "bg-green-50", text: "text-green-700" },
    voided: { bg: "bg-gray-50", text: "text-gray-700" },
  };

  const statusStyle = statusConfig[invoice.status] || statusConfig.open;

  return (
    <div
      className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
    >
      <div className="flex items-center gap-3">
        {onClick ? (
          <button
            onClick={onClick}
            className="text-blue-600 hover:text-blue-800 hover:underline text-sm font-medium"
          >
            {invoice.invoice_number}
          </button>
        ) : (
          <span className="text-sm font-medium text-gray-900">{invoice.invoice_number}</span>
        )}
        <span className="text-xs text-gray-500">
          {invoice.invoice_date}
        </span>
        <span className={`px-1.5 py-0.5 ${statusStyle.bg} ${statusStyle.text} rounded text-xs`}>
          {invoice.status}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">
          {invoice.total_amount}
        </span>
        <span className="text-xs text-gray-400">
          {invoice.linked_lines} line{invoice.linked_lines !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}

/**
 * Compact badge showing downstream invoice count.
 */
interface InvoiceCountBadgeProps {
  count: number;
  onClick?: () => void;
}

export function InvoiceCountBadge({ count, onClick }: InvoiceCountBadgeProps) {
  if (count === 0) {
    return (
      <span className="text-xs text-gray-400">No invoices</span>
    );
  }

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs hover:bg-blue-100 transition-colors"
    >
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      {count} invoice{count !== 1 ? "s" : ""}
    </button>
  );
}
