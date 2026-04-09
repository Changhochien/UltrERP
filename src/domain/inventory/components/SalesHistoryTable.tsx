import { parseBackendDate } from "@/lib/time";
import type { SalesHistoryItem } from "../hooks/useProductSalesHistory";

interface SalesHistoryTableProps {
  items: SalesHistoryItem[];
}

function formatDate(dateStr: string): string {
  return parseBackendDate(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const REASON_LABELS: Record<string, string> = {
  sales_reservation: "Sales / Reservation",
  supplier_delivery: "Supplier Delivery",
  transfer_in: "Transfer In",
  transfer_out: "Transfer Out",
  adjustment: "Adjustment",
  opening: "Opening",
};

export function SalesHistoryTable({ items }: SalesHistoryTableProps) {
  if (items.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-muted-foreground">
        <p className="text-sm">No sales history found</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <th className="pb-2 pr-4 font-medium">Date</th>
            <th className="pb-2 pr-4 font-medium">Qty</th>
            <th className="pb-2 pr-4 font-medium">Reason</th>
            <th className="pb-2 font-medium">Actor</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {items.map((item, i) => (
            <tr key={i} className="text-sm">
              <td className="py-2 pr-4 text-muted-foreground">
                {formatDate(item.date)}
              </td>
              <td
                className={`py-2 pr-4 font-medium ${
                  item.quantity_change > 0
                    ? "text-success"
                    : "text-destructive"
                }`}
              >
                {item.quantity_change > 0 ? "+" : ""}
                {item.quantity_change}
              </td>
              <td className="py-2 pr-4 text-muted-foreground">
                {REASON_LABELS[item.reason_code] ?? item.reason_code}
              </td>
              <td className="py-2 text-muted-foreground">{item.actor_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
