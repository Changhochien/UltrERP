/** Paginated table of customer summaries. */

import { DataTable } from "../layout/DataTable";
import { Badge } from "../ui/badge";
import type { CustomerSummary } from "../../domain/customers/types";

interface Props {
  items: CustomerSummary[];
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onSelect: (id: string) => void;
}

export function CustomerResultsTable({
  items,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onSelect,
}: Props) {
  const statusVariant = (status: string) => {
    switch (status) {
      case "active":
        return "success" as const;
      case "suspended":
        return "warning" as const;
      default:
        return "outline" as const;
    }
  };

  return (
    <DataTable
      columns={[
        {
          id: "company_name",
          header: "Company Name",
          sortable: true,
          getSortValue: (customer) => customer.company_name,
          cell: (customer) => <span className="font-medium">{customer.company_name}</span>,
        },
        {
          id: "normalized_business_number",
          header: "BAN",
          sortable: true,
          getSortValue: (customer) => customer.normalized_business_number,
          cell: (customer) => customer.normalized_business_number,
        },
        {
          id: "contact_phone",
          header: "Phone",
          sortable: true,
          getSortValue: (customer) => customer.contact_phone,
          cell: (customer) => customer.contact_phone,
        },
        {
          id: "status",
          header: "Status",
          sortable: true,
          getSortValue: (customer) => customer.status,
          cell: (customer) => (
            <Badge variant={statusVariant(customer.status)} className="normal-case tracking-normal">
              {customer.status}
            </Badge>
          ),
        },
      ]}
      data={items}
      emptyTitle="No customers found."
      emptyDescription="Try broadening your search or clearing the status filter."
      page={page}
      pageSize={pageSize}
      totalItems={totalCount}
      onPageChange={onPageChange}
      getRowId={(customer) => customer.id}
      rowLabel={(customer) => `Customer ${customer.company_name}`}
      onRowClick={(customer) => onSelect(customer.id)}
    />
  );
}
