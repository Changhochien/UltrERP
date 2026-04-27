import { useTranslation } from "react-i18next";

import type { LeadSummary } from "@/domain/crm/types";
import { DataTable } from "@/components/layout/DataTable";
import { Badge } from "@/components/ui/badge";

interface LeadResultsTableProps {
  items: LeadSummary[];
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onSelect: (id: string) => void;
}

function statusVariant(status: LeadSummary["status"]) {
  switch (status) {
    case "converted":
    case "interested":
      return "success" as const;
    case "lost_quotation":
    case "do_not_contact":
      return "warning" as const;
    default:
      return "outline" as const;
  }
}

export function LeadResultsTable({
  items,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onSelect,
}: LeadResultsTableProps) {
  const { t } = useTranslation("crm");

  return (
    <DataTable
      columns={[
        {
          id: "lead_name",
          header: t("table.lead"),
          sortable: true,
          getSortValue: (lead) => lead.lead_name,
          cell: (lead) => (
            <div className="space-y-0.5">
              <span className="font-medium">{lead.lead_name}</span>
              <p className="text-xs text-muted-foreground">{lead.company_name || t("table.noCompany")}</p>
            </div>
          ),
        },
        {
          id: "lead_owner",
          header: t("table.owner"),
          sortable: true,
          getSortValue: (lead) => lead.lead_owner,
          cell: (lead) => lead.lead_owner || "-",
        },
        {
          id: "status",
          header: t("table.status"),
          sortable: true,
          getSortValue: (lead) => lead.status,
          cell: (lead) => (
            <Badge variant={statusVariant(lead.status)} className="normal-case tracking-normal">
              {t(`crm.statusValues.${lead.status}`)}
            </Badge>
          ),
        },
        {
          id: "qualification_status",
          header: t("table.qualification"),
          sortable: true,
          getSortValue: (lead) => lead.qualification_status,
          cell: (lead) => t(`crm.qualificationValues.${lead.qualification_status}`),
        },
      ]}
      data={items}
      emptyTitle={t("table.emptyTitle")}
      emptyDescription={t("table.emptyDescription")}
      page={page}
      pageSize={pageSize}
      totalItems={totalCount}
      onPageChange={onPageChange}
      getRowId={(lead) => lead.id}
      rowLabel={(lead) => `Lead ${lead.lead_name}`}
      onRowClick={(lead) => onSelect(lead.id)}
    />
  );
}
