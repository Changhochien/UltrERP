import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { SupplierInvoiceDetail } from "../domain/purchases/components/SupplierInvoiceDetail";
import { SupplierInvoiceList } from "../domain/purchases/components/SupplierInvoiceList";

export function PurchasesPage() {
  const { t } = useTranslation("common");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("purchase.page.eyebrow")}
        title={t("purchase.page.title")}
        description={t("purchase.page.description")}
        actions={
          selectedInvoiceId ? (
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setSelectedInvoiceId(null)}
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
            onBack={() => setSelectedInvoiceId(null)}
          />
        ) : (
          <SupplierInvoiceList onSelect={setSelectedInvoiceId} />
        )}
      </SectionCard>
    </div>
  );
}