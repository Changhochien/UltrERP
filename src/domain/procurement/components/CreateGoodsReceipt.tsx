/**
 * CreateGoodsReceipt - Create a new goods receipt from a Purchase Order.
 */

import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { usePurchaseOrder } from "../hooks/usePurchaseOrder";
import { useGoodsReceiptActions } from "../hooks/useGoodsReceipt";
import type {
  PurchaseOrderResponse,
  GoodsReceiptCreatePayload,
  GRItemPayload,
} from "../types";

interface CreateGoodsReceiptProps {
  purchaseOrderId: string;
}

export function CreateGoodsReceipt({ purchaseOrderId }: CreateGoodsReceiptProps) {
  const navigate = useNavigate();
  const { data: poData, loading: poLoading, error: poError } = usePurchaseOrder(purchaseOrderId);
  const { create: createGR } = useGoodsReceiptActions();

  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form state
  const [transactionDate, setTransactionDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [setWarehouse, setSetWarehouse] = useState("");
  const [notes, setNotes] = useState("");

  // Line items state - initialized from PO
  const [lineItems, setLineItems] = useState<Array<{
    poLineId: string;
    itemCode: string;
    itemName: string;
    description: string;
    orderedQty: string;
    receivedQty: string;
    remainingQty: string;
    acceptedQty: string;
    rejectedQty: string;
    rejectedWarehouse: string;
    exceptionNotes: string;
    uom: string;
    warehouse: string;
    unitRate: string;
  }>>([]);

  // Initialize line items from PO
  useEffect(() => {
    if (poData?.items) {
      const items = poData.items.map((item) => {
        const remaining = Math.max(0, Number(item.qty) - Number(item.received_qty));
        return {
          poLineId: item.id,
          itemCode: item.item_code,
          itemName: item.item_name,
          description: item.description || "",
          orderedQty: item.qty,
          receivedQty: item.received_qty,
          remainingQty: String(remaining),
          acceptedQty: remaining > 0 ? String(remaining) : "0",
          rejectedQty: "0",
          rejectedWarehouse: "",
          exceptionNotes: "",
          uom: item.uom,
          warehouse: item.warehouse || poData.set_warehouse || "",
          unitRate: item.unit_rate,
        };
      });
      setLineItems(items);
      if (poData.set_warehouse) {
        setSetWarehouse(poData.set_warehouse);
      }
    }
  }, [poData]);

  const handleLineChange = useCallback((
    index: number,
    field: string,
    value: string,
  ) => {
    setLineItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }, []);

  const handleAcceptedQtyChange = useCallback((
    index: number,
    value: string,
  ) => {
    const numValue = parseFloat(value) || 0;
    const remaining = parseFloat(lineItems[index].remainingQty) || 0;
    if (numValue > remaining) {
      value = String(remaining);
    }
    handleLineChange(index, "acceptedQty", value);
    // Auto-clear rejected if accepting full remaining
    if (numValue >= remaining) {
      handleLineChange(index, "rejectedQty", "0");
      handleLineChange(index, "rejectedWarehouse", "");
      handleLineChange(index, "exceptionNotes", "");
    }
  }, [lineItems, handleLineChange]);

  const handleRejectedQtyChange = useCallback((
    index: number,
    value: string,
  ) => {
    const numValue = parseFloat(value) || 0;
    const remaining = parseFloat(lineItems[index].remainingQty) || 0;
    const accepted = parseFloat(lineItems[index].acceptedQty) || 0;
    // Ensure accepted + rejected <= remaining
    const maxRejected = Math.max(0, remaining - accepted);
    if (numValue > maxRejected) {
      value = String(maxRejected);
    }
    handleLineChange(index, "rejectedQty", value);
    if ((parseFloat(value) || 0) <= 0) {
      handleLineChange(index, "rejectedWarehouse", "");
      handleLineChange(index, "exceptionNotes", "");
    }
  }, [lineItems, handleLineChange]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setActionError(null);

    // Validate at least one item has quantity
    const itemsWithQty = lineItems.filter(
      (item) => Number(item.acceptedQty) > 0 || Number(item.rejectedQty) > 0,
    );

    if (itemsWithQty.length === 0) {
      setActionError("At least one item must have accepted or rejected quantity.");
      setSubmitting(false);
      return;
    }

    const payload: GoodsReceiptCreatePayload = {
      purchase_order_id: purchaseOrderId,
      transaction_date: transactionDate,
      set_warehouse: setWarehouse,
      contact_person: "",
      notes,
      items: lineItems
        .filter((item) => Number(item.acceptedQty) > 0 || Number(item.rejectedQty) > 0)
        .map((item): GRItemPayload => ({
          purchase_order_item_id: item.poLineId,
          item_code: item.itemCode,
          item_name: item.itemName,
          description: item.description,
          accepted_qty: item.acceptedQty,
          rejected_qty: item.rejectedQty,
          uom: item.uom,
          warehouse: item.warehouse || setWarehouse,
          rejected_warehouse: Number(item.rejectedQty) > 0 ? item.rejectedWarehouse : "",
          batch_no: "",
          serial_no: "",
          exception_notes: item.exceptionNotes,
          unit_rate: item.unitRate,
        })),
    };

    try {
      const newGR = await createGR(payload);
      navigate(`/procurement/goods-receipts/${newGR.id}`);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to create goods receipt");
      setSubmitting(false);
    }
  }, [lineItems, purchaseOrderId, transactionDate, setWarehouse, notes, createGR, navigate]);

  const handleCancel = useCallback(() => {
    navigate(`/procurement/purchase-orders/${purchaseOrderId}`);
  }, [navigate, purchaseOrderId]);

  if (poLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      </div>
    );
  }

  if (poError || !poData) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        {poError || "Purchase order not found"}
      </div>
    );
  }

  const po = poData as PurchaseOrderResponse;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h1 className="text-2xl font-bold text-gray-900">Create Goods Receipt</h1>
        <p className="mt-1 text-sm text-gray-500">
          PO: {po.name} | Supplier: {po.supplier_name}
        </p>
      </div>

      {/* Error Message */}
      {actionError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {actionError}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header Fields */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Receipt Details</h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Transaction Date
              </label>
              <input
                type="date"
                value={transactionDate}
                onChange={(e) => setTransactionDate(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Receiving Warehouse
              </label>
              <input
                type="text"
                value={setWarehouse}
                onChange={(e) => setSetWarehouse(e.target.value)}
                placeholder={po.set_warehouse || "Enter warehouse"}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700">
                Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Optional notes about this receipt..."
              />
            </div>
          </div>
        </div>

        {/* Line Items */}
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">Line Items</h2>
            <p className="mt-1 text-sm text-gray-500">
              Enter accepted and rejected quantities for each line. Partial deliveries are supported.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Item
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Ordered
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Received
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Remaining
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Accepted
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Rejected
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Warehouse
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Exceptions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {lineItems.map((item, idx) => {
                  const remaining = Number(item.remainingQty);
                  const hasRemaining = remaining > 0;
                  return (
                    <tr key={item.poLineId} className={!hasRemaining ? "bg-gray-50" : ""}>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-gray-900">{item.itemName}</div>
                        <div className="text-xs text-gray-500">{item.itemCode}</div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                        {item.orderedQty} {item.uom}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                        {item.receivedQty} {item.uom}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                        {item.remainingQty} {item.uom}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        {hasRemaining ? (
                          <input
                            type="number"
                            min="0"
                            max={remaining}
                            step="0.001"
                            aria-label={`Accepted quantity for line ${idx + 1}`}
                            value={item.acceptedQty}
                            onChange={(e) => handleAcceptedQtyChange(idx, e.target.value)}
                            className="w-24 rounded-md border border-gray-300 px-2 py-1 text-right text-sm text-green-700 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                          />
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        {hasRemaining ? (
                          <input
                            type="number"
                            min="0"
                            max={Math.max(0, remaining - Number(item.acceptedQty))}
                            step="0.001"
                            aria-label={`Rejected quantity for line ${idx + 1}`}
                            value={item.rejectedQty}
                            onChange={(e) => handleRejectedQtyChange(idx, e.target.value)}
                            className="w-24 rounded-md border border-gray-300 px-2 py-1 text-right text-sm text-red-700 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                          />
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {hasRemaining ? (
                          <input
                            type="text"
                            aria-label={`Receiving warehouse for line ${idx + 1}`}
                            value={item.warehouse || setWarehouse}
                            onChange={(e) => handleLineChange(idx, "warehouse", e.target.value)}
                            placeholder="Warehouse"
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <span className="text-sm text-gray-400">{item.warehouse || "-"}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {hasRemaining && Number(item.rejectedQty) > 0 ? (
                          <div className="space-y-2">
                            <input
                              type="text"
                              aria-label={`Rejected warehouse for line ${idx + 1}`}
                              value={item.rejectedWarehouse}
                              onChange={(e) => handleLineChange(idx, "rejectedWarehouse", e.target.value)}
                              placeholder="Rejected warehouse"
                              className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                            />
                            <input
                              type="text"
                              aria-label={`Exception notes for line ${idx + 1}`}
                              value={item.exceptionNotes}
                              onChange={(e) => handleLineChange(idx, "exceptionNotes", e.target.value)}
                              placeholder="Reason for rejection or exception"
                              className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
                            />
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleCancel}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Receipt"}
          </button>
        </div>
      </form>
    </div>
  );
}
