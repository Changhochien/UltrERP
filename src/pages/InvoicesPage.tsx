import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { InvoiceDetail } from "../domain/invoices/components/InvoiceDetail";
import { InvoiceList } from "../domain/invoices/components/InvoiceList";
import { usePermissions } from "../hooks/usePermissions";
import { INVOICE_CREATE_ROUTE } from "../lib/routes";

export function InvoicesPage() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("invoice.listPage.eyebrow")}
        title={t("invoice.listPage.title")}
        description={t("invoice.listPage.description")}
        actions={(
          <div className="flex flex-wrap gap-3">
            {selectedInvoiceId ? (
              <Button type="button" variant="outline" onClick={() => setSelectedInvoiceId(null)}>
                {t("invoice.listPage.backToList")}
              </Button>
            ) : null}
            {canWrite("invoices") ? (
              <Button type="button" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
                {t("invoice.listPage.createInvoice")}
              </Button>
            ) : null}
          </div>
        )}
      />

      <SectionCard
        title={selectedInvoiceId ? t("invoice.listPage.invoiceDetail") : t("invoice.listPage.invoiceWorkspace")}
        description={selectedInvoiceId ? t("invoice.listPage.invoiceDetailDescription") : t("invoice.listPage.invoiceWorkspaceDescription")}
      >
        {selectedInvoiceId ? (
          <InvoiceDetail invoiceId={selectedInvoiceId} onBack={() => setSelectedInvoiceId(null)} />
        ) : (
          <InvoiceList onSelect={setSelectedInvoiceId} />
        )}
      </SectionCard>
    </div>
  );
}