/**
 * GoodsReceiptListPage - Page wrapper for goods receipt list.
 */

import { GoodsReceiptList } from "@/domain/procurement/components/GoodsReceiptList";

export function GoodsReceiptListPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Goods Receipts</h1>
      <GoodsReceiptList showCreateButton={false} />
    </div>
  );
}
