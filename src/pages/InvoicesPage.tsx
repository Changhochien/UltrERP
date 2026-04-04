import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { InvoiceDetail } from "../domain/invoices/components/InvoiceDetail";
import { InvoiceList } from "../domain/invoices/components/InvoiceList";
import { usePermissions } from "../hooks/usePermissions";
import { INVOICE_CREATE_ROUTE } from "../lib/routes";

export function InvoicesPage() {
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);

  return (
    <section className="hero-card" style={{ width: "min(72rem, 100%)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: "2rem", lineHeight: 1.1 }}>Invoices</h1>
          <p className="caption">Browse invoice status and payment progress.</p>
        </div>
        {canWrite("invoices") && (
          <button type="button" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
            Create Invoice
          </button>
        )}
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        {selectedInvoiceId ? (
          <InvoiceDetail invoiceId={selectedInvoiceId} onBack={() => setSelectedInvoiceId(null)} />
        ) : (
          <InvoiceList onSelect={setSelectedInvoiceId} />
        )}
      </div>
    </section>
  );
}