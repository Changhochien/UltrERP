import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import { createSupplier, setSupplierStatus } from "../../lib/api/inventory";
import {
  buildSupplierDetailPath,
} from "../../lib/routes";
import { SupplierForm, type SupplierFormFieldError } from "../../domain/inventory/components/SupplierForm";
import { useSuppliers } from "../../domain/inventory/hooks/useSuppliers";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function toFieldErrors(
  errors?: Array<{ field: string; message: string }>,
): SupplierFormFieldError[] | undefined {
  if (!errors?.length) {
    return undefined;
  }
  return errors.map((error) => ({ field: error.field, message: error.message }));
}

export function SuppliersPage() {
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const inventoryTabs = buildInventorySectionTabs(tRoutes);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [formKey, setFormKey] = useState(0);
  const [statusPendingId, setStatusPendingId] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const { suppliers, total, loading, error, reload } = useSuppliers({
    q: query.trim() || undefined,
    activeOnly: !showInactive,
    limit: 100,
  });

  async function handleToggleStatus(supplierId: string, isActive: boolean) {
    setStatusPendingId(supplierId);
    setStatusError(null);
    const result = await setSupplierStatus(supplierId, !isActive);
    setStatusPendingId(null);

    if (!result.ok) {
      setStatusError(result.error);
      return;
    }

    await reload();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("inventorySuppliers.label") }]}
        eyebrow={t("suppliersPage.eyebrow")}
        title={t("suppliersPage.title")}
        description={t("suppliersPage.description")}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="suppliers"
            ariaLabel={t("page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {canWrite("inventory") ? (
        <SectionCard title={t("suppliersPage.createTitle")} description={t("suppliersPage.formDescription")}>
          <SupplierForm
            key={formKey}
            submitLabel={t("suppliersPage.save")}
            submittingLabel={t("suppliersPage.saving")}
            onSubmit={async (values) => {
              const result = await createSupplier(values);
              if (result.ok) {
                return { ok: true, supplier: result.data };
              }
              return {
                ok: false,
                fieldErrors: toFieldErrors(result.errors),
                formError: result.error,
              };
            }}
            onSuccess={async () => {
              setFormKey((current) => current + 1);
              await reload();
            }}
          />
        </SectionCard>
      ) : (
        <SectionCard title={t("suppliersPage.createTitle")} description={t("suppliersPage.readOnly")} />
      )}

      <SectionCard
        title={t("suppliersPage.directoryTitle")}
        description={t("suppliersPage.directoryDescription")}
        actions={<div className="text-sm text-muted-foreground">{t("total", { count: total })}</div>}
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="w-full max-w-md">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("suppliersPage.searchPlaceholder")}
                aria-label={t("suppliersPage.searchPlaceholder")}
              />
            </div>
            <Button
              type="button"
              variant={showInactive ? "default" : "outline"}
              onClick={() => setShowInactive((current) => !current)}
              aria-pressed={showInactive}
            >
              {t("suppliersPage.showInactive")}
            </Button>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {statusError ? <p className="text-sm text-destructive">{statusError}</p> : null}

          {loading ? (
            <p className="text-sm text-muted-foreground">{t("suppliersPage.loading")}</p>
          ) : suppliers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 px-4 py-8 text-center">
              <p className="font-medium">{t("suppliersPage.empty")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("suppliersPage.emptyDescription")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/30 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("suppliersPage.name")}</th>
                    <th className="px-4 py-3 font-medium">{t("suppliersPage.contact")}</th>
                    <th className="px-4 py-3 font-medium">{t("suppliersPage.leadTime")}</th>
                    <th className="px-4 py-3 font-medium">{t("suppliersPage.status")}</th>
                    <th className="px-4 py-3 font-medium">{t("suppliersPage.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {suppliers.map((supplier) => (
                    <tr key={supplier.id} className={!supplier.is_active ? "bg-muted/20 text-muted-foreground" : undefined}>
                      <td className="px-4 py-3 font-medium">{supplier.name}</td>
                      <td className="px-4 py-3">
                        {supplier.contact_email ?? supplier.phone ?? t("suppliersPage.noContact")}
                      </td>
                      <td className="px-4 py-3">
                        {supplier.default_lead_time_days == null ? t("suppliersPage.notSet") : supplier.default_lead_time_days}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={supplier.is_active ? "success" : "outline"} className="normal-case tracking-normal">
                          {supplier.is_active ? t("suppliersPage.active") : t("suppliersPage.inactive")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(buildSupplierDetailPath(supplier.id))}
                          >
                            {t("suppliersPage.view")}
                          </Button>
                          {canWrite("inventory") ? (
                            <Button
                              type="button"
                              size="sm"
                              variant={supplier.is_active ? "outline" : "default"}
                              onClick={() => void handleToggleStatus(supplier.id, supplier.is_active)}
                              disabled={statusPendingId === supplier.id}
                            >
                              {supplier.is_active ? t("suppliersPage.deactivate") : t("suppliersPage.activate")}
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
