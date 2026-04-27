import { useTranslation } from "react-i18next";

import type { QuotationSummary } from "@/domain/crm/types";
import { DataTable } from "@/components/layout/DataTable";
import { Badge } from "@/components/ui/badge";

interface QuotationResultsTableProps {
  items: QuotationSummary[];
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onSelect: (id: string) => void;
}

function statusVariant(status: QuotationSummary["status"]) {
  switch (status) {
    case "ordered":
      return "success" as const;
    case "lost":
    case "cancelled":
    case "expired":
      return "warning" as const;
    default:
      return "outline" as const;
  }
}

export function QuotationResultsTable({
  items,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onSelect,
}: QuotationResultsTableProps) {
  const { t } = useTranslation("crm");

  return (
    <DataTable
      columns={[
        {
          id: "party_label",
          header: t("quotations.table.party"),
          sortable: true,
          getSortValue: (quotation) => quotation.party_label,
          cell: (quotation) => (
            <div className="space-y-0.5">
              <span className="font-medium">{quotation.party_label}</span>
              <p className="text-xs text-muted-foreground">{quotation.company}</p>
            </div>
          ),
        },
        {
          id: "valid_till",
          header: t("quotations.table.validTill"),
          sortable: true,
          getSortValue: (quotation) => quotation.valid_till,
          cell: (quotation) => quotation.valid_till,
        },
        {
          id: "grand_total",
          header: t("quotations.table.total"),
          sortable: true,
          getSortValue: (quotation) => quotation.grand_total,
          cell: (quotation) => quotation.grand_total,
        },
        {
          id: "conversion",
          header: t("quotations.table.conversion"),
          sortable: true,
          getSortValue: (quotation) => quotation.order_count ?? 0,
          cell: (quotation) => (
            <div className="space-y-0.5 text-sm">
              <p className="font-medium text-foreground">
                {(quotation.order_count ?? 0) > 0
                  ? t("quotations.table.orderCount", { count: quotation.order_count ?? 0 })
                  : t("quotations.table.notConverted")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("quotations.table.convertedAmount", {
                  amount: quotation.ordered_amount ?? "0.00",
                })}
              </p>
            </div>
          ),
        },
        {
          id: "status",
          header: t("quotations.table.status"),
          sortable: true,
          getSortValue: (quotation) => quotation.status,
          cell: (quotation) => (
            <Badge variant={statusVariant(quotation.status)} className="normal-case tracking-normal">
              {t(`crm.quotations.statusValues.${quotation.status}`)}
            </Badge>
          ),
        },
        {
          id: "revision_no",
          header: t("quotations.table.revision"),
          sortable: true,
          getSortValue: (quotation) => quotation.revision_no,
          cell: (quotation) => quotation.revision_no,
        },
      ]}
      data={items}
      emptyTitle={t("quotations.table.emptyTitle")}
      emptyDescription={t("quotations.table.emptyDescription")}
      page={page}
      pageSize={pageSize}
      totalItems={totalCount}
      onPageChange={onPageChange}
      getRowId={(quotation) => quotation.id}
      rowLabel={(quotation) => `Quotation ${quotation.party_label}`}
      onRowClick={(quotation) => onSelect(quotation.id)}
    />
  );
}

export default QuotationResultsTable;