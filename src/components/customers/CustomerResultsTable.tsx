/** Paginated table of customer summaries. */

import type { CustomerSummary } from "../../domain/customers/types";

interface Props {
  items: CustomerSummary[];
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onSelect: (id: string) => void;
}

export function CustomerResultsTable({
  items,
  page,
  totalPages,
  onPageChange,
  onSelect,
}: Props) {
  return (
    <div className="results-table-wrapper">
      <table className="results-table">
        <thead>
          <tr>
            <th>Company Name</th>
            <th>BAN</th>
            <th>Phone</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={4} className="empty-row">
                No customers found.
              </td>
            </tr>
          ) : (
            items.map((c) => (
              <tr key={c.id} onClick={() => onSelect(c.id)} className="clickable-row">
                <td>{c.company_name}</td>
                <td>{c.normalized_business_number}</td>
                <td>{c.contact_phone}</td>
                <td>{c.status}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
            ← Prev
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
