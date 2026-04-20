import type {
  OrderBillingStatus,
  OrderCommercialStatus,
  OrderFulfillmentStatus,
  OrderReservationStatus,
} from "./types";

export type OrderWorkflowBadgeVariant =
  | "outline"
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "destructive";

export const FULFILLMENT_STATUS_META: Record<
  OrderFulfillmentStatus,
  { labelKey: string; variant: OrderWorkflowBadgeVariant }
> = {
  not_started: {
    labelKey: "orders.workflow.fulfillment.notStarted",
    variant: "neutral",
  },
  ready_to_ship: {
    labelKey: "orders.workflow.fulfillment.readyToShip",
    variant: "info",
  },
  shipped: {
    labelKey: "orders.workflow.fulfillment.shipped",
    variant: "info",
  },
  fulfilled: {
    labelKey: "orders.workflow.fulfillment.fulfilled",
    variant: "success",
  },
  cancelled: {
    labelKey: "orders.workflow.fulfillment.cancelled",
    variant: "outline",
  },
};

export const COMMERCIAL_STATUS_META: Record<
  OrderCommercialStatus,
  { labelKey: string; variant: OrderWorkflowBadgeVariant }
> = {
  pre_commit: {
    labelKey: "orders.workflow.commercial.preCommit",
    variant: "outline",
  },
  committed: {
    labelKey: "orders.workflow.commercial.committed",
    variant: "info",
  },
  cancelled: {
    labelKey: "orders.workflow.commercial.cancelled",
    variant: "outline",
  },
};

export const BILLING_STATUS_META: Record<
  OrderBillingStatus,
  { labelKey: string; variant: OrderWorkflowBadgeVariant }
> = {
  not_invoiced: {
    labelKey: "orders.workflow.billing.notInvoiced",
    variant: "outline",
  },
  unpaid: {
    labelKey: "orders.workflow.billing.unpaid",
    variant: "warning",
  },
  partial: {
    labelKey: "orders.workflow.billing.partial",
    variant: "warning",
  },
  paid: {
    labelKey: "orders.workflow.billing.paid",
    variant: "success",
  },
  overdue: {
    labelKey: "orders.workflow.billing.overdue",
    variant: "destructive",
  },
  voided: {
    labelKey: "orders.workflow.billing.voided",
    variant: "outline",
  },
};

export const RESERVATION_STATUS_META: Record<
  OrderReservationStatus,
  { labelKey: string; variant: OrderWorkflowBadgeVariant }
> = {
  not_reserved: {
    labelKey: "orders.workflow.reservation.notReserved",
    variant: "outline",
  },
  reserved: {
    labelKey: "orders.workflow.reservation.reserved",
    variant: "success",
  },
  released: {
    labelKey: "orders.workflow.reservation.released",
    variant: "outline",
  },
};