/**
 * GoodsReceiptDetail - View and manage a goods receipt.
 */

import { useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { format } from "date-fns";
import { useGoodsReceipt, useGoodsReceiptActions, useReceiptsForPO } from "../hooks/useGoodsReceipt";
import { GR_STATUS_COLORS, GR_STATUS_LABELS } from "../constants";
import type { GoodsReceiptResponse, GoodsReceiptStatus } from "../types";

interface GoodsReceiptDetailProps {
  isNew?: boolean;
  purchaseOrderId?: string | null;
  initialData?: Partial<GoodsReceiptResponse>;
}

export function GoodsReceiptDetail({ isNew = false, purchaseOrderId, initialData }: GoodsReceiptDetailProps) {
  const { grId } = useParams<{ grId: string }>();
  const navigate = useNavigate();
  const { data: grData, loading, error, refetch } = useGoodsReceipt(isNew ? null : grId ?? null);
  const { submit: submitGR, cancel: cancelGR } = useGoodsReceiptActions();
  const { data: receiptsData, refetch: refetchReceipts } = useReceiptsForPO(
    purchaseOrderId ?? grData?.purchase_order_id ?? null,
  );

  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const gr = (grData ?? initialData ?? null) as GoodsReceiptResponse | null;

  const handleSubmit = useCallback(async () => {
    if (!grId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await submitGR(grId);
      setSuccessMessage("Goods receipt submitted. Inventory mutated and PO progress updated.");
      refetch();
      refetchReceipts();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }, [grId, submitGR, refetch, refetchReceipts]);

  const handleCancel = useCallback(async () => {
    if (!grId) return;
    if (!confirm("Are you sure you want to cancel this goods receipt?")) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await cancelGR(grId);
      setSuccessMessage("Goods receipt cancelled. PO progress recomputed.");
      refetch();
      refetchReceipts();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to cancel");
    } finally {
      setSubmitting(false);
    }
  }, [grId, cancelGR, refetch, refetchReceipts]);

  const handleBackToPO = useCallback(() => {
    if (grData?.purchase_order_id) {
      navigate(`/procurement/purchase-orders/${grData.purchase_order_id}`);
    } else if (purchaseOrderId) {
      navigate(`/procurement/purchase-orders/${purchaseOrderId}`);
    }
  }, [navigate, grData?.purchase_order_id, purchaseOrderId]);

  if (loading || submitting) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        {error}
      </div>
    );
  }

  if (!grData && !initialData) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
        Goods receipt not found.
      </div>
    );
  }

  if (!gr) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
        Goods receipt not found.
      </div>
    );
  }

  const statusClass = (status: string) => GR_STATUS_COLORS[status as GoodsReceiptStatus] ?? "bg-gray-100 text-gray-700";
  const statusLabel = (status: string) => GR_STATUS_LABELS[status as GoodsReceiptStatus] ?? status;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        {gr.purchase_order_id && (
          <>
            <Link to="/procurement/purchase-orders" className="hover:text-blue-600">Purchase Orders</Link> /{" "}
            <Link to={`/procurement/purchase-orders/${gr.purchase_order_id}`} className="hover:text-blue-600">
              {gr.purchase_order_id.slice(0, 8)}...
            </Link> /{" "}
          </>
        )}
        {gr.name}
      </nav>

      {/* Messages */}
      {successMessage && <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">{successMessage}</div>}
      {actionError && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{actionError}</div>}

      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{gr.name}</h1>
            <p className="mt-1 text-sm text-gray-500">
              Created: {format(new Date(gr.created_at), "yyyy-MM-dd HH:mm")}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${statusClass(gr.status)}`}>
              {statusLabel(gr.status)}
            </span>
            {gr.inventory_mutated && (
              <span className="inline-flex rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
                Inventory Updated
              </span>
            )}
          </div>
        </div>

        {/* Supplier & Company */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Supplier</h3>
            <p className="mt-1 text-gray-900">{gr.supplier_name}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Company</h3>
            <p className="mt-1 text-gray-900">{gr.company}</p>
          </div>
        </div>

        {/* Dates */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Transaction Date</h3>
            <p className="mt-1 text-gray-900">{format(new Date(gr.transaction_date), "yyyy-MM-dd")}</p>
          </div>
          {gr.posting_date && (
            <div>
              <h3 className="text-sm font-medium text-gray-500">Posting Date</h3>
              <p className="mt-1 text-gray-900">{format(new Date(gr.posting_date), "yyyy-MM-dd")}</p>
            </div>
          )}
        </div>

        {gr.set_warehouse && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500">Receiving Warehouse</h3>
            <p className="mt-1 text-gray-900">{gr.set_warehouse}</p>
          </div>
        )}
        {gr.notes && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500">Notes</h3>
            <p className="mt-1 text-gray-900 whitespace-pre-wrap">{gr.notes}</p>
          </div>
        )}
      </div>

      {/* Receipt History */}
      {receiptsData && receiptsData.items.length > 1 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Receipt History for this PO</h2>
          <div className="space-y-2">
            {receiptsData.items.map((receipt) => (
              <div key={receipt.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-gray-900">{receipt.name}</span>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusClass(receipt.status)}`}>
                    {statusLabel(receipt.status)}
                  </span>
                  <span className="text-sm text-gray-500">{format(new Date(receipt.transaction_date), "yyyy-MM-dd")}</span>
                </div>
                <Link to={`/procurement/goods-receipts/${receipt.id}`} className="text-sm text-blue-600 hover:text-blue-800">View</Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Items Table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-medium text-gray-900">Received Items</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">#</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Item</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Accepted</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Rejected</th>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">Total</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Warehouse</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {gr.items?.map((item, idx) => (
                <tr key={item.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{item.item_name}</div>
                    <div className="text-xs text-gray-500">{item.item_code}</div>
                    {item.exception_notes && <div className="mt-1 text-xs text-orange-600">Note: {item.exception_notes}</div>}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-green-700 font-medium">{item.accepted_qty} {item.uom}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-red-700 font-medium">
                    {Number(item.rejected_qty) > 0 ? `${item.rejected_qty} ${item.uom}` : "-"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm text-gray-900">{item.total_qty} {item.uom}</td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900">{item.warehouse || gr.set_warehouse}</div>
                    {Number(item.rejected_qty) > 0 && item.rejected_warehouse && (
                      <div className="text-xs text-red-600">Rejected: {item.rejected_warehouse}</div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-between">
        <button onClick={handleBackToPO} className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Back to PO
        </button>
        <div className="flex gap-3">
          {gr.status === "draft" && (
            <button onClick={handleSubmit} disabled={submitting} className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
              Submit Receipt
            </button>
          )}
          {(gr.status === "draft" || gr.status === "submitted") && (
            <button onClick={handleCancel} disabled={submitting} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
