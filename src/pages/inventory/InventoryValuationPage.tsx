import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { WarehouseSelector } from "../../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../../domain/inventory/context/WarehouseContext";
import { useInventoryValuation } from "../../domain/inventory/hooks/useInventoryValuation";
import type { InventoryValuationItem } from "../../domain/inventory/types";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function CostSourceBadge({ source }: { source: InventoryValuationItem["cost_source"] }) {
  const { t } = useTranslation("inventory");
  const variant = source === "standard_cost"
    ? "success"
    : source === "latest_purchase"
      ? "warning"
      : "outline";

  return (
    <Badge variant={variant} className="normal-case tracking-normal">
      {t(`costSource.${source}`)}
    </Badge>
  );
}

function InventoryValuationWorkspace() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const inventoryTabs = buildInventorySectionTabs(t);
  const {
    items,
    warehouseTotals,
    grandTotalValue,
    grandTotalQuantity,
    totalRows,
    loading,
    error,
  } = useInventoryValuation({
    warehouseId: selectedWarehouse?.id,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("inventoryValuation.label") }]}
        eyebrow={t("inventory.inventoryValuationPage.eyebrow")}
        title={t("inventory.inventoryValuationPage.title")}
        description={t("inventory.inventoryValuationPage.description")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <WarehouseSelector value={selectedWarehouse} onChange={setSelectedWarehouse} />
          </div>
        )}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="valuation"
            ariaLabel={t("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

      <SectionCard
        title={t("inventory.inventoryValuationPage.summaryTitle")}
        description={t("inventory.inventoryValuationPage.summaryDescription")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="normal-case tracking-normal">
              {t("totalRows", { count: totalRows })}
            </Badge>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t("grandTotalQuantity", { count: grandTotalQuantity })}
            </Badge>
            <Badge variant="success" className="normal-case tracking-normal">
              {t("grandTotalValue", { value: grandTotalValue })}
            </Badge>
          </div>
        )}
      >
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("inventory.inventoryValuationPage.loading")}</p>
        ) : totalRows === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
            <p className="font-medium">{t("inventory.inventoryValuationPage.empty")}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t("inventory.inventoryValuationPage.emptyDescription")}</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border/70 bg-card/60 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("inventory.inventoryValuationPage.grandTotalValueLabel")}
              </p>
              <p className="mt-2 text-2xl font-semibold">{grandTotalValue}</p>
            </div>
            <div className="rounded-xl border border-border/70 bg-card/60 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("inventory.inventoryValuationPage.grandTotalQuantityLabel")}
              </p>
              <p className="mt-2 text-2xl font-semibold">{grandTotalQuantity}</p>
            </div>
            <div className="rounded-xl border border-border/70 bg-card/60 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("inventory.inventoryValuationPage.rowCountLabel")}
              </p>
              <p className="mt-2 text-2xl font-semibold">{totalRows}</p>
            </div>
          </div>
        )}
      </SectionCard>

      {!loading && totalRows > 0 ? (
        <SectionCard title={t("inventory.inventoryValuationPage.warehouseTotalsTitle")} description={t("inventory.inventoryValuationPage.warehouseTotalsDescription")}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {warehouseTotals.map((warehouseTotal) => (
              <div key={warehouseTotal.warehouse_id} className="rounded-xl border border-border/70 bg-card/60 p-4">
                <p className="text-sm font-semibold">{warehouseTotal.warehouse_name}</p>
                <p className="mt-2 text-2xl font-semibold">{warehouseTotal.total_value}</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t("subtotalQuantity", { count: warehouseTotal.total_quantity })}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t("subtotalRows", { count: warehouseTotal.row_count })}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}

      {!loading && totalRows > 0 ? (
        <SectionCard title={t("inventory.inventoryValuationPage.tableTitle")} description={t("inventory.inventoryValuationPage.tableDescription")}>
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <table className="min-w-full divide-y divide-border/70 text-sm">
              <thead className="bg-muted/30 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.productCode")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.productName")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.category")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.warehouse")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.quantity")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.unitCost")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.extendedValue")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.inventoryValuationPage.col.costSource")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {items.map((item) => (
                  <tr key={`${item.product_id}:${item.warehouse_id}`}>
                    <td className="px-4 py-3">{item.product_code}</td>
                    <td className="px-4 py-3 font-medium">{item.product_name}</td>
                    <td className="px-4 py-3">{item.category ?? ""}</td>
                    <td className="px-4 py-3">{item.warehouse_name}</td>
                    <td className="px-4 py-3">{item.quantity}</td>
                    <td className="px-4 py-3">{item.unit_cost ?? "-"}</td>
                    <td className="px-4 py-3">{item.extended_value}</td>
                    <td className="px-4 py-3">
                      <CostSourceBadge source={item.cost_source} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}

export function InventoryValuationPage() {
  return (
    <WarehouseProvider>
      <InventoryValuationWorkspace />
    </WarehouseProvider>
  );
}
