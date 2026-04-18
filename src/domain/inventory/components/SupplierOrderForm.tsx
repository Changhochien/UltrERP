/** Form to create a new supplier order with dynamic line items. */

import { useEffect, useMemo, useRef, useState } from "react";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { ProductCombobox } from "../../../components/products/ProductCombobox";
import { fetchProductSupplier } from "../../../lib/api/inventory";
import { SupplierCombobox } from "./SupplierCombobox";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useCreateSupplierOrder,
} from "../hooks/useSupplierOrders";
import type { ProductSupplierInfo } from "../types";

interface OrderLine {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  unit_cost: string;
}

export interface SupplierOrderDraftLine {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  unit_cost?: string;
}

interface SupplierOrderFormProps {
  onCreated: (orderId: string) => void;
  onCancel: () => void;
  initialSupplierId?: string;
  initialOrderDate?: string;
  initialExpectedArrivalDate?: string;
  initialLines?: SupplierOrderDraftLine[];
}

function emptyLine(): OrderLine {
  return { product_id: "", warehouse_id: "", quantity: 1, unit_cost: "" };
}

function hydrateLine(line: SupplierOrderDraftLine): OrderLine {
  return {
    product_id: line.product_id,
    warehouse_id: line.warehouse_id,
    quantity: line.quantity,
    unit_cost: line.unit_cost ?? "",
  };
}

export function SupplierOrderForm({
  onCreated,
  onCancel,
  initialSupplierId = "",
  initialOrderDate,
  initialExpectedArrivalDate = "",
  initialLines,
}: SupplierOrderFormProps) {
  const { warehouses, loading: whLoading } = useWarehouses();
  const { create, submitting, error } = useCreateSupplierOrder();

  const [supplierId, setSupplierId] = useState(initialSupplierId);
  const [orderDate, setOrderDate] = useState(
    () => initialOrderDate ?? new Date().toISOString().slice(0, 10),
  );
  const [expectedArrival, setExpectedArrival] = useState(initialExpectedArrivalDate);
  const [lines, setLines] = useState<OrderLine[]>(
    () => initialLines?.length ? initialLines.map(hydrateLine) : [emptyLine()],
  );
  const [supplierResolutionMessage, setSupplierResolutionMessage] = useState<string | null>(null);
  const autoResolvedSupplierId = useRef("");

  const selectedProductIds = useMemo(
    () => Array.from(new Set(lines.map((line) => line.product_id).filter(Boolean))),
    [lines],
  );
  const selectedProductKey = selectedProductIds.join("|");

  useEffect(() => {
    setSupplierId(initialSupplierId);
    setOrderDate(initialOrderDate ?? new Date().toISOString().slice(0, 10));
    setExpectedArrival(initialExpectedArrivalDate);
    setLines(initialLines?.length ? initialLines.map(hydrateLine) : [emptyLine()]);
    autoResolvedSupplierId.current = initialSupplierId;
    setSupplierResolutionMessage(null);
  }, [initialExpectedArrivalDate, initialLines, initialOrderDate, initialSupplierId]);

  useEffect(() => {
    if (initialSupplierId) {
      return;
    }

    let cancelled = false;

    async function resolveSupplierPrefill() {
      if (selectedProductIds.length === 0) {
        setSupplierResolutionMessage(null);
        setSupplierId((current) => (current === autoResolvedSupplierId.current ? "" : current));
        autoResolvedSupplierId.current = "";
        return;
      }

      try {
        const rawResults = await Promise.all(selectedProductIds.map((productId) => fetchProductSupplier(productId)));
        if (cancelled) {
          return;
        }

        const results = rawResults.map((result) => {
          if (result && typeof result === "object" && "ok" in result) {
            return result;
          }
          return { ok: false as const, error: "Failed to fetch product supplier" };
        });

        const resolvedSuppliers = results
          .filter((result): result is { ok: true; data: ProductSupplierInfo } => result.ok && result.data != null)
          .map((result) => result.data);
        const uniqueSupplierIds = Array.from(new Set(resolvedSuppliers.map((supplier) => supplier.supplier_id)));
        const hasMissingSupplier = results.some((result) => !result.ok || (result.ok && result.data == null));
        const resolvedSupplierId = !hasMissingSupplier && uniqueSupplierIds.length === 1 ? uniqueSupplierIds[0] : null;

        if (resolvedSupplierId) {
          setSupplierResolutionMessage(null);
          setSupplierId((current) => {
            if (current === "" || current === autoResolvedSupplierId.current) {
              autoResolvedSupplierId.current = resolvedSupplierId;
              return resolvedSupplierId;
            }
            return current;
          });
          return;
        }

        setSupplierId((current) => {
          if (current === autoResolvedSupplierId.current) {
            return "";
          }
          return current;
        });
        autoResolvedSupplierId.current = "";

        if (uniqueSupplierIds.length > 1) {
          setSupplierResolutionMessage("Selected products have different default suppliers. Choose one manually.");
        } else if (selectedProductIds.length > 1 && hasMissingSupplier) {
          setSupplierResolutionMessage("Selected products do not resolve to one supplier. Choose one manually.");
        } else {
          setSupplierResolutionMessage(null);
        }
      } catch {
        setSupplierResolutionMessage(null);
      }
    }

    void resolveSupplierPrefill();
    return () => {
      cancelled = true;
    };
  }, [initialSupplierId, selectedProductKey]);

  if (whLoading) return <p aria-busy="true">Loading…</p>;

  const updateLine = (idx: number, patch: Partial<OrderLine>) => {
    setLines((prev) =>
      prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)),
    );
  };

  const removeLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const validLines = lines.filter(
    (l) => l.product_id && l.warehouse_id && l.quantity > 0,
  );
  const canSubmit = supplierId && orderDate && validLines.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await create({
      supplier_id: supplierId,
      order_date: orderDate,
      expected_arrival_date: expectedArrival || undefined,
      lines: validLines.map((l) => {
        const normalizedUnitPrice = l.unit_cost.trim();

        return {
          product_id: l.product_id,
          warehouse_id: l.warehouse_id,
          quantity_ordered: l.quantity,
          unit_price: normalizedUnitPrice === "" ? undefined : Number(normalizedUnitPrice),
        };
      }),
    });
    if (result) onCreated(result.id);
  };

  return (
    <section aria-label="Create supplier order" className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight">New Supplier Order</h2>
        <p className="text-sm text-muted-foreground">Create a supplier PO with warehouse-specific receiving lines.</p>
      </div>

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

      <form onSubmit={(e) => void handleSubmit(e)} aria-label="Order form" className="space-y-6">
        <SectionCard title="Order Header" description="Supplier and expected arrival details for the purchase order.">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label className="space-y-2">
              <span>Supplier</span>
              <SupplierCombobox
                inputId="so-supplier"
                value={supplierId}
                onChange={setSupplierId}
                onClear={() => setSupplierId("")}
                placeholder="Search supplier…"
                ariaLabel="Supplier"
              />
            </label>

            {supplierResolutionMessage ? (
              <SurfaceMessage tone="warning" className="md:col-span-2 xl:col-span-3">
                {supplierResolutionMessage}
              </SurfaceMessage>
            ) : null}

            <label className="space-y-2">
              <span>Order date</span>
              <Input
                id="so-date"
                type="date"
                required
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
              />
            </label>

            <label className="space-y-2">
              <span>Expected arrival</span>
              <Input
                id="so-arrival"
                type="date"
                value={expectedArrival}
                onChange={(e) => setExpectedArrival(e.target.value)}
              />
            </label>
          </div>
        </SectionCard>

        <SectionCard title="Order Lines" description="Warehouse-scoped line items for the supplier order.">
          <div className="overflow-x-auto rounded-2xl border border-border/80 bg-card/90 shadow-sm">
            <Table aria-label="Order line items" className="min-w-[640px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Warehouse</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Unit Cost</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {lines.map((line, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <ProductCombobox
                        value={line.product_id}
                        onChange={(id) => updateLine(idx, { product_id: id })}
                        placeholder="Search product…"
                        ariaLabel={`Line ${idx + 1} product`}
                      />
                    </TableCell>
                    <TableCell>
                      <select
                        required
                        value={line.warehouse_id}
                        onChange={(e) => updateLine(idx, { warehouse_id: e.target.value })}
                        aria-label={`Line ${idx + 1} warehouse`}
                      >
                        <option value="">Select</option>
                        {warehouses.map((warehouse) => (
                          <option key={warehouse.id} value={warehouse.id}>
                            {warehouse.name}
                          </option>
                        ))}
                      </select>
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        required
                        min={1}
                        value={line.quantity}
                        onChange={(e) => updateLine(idx, { quantity: Number(e.target.value) })}
                        aria-label={`Line ${idx + 1} quantity`}
                        className="w-24"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={line.unit_cost}
                        onChange={(e) => updateLine(idx, { unit_cost: e.target.value })}
                        aria-label={`Line ${idx + 1} unit cost`}
                        className="w-28"
                      />
                    </TableCell>
                    <TableCell>
                      {lines.length > 1 ? (
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeLine(idx)} aria-label={`Remove line ${idx + 1}`}>
                          Remove
                        </Button>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4">
            <Button type="button" variant="outline" onClick={() => setLines((prev) => [...prev, emptyLine()])}>
              Add Line
            </Button>
          </div>
        </SectionCard>

        <div className="flex gap-3">
          <Button type="submit" disabled={!canSubmit || submitting}>
            {submitting ? "Creating…" : "Create Order"}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </section>
  );
}
