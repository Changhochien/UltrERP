import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { usePermissions } from "../../hooks/usePermissions";
import { useCommercialDefaultsOptions } from "../../hooks/useCommercialDefaultsOptions";
import { setSupplierStatus, updateSupplier } from "../../lib/api/inventory";
import { INVENTORY_SUPPLIERS_ROUTE } from "../../lib/routes";
import { SupplierForm, type SupplierFormFieldError } from "../../domain/inventory/components/SupplierForm";
import { useSupplierDetail } from "../../domain/inventory/hooks/useSuppliers";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

function toFieldErrors(
  errors?: Array<{ field: string; message: string }>,
): SupplierFormFieldError[] | undefined {
  if (!errors?.length) {
    return undefined;
  }
  return errors.map((error) => ({ field: error.field, message: error.message }));
}

export function SupplierDetailPage() {
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { supplierId } = useParams<{ supplierId: string }>();
  const { canWrite } = usePermissions();
  const { supplier, loading, error, reload } = useSupplierDetail(supplierId ?? null);
  const commercialOptions = useCommercialDefaultsOptions();
  const [statusPending, setStatusPending] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const inventoryTabs = buildInventorySectionTabs(t);

  if (!supplierId) {
    return <p className="text-sm text-destructive">{t("inventory.supplierDetail.loadError")}</p>;
  }

  async function handleToggleStatus() {
    if (!supplier) {
      return;
    }

    setStatusPending(true);
    setStatusError(null);
    const result = await setSupplierStatus(supplier.id, !supplier.is_active);
    setStatusPending(false);

    if (!result.ok) {
      setStatusError(result.error);
      return;
    }

    await reload();
  }

  const paymentTermsName = supplier?.payment_terms_template_id
    ? commercialOptions.paymentTerms.find((template) => template.id === supplier.payment_terms_template_id)?.template_name
      ?? supplier.payment_terms_template_id
    : t("inventory.supplierDetail.notSet");

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: tRoutes("inventorySuppliers.label"), href: INVENTORY_SUPPLIERS_ROUTE },
          { label: supplier?.name ?? t("inventory.supplierDetail.title") },
        ]}
        eyebrow={t("inventory.supplierDetail.eyebrow")}
        title={supplier?.name ?? t("inventory.supplierDetail.title")}
        description={t("inventory.supplierDetail.description")}
        actions={(
          <Button type="button" variant="outline" onClick={() => navigate(INVENTORY_SUPPLIERS_ROUTE)}>
            {t("inventory.supplierDetail.backToSuppliers")}
          </Button>
        )}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="suppliers"
            ariaLabel={t("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {loading ? <p className="text-sm text-muted-foreground">{t("inventory.supplierDetail.loading")}</p> : null}
      {!loading && error ? (
        <SectionCard title={t("inventory.supplierDetail.title")} description={t("inventory.supplierDetail.description")}>
          <div className="space-y-3">
            <p className="text-sm text-destructive">{error}</p>
            <Button type="button" variant="outline" onClick={() => void reload()}>
              {t("inventory.supplierDetail.retry")}
            </Button>
          </div>
        </SectionCard>
      ) : null}

      {!loading && supplier ? (
        <>
          <SectionCard
            title={t("inventory.supplierDetail.summaryTitle")}
            description={t("inventory.supplierDetail.summaryDescription")}
            actions={(
              canWrite("inventory") ? (
                <Button type="button" variant={supplier.is_active ? "outline" : "default"} onClick={() => void handleToggleStatus()} disabled={statusPending}>
                  {supplier.is_active ? t("inventory.supplierDetail.deactivate") : t("inventory.supplierDetail.activate")}
                </Button>
              ) : undefined
            )}
          >
            <dl className="grid gap-4 md:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.status")}</dt>
                <dd className="mt-1">
                  <Badge variant={supplier.is_active ? "success" : "outline"} className="normal-case tracking-normal">
                    {supplier.is_active ? t("inventory.supplierDetail.active") : t("inventory.supplierDetail.inactive")}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.leadTime")}</dt>
                <dd className="mt-1">
                  {supplier.default_lead_time_days == null ? t("inventory.supplierDetail.notSet") : supplier.default_lead_time_days}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.defaultCurrency")}</dt>
                <dd className="mt-1">{supplier.default_currency_code ?? t("inventory.supplierDetail.notSet")}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.paymentTerms")}</dt>
                <dd className="mt-1">{paymentTermsName}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.contactEmail")}</dt>
                <dd className="mt-1">{supplier.contact_email ?? t("inventory.supplierDetail.notSet")}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.phone")}</dt>
                <dd className="mt-1">{supplier.phone ?? t("inventory.supplierDetail.notSet")}</dd>
              </div>
              <div className="md:col-span-2">
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.address")}</dt>
                <dd className="mt-1 whitespace-pre-wrap">{supplier.address ?? t("inventory.supplierDetail.notSet")}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">{t("inventory.supplierDetail.createdAt")}</dt>
                <dd className="mt-1">{supplier.created_at.slice(0, 10)}</dd>
              </div>
            </dl>
            {statusError ? <p className="mt-4 text-sm text-destructive">{statusError}</p> : null}
          </SectionCard>

          {canWrite("inventory") ? (
            <SectionCard title={t("inventory.supplierDetail.editTitle")} description={t("inventory.supplierDetail.editDescription")}>
              <SupplierForm
                initialValues={{
                  name: supplier.name,
                  contact_email: supplier.contact_email ?? "",
                  phone: supplier.phone ?? "",
                  address: supplier.address ?? "",
                  default_lead_time_days:
                    supplier.default_lead_time_days == null
                      ? ""
                      : String(supplier.default_lead_time_days),
                  default_currency_code: supplier.default_currency_code ?? "",
                  payment_terms_template_id: supplier.payment_terms_template_id ?? "",
                }}
                submitLabel={t("inventory.supplierDetail.save")}
                submittingLabel={t("inventory.supplierDetail.saving")}
                onSubmit={async (values) => {
                  const result = await updateSupplier(supplier.id, values);
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
                  await reload();
                }}
              />
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
