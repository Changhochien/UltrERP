import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import { Button } from "../components/ui/button";
import { InvoiceDetail } from "../domain/invoices/components/InvoiceDetail";
import { InvoiceList } from "../domain/invoices/components/InvoiceList";
import { usePermissions } from "../hooks/usePermissions";
import { INVOICE_CREATE_ROUTE } from "../lib/routes";

export function InvoicesPage() {
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance"
        title="Invoices"
        description="Payment-aware invoice operations with list filtering, detail drill-in, and print workflows."
        actions={(
          <div className="flex flex-wrap gap-3">
            {selectedInvoiceId ? (
              <Button type="button" variant="outline" onClick={() => setSelectedInvoiceId(null)}>
                Back to list
              </Button>
            ) : null}
            {canWrite("invoices") ? (
              <Button type="button" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
                Create Invoice
              </Button>
            ) : null}
          </div>
        )}
      />

      <SectionCard
        title={selectedInvoiceId ? "Invoice Detail" : "Invoice Workspace"}
        description={selectedInvoiceId ? "Inspect invoice totals, payment history, and print readiness." : "Track outstanding balances, overdue accounts, and payment status."}
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