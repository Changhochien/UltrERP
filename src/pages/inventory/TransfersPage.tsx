import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ProductCombobox } from "@/domain/inventory/components/ProductCombobox";
import { PageHeader, PageTabs, SectionCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { usePermissions } from "@/hooks/usePermissions";
import { fetchTransferDetail, fetchTransferHistory } from "@/lib/api/inventory";
import { formatForDisplayWithTime } from "@/lib/time";

import { StockTransferForm } from "../../domain/inventory/components/StockTransferForm";
import { useWarehouses } from "../../domain/inventory/hooks/useWarehouses";
import type { TransferHistoryItem } from "../../domain/inventory/types";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function TransferMetadataRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null;
}) {
  return (
    <div className="space-y-1 rounded-lg border border-border/70 bg-muted/20 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium text-foreground">{value ?? "-"}</div>
    </div>
  );
}

export function TransfersPage() {
  const { t } = useTranslation("inventory");
  const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { canWrite } = usePermissions();
  const { warehouses, loading: warehousesLoading } = useWarehouses();
  const inventoryTabs = buildInventorySectionTabs(tRoutes);

  const [productId, setProductId] = useState(searchParams.get("productId") ?? "");
  const [warehouseId, setWarehouseId] = useState(searchParams.get("warehouseId") ?? "");
  const [items, setItems] = useState<TransferHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const [selectedTransferId, setSelectedTransferId] = useState<string | null>(null);
  const [selectedTransfer, setSelectedTransfer] = useState<TransferHistoryItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    setProductId(searchParams.get("productId") ?? "");
    setWarehouseId(searchParams.get("warehouseId") ?? "");
  }, [searchParams]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (productId) {
      params.set("productId", productId);
    }
    if (warehouseId) {
      params.set("warehouseId", warehouseId);
    }

    const nextQuery = params.toString();
    if (nextQuery !== searchParams.toString()) {
      setSearchParams(params, { replace: true });
    }
  }, [productId, searchParams, setSearchParams, warehouseId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchTransferHistory({
      productId: productId || undefined,
      warehouseId: warehouseId || undefined,
      limit: 100,
    })
      .then((result) => {
        if (cancelled) {
          return;
        }
        if (!result.ok) {
          setItems([]);
          setTotal(0);
          setError(result.error);
          return;
        }

        setItems(result.data.items);
        setTotal(result.data.total);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [productId, refreshKey, warehouseId]);

  useEffect(() => {
    if (!selectedTransferId) {
      setSelectedTransfer(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);

    fetchTransferDetail(selectedTransferId)
      .then((result) => {
        if (cancelled) {
          return;
        }

        if (!result.ok) {
          setSelectedTransfer(null);
          setDetailError(result.error);
          return;
        }

        setSelectedTransfer(result.data);
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTransferId]);

  const historyCountLabel = useMemo(
    () => t("historyCount", { count: total }),
    [t, total],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("inventoryTransfers.label") }]}
        eyebrow={t("transfersPage.eyebrow")}
        title={t("transfersPage.title")}
        description={t("transfersPage.description")}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="transfers"
            ariaLabel={t("page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {canWrite("inventory") ? (
        <SectionCard title={t("transfersPage.formTitle")} description={t("transfersPage.formDescription")}>
          <StockTransferForm
            defaultProductId={productId}
            defaultFromWarehouseId={warehouseId}
            onSuccess={(transfer) => {
              setRefreshKey((value) => value + 1);
              setSelectedTransferId(transfer.id);
            }}
          />
        </SectionCard>
      ) : (
        <SectionCard title={t("transfersPage.formTitle")} description={t("readOnly")} />
      )}

      <SectionCard
        title={t("transfersPage.historyTitle")}
        description={t("transfersPage.historyDescription")}
        actions={<div className="text-sm text-muted-foreground">{historyCountLabel}</div>}
      >
        <div className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_240px_auto]">
            <div className="space-y-2">
              <label id="transfer-history-product-label" className="block text-sm font-medium">
                {t("filters.product")}
              </label>
              <ProductCombobox
                value={productId}
                onChange={setProductId}
                onClear={() => setProductId("")}
                placeholder={t("filters.productPlaceholder")}
                ariaLabelledBy="transfer-history-product-label"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="transfer-history-warehouse" className="block text-sm font-medium">
                {t("filters.warehouse")}
              </label>
              <select
                id="transfer-history-warehouse"
                className="flex h-10 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm"
                value={warehouseId}
                onChange={(event) => setWarehouseId(event.target.value)}
                disabled={warehousesLoading}
              >
                <option value="">{t("filters.allWarehouses")}</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name} ({warehouse.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setProductId("");
                  setWarehouseId("");
                }}
                disabled={!productId && !warehouseId}
              >
                {t("filters.clear")}
              </Button>
            </div>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {loading ? (
            <p className="text-sm text-muted-foreground">{t("transfersPage.loading")}</p>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
              <p className="font-medium">{t("transfersPage.empty")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("transfersPage.emptyDescription")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/30 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.product")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.route")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.quantity")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.actor")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.notes")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.createdAt")}</th>
                    <th className="px-4 py-3 font-medium">{t("transfersPage.columns.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">{item.product_name}</div>
                        <div className="text-xs text-muted-foreground">{item.product_code}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-foreground">{item.from_warehouse_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {item.from_warehouse_code} → {item.to_warehouse_name} ({item.to_warehouse_code})
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="font-medium">
                          {item.quantity}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{item.actor_id}</td>
                      <td className="px-4 py-3 text-muted-foreground">{item.notes || t("transfersPage.emptyNote")}</td>
                      <td className="px-4 py-3">{formatForDisplayWithTime(item.created_at)}</td>
                      <td className="px-4 py-3">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedTransferId(item.id)}
                        >
                          {t("viewDetails")}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SectionCard>

      <Sheet open={selectedTransferId !== null} onOpenChange={(open) => {
        if (!open) {
          setSelectedTransferId(null);
        }
      }}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{t("detail.title")}</SheetTitle>
            <SheetDescription>{t("transfersPage.detail.description")}</SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-4">
            {detailLoading ? <p className="text-sm text-muted-foreground">{t("detail.loading")}</p> : null}
            {detailError ? <p className="text-sm text-destructive">{detailError}</p> : null}

            {!detailLoading && !detailError && selectedTransfer ? (
              <div className="grid gap-3">
                <TransferMetadataRow label={t("detail.fields.transferId")} value={selectedTransfer.id} />
                <TransferMetadataRow
                  label={t("transfersPage.detail.fields.product")}
                  value={`${selectedTransfer.product_name} (${selectedTransfer.product_code})`}
                />
                <TransferMetadataRow
                  label={t("transfersPage.detail.fields.fromWarehouse")}
                  value={`${selectedTransfer.from_warehouse_name} (${selectedTransfer.from_warehouse_code})`}
                />
                <TransferMetadataRow
                  label={t("transfersPage.detail.fields.toWarehouse")}
                  value={`${selectedTransfer.to_warehouse_name} (${selectedTransfer.to_warehouse_code})`}
                />
                <TransferMetadataRow label={t("transfersPage.detail.fields.quantity")} value={selectedTransfer.quantity} />
                <TransferMetadataRow label={t("transfersPage.detail.fields.actor")} value={selectedTransfer.actor_id} />
                <TransferMetadataRow label={t("transfersPage.detail.fields.notes")} value={selectedTransfer.notes || t("transfersPage.emptyNote")} />
                <TransferMetadataRow
                  label={t("transfersPage.detail.fields.createdAt")}
                  value={formatForDisplayWithTime(selectedTransfer.created_at)}
                />
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
