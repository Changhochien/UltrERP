/**
 * GoodsReceiptList - List and manage goods receipts.
 */

import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { useGoodsReceiptList } from "../hooks/useGoodsReceipt";
import { GR_STATUS_COLORS, GR_STATUS_LABELS } from "../constants";
import type { GoodsReceiptStatus, GoodsReceiptSummary } from "../types";

interface GoodsReceiptListProps {
  purchaseOrderId?: string | null;
  showCreateButton?: boolean;
}

export function GoodsReceiptList({
  purchaseOrderId,
  showCreateButton = true,
}: GoodsReceiptListProps) {
  const navigate = useNavigate();
  const { data, loading, error } = useGoodsReceiptList({
    purchaseOrderId: purchaseOrderId ?? undefined,
    pageSize: 20,
  });

  const [filter, setFilter] = useState<"all" | GoodsReceiptStatus>("all");

  const filteredItems = data?.items?.filter((item) => {
    if (filter === "all") return true;
    return item.status === filter;
  }) ?? [];

  const handleViewReceipt = useCallback((grId: string) => {
    navigate(`/procurement/goods-receipts/${grId}`);
  }, [navigate]);

  const handleCreateReceipt = useCallback(() => {
    if (purchaseOrderId) {
      navigate(`/procurement/purchase-orders/${purchaseOrderId}/create-receipt`);
    } else {
      navigate("/procurement/goods-receipts/new");
    }
  }, [navigate, purchaseOrderId]);

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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-gray-900">Goods Receipts</h2>
          {data && (
            <p className="mt-1 text-sm text-gray-500">
              {data.total} receipt{data.total !== 1 ? "s" : ""}
              {purchaseOrderId && " for this PO"}
            </p>
          )}
        </div>
        {showCreateButton && purchaseOrderId && (
          <button
            onClick={handleCreateReceipt}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            Create Receipt
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(["all", "draft", "submitted", "cancelled"] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
              filter === status
                ? "bg-blue-100 text-blue-700"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {status === "all" ? "All" : GR_STATUS_LABELS[status as GoodsReceiptStatus] ?? status}
          </button>
        ))}
      </div>

      {/* List */}
      {filteredItems.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-gray-500">
            {filter === "all" ? "No goods receipts found." : `No ${filter} receipts found.`}
          </p>
          {showCreateButton && purchaseOrderId && (
            <button
              onClick={handleCreateReceipt}
              className="mt-4 text-blue-600 hover:text-blue-800"
            >
              Create your first receipt
            </button>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Supplier
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Inventory
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredItems.map((receipt: GoodsReceiptSummary) => (
                  <tr
                    key={receipt.id}
                    className="hover:bg-gray-50"
                  >
                    <td className="whitespace-nowrap px-4 py-3">
                      <button
                        onClick={() => handleViewReceipt(receipt.id)}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800"
                      >
                        {receipt.name}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          GR_STATUS_COLORS[receipt.status as GoodsReceiptStatus] ??
                          "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {GR_STATUS_LABELS[receipt.status as GoodsReceiptStatus] ?? receipt.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                      {receipt.supplier_name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                      {format(new Date(receipt.transaction_date), "yyyy-MM-dd")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {receipt.inventory_mutated ? (
                        <span className="text-xs text-green-600">Updated</span>
                      ) : (
                        <span className="text-xs text-gray-400">Pending</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      <Link
                        to={`/procurement/goods-receipts/${receipt.id}`}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
