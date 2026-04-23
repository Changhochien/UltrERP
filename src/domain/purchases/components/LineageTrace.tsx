/** Procurement Lineage Trace Component (Story 24-4).

Displays the procurement lineage chain from RFQ through supplier quotation,
PO, and goods receipt to supplier invoice. Used for audit and three-way-match review.

Note: This is a readiness component - no AP posting workflow is implemented.
*/

import type { ProcurementLineage, MismatchSummary, ProcurementMismatchStatus } from "../types";

interface LineageTraceProps {
  lineage: ProcurementLineage;
  mismatchSummary?: MismatchSummary | null;
  compact?: boolean;
}

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  rfq: "RFQ",
  supplier_quotation: "Supplier Quotation",
  purchase_order: "Purchase Order",
  goods_receipt: "Goods Receipt",
};

const LINEAGE_STATE_LABELS: Record<string, { label: string; color: string }> = {
  linked: { label: "Linked", color: "text-green-600" },
  unlinked_historical: { label: "Unlinked (Historical)", color: "text-gray-500" },
  missing_reference: { label: "Missing Reference", color: "text-amber-600" },
};

const MISMATCH_STATUS_LABELS: Record<ProcurementMismatchStatus, { label: string; color: string }> = {
  not_checked: { label: "Not Checked", color: "text-gray-400" },
  within_tolerance: { label: "Within Tolerance", color: "text-green-600" },
  outside_tolerance: { label: "Outside Tolerance", color: "text-red-600" },
  review_required: { label: "Review Required", color: "text-amber-600" },
};

export function LineageTrace({ lineage, mismatchSummary, compact = false }: LineageTraceProps) {
  const stateInfo = LINEAGE_STATE_LABELS[lineage.lineage_state] || LINEAGE_STATE_LABELS.unlinked_historical;

  const hasLineage = lineage.rfq_id ||
    lineage.supplier_quotation_id ||
    lineage.purchase_order_id ||
    lineage.goods_receipt_id;

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className={`font-medium ${stateInfo.color}`}>{stateInfo.label}</span>
        {hasLineage && (
          <span className="text-gray-400">
            {[
              lineage.rfq_id && "RFQ",
              lineage.supplier_quotation_id && "SQ",
              lineage.purchase_order_id && "PO",
              lineage.goods_receipt_id && "GR",
            ].filter(Boolean).join(" → ")}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Lineage State Badge */}
      <div className="flex items-center gap-2">
        <span className={`text-sm font-medium ${stateInfo.color}`}>
          {stateInfo.label}
        </span>
      </div>

      {/* Document Chain */}
      {hasLineage ? (
        <div className="space-y-1">
          <div className="text-xs text-gray-500 mb-1">Procurement Chain</div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {lineage.rfq_id && (
              <>
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                  RFQ
                </span>
                <span className="text-gray-400">→</span>
              </>
            )}
            {lineage.supplier_quotation_id && (
              <>
                <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded">
                  SQ
                </span>
                <span className="text-gray-400">→</span>
              </>
            )}
            {lineage.purchase_order_id && (
              <>
                <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                  PO
                </span>
                <span className="text-gray-400">→</span>
              </>
            )}
            {lineage.goods_receipt_id && (
              <>
                <span className="px-2 py-0.5 bg-teal-50 text-teal-700 rounded">
                  GR
                </span>
                <span className="text-gray-400">→</span>
              </>
            )}
            <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
              Invoice
            </span>
          </div>
        </div>
      ) : (
        <div className="text-sm text-gray-500 italic">
          This line predates procurement lineage tracking.
        </div>
      )}

      {/* Mismatch Summary */}
      {mismatchSummary && mismatchSummary.mismatch_status !== "not_checked" && (
        <div className="pt-2 border-t border-gray-100">
          <MismatchIndicator summary={mismatchSummary} />
        </div>
      )}
    </div>
  );
}

interface MismatchIndicatorProps {
  summary: MismatchSummary;
}

export function MismatchIndicator({ summary }: MismatchIndicatorProps) {
  const statusInfo = MISMATCH_STATUS_LABELS[summary.mismatch_status] ||
    MISMATCH_STATUS_LABELS.not_checked;

  const hasVariance = summary.quantity_variance !== null ||
    summary.unit_price_variance !== null ||
    summary.total_amount_variance !== null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className={`text-sm font-medium ${statusInfo.color}`}>
          {statusInfo.label}
        </span>
        {summary.tolerance_rule_code && (
          <span className="text-xs text-gray-400">
            Rule: {summary.tolerance_rule_code}
          </span>
        )}
      </div>

      {hasVariance && (
        <div className="grid grid-cols-3 gap-2 text-xs">
          {summary.quantity_variance !== null && (
            <VarianceCell
              label="Qty"
              value={summary.quantity_variance}
              pct={summary.quantity_variance_pct}
            />
          )}
          {summary.unit_price_variance !== null && (
            <VarianceCell
              label="Price"
              value={summary.unit_price_variance}
              pct={summary.unit_price_variance_pct}
            />
          )}
          {summary.total_amount_variance !== null && (
            <VarianceCell
              label="Total"
              value={summary.total_amount_variance}
              pct={summary.total_amount_variance_pct}
            />
          )}
        </div>
      )}
    </div>
  );
}

interface VarianceCellProps {
  label: string;
  value: string | null;
  pct: string | null;
}

function VarianceCell({ label, value, pct }: VarianceCellProps) {
  if (value === null) return null;

  const numValue = parseFloat(value);
  const isNegative = numValue < 0;
  const colorClass = isNegative ? "text-red-600" : numValue > 0 ? "text-amber-600" : "text-gray-600";

  return (
    <div className="bg-gray-50 rounded px-2 py-1">
      <div className="text-gray-500">{label}</div>
      <div className={`font-medium ${colorClass}`}>
        {isNegative ? "" : "+"}
        {value}
      </div>
      {pct !== null && (
        <div className={`text-xs ${colorClass}`}>
          {parseFloat(pct) >= 0 ? "+" : ""}
          {parseFloat(pct).toFixed(2)}%
        </div>
      )}
    </div>
  );
}

interface MismatchStatusBadgeProps {
  status: ProcurementMismatchStatus;
  size?: "sm" | "md";
}

export function MismatchStatusBadge({ status, size = "sm" }: MismatchStatusBadgeProps) {
  const statusInfo = MISMATCH_STATUS_LABELS[status] || MISMATCH_STATUS_LABELS.not_checked;

  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1";

  const bgClass = status === "within_tolerance"
    ? "bg-green-50"
    : status === "outside_tolerance"
    ? "bg-red-50"
    : status === "review_required"
    ? "bg-amber-50"
    : "bg-gray-50";

  return (
    <span className={`${sizeClasses} ${bgClass} ${statusInfo.color} rounded font-medium`}>
      {statusInfo.label}
    </span>
  );
}

interface LineageDocumentLinkProps {
  type: "rfq" | "supplier_quotation" | "purchase_order" | "goods_receipt";
  id: string;
  name?: string | null;
}

export function LineageDocumentLink({ type, id, name }: LineageDocumentLinkProps) {
  const label = DOCUMENT_TYPE_LABELS[type] || type;
  const displayName = name || id.slice(0, 8);

  // Map type to route
  const routeMap: Record<string, string> = {
    rfq: "/procurement/rfqs",
    supplier_quotation: "/procurement/quotations",
    purchase_order: "/procurement/purchase-orders",
    goods_receipt: "/procurement/goods-receipts",
  };

  const route = routeMap[type] || "/";

  return (
    <a
      href={`${route}/${encodeURIComponent(id)}`}
      className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
    >
      <span className="px-1.5 py-0.5 bg-blue-50 rounded text-xs font-medium">
        {label}
      </span>
      <span>{displayName}</span>
    </a>
  );
}
