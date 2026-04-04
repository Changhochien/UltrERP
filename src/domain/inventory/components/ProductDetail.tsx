import { useState } from "react";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useProductDetail } from "../hooks/useProductDetail";

interface ProductDetailProps {
  productId: string;
}

function ReorderBadge({ below }: { below: boolean }) {
  if (!below) return null;
  return (
    <Badge
      role="status"
      aria-label="Below reorder point"
      variant="destructive"
      className="normal-case tracking-normal"
    >
      Below reorder point
    </Badge>
  );
}

export function ProductDetail({ productId }: ProductDetailProps) {
  const { product, loading, error, reload } = useProductDetail(productId);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string | null>(
    null,
  );

  if (loading) return <div aria-busy="true">Loading product details…</div>;
  if (error)
    return (
      <div role="alert" className="space-y-3">
        <p className="text-sm text-destructive">Error: {error}</p>
        <Button type="button" variant="outline" onClick={() => void reload()}>
          Retry
        </Button>
      </div>
    );
  if (!product) return null;

  const filteredWarehouses = selectedWarehouse
    ? product.warehouses.filter((w) => w.warehouse_id === selectedWarehouse)
    : product.warehouses;

  return (
    <article aria-label={`Product detail: ${product.name}`} className="space-y-5">
      <SectionCard title={product.name} description={product.category ? `Category: ${product.category}` : "Product stock detail and warehouse history."}>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={product.status === "active" ? "success" : "outline"} className="normal-case tracking-normal">
            {product.status}
          </Badge>
          <Badge variant="outline" className="normal-case tracking-normal">
            Code: {product.code}
          </Badge>
          <Badge variant="outline" className="normal-case tracking-normal">
            Total stock: {product.total_stock}
          </Badge>
        </div>
      </SectionCard>

      <SectionCard title="Stock by Warehouse" description="Current quantity, reorder posture, and most recent adjustment by warehouse.">
        <DataTable
          columns={[
            {
              id: "warehouse_name",
              header: "Warehouse",
              sortable: true,
              getSortValue: (warehouse) => warehouse.warehouse_name,
              cell: (warehouse) => warehouse.warehouse_name,
            },
            {
              id: "current_stock",
              header: "Quantity",
              sortable: true,
              getSortValue: (warehouse) => warehouse.current_stock,
              className: "text-right",
              headerClassName: "text-right",
              cell: (warehouse) => warehouse.current_stock,
            },
            {
              id: "reorder_point",
              header: "Reorder Point",
              sortable: true,
              getSortValue: (warehouse) => warehouse.reorder_point,
              className: "text-right",
              headerClassName: "text-right",
              cell: (warehouse) => warehouse.reorder_point,
            },
            {
              id: "status",
              header: "Status",
              cell: (warehouse) => <ReorderBadge below={warehouse.is_below_reorder} />,
            },
            {
              id: "last_adjusted",
              header: "Last Adjusted",
              sortable: true,
              getSortValue: (warehouse) => warehouse.last_adjusted ?? "",
              cell: (warehouse) => warehouse.last_adjusted
                ? new Date(warehouse.last_adjusted).toLocaleDateString()
                : "—",
            },
          ]}
          data={filteredWarehouses}
          emptyTitle="No stock records."
          emptyDescription="No warehouse stock records match the selected filter."
          toolbar={product.warehouses.length > 1 ? (
            <DataTableToolbar>
              <div className="text-sm text-muted-foreground">Filter warehouse-level stock records.</div>
              <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
                <span>Warehouse</span>
                <select
                  id="wh-toggle"
                  value={selectedWarehouse ?? ""}
                  onChange={(e) => setSelectedWarehouse(e.target.value || null)}
                  className="w-full sm:w-48"
                >
                  <option value="">All warehouses</option>
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

      <SectionCard title="Adjustment History" description="Chronological record of manual and system stock changes.">
        <DataTable
          columns={[
            {
              id: "created_at",
              header: "Date",
              sortable: true,
              getSortValue: (item) => item.created_at,
              cell: (item) => new Date(item.created_at).toLocaleString(),
            },
            {
              id: "quantity_change",
              header: "Change",
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
            { id: "reason_code", header: "Reason", sortable: true, getSortValue: (item) => item.reason_code, cell: (item) => item.reason_code },
            { id: "actor_id", header: "Actor", sortable: true, getSortValue: (item) => item.actor_id, cell: (item) => item.actor_id },
            { id: "notes", header: "Notes", cell: (item) => item.notes ?? "—" },
          ]}
          data={product.adjustment_history}
          emptyTitle="No adjustment history available."
          emptyDescription="Recorded stock changes for this product will appear here."
          getRowId={(item) => item.id}
        />
      </SectionCard>
    </article>
  );
}
