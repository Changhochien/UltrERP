import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { SupplierInvoiceDetail } from "../domain/purchases/components/SupplierInvoiceDetail";
import { SupplierInvoiceList } from "../domain/purchases/components/SupplierInvoiceList";

export function PurchasesPage() {
  const { t } = useTranslation("purchase");
  const { t: tRoutes } = useTranslation("routes");
  const location = useLocation();
  const navigate = useNavigate();
  const requestedInvoiceId =
    ((location.state as { selectedInvoiceId?: string | null } | null)?.selectedInvoiceId ?? null);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(requestedInvoiceId);

  useEffect(() => {
    setSelectedInvoiceId(requestedInvoiceId);
  }, [requestedInvoiceId]);

  const handleSelectInvoice = (invoiceId: string | null) => {
    setSelectedInvoiceId(invoiceId);
    navigate(location.pathname, {
      replace: true,
      state: invoiceId ? { selectedInvoiceId: invoiceId } : {},
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("purchases.label") }]}
        eyebrow={t("page.eyebrow")}
        title={t("page.title")}
        description={t("page.description")}
        actions={
          selectedInvoiceId ? (
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleSelectInvoice(null)}
              >
                {t("detail.backToList")}
              </Button>
            </div>
          ) : undefined
        }
      />

      <SectionCard
        title={
          selectedInvoiceId
            ? t("page.detailTitle")
            : t("page.workspaceTitle")
        }
        description={
          selectedInvoiceId
            ? t("page.detailDescription")
            : t("page.workspaceDescription")
        }
      >
        {selectedInvoiceId ? (
          <SupplierInvoiceDetail
            invoiceId={selectedInvoiceId}
            onBack={() => handleSelectInvoice(null)}
          />
        ) : (
          <SupplierInvoiceList onSelect={handleSelectInvoice} />
        )}
      </SectionCard>
    </div>
  );
}