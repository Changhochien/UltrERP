import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { WarehouseSelector } from "../../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../../domain/inventory/context/WarehouseContext";
import { useBelowReorderReport } from "../../domain/inventory/hooks/useBelowReorderReport";
import { exportBelowReorderReport } from "../../lib/api/inventory";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function BelowReorderReportWorkspace() {
  const { t } = useTranslation("common", { keyPrefix: "inventory.belowReorderReportPage" });
  const { t: tCommon } = useTranslation("common");
  const navigate = useNavigate();
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const inventoryTabs = buildInventorySectionTabs(tCommon);
  const { items, total, loading, error } = useBelowReorderReport({
    warehouseId: selectedWarehouse?.id,
  });
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const totalShortage = useMemo(
    () => items.reduce((sum, item) => sum + item.shortage_qty, 0),
    [items],
  );

  async function handleExport() {
    setExporting(true);
    setExportError(null);
    const result = await exportBelowReorderReport({ warehouseId: selectedWarehouse?.id });
    if (!result.ok) {
      setExportError(result.message);
    }
    setExporting(false);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tCommon("routes.belowReorderReport.label") }]}
        eyebrow={t("eyebrow")}
        title={t("title")}
        description={t("description")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <WarehouseSelector value={selectedWarehouse} onChange={setSelectedWarehouse} />
            <Button type="button" onClick={() => void handleExport()} disabled={exporting}>
              {exporting ? t("exporting") : t("exportCsv")}
            </Button>
          </div>
        )}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="below-reorder"
            ariaLabel={tCommon("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}
      {exportError ? <SurfaceMessage tone="danger">{exportError}</SurfaceMessage> : null}

      <SectionCard
        title={t("previewTitle")}
        description={t("previewDescription")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="normal-case tracking-normal">
              {t("totalRows", { count: total })}
            </Badge>
            <Badge variant="warning" className="normal-case tracking-normal">
              {t("totalShortage", { count: totalShortage })}
            </Badge>
          </div>
        )}
      >
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("loading")}</p>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
            <p className="font-medium">{t("empty")}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t("emptyDescription")}</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <table className="min-w-full divide-y divide-border/70 text-sm">
              <thead className="bg-muted/30 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">{t("col.productCode")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.productName")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.category")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.warehouse")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.currentStock")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.reorderPoint")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.shortageQty")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.onOrderQty")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.inTransitQty")}</th>
                  <th className="px-4 py-3 font-medium">{t("col.defaultSupplier")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {items.map((item) => (
                  <tr key={`${item.product_id}:${item.warehouse_id}`}>
                    <td className="px-4 py-3">{item.product_code}</td>
                    <td className="px-4 py-3 font-medium">{item.product_name}</td>
                    <td className="px-4 py-3">{item.category ?? ""}</td>
                    <td className="px-4 py-3">{item.warehouse_name}</td>
                    <td className="px-4 py-3">{item.current_stock}</td>
                    <td className="px-4 py-3">{item.reorder_point}</td>
                    <td className="px-4 py-3">{item.shortage_qty}</td>
                    <td className="px-4 py-3">{item.on_order_qty}</td>
                    <td className="px-4 py-3">{item.in_transit_qty}</td>
                    <td className="px-4 py-3">{item.default_supplier ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}

export function BelowReorderReportPage() {
  return (
    <WarehouseProvider>
      <BelowReorderReportWorkspace />
    </WarehouseProvider>
  );
}
