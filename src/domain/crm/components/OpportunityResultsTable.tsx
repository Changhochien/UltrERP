import { useTranslation } from "react-i18next";

import type { OpportunitySummary } from "@/domain/crm/types";
import { DataTable } from "@/components/layout/DataTable";
import { Badge } from "@/components/ui/badge";

interface OpportunityResultsTableProps {
  items: OpportunitySummary[];
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onSelect: (id: string) => void;
}

function statusVariant(status: OpportunitySummary["status"]) {
  switch (status) {
    case "converted":
      return "success" as const;
    case "closed":
    case "lost":
      return "warning" as const;
    default:
      return "outline" as const;
  }
}

export function OpportunityResultsTable({
  items,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onSelect,
}: OpportunityResultsTableProps) {
  const { t } = useTranslation("crm");

  return (
    <DataTable
      columns={[
        {
          id: "opportunity_title",
          header: t("opportunities.table.opportunity"),
          sortable: true,
          getSortValue: (opportunity) => opportunity.opportunity_title,
          cell: (opportunity) => (
            <div className="space-y-0.5">
              <span className="font-medium">{opportunity.opportunity_title}</span>
              <p className="text-xs text-muted-foreground">{opportunity.party_label}</p>
            </div>
          ),
        },
        {
          id: "sales_stage",
          header: t("opportunities.table.stage"),
          sortable: true,
          getSortValue: (opportunity) => opportunity.sales_stage,
          cell: (opportunity) => opportunity.sales_stage || "-",
        },
        {
          id: "probability",
          header: t("opportunities.table.probability"),
          sortable: true,
          getSortValue: (opportunity) => opportunity.probability,
          cell: (opportunity) => `${opportunity.probability}%`,
        },
        {
          id: "status",
          header: t("opportunities.table.status"),
          sortable: true,
          getSortValue: (opportunity) => opportunity.status,
          cell: (opportunity) => (
            <Badge variant={statusVariant(opportunity.status)} className="normal-case tracking-normal">
              {t(`opportunities.statusValues.${opportunity.status}`)}
            </Badge>
          ),
        },
      ]}
      data={items}
      emptyTitle={t("opportunities.table.emptyTitle")}
      emptyDescription={t("opportunities.table.emptyDescription")}
      page={page}
      pageSize={pageSize}
      totalItems={totalCount}
      onPageChange={onPageChange}
      getRowId={(opportunity) => opportunity.id}
      rowLabel={(opportunity) => `Opportunity ${opportunity.opportunity_title}`}
      onRowClick={(opportunity) => onSelect(opportunity.id)}
    />
  );
}

export default OpportunityResultsTable;