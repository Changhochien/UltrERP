import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { SupplierOrderForm, type SupplierOrderDraftLine } from "../../domain/inventory/components/SupplierOrderForm";
import { WarehouseSelector } from "../../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../../domain/inventory/context/WarehouseContext";
import {
  useCreateReorderSuggestionOrders,
  useReorderSuggestions,
} from "../../domain/inventory/hooks/useReorderSuggestions";
import type {
  ReorderSuggestionCreatedOrder,
  ReorderSuggestionItem,
} from "../../domain/inventory/types";
import { usePermissions } from "../../hooks/usePermissions";
import { INVENTORY_ROUTE } from "../../lib/routes";

function selectionKey(item: ReorderSuggestionItem): string {
  return `${item.product_id}:${item.warehouse_id}`;
}

function toOrderRequest(item: ReorderSuggestionItem) {
  return {
    product_id: item.product_id,
    warehouse_id: item.warehouse_id,
    suggested_qty: item.suggested_qty,
  };
}

function toDraftLines(rows: ReorderSuggestionItem[]): SupplierOrderDraftLine[] {
  return rows.map((row) => ({
    product_id: row.product_id,
    warehouse_id: row.warehouse_id,
    quantity: row.suggested_qty,
    unit_cost: row.supplier_hint?.unit_cost ?? "",
  }));
}

function CreatedOrdersSummary({
  orders,
}: {
  orders: ReorderSuggestionCreatedOrder[];
}) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.reorderSuggestionsPage" });

  if (orders.length === 0) {
    return null;
  }

  return (
    <SurfaceMessage tone="success">
      <div className="space-y-2">
        <p className="font-medium">{t("createdOrdersSummary", { count: orders.length })}</p>
        <div className="flex flex-wrap gap-2">
          {orders.map((order) => (
            <Badge key={order.order_id} variant="success" className="normal-case tracking-normal">
              {order.order_number} · {order.supplier_name}
            </Badge>
          ))}
        </div>
      </div>
    </SurfaceMessage>
  );
}

function ReorderSuggestionsWorkspace() {
  const { t } = useTranslation("common", { keyPrefix: "inventory.reorderSuggestionsPage" });
  const navigate = useNavigate();
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const { canWrite } = usePermissions();
  const { suggestions, total, loading, error, reload } = useReorderSuggestions({
    warehouseId: selectedWarehouse?.id,
  });
  const {
    create,
    submitting,
    error: createError,
  } = useCreateReorderSuggestionOrders();

  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [createdOrders, setCreatedOrders] = useState<ReorderSuggestionCreatedOrder[]>([]);
  const [unresolvedRows, setUnresolvedRows] = useState<ReorderSuggestionItem[]>([]);
  const [manualDraftRows, setManualDraftRows] = useState<ReorderSuggestionItem[] | null>(null);

  const writable = canWrite("inventory");
  const selectableRows = useMemo(
    () => suggestions.filter((item) => item.suggested_qty > 0),
    [suggestions],
  );
  const selectedRows = useMemo(
    () => suggestions.filter((item) => selectedKeys.includes(selectionKey(item))),
    [selectedKeys, suggestions],
  );

  useEffect(() => {
    setSelectedKeys((current) =>
      current.filter((key) => suggestions.some((item) => selectionKey(item) === key)),
    );
  }, [suggestions]);

  async function submitRows(
    rows: ReorderSuggestionItem[],
    options?: { openManualDraft?: boolean },
  ) {
    const payloadRows = rows.filter((row) => row.suggested_qty > 0);
    if (payloadRows.length === 0) {
      return;
    }

    const result = await create({
      items: payloadRows.map(toOrderRequest),
    });
    if (!result) {
      return;
    }

    setCreatedOrders(result.created_orders);
    setUnresolvedRows(result.unresolved_rows);
    setSelectedKeys([]);

    if (
      options?.openManualDraft &&
      result.created_orders.length === 0 &&
      result.unresolved_rows.length > 0
    ) {
      setManualDraftRows(result.unresolved_rows);
    }

    if (result.unresolved_rows.length === 0) {
      setManualDraftRows(null);
    }

    await reload();
  }

  const allSelected = selectableRows.length > 0 && selectedRows.length === selectableRows.length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={t("title")}
        description={t("description")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <WarehouseSelector value={selectedWarehouse} onChange={setSelectedWarehouse} />
            <Button type="button" variant="outline" onClick={() => navigate(INVENTORY_ROUTE)}>
              {t("backToInventory")}
            </Button>
          </div>
        )}
      />

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}
      {createError ? <SurfaceMessage tone="danger">{createError}</SurfaceMessage> : null}
      <CreatedOrdersSummary orders={createdOrders} />

      <SectionCard
        title={t("listTitle")}
        description={t("listDescription")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="normal-case tracking-normal">
              {t("total", { count: total })}
            </Badge>
            {writable ? (
              <>
                <Badge variant="secondary" className="normal-case tracking-normal">
                  {t("selectedCount", { count: selectedRows.length })}
                </Badge>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void submitRows(selectedRows)}
                  disabled={selectedRows.length === 0 || submitting}
                >
                  {submitting ? t("creating") : t("createSelected")}
                </Button>
              </>
            ) : null}
          </div>
        )}
      >
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("loading")}</p>
        ) : suggestions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
            <p className="font-medium">{t("empty")}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t("emptyDescription")}</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <table className="min-w-full divide-y divide-border/70 text-sm">
              <thead className="bg-muted/30 text-left text-muted-foreground">
                <tr>
                  <th className="w-12 px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={t("selectAll")}
                      checked={allSelected}
                      onChange={(event) => {
                        setSelectedKeys(
                          event.target.checked
                            ? selectableRows.map(selectionKey)
                            : [],
                        );
                      }}
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">{t("col.product")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.warehouse")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.currentStock")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.inventoryPosition")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.reorderPoint")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.targetStock")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.suggestedQty")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.supplier")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {suggestions.map((item) => {
                  const rowKey = selectionKey(item);
                  const checked = selectedKeys.includes(rowKey);
                  const hasSupplier = Boolean(item.supplier_hint);
                  const rowDisabled = item.suggested_qty <= 0 || !writable;

                  return (
                    <tr key={rowKey}>
                      <td className="px-4 py-3 align-top">
                        <input
                          type="checkbox"
                          aria-label={t("selectRow", { product: item.product_name })}
                          checked={checked}
                          disabled={item.suggested_qty <= 0}
                          onChange={() => {
                            setSelectedKeys((current) =>
                              current.includes(rowKey)
                                ? current.filter((key) => key !== rowKey)
                                : [...current, rowKey],
                            );
                          }}
                        />
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-muted-foreground">{item.product_code}</div>
                      </td>
                      <td className="px-4 py-3 align-top">{item.warehouse_name}</td>
                      <td className="px-4 py-3 align-top">{item.current_stock}</td>
                      <td className="px-4 py-3 align-top">{item.inventory_position}</td>
                      <td className="px-4 py-3 align-top">{item.reorder_point}</td>
                      <td className="px-4 py-3 align-top">{item.target_stock_qty}</td>
                      <td className="px-4 py-3 align-top">
                        <Badge variant={item.suggested_qty > 0 ? "warning" : "outline"} className="normal-case tracking-normal">
                          {item.suggested_qty}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 align-top">
                        {hasSupplier ? (
                          <div className="space-y-1">
                            <div className="font-medium">{item.supplier_hint?.supplier_name}</div>
                            <div className="text-xs text-muted-foreground">
                              {t("leadTimeDays", { count: item.supplier_hint?.default_lead_time_days ?? 0 })}
                            </div>
                          </div>
                        ) : (
                          <Badge variant="outline" className="normal-case tracking-normal">
                            {t("supplierMissing")}
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={rowDisabled || submitting}
                          onClick={() => void submitRows([item], { openManualDraft: true })}
                        >
                          {t("createDraft")}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {unresolvedRows.length > 0 ? (
        <SectionCard
          title={t("unresolvedTitle")}
          description={t("unresolvedDescription")}
          actions={(
            <Button type="button" variant="outline" onClick={() => setManualDraftRows(unresolvedRows)}>
              {t("openManualDraft")}
            </Button>
          )}
        >
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <table className="min-w-full divide-y divide-border/70 text-sm">
              <thead className="bg-muted/30 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">{t("col.product")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.warehouse")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.suggestedQty")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {unresolvedRows.map((item) => (
                  <tr key={selectionKey(item)}>
                    <td className="px-4 py-3">{item.product_name}</td>
                    <td className="px-4 py-3">{item.warehouse_name}</td>
                    <td className="px-4 py-3">{item.suggested_qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      ) : null}

      {manualDraftRows ? (
        <div className="rounded-2xl border border-border/80 bg-background p-6 shadow-sm">
          <SurfaceMessage className="mb-4">
            {t("manualDraftDescription")}
          </SurfaceMessage>
          <SupplierOrderForm
            initialLines={toDraftLines(manualDraftRows)}
            onCreated={async () => {
              setManualDraftRows(null);
              setUnresolvedRows([]);
              await reload();
            }}
            onCancel={() => setManualDraftRows(null)}
          />
        </div>
      ) : null}
    </div>
  );
}

export function ReorderSuggestionsPage() {
  return (
    <WarehouseProvider>
      <ReorderSuggestionsWorkspace />
    </WarehouseProvider>
  );
}