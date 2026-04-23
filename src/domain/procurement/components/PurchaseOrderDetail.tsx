/**
 * PurchaseOrderDetail - View and edit a purchase order.
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { format } from "date-fns";
import { usePurchaseOrder, usePurchaseOrderActions } from "../hooks/usePurchaseOrder";
import type { PurchaseOrderResponse, POStatus } from "../types";

const STATUS_COLORS: Record<POStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  on_hold: "bg-yellow-100 text-yellow-700",
  to_receive: "bg-orange-100 text-orange-700",
  to_bill: "bg-purple-100 text-purple-700",
  to_receive_and_bill: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
  closed: "bg-gray-100 text-gray-500",
};

const STATUS_LABELS: Record<POStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  on_hold: "On Hold",
  to_receive: "To Receive",
  to_bill: "To Bill",
  to_receive_and_bill: "To Receive & Bill",
  completed: "Completed",
  cancelled: "Cancelled",
  closed: "Closed",
};

interface PurchaseOrderDetailProps {
  isNew?: boolean;
  awardId?: string | null;
  initialData?: Partial<PurchaseOrderResponse>;
}

export function PurchaseOrderDetail({ isNew = false, awardId, initialData }: PurchaseOrderDetailProps) {
  const { poId } = useParams<{ poId: string }>();
  const navigate = useNavigate();
  const { data: poData, loading, error, refetch } = usePurchaseOrder(isNew ? null : poId ?? null);
  const { createFromAward, submit, hold, release, complete, cancel, close } = usePurchaseOrderActions();

  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load PO from award if provided
  useEffect(() => {
    if (isNew && awardId && !initialData) {
      setSubmitting(true);
      createFromAward(awardId)
        .then((newPo) => {
          navigate(`/procurement/purchase-orders/${newPo.id}`, { replace: true });
        })
        .catch((err: Error) => {
          setActionError(err.message);
        })
        .finally(() => {
          setSubmitting(false);
        });
    }
  }, [isNew, awardId, initialData, createFromAward, navigate]);

  const poDataOrInitial = poData ?? initialData ?? null;

  const handleSubmit = useCallback(async () => {
    if (!poId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await submit(poId);
      setSuccessMessage("Purchase order submitted for approval.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }, [poId, submit, refetch]);

  const handleHold = useCallback(async () => {
    if (!poId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await hold(poId);
      setSuccessMessage("Purchase order placed on hold.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to hold");
    } finally {
      setSubmitting(false);
    }
  }, [poId, hold, refetch]);

  const handleRelease = useCallback(async () => {
    if (!poId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await release(poId);
      setSuccessMessage("Purchase order released from hold.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to release");
    } finally {
      setSubmitting(false);
    }
  }, [poId, release, refetch]);

  const handleComplete = useCallback(async () => {
    if (!poId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await complete(poId);
      setSuccessMessage("Purchase order marked as complete.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to complete");
    } finally {
      setSubmitting(false);
    }
  }, [poId, complete, refetch]);

  const handleCancel = useCallback(async () => {
    if (!poId) return;
    if (!confirm("Are you sure you want to cancel this purchase order?")) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await cancel(poId);
      setSuccessMessage("Purchase order cancelled.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to cancel");
    } finally {
      setSubmitting(false);
    }
  }, [poId, cancel, refetch]);

  const handleClose = useCallback(async () => {
    if (!poId) return;
    if (!confirm("Are you sure you want to close this purchase order? This cannot be undone.")) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await close(poId);
      setSuccessMessage("Purchase order closed.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to close");
    } finally {
      setSubmitting(false);
    }
  }, [poId, close, refetch]);

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

  if (!poData) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
        Purchase order not found.
      </div>
    );
  }

  const po = poDataOrInitial as PurchaseOrderResponse;

  const canSubmit = po.status === "draft";
  const canHold = ["submitted", "to_receive", "to_bill", "to_receive_and_bill"].includes(po.status);
  const canRelease = po.status === "on_hold";
  const canComplete = ["submitted", "to_receive", "to_bill", "to_receive_and_bill"].includes(po.status);
  const canCancel = !["completed", "cancelled", "closed"].includes(po.status);
  const canClose = ["completed", "cancelled"].includes(po.status);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        <Link to="/procurement/purchase-orders" className="hover:text-blue-600">
          Purchase Orders
        </Link>{" "}
        / {po.name}
      </nav>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">
          {successMessage}
        </div>
      )}
      {actionError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {actionError}
        </div>
      )}

      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{po.name}</h1>
            <p className="mt-1 text-sm text-gray-500">
              Created: {format(new Date(po.created_at), "yyyy-MM-dd HH:mm")}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span
              className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[po.status as POStatus] ?? "bg-gray-100 text-gray-700"}`}
            >
              {STATUS_LABELS[po.status as POStatus] ?? po.status}
            </span>
            {po.is_approved && (
              <span className="inline-flex rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
                Approved
              </span>
            )}
          </div>
        </div>

        {/* Sourcing Lineage */}
        {(po.rfq_id || po.quotation_id || po.award_id) && (
          <div className="mt-4 rounded-lg bg-blue-50 p-4">
            <h3 className="text-sm font-medium text-blue-900">Sourcing Lineage</h3>
            <div className="mt-2 flex flex-wrap gap-4 text-sm">
              {po.award_id && (
                <Link
                  to={`/procurement/awards/${po.award_id}`}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Award: {po.award_id.slice(0, 8)}...
                </Link>
              )}
              {po.quotation_id && (
                <Link
                  to={`/procurement/supplier-quotations/${po.quotation_id}`}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Quotation: {po.quotation_id.slice(0, 8)}...
                </Link>
              )}
              {po.rfq_id && (
                <Link to={`/procurement/rfqs/${po.rfq_id}`} className="text-blue-600 hover:text-blue-800">
                  RFQ: {po.rfq_id.slice(0, 8)}...
                </Link>
              )}
            </div>
          </div>
        )}

        {/* Supplier & Company */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Supplier</h3>
            <p className="mt-1 text-gray-900">{po.supplier_name}</p>
            {po.contact_email && (
              <p className="text-sm text-gray-500">{po.contact_email}</p>
            )}
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Company</h3>
            <p className="mt-1 text-gray-900">{po.company}</p>
            <p className="text-sm text-gray-500">Currency: {po.currency}</p>
          </div>
        </div>

        {/* Dates */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Transaction Date</h3>
            <p className="mt-1 text-gray-900">
              {format(new Date(po.transaction_date), "yyyy-MM-dd")}
            </p>
          </div>
          {po.schedule_date ? (
            <div>
              <h3 className="text-sm font-medium text-gray-500">Schedule Date</h3>
              <p className="mt-1 text-gray-900">
                {format(new Date(po.schedule_date), "yyyy-MM-dd")}
              </p>
            </div>
          ) : null}
        </div>

        {/* Progress */}
        <div className="mt-6 rounded-lg bg-gray-50 p-4">
          <h3 className="text-sm font-medium text-gray-900">Progress</h3>
          <div className="mt-3 grid grid-cols-2 gap-6">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Received</span>
                <span className="text-sm font-medium text-gray-900">
                  {Number(po.per_received).toFixed(1)}%
                </span>
              </div>
              <div className="mt-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-2 bg-blue-500 transition-all"
                  style={{ width: `${Number(po.per_received)}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Billed</span>
                <span className="text-sm font-medium text-gray-900">
                  {Number(po.per_billed).toFixed(1)}%
                </span>
              </div>
              <div className="mt-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-2 bg-purple-500 transition-all"
                  style={{ width: `${Number(po.per_billed)}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Notes */}
        {po.notes && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500">Notes</h3>
            <p className="mt-1 text-gray-900 whitespace-pre-wrap">{po.notes}</p>
          </div>
        )}
      </div>

      {/* Items Table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-medium text-gray-900">Line Items</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Item
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Qty
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Unit Rate
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Amount
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                  Received
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {po.items?.map((item, idx) => (
                <tr key={item.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{item.item_name}</div>
                    <div className="text-xs text-gray-500">{item.item_code}</div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                    {item.qty} {item.uom}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                    {po.currency} {Number(item.unit_rate).toFixed(4)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                    {po.currency} {Number(item.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm text-gray-500">
                    {item.received_qty} {item.uom}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={4} className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                  Subtotal
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                  {po.currency} {Number(po.subtotal).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={4} className="px-4 py-3 text-right text-sm text-gray-700">
                  Taxes
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                  {po.currency} {Number(po.total_taxes).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={4} className="px-4 py-3 text-right text-base font-bold text-gray-900">
                  Grand Total
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-base font-bold text-gray-900">
                  {po.currency} {Number(po.grand_total).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        {canSubmit && (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Submit for Approval
          </button>
        )}
        {canHold && (
          <button
            onClick={handleHold}
            disabled={submitting}
            className="rounded-md bg-yellow-600 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50"
          >
            Hold
          </button>
        )}
        {canRelease && (
          <button
            onClick={handleRelease}
            disabled={submitting}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            Release
          </button>
        )}
        {canComplete && (
          <button
            onClick={handleComplete}
            disabled={submitting}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            Mark Complete
          </button>
        )}
        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={submitting}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        {canClose && (
          <button
            onClick={handleClose}
            disabled={submitting}
            className="rounded-md bg-gray-600 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            Close
          </button>
        )}
      </div>
    </div>
  );
}
