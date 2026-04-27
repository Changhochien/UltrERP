import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { InvoiceDetail } from "../domain/invoices/components/InvoiceDetail";
import { InvoiceList } from "../domain/invoices/components/InvoiceList";
import { usePermissions } from "../hooks/usePermissions";
import { INVOICE_CREATE_ROUTE, INVOICES_ROUTE } from "../lib/routes";

export function InvoicesPage() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const { canWrite } = usePermissions();

  if (invoiceId) {
    return (
      <InvoiceDetail invoiceId={invoiceId} onBack={() => navigate(INVOICES_ROUTE)} />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("invoices.label") }]}
        eyebrow={t("invoice.listPage.eyebrow")}
        title={t("invoice.listPage.title")}
        description={t("invoice.listPage.description")}
        actions={(
          <div className="flex flex-wrap gap-3">
            {canWrite("invoices") ? (
              <Button type="button" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
                {t("invoice.listPage.createInvoice")}
              </Button>
            ) : null}
          </div>
        )}
      />

      <SectionCard
        title={t("invoice.listPage.invoiceWorkspace")}
        description={t("invoice.listPage.invoiceWorkspaceDescription")}
      >
        <InvoiceList onSelect={(id) => navigate(`/invoices/${id}`)} />
      </SectionCard>
    </div>
  );
}
