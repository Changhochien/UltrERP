import { useTranslation } from "react-i18next";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import {
  supplierInvoiceStatusBadgeVariant,
  useSupplierInvoice,
  useSupplierInvoiceStatusLabel,
} from "../hooks/useSupplierInvoices";

interface SupplierInvoiceDetailProps {
  invoiceId: string;
  onBack: () => void;
}

export function SupplierInvoiceDetail({
  invoiceId,
  onBack,
}: SupplierInvoiceDetailProps) {
  const { t } = useTranslation("common");
  const statusLabel = useSupplierInvoiceStatusLabel();
  const { invoice, loading, error } = useSupplierInvoice(invoiceId);

  if (loading) {
    return <p>{t("purchase.detail.loading")}</p>;
  }

  if (error) {
    return <SurfaceMessage tone="danger">{error}</SurfaceMessage>;
  }

  if (!invoice) {
    return <p>{t("purchase.detail.notFound")}</p>;
  }

  return (
    <section aria-label={t("purchase.detail.ariaLabel")} className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <Button type="button" variant="outline" onClick={onBack}>
            {t("purchase.detail.backToList")}
          </Button>
          <h2>
            {t("purchase.detail.title", { invoiceNumber: invoice.invoice_number })}
          </h2>
        </div>
        <Badge
          variant={supplierInvoiceStatusBadgeVariant(invoice.status)}
          className="normal-case tracking-normal"
        >
          {statusLabel(invoice.status)}
        </Badge>
      </div>

      <SectionCard
        title={t("purchase.detail.summaryTitle")}
        description={t("purchase.detail.summaryDescription")}
      >
        <dl className="gap-y-4">
          <dt>{t("purchase.detail.supplier")}</dt>
          <dd>{invoice.supplier_name}</dd>
          <dt>{t("purchase.detail.invoiceDate")}</dt>
          <dd>{invoice.invoice_date}</dd>
          <dt>{t("purchase.detail.currency")}</dt>
          <dd>{invoice.currency_code}</dd>
          <dt>{t("purchase.detail.subtotal")}</dt>
          <dd>{invoice.currency_code} {invoice.subtotal_amount}</dd>
          <dt>{t("purchase.detail.tax")}</dt>
          <dd>{invoice.currency_code} {invoice.tax_amount}</dd>
          <dt>{t("purchase.detail.total")}</dt>
          <dd>{invoice.currency_code} {invoice.total_amount}</dd>
          <dt>{t("purchase.detail.notes")}</dt>
          <dd>{invoice.notes || t("purchase.detail.noNotes")}</dd>
        </dl>
      </SectionCard>

      <SectionCard
        title={t("purchase.detail.linesTitle")}
        description={t("purchase.detail.linesDescription")}
      >
        <DataTable
          columns={[
            {
              id: "product_code_snapshot",
              header: t("purchase.detail.columns.productCode"),
              cell: (line) => line.product_code_snapshot || "—",
            },
            {
              id: "product_name",
              header: t("purchase.detail.columns.productName"),
              cell: (line) => line.product_name || "—",
            },
            {
              id: "description",
              header: t("purchase.detail.columns.description"),
              cell: (line) => line.description,
            },
            {
              id: "quantity",
              header: t("purchase.detail.columns.quantity"),
              cell: (line) => line.quantity,
            },
            {
              id: "unit_price",
              header: t("purchase.detail.columns.unitPrice"),
              cell: (line) => `${invoice.currency_code} ${line.unit_price}`,
            },
            {
              id: "total_amount",
              header: t("purchase.detail.columns.total"),
              cell: (line) => `${invoice.currency_code} ${line.total_amount}`,
            },
          ]}
          data={invoice.lines}
          emptyTitle={t("purchase.detail.emptyTitle")}
          emptyDescription={t("purchase.detail.emptyDescription")}
          getRowId={(line) => line.id}
        />
      </SectionCard>
    </section>
  );
}