/**
 * PurchaseOrderListPage - Page wrapper for purchase orders.
 */

import { PurchaseOrderList } from "@/domain/procurement/components/PurchaseOrderList";

export function PurchaseOrderListPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Purchase Orders</h1>
      <PurchaseOrderList showCreateButton={false} />
    </div>
  );
}