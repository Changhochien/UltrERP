/**
 * PurchaseOrderDetail - View and edit a purchase order.
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { format } from "date-fns";
import { usePurchaseOrder, usePurchaseOrderActions } from "../hooks/usePurchaseOrder";
import { DownstreamInvoiceLineage } from "./DownstreamInvoiceLineage";
import { SubcontractingWorkflowPanel } from "./SubcontractingWorkflowPanel";
import { useReceiptsForPO } from "../hooks/useGoodsReceipt";
import { useSupplierControls } from "../hooks/useSupplierControls";
import { PO_STATUS_COLORS, PO_STATUS_LABELS } from "../constants";
import type { PurchaseOrderResponse, POStatus } from "../types";

interface PurchaseOrderDetailProps {
  isNew?: boolean;
  awardId?: string | null;
  initialData?: Partial<PurchaseOrderResponse>;
}

export function PurchaseOrderDetail({ isNew = false, awardId, initialData }: PurchaseOrderDetailProps) {
  const { poId } = useParams<{ poId: string }>();
  const navigate = useNavigate();
  const currentPoId = isNew ? null : poId ?? initialData?.id ?? null;
  const { data: poData, loading, error, refetch } = usePurchaseOrder(isNew ? null : poId ?? null);
  const supplierId = poData?.supplier_id ?? initialData?.supplier_id ?? null;
  const { createFromAward, update, submit, hold, release, complete, cancel, close } = usePurchaseOrderActions();
  const { data: receiptsData, loading: receiptsLoading, error: receiptsError } = useReceiptsForPO(currentPoId);
  const {
    data: supplierControls,
    loading: supplierControlsLoading,
    error: supplierControlsError,
  } = useSupplierControls(supplierId);

  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [procurementOptions, setProcurementOptions] = useState({
    isSubcontracted: false,
    finishedGoodsItemCode: "",
    finishedGoodsItemName: "",
    expectedSubcontractedQty: "",
    blanketOrderReferenceId: "",
    landedCostReferenceId: "",
  });

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

  useEffect(() => {
    if (!poDataOrInitial) {
      return;
    }

    setProcurementOptions({
      isSubcontracted: poDataOrInitial.is_subcontracted ?? false,
      finishedGoodsItemCode: poDataOrInitial.finished_goods_item_code ?? "",
      finishedGoodsItemName: poDataOrInitial.finished_goods_item_name ?? "",
      expectedSubcontractedQty: poDataOrInitial.expected_subcontracted_qty ?? "",
      blanketOrderReferenceId: poDataOrInitial.blanket_order_reference_id ?? "",
      landedCostReferenceId: poDataOrInitial.landed_cost_reference_id ?? "",
    });
  }, [poDataOrInitial]);

  const handleSaveProcurementOptions = useCallback(async () => {
    if (!poId) return;
    setSubmitting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await update(poId, {
        is_subcontracted: procurementOptions.isSubcontracted,
        finished_goods_item_code: procurementOptions.isSubcontracted
          ? procurementOptions.finishedGoodsItemCode || null
          : null,
        finished_goods_item_name: procurementOptions.isSubcontracted
          ? procurementOptions.finishedGoodsItemName || null
          : null,
        expected_subcontracted_qty: procurementOptions.isSubcontracted
          ? procurementOptions.expectedSubcontractedQty || null
          : null,
        blanket_order_reference_id: procurementOptions.blanketOrderReferenceId || null,
        landed_cost_reference_id: procurementOptions.landedCostReferenceId || null,
      });
      setSuccessMessage("Procurement options saved.");
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to save procurement options");
    } finally {
      setSubmitting(false);
    }
  }, [poId, procurementOptions, refetch, update]);

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

  const handleOpenInvoice = useCallback((invoiceId: string) => {
    navigate("/purchases", { state: { selectedInvoiceId: invoiceId } });
  }, [navigate]);

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
  const supplierStatusPending = Boolean(po.supplier_id) && supplierControlsLoading;
  const submitBlocked = canSubmit && Boolean(supplierControls?.po_blocked);
  const supplierControlMessage = supplierControls?.po_control_reason || supplierControlsError || "";
  const showSupplierControlAlert = Boolean(supplierControls && (supplierControls.po_blocked || supplierControls.po_warned));
  const showProcurementOptions =
    po.status === "draft" ||
    po.is_subcontracted ||
    Boolean(po.blanket_order_reference_id) ||
    Boolean(po.landed_cost_reference_id);
  const showSubcontractingFields =
    procurementOptions.isSubcontracted || Boolean(supplierControls?.is_subcontractor) || po.is_subcontracted;

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
      {showSupplierControlAlert && (
        <div
          role="alert"
          className={`rounded-lg border p-4 ${supplierControls?.po_blocked ? "border-red-200 bg-red-50 text-red-700" : "border-amber-200 bg-amber-50 text-amber-700"}`}
        >
          <div className="font-medium">
            {supplierControls?.po_blocked ? "Supplier controls block PO submission" : "Supplier controls require buyer attention"}
          </div>
          <p className="mt-1 text-sm">{supplierControlMessage}</p>
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
              className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${PO_STATUS_COLORS[po.status as POStatus] ?? "bg-gray-100 text-gray-700"}`}
            >
              {PO_STATUS_LABELS[po.status as POStatus] ?? po.status}
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

      {po.supplier_id && (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">Supplier Controls</h2>
            <p className="mt-1 text-sm text-gray-500">
              Draft submission stays aligned with supplier hold, scorecard, and subcontractor status.
            </p>
          </div>
          <div className="grid gap-4 px-6 py-4 md:grid-cols-2">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">PO authoring status</div>
              <div className="mt-2 text-sm font-medium text-gray-900">
                {supplierStatusPending
                  ? "Checking supplier controls..."
                  : submitBlocked
                    ? "Blocked"
                    : supplierControls?.po_warned
                      ? "Warning"
                      : "Ready"}
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {supplierStatusPending
                  ? "Control status is loading before draft submission can proceed."
                  : supplierControlMessage || "No supplier control issues detected for this PO."}
              </p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Supplier workflow profile</div>
              <div className="mt-2 text-sm font-medium text-gray-900">
                {supplierControls?.is_subcontractor ? "Eligible for subcontracting workflows" : "Standard supplier workflow"}
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {supplierControls?.is_subcontractor
                  ? "Subcontracting metadata can be attached to this draft PO before material transfer work begins."
                  : "This supplier does not currently expose subcontracting-specific PO fields."}
              </p>
            </div>
          </div>
        </div>
      )}

      {showProcurementOptions && (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">Procurement Options</h2>
            <p className="mt-1 text-sm text-gray-500">
              Draft-only extension hooks and subcontracting metadata stay on the PO so later workflows do not need schema retrofits.
            </p>
          </div>
          <div className="space-y-6 px-6 py-4">
            {showSubcontractingFields && (
              <div className="space-y-4 rounded-lg border border-gray-100 bg-gray-50 p-4">
                <label className="flex items-center gap-3 text-sm font-medium text-gray-900">
                  <input
                    type="checkbox"
                    aria-label="Subcontracting purchase order"
                    checked={procurementOptions.isSubcontracted}
                    disabled={po.status !== "draft"}
                    onChange={(event) => {
                      const checked = event.target.checked;
                      setProcurementOptions((current) => ({
                        ...current,
                        isSubcontracted: checked,
                        finishedGoodsItemCode: checked ? current.finishedGoodsItemCode : "",
                        finishedGoodsItemName: checked ? current.finishedGoodsItemName : "",
                        expectedSubcontractedQty: checked ? current.expectedSubcontractedQty : "",
                      }));
                    }}
                  />
                  Subcontracting purchase order
                </label>

                {procurementOptions.isSubcontracted && (
                  <div className="grid gap-4 md:grid-cols-3">
                    <label className="space-y-2 text-sm text-gray-700">
                      <span className="font-medium text-gray-900">Finished Goods Item Code</span>
                      <input
                        type="text"
                        aria-label="Finished Goods Item Code"
                        value={procurementOptions.finishedGoodsItemCode}
                        disabled={po.status !== "draft"}
                        onChange={(event) => setProcurementOptions((current) => ({
                          ...current,
                          finishedGoodsItemCode: event.target.value,
                        }))}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </label>
                    <label className="space-y-2 text-sm text-gray-700">
                      <span className="font-medium text-gray-900">Finished Goods Item Name</span>
                      <input
                        type="text"
                        aria-label="Finished Goods Item Name"
                        value={procurementOptions.finishedGoodsItemName}
                        disabled={po.status !== "draft"}
                        onChange={(event) => setProcurementOptions((current) => ({
                          ...current,
                          finishedGoodsItemName: event.target.value,
                        }))}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </label>
                    <label className="space-y-2 text-sm text-gray-700">
                      <span className="font-medium text-gray-900">Expected Subcontracted Quantity</span>
                      <input
                        type="number"
                        min="0"
                        step="0.001"
                        aria-label="Expected Subcontracted Quantity"
                        value={procurementOptions.expectedSubcontractedQty}
                        disabled={po.status !== "draft"}
                        onChange={(event) => setProcurementOptions((current) => ({
                          ...current,
                          expectedSubcontractedQty: event.target.value,
                        }))}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                      />
                    </label>
                  </div>
                )}
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">Blanket Order Reference</span>
                <input
                  type="text"
                  aria-label="Blanket Order Reference"
                  value={procurementOptions.blanketOrderReferenceId}
                  disabled={po.status !== "draft"}
                  onChange={(event) => setProcurementOptions((current) => ({
                    ...current,
                    blanketOrderReferenceId: event.target.value,
                  }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </label>
              <label className="space-y-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">Landed Cost Reference</span>
                <input
                  type="text"
                  aria-label="Landed Cost Reference"
                  value={procurementOptions.landedCostReferenceId}
                  disabled={po.status !== "draft"}
                  onChange={(event) => setProcurementOptions((current) => ({
                    ...current,
                    landedCostReferenceId: event.target.value,
                  }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </label>
            </div>

            {po.status === "draft" && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleSaveProcurementOptions}
                  disabled={submitting}
                  className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Save Procurement Options
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {procurementOptions.isSubcontracted && !po.is_subcontracted ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-blue-700">
          Save the subcontracting procurement options before creating material transfers or subcontracting receipts.
        </div>
      ) : null}

      {po.is_subcontracted ? <SubcontractingWorkflowPanel po={po} /> : null}

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
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                  Open Qty
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {po.items?.map((item, idx) => {
                const openQty = Math.max(0, Number(item.qty) - Number(item.received_qty));

                return (
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
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm font-medium text-gray-900">
                      {openQty.toLocaleString(undefined, { maximumFractionDigits: 3 })} {item.uom}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                  Subtotal
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                  {po.currency} {Number(po.subtotal).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-sm text-gray-700">
                  Taxes
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                  {po.currency} {Number(po.total_taxes).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-base font-bold text-gray-900">
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

      {currentPoId && (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">Receipt History</h2>
            <p className="mt-1 text-sm text-gray-500">
              {receiptsLoading
                ? "Loading receipt events..."
                : receiptsData
                  ? `${receiptsData.total} receipt${receiptsData.total === 1 ? "" : "s"} recorded against this PO.`
                  : "No receipt events recorded yet."}
            </p>
          </div>
          <div className="space-y-3 px-6 py-4">
            {receiptsError ? (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {receiptsError}
              </div>
            ) : receiptsLoading ? (
              <p className="text-sm text-gray-500">Loading receipt history...</p>
            ) : receiptsData && receiptsData.items.length > 0 ? (
              receiptsData.items.map((receipt) => (
                <div key={receipt.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <Link
                        to={`/procurement/goods-receipts/${receipt.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800"
                      >
                        {receipt.name}
                      </Link>
                      <span className="text-xs uppercase tracking-wide text-gray-500">
                        {receipt.status}
                      </span>
                    </div>
                    <div className="mt-1 text-sm text-gray-500">
                      {format(new Date(receipt.transaction_date), "yyyy-MM-dd")} • {receipt.supplier_name}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <div>{receipt.inventory_mutated ? "Inventory updated" : "Pending inventory update"}</div>
                    <div>PO open quantities shown above remain receipt-driven.</div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">
                No receipts recorded yet. Remaining open quantities stay visible on each PO line above.
              </p>
            )}
          </div>
        </div>
      )}

      {currentPoId && (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">Downstream Invoices</h2>
            <p className="mt-1 text-sm text-gray-500">
              Supplier invoices that reference this purchase order stay visible here for procurement and finance review.
            </p>
          </div>
          <div className="px-6 py-4">
            <DownstreamInvoiceLineage
              type="purchase_order"
              documentId={currentPoId}
              onInvoiceClick={handleOpenInvoice}
            />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between">
        <div className="flex gap-3">
          {["submitted", "to_receive", "to_bill", "to_receive_and_bill", "on_hold"].includes(po.status) && (
            <button
              onClick={() => navigate(`/procurement/purchase-orders/${poId}/create-receipt`)}
              className="rounded-md border border-green-600 bg-white px-4 py-2 text-sm font-medium text-green-600 hover:bg-green-50"
            >
              Create Receipt
            </button>
          )}
          {poId && (
            <button
              onClick={() => navigate(`/procurement/goods-receipts?purchase_order_id=${poId}`)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              View Receipts
            </button>
          )}
        </div>
        <div className="flex gap-3">
          {canSubmit && (
            <button
              onClick={handleSubmit}
              disabled={submitting || supplierStatusPending || submitBlocked}
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
    </div>
  );
}
