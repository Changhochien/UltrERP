import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { SupplierInvoiceDetail } from "../domain/purchases/components/SupplierInvoiceDetail";
import { SupplierInvoiceList } from "../domain/purchases/components/SupplierInvoiceList";

export function PurchasesPage() {
  const { t } = useTranslation("common");
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
        breadcrumb={[{ label: t("routes.purchases.label") }]}
        eyebrow={t("purchase.page.eyebrow")}
        title={t("purchase.page.title")}
        description={t("purchase.page.description")}
        actions={
          selectedInvoiceId ? (
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleSelectInvoice(null)}
              >
                {t("purchase.detail.backToList")}
              </Button>
            </div>
          ) : undefined
        }
      />

      <SectionCard
        title={
          selectedInvoiceId
            ? t("purchase.page.detailTitle")
            : t("purchase.page.workspaceTitle")
        }
        description={
          selectedInvoiceId
            ? t("purchase.page.detailDescription")
            : t("purchase.page.workspaceDescription")
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