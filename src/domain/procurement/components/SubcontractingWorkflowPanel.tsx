import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "../../../components/ui/button";
import {
  cancelSubcontractingMaterialTransfer,
  cancelSubcontractingReceipt,
  createSubcontractingMaterialTransfer,
  createSubcontractingReceipt,
  deliverSubcontractingMaterialTransfer,
  getSubcontractingMaterialTransfer,
  getSubcontractingReceipt,
  listSubcontractingMaterialTransfers,
  listSubcontractingReceipts,
  shipSubcontractingMaterialTransfer,
  submitSubcontractingMaterialTransfer,
  submitSubcontractingReceipt,
} from "../../../lib/api/procurement";
import type {
  PurchaseOrderResponse,
  SCRItemPayload,
  SMTItemPayload,
  SubcontractingMaterialTransferResponse,
  SubcontractingReceiptResponse,
} from "../types";

interface SubcontractingWorkflowPanelProps {
  po: PurchaseOrderResponse;
}

function today(): string {
  return new Date().toISOString().split("T")[0];
}

function createEmptyTransferItem(): SMTItemPayload {
  return {
    item_code: "",
    item_name: "",
    description: "",
    qty: "",
    uom: "",
    warehouse: "",
  };
}

function createEmptyReceiptItem(po: PurchaseOrderResponse): SCRItemPayload {
  return {
    item_code: po.finished_goods_item_code ?? "",
    item_name: po.finished_goods_item_name ?? "",
    description: "",
    accepted_qty: po.expected_subcontracted_qty ?? "",
    rejected_qty: "0",
    uom: po.items[0]?.uom ?? "",
    warehouse: po.set_warehouse,
    unit_rate: po.items[0]?.unit_rate ?? "0",
    exception_notes: "",
  };
}

function summarizeTransferItems(items: SubcontractingMaterialTransferResponse["items"]): string {
  if (items.length === 0) {
    return "No transfer items recorded.";
  }
  return items
    .map((item) => `${item.item_name || item.item_code} (${item.qty} ${item.uom || "units"})`)
    .join(", ");
}

function summarizeReceiptItems(items: SubcontractingReceiptResponse["items"]): string {
  if (items.length === 0) {
    return "No receipt items recorded.";
  }
  return items
    .map((item) => {
      const rejected = Number(item.rejected_qty) > 0 ? `, ${item.rejected_qty} rejected` : "";
      return `${item.item_name || item.item_code} (${item.accepted_qty} accepted${rejected})`;
    })
    .join(", ");
}

export function SubcontractingWorkflowPanel({ po }: SubcontractingWorkflowPanelProps) {
  const [materialTransfers, setMaterialTransfers] = useState<SubcontractingMaterialTransferResponse[]>([]);
  const [receipts, setReceipts] = useState<SubcontractingReceiptResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [showTransferForm, setShowTransferForm] = useState(false);
  const [showReceiptForm, setShowReceiptForm] = useState(false);
  const [transferDraft, setTransferDraft] = useState({
    transferDate: today(),
    sourceWarehouse: po.set_warehouse,
    contactPerson: po.contact_person,
    contactEmail: po.contact_email,
    notes: "",
    items: [createEmptyTransferItem()],
  });
  const [receiptDraft, setReceiptDraft] = useState({
    receiptDate: today(),
    postingDate: today(),
    setWarehouse: po.set_warehouse,
    contactPerson: po.contact_person,
    notes: "",
    materialTransferIds: [] as string[],
    items: [createEmptyReceiptItem(po)],
  });

  const resetTransferDraft = useCallback(() => {
    setTransferDraft({
      transferDate: today(),
      sourceWarehouse: po.set_warehouse,
      contactPerson: po.contact_person,
      contactEmail: po.contact_email,
      notes: "",
      items: [createEmptyTransferItem()],
    });
  }, [po.contact_email, po.contact_person, po.set_warehouse]);

  const resetReceiptDraft = useCallback(() => {
    setReceiptDraft({
      receiptDate: today(),
      postingDate: today(),
      setWarehouse: po.set_warehouse,
      contactPerson: po.contact_person,
      notes: "",
      materialTransferIds: [],
      items: [createEmptyReceiptItem(po)],
    });
  }, [po]);

  const loadSubcontractingData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [transferList, receiptList] = await Promise.all([
        listSubcontractingMaterialTransfers({ purchase_order_id: po.id, page_size: 50 }),
        listSubcontractingReceipts({ purchase_order_id: po.id, page_size: 50 }),
      ]);
      const [transferDetails, receiptDetails] = await Promise.all([
        Promise.all(
          transferList.items.map((transfer) => getSubcontractingMaterialTransfer(transfer.id)),
        ),
        Promise.all(
          receiptList.items.map((receipt) => getSubcontractingReceipt(receipt.id)),
        ),
      ]);

      setMaterialTransfers(transferDetails);
      setReceipts(receiptDetails);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load subcontracting operations");
    } finally {
      setLoading(false);
    }
  }, [po.id]);

  useEffect(() => {
    void loadSubcontractingData();
  }, [loadSubcontractingData]);

  useEffect(() => {
    resetTransferDraft();
    resetReceiptDraft();
  }, [resetReceiptDraft, resetTransferDraft]);

  const transferNamesById = useMemo(
    () => new Map(materialTransfers.map((transfer) => [transfer.id, transfer.name])),
    [materialTransfers],
  );

  async function runAction(actionName: string, work: () => Promise<void>) {
    setBusyAction(actionName);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await work();
      await loadSubcontractingData();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Subcontracting action failed");
    } finally {
      setBusyAction(null);
    }
  }

  function updateTransferItem(idx: number, field: keyof SMTItemPayload, value: string) {
    setTransferDraft((current) => ({
      ...current,
      items: current.items.map((item, i) => (i === idx ? { ...item, [field]: value } : item)),
    }));
  }

  function updateReceiptItem(idx: number, field: keyof SCRItemPayload, value: string) {
    setReceiptDraft((current) => ({
      ...current,
      items: current.items.map((item, i) => (i === idx ? { ...item, [field]: value } : item)),
    }));
  }

  async function handleCreateTransfer() {
    const items = transferDraft.items.filter((item) => item.item_code || item.item_name);
    if (!transferDraft.sourceWarehouse.trim()) {
      setActionError("Source warehouse is required for a material transfer.");
      return;
    }
    if (items.length === 0) {
      setActionError("At least one transfer item is required.");
      return;
    }

    await runAction("create-transfer", async () => {
      await createSubcontractingMaterialTransfer({
        purchase_order_id: po.id,
        transfer_date: transferDraft.transferDate,
        source_warehouse: transferDraft.sourceWarehouse,
        contact_person: transferDraft.contactPerson,
        contact_email: transferDraft.contactEmail,
        notes: transferDraft.notes,
        items,
      });
      setShowTransferForm(false);
      resetTransferDraft();
      setSuccessMessage("Material transfer created.");
    });
  }

  async function handleCreateReceipt() {
    const items = receiptDraft.items.filter((item) => item.item_code || item.item_name);
    if (!receiptDraft.setWarehouse.trim()) {
      setActionError("Receiving warehouse is required for a subcontracting receipt.");
      return;
    }
    if (receiptDraft.materialTransferIds.length === 0) {
      setActionError("Link at least one material transfer before creating a subcontracting receipt.");
      return;
    }
    if (items.length === 0) {
      setActionError("At least one subcontracting receipt item is required.");
      return;
    }

    await runAction("create-receipt", async () => {
      await createSubcontractingReceipt({
        purchase_order_id: po.id,
        receipt_date: receiptDraft.receiptDate,
        posting_date: receiptDraft.postingDate || null,
        set_warehouse: receiptDraft.setWarehouse,
        contact_person: receiptDraft.contactPerson,
        notes: receiptDraft.notes,
        material_transfer_ids: receiptDraft.materialTransferIds,
        items,
      });
      setShowReceiptForm(false);
      resetReceiptDraft();
      setSuccessMessage("Subcontracting receipt created.");
    });
  }

  return (
    <div className="space-y-6 rounded-lg border border-gray-200 bg-white p-6">
      <div>
        <h2 className="text-lg font-medium text-gray-900">Subcontracting Operations</h2>
        <p className="mt-1 text-sm text-gray-500">
          Track supplied materials separately from subcontracted output so the PO keeps an auditable hand-off history.
        </p>
      </div>

      {successMessage ? (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">
          {successMessage}
        </div>
      ) : null}
      {actionError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {actionError}
        </div>
      ) : null}
      {loadError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {loadError}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-4 rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-medium text-gray-900">Material Transfers</h3>
              <p className="text-sm text-gray-500">
                Initiate and progress material hand-offs to the subcontractor.
              </p>
            </div>
            <Button type="button" variant="outline" onClick={() => setShowTransferForm((current) => !current)}>
              {showTransferForm ? "Hide Transfer Form" : "New Material Transfer"}
            </Button>
          </div>

          {showTransferForm ? (
            <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Transfer Date</span>
                  <input
                    type="date"
                    aria-label="Transfer Date"
                    value={transferDraft.transferDate}
                    onChange={(event) => setTransferDraft((current) => ({
                      ...current,
                      transferDate: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Source Warehouse</span>
                  <input
                    type="text"
                    aria-label="Source Warehouse"
                    value={transferDraft.sourceWarehouse}
                    onChange={(event) => setTransferDraft((current) => ({
                      ...current,
                      sourceWarehouse: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Contact Person</span>
                  <input
                    type="text"
                    aria-label="Transfer Contact Person"
                    value={transferDraft.contactPerson}
                    onChange={(event) => setTransferDraft((current) => ({
                      ...current,
                      contactPerson: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Contact Email</span>
                  <input
                    type="email"
                    aria-label="Transfer Contact Email"
                    value={transferDraft.contactEmail}
                    onChange={(event) => setTransferDraft((current) => ({
                      ...current,
                      contactEmail: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>

              <label className="space-y-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">Notes</span>
                <textarea
                  aria-label="Transfer Notes"
                  value={transferDraft.notes}
                  onChange={(event) => setTransferDraft((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </label>

              <div className="space-y-3">
                {transferDraft.items.map((item, idx) => (
                  <div key={idx} className="grid gap-3 rounded-lg border border-gray-200 p-3 md:grid-cols-3">
                    <input
                      type="text"
                      aria-label={`Transfer Item Code ${idx + 1}`}
                      value={item.item_code}
                      onChange={(event) => updateTransferItem(idx, "item_code", event.target.value)}
                      placeholder="Item Code"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Transfer Item Name ${idx + 1}`}
                      value={item.item_name}
                      onChange={(event) => updateTransferItem(idx, "item_name", event.target.value)}
                      placeholder="Item Name"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      aria-label={`Transfer Quantity ${idx + 1}`}
                      value={item.qty}
                      onChange={(event) => updateTransferItem(idx, "qty", event.target.value)}
                      placeholder="Quantity"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Transfer UOM ${idx + 1}`}
                      value={item.uom}
                      onChange={(event) => updateTransferItem(idx, "uom", event.target.value)}
                      placeholder="UOM"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Transfer Item Warehouse ${idx + 1}`}
                      value={item.warehouse}
                      onChange={(event) => updateTransferItem(idx, "warehouse", event.target.value)}
                      placeholder="Item Warehouse"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Transfer Item Description ${idx + 1}`}
                      value={item.description}
                      onChange={(event) => updateTransferItem(idx, "description", event.target.value)}
                      placeholder="Description"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    {transferDraft.items.length > 1 ? (
                      <div className="md:col-span-3">
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setTransferDraft((current) => ({
                            ...current,
                            items: current.items.filter((_, itemIdx) => itemIdx !== idx),
                          }))}
                        >
                          Remove Transfer Item
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setTransferDraft((current) => ({
                    ...current,
                    items: [...current.items, createEmptyTransferItem()],
                  }))}
                >
                  Add Transfer Item
                </Button>
                <Button type="button" onClick={() => void handleCreateTransfer()} disabled={busyAction !== null}>
                  {busyAction === "create-transfer" ? "Creating..." : "Create Material Transfer"}
                </Button>
              </div>
            </div>
          ) : null}

          {loading ? (
            <p className="text-sm text-gray-500">Loading subcontracting material transfers...</p>
          ) : materialTransfers.length === 0 ? (
            <p className="text-sm text-gray-500">No material transfers recorded for this subcontracting PO yet.</p>
          ) : (
            <div className="space-y-3">
              {materialTransfers.map((transfer) => (
                <div key={transfer.id} className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{transfer.name}</div>
                      <div className="mt-1 text-sm text-gray-500">
                        {transfer.transfer_date} • {transfer.source_warehouse}
                      </div>
                    </div>
                    <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {transfer.status}
                    </span>
                  </div>

                  <p className="mt-3 text-sm text-gray-700">{summarizeTransferItems(transfer.items)}</p>
                  {transfer.notes ? (
                    <p className="mt-2 text-sm text-gray-500">{transfer.notes}</p>
                  ) : null}

                  <div className="mt-3 flex flex-wrap gap-2">
                    {transfer.status === "draft" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => void runAction(`submit-transfer-${transfer.id}`, async () => {
                          await submitSubcontractingMaterialTransfer(transfer.id);
                          setSuccessMessage(`Submitted ${transfer.name}.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Submit Transfer
                      </Button>
                    ) : null}
                    {transfer.status === "pending" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => void runAction(`ship-transfer-${transfer.id}`, async () => {
                          await shipSubcontractingMaterialTransfer(transfer.id);
                          setSuccessMessage(`Marked ${transfer.name} in transit.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Mark In Transit
                      </Button>
                    ) : null}
                    {transfer.status === "in_transit" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => void runAction(`deliver-transfer-${transfer.id}`, async () => {
                          await deliverSubcontractingMaterialTransfer(transfer.id);
                          setSuccessMessage(`Marked ${transfer.name} delivered.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Mark Delivered
                      </Button>
                    ) : null}
                    {!(["delivered", "cancelled"] as string[]).includes(transfer.status) ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => void runAction(`cancel-transfer-${transfer.id}`, async () => {
                          await cancelSubcontractingMaterialTransfer(transfer.id);
                          setSuccessMessage(`Cancelled ${transfer.name}.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Cancel Transfer
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4 rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-medium text-gray-900">Subcontracting Receipts</h3>
              <p className="text-sm text-gray-500">
                Record finished output separately from standard goods receipts and keep linked transfer audit context.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              disabled={materialTransfers.length === 0}
              onClick={() => setShowReceiptForm((current) => !current)}
            >
              {showReceiptForm ? "Hide Receipt Form" : "New Subcontracting Receipt"}
            </Button>
          </div>

          {showReceiptForm ? (
            <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Receipt Date</span>
                  <input
                    type="date"
                    aria-label="Receipt Date"
                    value={receiptDraft.receiptDate}
                    onChange={(event) => setReceiptDraft((current) => ({
                      ...current,
                      receiptDate: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Posting Date</span>
                  <input
                    type="date"
                    aria-label="Posting Date"
                    value={receiptDraft.postingDate}
                    onChange={(event) => setReceiptDraft((current) => ({
                      ...current,
                      postingDate: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Receiving Warehouse</span>
                  <input
                    type="text"
                    aria-label="Receiving Warehouse"
                    value={receiptDraft.setWarehouse}
                    onChange={(event) => setReceiptDraft((current) => ({
                      ...current,
                      setWarehouse: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="space-y-2 text-sm text-gray-700">
                  <span className="font-medium text-gray-900">Contact Person</span>
                  <input
                    type="text"
                    aria-label="Receipt Contact Person"
                    value={receiptDraft.contactPerson}
                    onChange={(event) => setReceiptDraft((current) => ({
                      ...current,
                      contactPerson: event.target.value,
                    }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>

              <label className="space-y-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">Linked Material Transfers</span>
                <div className="space-y-2 rounded-md border border-gray-200 p-3">
                  {materialTransfers.length === 0 ? (
                    <p className="text-sm text-gray-500">Create a material transfer before receiving subcontracted output.</p>
                  ) : (
                    materialTransfers.map((transfer) => (
                      <label key={transfer.id} className="flex items-center gap-2 text-sm text-gray-700">
                        <input
                          type="checkbox"
                          checked={receiptDraft.materialTransferIds.includes(transfer.id)}
                          onChange={(event) => setReceiptDraft((current) => ({
                            ...current,
                            materialTransferIds: event.target.checked
                              ? [...current.materialTransferIds, transfer.id]
                              : current.materialTransferIds.filter((transferId) => transferId !== transfer.id),
                          }))}
                        />
                        <span>{transfer.name} • {transfer.status}</span>
                      </label>
                    ))
                  )}
                </div>
              </label>

              <label className="space-y-2 text-sm text-gray-700">
                <span className="font-medium text-gray-900">Notes</span>
                <textarea
                  aria-label="Receipt Notes"
                  value={receiptDraft.notes}
                  onChange={(event) => setReceiptDraft((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </label>

              <div className="space-y-3">
                {receiptDraft.items.map((item, idx) => (
                  <div key={idx} className="grid gap-3 rounded-lg border border-gray-200 p-3 md:grid-cols-3">
                    <input
                      type="text"
                      aria-label={`Receipt Item Code ${idx + 1}`}
                      value={item.item_code}
                      onChange={(event) => updateReceiptItem(idx, "item_code", event.target.value)}
                      placeholder="Finished Goods Item Code"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Receipt Item Name ${idx + 1}`}
                      value={item.item_name}
                      onChange={(event) => updateReceiptItem(idx, "item_name", event.target.value)}
                      placeholder="Finished Goods Item Name"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      aria-label={`Accepted Quantity ${idx + 1}`}
                      value={item.accepted_qty}
                      onChange={(event) => updateReceiptItem(idx, "accepted_qty", event.target.value)}
                      placeholder="Accepted Quantity"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      aria-label={`Rejected Quantity ${idx + 1}`}
                      value={item.rejected_qty}
                      onChange={(event) => updateReceiptItem(idx, "rejected_qty", event.target.value)}
                      placeholder="Rejected Quantity"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Receipt UOM ${idx + 1}`}
                      value={item.uom}
                      onChange={(event) => updateReceiptItem(idx, "uom", event.target.value)}
                      placeholder="UOM"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Receipt Warehouse ${idx + 1}`}
                      value={item.warehouse}
                      onChange={(event) => updateReceiptItem(idx, "warehouse", event.target.value)}
                      placeholder="Receipt Warehouse"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.0001"
                      aria-label={`Receipt Unit Rate ${idx + 1}`}
                      value={item.unit_rate}
                      onChange={(event) => updateReceiptItem(idx, "unit_rate", event.target.value)}
                      placeholder="Unit Rate"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                    <input
                      type="text"
                      aria-label={`Receipt Exception Notes ${idx + 1}`}
                      value={item.exception_notes}
                      onChange={(event) => updateReceiptItem(idx, "exception_notes", event.target.value)}
                      placeholder="Exception Notes"
                      className="rounded-md border border-gray-300 px-3 py-2 text-sm md:col-span-2"
                    />
                    {receiptDraft.items.length > 1 ? (
                      <div className="md:col-span-3">
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setReceiptDraft((current) => ({
                            ...current,
                            items: current.items.filter((_, itemIdx) => itemIdx !== idx),
                          }))}
                        >
                          Remove Receipt Item
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setReceiptDraft((current) => ({
                    ...current,
                    items: [...current.items, createEmptyReceiptItem(po)],
                  }))}
                >
                  Add Receipt Item
                </Button>
                <Button type="button" onClick={() => void handleCreateReceipt()} disabled={busyAction !== null}>
                  {busyAction === "create-receipt" ? "Creating..." : "Create Subcontracting Receipt"}
                </Button>
              </div>
            </div>
          ) : materialTransfers.length === 0 ? (
            <p className="text-sm text-gray-500">
              Record a material transfer first so subcontracting receipts can retain transfer lineage.
            </p>
          ) : null}

          {loading ? (
            <p className="text-sm text-gray-500">Loading subcontracting receipts...</p>
          ) : receipts.length === 0 ? (
            <p className="text-sm text-gray-500">No subcontracting receipts recorded for this PO yet.</p>
          ) : (
            <div className="space-y-3">
              {receipts.map((receipt) => (
                <div key={receipt.id} className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{receipt.name}</div>
                      <div className="mt-1 text-sm text-gray-500">
                        {receipt.receipt_date} • {receipt.set_warehouse}
                      </div>
                    </div>
                    <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {receipt.status}
                    </span>
                  </div>

                  <p className="mt-3 text-sm text-gray-700">{summarizeReceiptItems(receipt.items)}</p>
                  <p className="mt-2 text-sm text-gray-500">
                    Linked transfers: {receipt.material_transfer_refs.length > 0
                      ? receipt.material_transfer_refs
                        .map((reference) => transferNamesById.get(reference.material_transfer_id) ?? reference.material_transfer_id)
                        .join(", ")
                      : "None"}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {receipt.inventory_mutated ? "Inventory impact recorded." : "Inventory mutation still pending submission."}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {receipt.status === "draft" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => void runAction(`submit-receipt-${receipt.id}`, async () => {
                          await submitSubcontractingReceipt(receipt.id);
                          setSuccessMessage(`Submitted ${receipt.name}.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Submit Receipt
                      </Button>
                    ) : null}
                    {receipt.status !== "cancelled" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => void runAction(`cancel-receipt-${receipt.id}`, async () => {
                          await cancelSubcontractingReceipt(receipt.id);
                          setSuccessMessage(`Cancelled ${receipt.name}.`);
                        })}
                        disabled={busyAction !== null}
                      >
                        Cancel Receipt
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}