/**
 * CreatePurchaseOrderPage - Guided entry for creating a purchase order from an award.
 */

import { Link, useSearchParams } from "react-router-dom";

import { PurchaseOrderDetail } from "@/domain/procurement/components/PurchaseOrderDetail";
import { PROCUREMENT_ROUTE } from "@/lib/routes";

export function CreatePurchaseOrderPage() {
  const [searchParams] = useSearchParams();
  const awardId = searchParams.get("awardId");

  if (!awardId) {
    return (
      <div className="space-y-4 rounded-lg border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <h1 className="text-xl font-semibold">Create Purchase Order</h1>
        <p>Select a winning supplier quotation from an RFQ before creating a purchase order.</p>
        <div>
          <Link className="text-sm font-medium text-amber-900 underline" to={PROCUREMENT_ROUTE}>
            Return to sourcing workspace
          </Link>
        </div>
      </div>
    );
  }

  return <PurchaseOrderDetail isNew awardId={awardId} />;
}