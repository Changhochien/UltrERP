/**
 * Purchase Order and Goods Receipt shared constants.
 */

import type { POStatus, GoodsReceiptStatus } from "./types";

export const PO_STATUS_COLORS: Record<POStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  on_hold: "bg-yellow-100 text-yellow-700",
  to_receive: "bg-orange-100 text-orange-700",
  to_bill: "bg-purple-100 text-purple-700",
  to_receive_and_bill: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
  closed: "bg-gray-100 text-gray-500",
};

export const PO_STATUS_LABELS: Record<POStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  on_hold: "On Hold",
  to_receive: "To Receive",
  to_bill: "To Bill",
  to_receive_and_bill: "To Receive & Bill",
  completed: "Completed",
  cancelled: "Cancelled",
  closed: "Closed",
};

export const GR_STATUS_COLORS: Record<GoodsReceiptStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
};

export const GR_STATUS_LABELS: Record<GoodsReceiptStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  cancelled: "Cancelled",
};
