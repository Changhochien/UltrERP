import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { useWarehouses } from "../../domain/inventory/hooks/useWarehouses";
import type { PhysicalCountSessionSummary } from "../../domain/inventory/types";
import { countSessionStatusVariant } from "../../domain/inventory/utils";
import {
  createPhysicalCountSession,
  fetchPhysicalCountSessions,
} from "../../lib/api/inventory";
import {
  buildCountSessionDetailPath,
} from "../../lib/routes";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

export function CountSessionsPage() {
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { warehouses, loading: warehousesLoading } = useWarehouses();
  const inventoryTabs = buildInventorySectionTabs(t);

  const [sessions, setSessions] = useState<PhysicalCountSessionSummary[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedWarehouseId && warehouses.length > 0) {
      setSelectedWarehouseId(warehouses[0].id);
    }
  }, [selectedWarehouseId, warehouses]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchPhysicalCountSessions({
      warehouseId: selectedWarehouseId || undefined,
      status: statusFilter || undefined,
      limit: 100,
    })
      .then((result) => {
        if (cancelled) {
          return;
        }
        if (!result.ok) {
          setSessions([]);
          setError(result.error);
          return;
        }
        setSessions(result.data.items);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setSessions([]);
          setError(loadError instanceof Error ? loadError.message : t("inventory.countSessionsPage.loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedWarehouseId, statusFilter, t]);

  const totalLabel = useMemo(() => t("inventory.countSessionsPage.total", { count: sessions.length }), [sessions.length, t]);

  async function handleCreateSession() {
    if (!selectedWarehouseId) {
      return;
    }
    setCreating(true);
    setError(null);
    const result = await createPhysicalCountSession({ warehouse_id: selectedWarehouseId });
    setCreating(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    navigate(buildCountSessionDetailPath(result.data.id));
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("inventoryCountSessions.label") }]}
        eyebrow={t("inventory.countSessionsPage.eyebrow")}
        title={t("inventory.countSessionsPage.title")}
        description={t("inventory.countSessionsPage.description")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              onClick={() => void handleCreateSession()}
              disabled={creating || !selectedWarehouseId || warehousesLoading}
            >
              {creating ? t("inventory.countSessionsPage.creating") : t("inventory.countSessionsPage.create")}
            </Button>
          </div>
        )}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="count-sessions"
            ariaLabel={t("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      <SectionCard title={t("inventory.countSessionsPage.filtersTitle")} description={t("inventory.countSessionsPage.filtersDescription")}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm font-medium">
            <span>{t("inventory.countSessionsPage.warehouseLabel")}</span>
            <select
              value={selectedWarehouseId}
              onChange={(event) => setSelectedWarehouseId(event.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2"
            >
              <option value="">{t("countSessionsPage.allWarehouses")}</option>
              {warehouses.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm font-medium">
            <span>{t("inventory.countSessionsPage.statusLabel")}</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2"
            >
              <option value="">{t("inventory.countSessionsPage.allStatuses")}</option>
              <option value="in_progress">{t("inventory.countSessionsPage.status.in_progress")}</option>
              <option value="submitted">{t("inventory.countSessionsPage.status.submitted")}</option>
              <option value="approved">{t("inventory.countSessionsPage.status.approved")}</option>
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard
        title={t("inventory.countSessionsPage.directoryTitle")}
        description={t("inventory.countSessionsPage.directoryDescription")}
        actions={<div className="text-sm text-muted-foreground">{totalLabel}</div>}
      >
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {loading ? (
          <p className="text-sm text-muted-foreground">{t("inventory.countSessionsPage.loading")}</p>
        ) : sessions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
            <p className="font-medium">{t("inventory.countSessionsPage.empty")}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t("inventory.countSessionsPage.emptyDescription")}</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <table className="min-w-full divide-y divide-border/70 text-sm">
              <thead className="bg-muted/30 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.warehouse")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.status")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.counted")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.variance")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.created")}</th>
                  <th className="px-4 py-3 font-medium">{t("inventory.countSessionsPage.columns.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td className="px-4 py-3 font-medium">{session.warehouse_name ?? t("inventory.countSessionsPage.unknownWarehouse")}</td>
                    <td className="px-4 py-3">
                      <Badge variant={countSessionStatusVariant(session.status)} className="normal-case tracking-normal">
                        {t(`inventory.countSessionsPage.status.${session.status}`)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">{t("inventory.countSessionsPage.countedProgress", { counted: session.counted_lines, total: session.total_lines })}</td>
                    <td className="px-4 py-3 font-mono">{session.variance_total}</td>
                    <td className="px-4 py-3">{session.created_at.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(buildCountSessionDetailPath(session.id))}
                      >
                        {t("inventory.countSessionsPage.open")}
                      </Button>
                    </td>
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
