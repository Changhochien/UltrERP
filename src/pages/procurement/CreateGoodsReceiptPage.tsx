/**
 * CreateGoodsReceiptPage - Page wrapper for creating goods receipt from PO.
 */

import { useParams } from "react-router-dom";
import { CreateGoodsReceipt } from "@/domain/procurement/components/CreateGoodsReceipt";

export function CreateGoodsReceiptPage() {
  const { poId } = useParams<{ poId: string }>();

  if (!poId) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        Purchase order ID is required.
      </div>
    );
  }

  return <CreateGoodsReceipt purchaseOrderId={poId} />;
}
