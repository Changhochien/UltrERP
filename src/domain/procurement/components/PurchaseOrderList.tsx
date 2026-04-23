/**
 * PurchaseOrderList - Table view of all purchase orders.
 */

import { Link } from "react-router-dom";
import { format } from "date-fns";
import { usePurchaseOrderList } from "../hooks/usePurchaseOrder";
import { PO_STATUS_COLORS, PO_STATUS_LABELS } from "../constants";
import type { PurchaseOrderSummary, POStatus } from "../types";

interface PurchaseOrderListProps {
  statusFilter?: string;
  supplierIdFilter?: string;
  searchQuery?: string;
  page?: number;
  pageSize?: number;
  showCreateButton?: boolean;
}

export function PurchaseOrderList({
  statusFilter,
  supplierIdFilter,
  searchQuery,
  page = 1,
  pageSize = 20,
  showCreateButton = true,
}: PurchaseOrderListProps) {
  const { data, loading, error, refetch } = usePurchaseOrderList({
    status: statusFilter,
    supplierId: supplierIdFilter,
    q: searchQuery,
    page,
    pageSize,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        {error}
      </div>
    );
  }

  const pos = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;

  return (
    <div className="space-y-4">
      {showCreateButton && (
        <div className="flex justify-end">
          <Link
            to="/procurement/purchase-orders/new"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New Purchase Order
          </Link>
        </div>
      )}

      {pos.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
          No purchase orders found.
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    PO Number
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Supplier
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Company
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Date
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Grand Total
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                    Progress
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {pos.map((po: PurchaseOrderSummary) => (
                  <tr key={po.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3">
                      <Link
                        to={`/procurement/purchase-orders/${po.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800"
                      >
                        {po.name}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                      {po.supplier_name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                      {po.company}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                      {format(new Date(po.transaction_date), "yyyy-MM-dd")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                      {po.currency} {Number(po.grand_total).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${PO_STATUS_COLORS[po.status as POStatus] ?? "bg-gray-100 text-gray-700"}`}
                      >
                        {PO_STATUS_LABELS[po.status as POStatus] ?? po.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm text-gray-500">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 overflow-hidden rounded-full bg-gray-200">
                          <div
                            className="h-2 bg-blue-500"
                            style={{ width: `${po.per_received}%` }}
                          />
                        </div>
                        <span className="text-xs">{Number(po.per_received).toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">
                Page {page} of {pages} ({total} total)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => refetch()}
                  disabled={page <= 1}
                  className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => refetch()}
                  disabled={page >= pages}
                  className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
