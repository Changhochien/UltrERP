import { useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useProductDetail } from "../hooks/useProductDetail";

interface ProductDetailProps {
  productId: string;
}

function ReorderBadge({ below }: { below: boolean }) {
  const { t } = useTranslation("common");
  if (!below) return null;
  return (
    <Badge
      role="status"
      aria-label={t("inventory.productDetail.belowReorderPoint")}
      variant="destructive"
      className="normal-case tracking-normal"
    >
      {t("inventory.productDetail.belowReorderPoint")}
    </Badge>
  );
}

export function ProductDetail({ productId }: ProductDetailProps) {
  const { t } = useTranslation("common");
  const { product, loading, error, reload } = useProductDetail(productId);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string | null>(null);

  if (loading) return <div aria-busy="true">{t("inventory.productDetail.loading")}</div>;
  if (error)
    return (
      <div role="alert" className="space-y-3">
        <p className="text-sm text-destructive">{t("inventory.productDetail.error", { message: error })}</p>
        <Button type="button" variant="outline" onClick={() => void reload()}>
          {t("inventory.productDetail.retry")}
        </Button>
      </div>
    );
  if (!product) return null;

  const filteredWarehouses = selectedWarehouse
    ? product.warehouses.filter((w) => w.warehouse_id === selectedWarehouse)
    : product.warehouses;

  return (
    <article aria-label={`Product detail: ${product.name}`} className="space-y-5">
      <SectionCard
        title={product.name}
        description={product.category ? t("inventory.productDetail.category", { category: product.category }) : t("inventory.productDetail.productDescription")}
      >
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={product.status === "active" ? "success" : "outline"} className="normal-case tracking-normal">
            {product.status}
          </Badge>
          <Badge variant="outline" className="normal-case tracking-normal">
            {t("inventory.productDetail.code", { code: product.code })}
          </Badge>
          <Badge variant="outline" className="normal-case tracking-normal">
            {t("inventory.productDetail.totalStock", { stock: product.total_stock })}
          </Badge>
        </div>
      </SectionCard>

      <SectionCard title={t("inventory.productDetail.stockByWarehouse.title")} description={t("inventory.productDetail.stockByWarehouse.description")}>
        <DataTable
          columns={[
            {
              id: "warehouse_name",
              header: t("inventory.productDetail.stockByWarehouse.warehouse"),
              sortable: true,
              getSortValue: (warehouse) => warehouse.warehouse_name,
              cell: (warehouse) => warehouse.warehouse_name,
            },
            {
              id: "current_stock",
              header: t("inventory.productDetail.stockByWarehouse.quantity"),
              sortable: true,
              getSortValue: (warehouse) => warehouse.current_stock,
              className: "text-right",
              headerClassName: "text-right",
              cell: (warehouse) => warehouse.current_stock,
            },
            {
              id: "reorder_point",
              header: t("inventory.productDetail.stockByWarehouse.reorderPoint"),
              sortable: true,
              getSortValue: (warehouse) => warehouse.reorder_point,
              className: "text-right",
              headerClassName: "text-right",
              cell: (warehouse) => warehouse.reorder_point,
            },
            {
              id: "status",
              header: t("inventory.productDetail.stockByWarehouse.status"),
              cell: (warehouse) => <ReorderBadge below={warehouse.is_below_reorder} />,
            },
            {
              id: "last_adjusted",
              header: t("inventory.productDetail.stockByWarehouse.lastAdjusted"),
              sortable: true,
              getSortValue: (warehouse) => warehouse.last_adjusted ?? "",
              cell: (warehouse) => warehouse.last_adjusted
                ? new Date(warehouse.last_adjusted).toLocaleDateString()
                : "—",
            },
          ]}
          data={filteredWarehouses}
          emptyTitle={t("inventory.productDetail.stockByWarehouse.noRecords")}
          emptyDescription={t("inventory.productDetail.stockByWarehouse.noMatch")}
          toolbar={product.warehouses.length > 1 ? (
            <DataTableToolbar>
              <div className="text-sm text-muted-foreground">{t("inventory.productDetail.stockByWarehouse.filterLabel")}</div>
              <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
                <span>{t("inventory.productDetail.stockByWarehouse.warehouseLabel")}</span>
                <select
                  id="wh-toggle"
                  value={selectedWarehouse ?? ""}
                  onChange={(e) => setSelectedWarehouse(e.target.value || null)}
                  className="w-full sm:w-48"
                >
                  <option value="">{t("inventory.productDetail.stockByWarehouse.allWarehouses")}</option>
                  {product.warehouses.map((warehouse) => (
                    <option key={warehouse.warehouse_id} value={warehouse.warehouse_id}>
                      {warehouse.warehouse_name}
                    </option>
                  ))}
                </select>
              </label>
            </DataTableToolbar>
          ) : undefined}
          getRowId={(warehouse) => warehouse.warehouse_id}
        />
      </SectionCard>

      <SectionCard title={t("inventory.productDetail.adjustmentHistory.title")} description={t("inventory.productDetail.adjustmentHistory.description")}>
        <DataTable
          columns={[
            {
              id: "created_at",
              header: t("inventory.productDetail.adjustmentHistory.date"),
              sortable: true,
              getSortValue: (item) => item.created_at,
              cell: (item) => new Date(item.created_at).toLocaleString(),
            },
            {
              id: "quantity_change",
              header: t("inventory.productDetail.adjustmentHistory.change"),
              sortable: true,
              getSortValue: (item) => item.quantity_change,
              className: "text-right",
              headerClassName: "text-right",
              cell: (item) => (
                <span className={item.quantity_change < 0 ? "text-destructive" : "text-success-token"}>
                  {item.quantity_change > 0 ? "+" : ""}
                  {item.quantity_change}
                </span>
              ),
            },
            { id: "reason_code", header: t("inventory.productDetail.adjustmentHistory.reason"), sortable: true, getSortValue: (item) => item.reason_code, cell: (item) => item.reason_code },
            { id: "actor_id", header: t("inventory.productDetail.adjustmentHistory.actor"), sortable: true, getSortValue: (item) => item.actor_id, cell: (item) => item.actor_id },
            { id: "notes", header: t("inventory.productDetail.adjustmentHistory.notes"), cell: (item) => item.notes ?? "—" },
          ]}
          data={product.adjustment_history}
          emptyTitle={t("inventory.productDetail.adjustmentHistory.noHistory")}
          emptyDescription={t("inventory.productDetail.adjustmentHistory.noHistoryDescription")}
          getRowId={(item) => item.id}
        />
      </SectionCard>
    </article>
  );
}
