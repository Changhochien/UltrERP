/** Paginated invoice list with payment status columns, filter, and sort. */

import { useState } from "react";
import { useInvoices, paymentStatusLabel, paymentStatusColor } from "../hooks/useInvoices";

interface InvoiceListProps {
  onSelect: (invoiceId: string) => void;
}

const PAYMENT_STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All" },
  { value: "unpaid", label: "Unpaid" },
  { value: "partial", label: "Partial" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
];

export function InvoiceList({ onSelect }: InvoiceListProps) {
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("outstanding_balance");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const { items, total, page, pageSize, loading, error, reload } = useInvoices({
    payment_status: statusFilter || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const toggleSort = (col: string) => {
    if (sortBy === col) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col);
      setSortOrder("desc");
    }
  };

  const sortArrow = (col: string) =>
    sortBy === col ? (sortOrder === "asc" ? " ↑" : " ↓") : "";

  return (
    <section aria-label="Invoice list">
      <h2>Invoices</h2>

      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <label htmlFor="inv-payment-status">Payment Status: </label>
        <select
          id="inv-payment-status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {PAYMENT_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div role="alert" style={{ color: "#dc2626" }}>
          {error}
        </div>
      )}

      {loading && <p aria-busy="true">Loading…</p>}

      {!loading && items.length === 0 && <p>No invoices found.</p>}

      {!loading && items.length > 0 && (
        <>
          <table aria-label="Invoices table">
            <thead>
              <tr>
                <th>Invoice #</th>
                <th
                  style={{ cursor: "pointer" }}
                  onClick={() => toggleSort("invoice_date")}
                >
                  Date{sortArrow("invoice_date")}
                </th>
                <th>Total</th>
                <th>Paid</th>
                <th
                  style={{ cursor: "pointer" }}
                  onClick={() => toggleSort("outstanding_balance")}
                >
                  Outstanding{sortArrow("outstanding_balance")}
                </th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Invoice ${item.invoice_number}`}
                  onClick={() => onSelect(item.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(item.id);
                    }
                  }}
                  style={{
                    cursor: "pointer",
                    backgroundColor: item.payment_status === "overdue" ? "#fef2f2" : undefined,
                    borderLeft: item.payment_status === "overdue" ? "4px solid #dc2626" : undefined,
                  }}
                >
                  <td>{item.invoice_number}</td>
                  <td>{item.invoice_date}</td>
                  <td>{item.currency_code} {item.total_amount}</td>
                  <td>{item.currency_code} {item.amount_paid}</td>
                  <td>{item.currency_code} {item.outstanding_balance}</td>
                  <td>
                    <span
                      style={{
                        color: paymentStatusColor(item.payment_status),
                        fontWeight: 600,
                      }}
                    >
                      {paymentStatusLabel(item.payment_status)}
                    </span>
                    {item.payment_status === "overdue" && item.days_overdue > 0 && (
                      <span
                        style={{
                          marginLeft: 6,
                          background: "#dc2626",
                          color: "#fff",
                          padding: "1px 6px",
                          borderRadius: 4,
                          fontSize: "0.75em",
                        }}
                      >
                        {item.days_overdue}d
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 8 }}>
            <span>
              Page {page} · {total} total
            </span>
            {page > 1 && (
              <button
                type="button"
                onClick={() => void reload(page - 1)}
                style={{ marginLeft: 8 }}
              >
                ← Prev
              </button>
            )}
            {page * pageSize < total && (
              <button
                type="button"
                onClick={() => void reload(page + 1)}
                style={{ marginLeft: 8 }}
              >
                Next →
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
