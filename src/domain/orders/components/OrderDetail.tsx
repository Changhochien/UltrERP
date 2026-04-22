/** Read-only order detail view with line items and status actions. */

import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Breadcrumb } from "../../../components/ui/Breadcrumb";
import { Button } from "../../../components/ui/button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { usePermissions } from "../../../hooks/usePermissions";
import { useToast } from "../../../hooks/useToast";
import { useOrderDetail, statusBadgeVariant, statusLabel } from "../hooks/useOrders";
import { updateOrderStatus } from "../../../lib/api/orders";
import { buildQuotationDetailPath, ORDERS_ROUTE } from "../../../lib/routes";
import type { OrderStatus } from "../types";
import { BILLING_STATUS_META } from "../workflowMeta";

interface StatusAction {
  labelKey: string;
  targetStatus: OrderStatus;
  confirmMessageKey: string;
  /** Set true for confirmOrder which shows explicit invoice+stock message */
  isConfirmOrder?: boolean;
}

const STATUS_ACTIONS: Record<string, StatusAction[]> = {
  pending: [
    { labelKey: "orders.detail.confirmOrder", targetStatus: "confirmed" as OrderStatus, confirmMessageKey: "orders.detail.createsInvoice", isConfirmOrder: true },
    { labelKey: "orders.detail.cancelOrder", targetStatus: "cancelled" as OrderStatus, confirmMessageKey: "orders.detail.cancelOrderMessage" },
  ],
  confirmed: [
    { labelKey: "orders.detail.shipOrder", targetStatus: "shipped" as OrderStatus, confirmMessageKey: "orders.detail.markShippedMessage" },
  ],
  shipped: [
    { labelKey: "orders.detail.markFulfilled", targetStatus: "fulfilled" as OrderStatus, confirmMessageKey: "orders.detail.markFulfilledMessage" },
  ],
};

interface OrderDetailProps {
  orderId: string;
  onBack: () => void;
}

const ORDER_PROGRESS_INDEX: Record<OrderStatus, number> = {
  pending: 0,
  confirmed: 1,
  shipped: 2,
  fulfilled: 3,
  cancelled: 0,
};

function ActionGroup({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
      <div className="space-y-1">
        <h4 className="text-sm font-semibold tracking-tight text-foreground">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="mt-4 space-y-2">{children}</div>
    </div>
  );
}

function buildStatusToastCopy(
  t: ReturnType<typeof useTranslation>["t"],
  targetStatus: OrderStatus,
  orderNumber: string,
  invoiceNumber?: string | null,
) {
  if (targetStatus === "confirmed") {
    return {
      title: t("orders.detail.toast.confirmedTitle"),
      description: invoiceNumber
        ? t("orders.detail.toast.confirmedDescription", { invoiceNumber })
        : t("orders.detail.toast.confirmedDescriptionFallback", { orderNumber }),
    };
  }

  if (targetStatus === "shipped") {
    return {
      title: t("orders.detail.toast.shippedTitle"),
      description: t("orders.detail.toast.shippedDescription", { orderNumber }),
    };
  }

  if (targetStatus === "fulfilled") {
    return {
      title: t("orders.detail.toast.fulfilledTitle"),
      description: t("orders.detail.toast.fulfilledDescription", { orderNumber }),
    };
  }

  return {
    title: t("orders.detail.toast.cancelledTitle"),
    description: t("orders.detail.toast.cancelledDescription", { orderNumber }),
  };
}

function snapshotText(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function OrderDetail({ orderId, onBack }: OrderDetailProps) {
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const navigate = useNavigate();
  const { order, loading, error, reload } = useOrderDetail(orderId);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<StatusAction | null>(null);
  const [showInvoiceSuccess, setShowInvoiceSuccess] = useState<{
    invoiceId: string | null;
    invoiceNumber: string | null;
  } | null>(null);
  const canWriteOrders = canWrite("orders");

  const handleStatusChange = async (targetStatus: OrderStatus) => {
    if (!canWriteOrders) {
      return;
    }
    setUpdating(true);
    setUpdateError(null);
    const result = await updateOrderStatus(orderId, targetStatus);
    setUpdating(false);
    if (result.ok) {
      setActiveAction(null);
      const toastCopy = buildStatusToastCopy(
        t,
        targetStatus,
        result.data.order_number,
        result.data.invoice_number,
      );
      showSuccessToast(toastCopy.title, toastCopy.description);
      if (activeAction?.isConfirmOrder && result.data.invoice_id) {
        setShowInvoiceSuccess({
          invoiceId: result.data.invoice_id,
          invoiceNumber: result.data.invoice_number,
        });
      }
      reload();
    } else {
      setUpdateError(result.error);
      showErrorToast(t("orders.detail.toast.errorTitle"), result.error);
    }
  };

  if (loading) return <p aria-busy="true">{t("messages.loading")}</p>;
  if (error) return <div role="alert" className="text-sm text-destructive">{error}</div>;
  if (!order) return <p>{t("orders.detail.notFound")}</p>;

  const actions = STATUS_ACTIONS[order.status] ?? [];
  const salesTeam = order.sales_team ?? [];
  const crmContext = order.crm_context_snapshot ?? null;
  const sourcePartyLabel = snapshotText(crmContext?.party_label);
  const sourceTerritory = snapshotText(crmContext?.territory);
  const sourceCustomerGroup = snapshotText(crmContext?.customer_group);
  const sourceContact = snapshotText(crmContext?.contact_person);
  const sourceBillingAddress = snapshotText(crmContext?.billing_address);
  const sourceShippingAddress = snapshotText(crmContext?.shipping_address);
  const utmSource = order.utm_source || snapshotText(crmContext?.utm_source);
  const utmMedium = order.utm_medium || snapshotText(crmContext?.utm_medium);
  const utmCampaign = order.utm_campaign || snapshotText(crmContext?.utm_campaign);
  const utmContent = order.utm_content || snapshotText(crmContext?.utm_content);
  const utmAttributionOrigin = order.utm_attribution_origin || snapshotText(crmContext?.utm_attribution_origin);

  const isConfirmed = order.status === "confirmed" || order.status === "shipped" || order.status === "fulfilled";
  const exec = isConfirmed ? order.execution : null;
  const billingMeta = exec ? BILLING_STATUS_META[exec.billing_status] : null;
  const commercialActions = actions.filter((action) =>
    action.targetStatus === "confirmed" || action.targetStatus === "cancelled",
  );
  const warehouseActions = actions.filter((action) =>
    action.targetStatus === "shipped" || action.targetStatus === "fulfilled",
  );
  const timelineSteps = [
    {
      key: "intake",
      label: t("orders.detail.timeline.intake"),
      detail: new Date(order.created_at).toLocaleString(),
    },
    {
      key: "commit",
      label: t("orders.detail.timeline.commit"),
      detail: order.invoice_number
        ? t("orders.detail.timeline.invoiceLinked", { number: order.invoice_number })
        : t("orders.list.invoiceOnConfirmation"),
    },
    {
      key: "ship",
      label: t("orders.detail.timeline.ship"),
      detail: exec?.has_backorder
        ? t("orders.list.backorderRisk")
        : exec?.ready_to_ship
          ? t("orders.list.readyToShip")
          : t("orders.workflow.fulfillment.notStarted"),
    },
    {
      key: "fulfill",
      label: t("orders.detail.timeline.fulfill"),
      detail: order.status === "fulfilled"
        ? new Date(order.updated_at).toLocaleString()
        : t("orders.workflow.fulfillment.notStarted"),
    },
  ] as const;

  return (
    <section aria-label="Order detail" className="space-y-5">
      <Breadcrumb
        items={[
          { label: t("routes.orders.label"), href: ORDERS_ROUTE },
          { label: `${t("orders.detail.orderTitle")} ${order.order_number}` },
        ]}
      />

      <Button type="button" variant="outline" onClick={onBack}>
        {t("orders.detail.backToList")}
      </Button>

      {showInvoiceSuccess ? (
        <SectionCard title={t("orders.detail.confirmed")}>
          <div className="space-y-3">
            <SurfaceMessage tone="success">
              {t("orders.detail.invoiceCreated", { number: showInvoiceSuccess.invoiceNumber ?? "" })}
            </SurfaceMessage>
            <Button
              type="button"
              onClick={() => navigate(`/invoices/${showInvoiceSuccess.invoiceId}`)}
            >
              {t("orders.detail.viewInvoice", { number: showInvoiceSuccess.invoiceNumber ?? "" })}
            </Button>
          </div>
        </SectionCard>
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold tracking-tight">{t("orders.detail.orderTitle")} {order.order_number}</h2>
          <StatusBadge status={order.status} label={statusLabel(order.status as OrderStatus)} />
        </div>
      </div>

      {order.source_quotation_id || crmContext ? (
        <SectionCard
          title={t("orders.detail.crmContextTitle")}
          description={t("orders.detail.crmContextDescription")}
        >
          <div className="space-y-4">
            <div className="flex flex-col gap-3 rounded-2xl border border-border/70 bg-background/50 p-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  {sourcePartyLabel ?? t("orders.detail.crmContextFallback")}
                </p>
                {order.source_quotation_id ? (
                  <p className="text-sm text-muted-foreground">
                    {t("orders.detail.sourceQuotation", { quotationId: order.source_quotation_id })}
                  </p>
                ) : null}
              </div>
              {order.source_quotation_id ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(buildQuotationDetailPath(order.source_quotation_id as string))}
                >
                  {t("orders.detail.viewSourceQuotation")}
                </Button>
              ) : null}
            </div>

            <div className="grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-3">
              {sourceTerritory ? (
                <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmTerritory")}</p>
                  <p className="mt-1 font-medium text-foreground">{sourceTerritory}</p>
                </div>
              ) : null}
              {sourceCustomerGroup ? (
                <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmCustomerGroup")}</p>
                  <p className="mt-1 font-medium text-foreground">{sourceCustomerGroup}</p>
                </div>
              ) : null}
              {sourceContact ? (
                <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmContact")}</p>
                  <p className="mt-1 font-medium text-foreground">{sourceContact}</p>
                </div>
              ) : null}
            </div>

            {utmSource || utmMedium || utmCampaign || utmContent ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("orders.detail.crmAttribution")}
                  </p>
                  {utmAttributionOrigin ? (
                    <Badge variant="outline" className="normal-case tracking-normal">
                      {utmAttributionOrigin === "manual_override"
                        ? t("orders.detail.crmAttributionManualOverride")
                        : t("orders.detail.crmAttributionSourceDocument")}
                    </Badge>
                  ) : null}
                </div>
                <div className="grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
                  {utmSource ? (
                    <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmUtmSource")}</p>
                      <p className="mt-1 font-medium text-foreground">{utmSource}</p>
                    </div>
                  ) : null}
                  {utmMedium ? (
                    <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmUtmMedium")}</p>
                      <p className="mt-1 font-medium text-foreground">{utmMedium}</p>
                    </div>
                  ) : null}
                  {utmCampaign ? (
                    <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmUtmCampaign")}</p>
                      <p className="mt-1 font-medium text-foreground">{utmCampaign}</p>
                    </div>
                  ) : null}
                  {utmContent ? (
                    <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmUtmContent")}</p>
                      <p className="mt-1 font-medium text-foreground">{utmContent}</p>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {sourceBillingAddress || sourceShippingAddress ? (
              <div className="grid gap-3 text-sm md:grid-cols-2">
                {sourceBillingAddress ? (
                  <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmBillingAddress")}</p>
                    <p className="mt-1 whitespace-pre-wrap text-foreground">{sourceBillingAddress}</p>
                  </div>
                ) : null}
                {sourceShippingAddress ? (
                  <div className="rounded-xl border border-border/60 bg-background/40 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("orders.detail.crmShippingAddress")}</p>
                    <p className="mt-1 whitespace-pre-wrap text-foreground">{sourceShippingAddress}</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            <SurfaceMessage>{t("orders.detail.crmContextNote")}</SurfaceMessage>
          </div>
        </SectionCard>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <SectionCard
          title={t("orders.detail.workflowTimeline")}
          description={t("orders.detail.workflowTimelineDescription")}
        >
          <ol className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {timelineSteps.map((step, index) => {
              const state = order.status === "cancelled"
                ? index === 0
                  ? "completed"
                  : "cancelled"
                : index < ORDER_PROGRESS_INDEX[order.status as OrderStatus]
                  ? "completed"
                  : index === ORDER_PROGRESS_INDEX[order.status as OrderStatus]
                    ? "current"
                    : "upcoming";

              const badgeVariant = state === "completed"
                ? "success"
                : state === "current"
                  ? "info"
                  : state === "cancelled"
                    ? "destructive"
                    : "outline";

              return (
                <li key={step.key} className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                        {step.label}
                      </p>
                      <p className="text-sm text-foreground">{step.detail}</p>
                    </div>
                    <Badge variant={badgeVariant} className="normal-case tracking-normal">
                      {t(`orders.detail.timeline.${state}`)}
                    </Badge>
                  </div>
                </li>
              );
            })}
          </ol>
        </SectionCard>

        <SectionCard
          title={t("orders.detail.nextActions")}
          description={t("orders.detail.nextActionsDescription")}
        >
          <div className="space-y-3">
            {exec?.has_backorder ? (
              <SurfaceMessage tone="warning">
                {t(
                  exec.backorder_line_count === 1
                    ? "orders.detail.backorderCallout_one"
                    : "orders.detail.backorderCallout_other",
                  { count: exec.backorder_line_count },
                )}
              </SurfaceMessage>
            ) : null}
            {isConfirmed && exec && exec.reservation_status !== "reserved" ? (
              <SurfaceMessage tone="warning">
                {t("orders.detail.reservationCallout")}
              </SurfaceMessage>
            ) : null}
            {exec?.ready_to_ship ? (
              <SurfaceMessage tone="success">
                {t("orders.detail.readyToShipCallout")}
              </SurfaceMessage>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-3">
              <ActionGroup
                title={t("orders.detail.commercialActions")}
                description={t("orders.detail.commercialActionsDescription")}
              >
                {!canWriteOrders ? (
                  <p className="text-sm text-muted-foreground">{t("orders.detail.readOnlyActions")}</p>
                ) : commercialActions.length > 0 ? commercialActions.map((action) => (
                  <Button key={action.targetStatus} type="button" onClick={() => setActiveAction(action)}>
                    {t(action.labelKey)}
                  </Button>
                )) : <p className="text-sm text-muted-foreground">{t("orders.detail.noCommercialActions")}</p>}
              </ActionGroup>

              <ActionGroup
                title={t("orders.detail.warehouseActions")}
                description={t("orders.detail.warehouseActionsDescription")}
              >
                {!canWriteOrders ? (
                  <p className="text-sm text-muted-foreground">{t("orders.detail.readOnlyActions")}</p>
                ) : warehouseActions.length > 0 ? warehouseActions.map((action) => (
                  <Button key={action.targetStatus} type="button" onClick={() => setActiveAction(action)}>
                    {t(action.labelKey)}
                  </Button>
                )) : <p className="text-sm text-muted-foreground">{t("orders.detail.noWarehouseActions")}</p>}
              </ActionGroup>

              <ActionGroup
                title={t("orders.detail.billingNavigation")}
                description={t("orders.detail.billingNavigationDescription")}
              >
                {order.invoice_id ? (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate(`/invoices/${order.invoice_id}`)}
                    >
                      {t("orders.detail.viewInvoice", { number: order.invoice_number ?? "" })}
                    </Button>
                    {billingMeta ? (
                      <Badge variant={billingMeta.variant} className="w-fit normal-case tracking-normal">
                        {t(billingMeta.labelKey)}
                      </Badge>
                    ) : null}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">{t("orders.detail.billingPending")}</p>
                )}
              </ActionGroup>
            </div>
          </div>
        </SectionCard>
      </div>

      {activeAction && canWriteOrders ? (
        <SectionCard title={t("orders.detail.confirmStatusChange")}>
          <div role="dialog" aria-label="Confirm status change" className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {activeAction.isConfirmOrder
                ? t("orders.detail.createsInvoice")
                : t(activeAction.confirmMessageKey)}
            </p>
            {updateError ? (
              <SurfaceMessage tone="danger">
                {updateError.includes("stock") || updateError.includes("Stock")
                  ? t("orders.detail.stockReservationFailed")
                  : updateError}
                {updateError.includes("stock") && (
                  <span> — {t("orders.detail.adjustQuantities")}</span>
                )}
              </SurfaceMessage>
            ) : null}
            <div className="flex gap-3">
              <Button type="button" onClick={() => handleStatusChange(activeAction.targetStatus)} disabled={updating}>
                {updating ? t("orders.detail.updating") : `${t("common.yes")}, ${t(activeAction.labelKey)}`}
              </Button>
              <Button type="button" variant="outline" onClick={() => { setActiveAction(null); setUpdateError(null); }}>
                {t("common.cancel")}
              </Button>
            </div>
          </div>
        </SectionCard>
      ) : null}

      {isConfirmed && exec ? (
        <SectionCard title={t("orders.detail.fulfillment")}>
          <div className="space-y-2 text-sm">
            <p>
              <span className="font-medium">{t("orders.list.readyToShip")}:</span>{" "}
              {exec.ready_to_ship ? t("common.yes") : t("common.no")}
            </p>
            {exec.has_backorder && (
              <p className="text-destructive">
                {t(
                  exec.backorder_line_count === 1
                    ? "orders.list.backorderLines_one"
                    : "orders.list.backorderLines_other",
                  { count: exec.backorder_line_count },
                )}
              </p>
            )}
            <p>
              <span className="font-medium">{t("orders.list.stockReserved")}:</span>{" "}
              {exec.reservation_status === "reserved" ? t("common.yes") : t("common.no")}
            </p>
          </div>
        </SectionCard>
      ) : null}

      {isConfirmed && exec ? (
        <SectionCard title={t("orders.detail.billingContext")}>
          <div className="space-y-2 text-sm">
            {order.invoice_id ? (
              <p>
                <span className="font-medium">{t("orders.detail.invoice")}:</span>{" "}
                {order.invoice_number ?? order.invoice_id}
              </p>
            ) : (
              <p>
                <span className="font-medium">{t("orders.detail.invoice")}:</span>{" "}
                {t("orders.list.invoiceOnConfirmation")}
              </p>
            )}
            {billingMeta ? (
              <p>
                <span className="font-medium">{t("orders.list.billing")}:</span>{" "}
                {t(billingMeta.labelKey)}
              </p>
            ) : null}
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title={t("orders.detail.orderSummary")} description={t("orders.detail.orderSummaryDescription")}>
        <dl className="gap-y-4">
          <dt>{t("orders.detail.customer")}</dt>
          <dd>{order.customer_name ?? order.customer_id}</dd>
          <dt>{t("orders.detail.paymentTerms")}</dt>
          <dd>{order.payment_terms_code} ({order.payment_terms_days} days)</dd>
          <dt>{t("orders.detail.subtotal")}</dt>
          <dd>${order.subtotal_amount}</dd>
          {Number(order.discount_amount ?? 0) > 0 || Number(order.discount_percent ?? 0) > 0 ? (
            <>
              <dt>{t("orders.detail.discount")}</dt>
              <dd>
                {Number(order.discount_percent ?? 0) > 0 ? `${(Number(order.discount_percent) * 100).toFixed(2)}%` : null}
                {Number(order.discount_amount ?? 0) > 0 ? ` ($${order.discount_amount})` : null}
              </dd>
            </>
          ) : null}
          <dt>{t("orders.detail.tax")}</dt>
          <dd>${order.tax_amount}</dd>
          <dt>{t("orders.detail.total")}</dt>
          <dd><strong>${order.total_amount}</strong></dd>
          {salesTeam.length > 0 ? (
            <>
              <dt>{t("orders.detail.totalCommission")}</dt>
              <dd><strong>${order.total_commission}</strong></dd>
            </>
          ) : null}
          {order.notes ? (
            <>
              <dt>{t("orders.detail.notes")}</dt>
              <dd>{order.notes}</dd>
            </>
          ) : null}
          <dt>{t("orders.detail.created")}</dt>
          <dd>{new Date(order.created_at).toLocaleString()}</dd>
          {order.confirmed_at ? (
            <>
              <dt>{t("orders.detail.confirmed")}</dt>
              <dd>{new Date(order.confirmed_at).toLocaleString()}</dd>
            </>
          ) : null}
        </dl>
      </SectionCard>

      {salesTeam.length > 0 ? (
        <SectionCard title={t("orders.detail.commissionTitle")} description={t("orders.detail.commissionDescription")}>
          <div className="space-y-4">
            <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                {t("orders.detail.totalCommission")}
              </p>
              <p className="mt-2 text-2xl font-semibold text-foreground">${order.total_commission}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {salesTeam.map((member) => (
                <div key={`${member.sales_person}-${member.allocated_percentage}-${member.commission_rate}`} className="rounded-2xl border border-border/70 bg-background/50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-foreground">{member.sales_person}</p>
                      <p className="text-sm text-muted-foreground">
                        {t("orders.detail.commissionSplit", {
                          allocation: member.allocated_percentage,
                          rate: member.commission_rate,
                        })}
                      </p>
                    </div>
                    <Badge variant="outline" className="normal-case tracking-normal">
                      ${member.allocated_amount}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title={t("orders.detail.lineItems")} description={t("orders.detail.lineItemsDescription")}>
        <DataTable
          columns={[
            { id: "line_number", header: "#", sortable: true, getSortValue: (line) => line.line_number, cell: (line) => line.line_number },
            { id: "description", header: t("orders.form.description"), sortable: true, getSortValue: (line) => line.description, cell: (line) => line.description },
            { id: "quantity", header: t("orders.form.quantity"), sortable: true, getSortValue: (line) => Number(line.quantity), cell: (line) => line.quantity },
            { id: "unit_price", header: t("orders.form.unitPrice"), sortable: true, getSortValue: (line) => Number(line.unit_price), cell: (line) => `$${line.unit_price}` },
            { id: "list_unit_price", header: t("orders.detail.listPrice"), sortable: true, getSortValue: (line) => Number(line.list_unit_price || 0), cell: (line) => { const lp = Number(line.list_unit_price || 0); const up = Number(line.unit_price || 0); return lp > 0 && lp !== up ? `$${line.list_unit_price}` : "—"; } },
            { id: "discount_amount", header: t("orders.detail.discount"), sortable: true, getSortValue: (line) => Number(line.discount_amount || 0), cell: (line) => { const da = Number(line.discount_amount || 0); const lp = Number(line.list_unit_price || 1); return da > 0 ? `${((da / lp) * 100).toFixed(1)}%` : "—"; } },
            { id: "tax_amount", header: t("orders.detail.tax"), sortable: true, getSortValue: (line) => Number(line.tax_amount), cell: (line) => `$${line.tax_amount}` },
            { id: "subtotal_amount", header: t("orders.detail.subtotal"), sortable: true, getSortValue: (line) => Number(line.subtotal_amount), cell: (line) => `$${line.subtotal_amount}` },
            { id: "total_amount", header: t("orders.detail.total"), sortable: true, getSortValue: (line) => Number(line.total_amount), cell: (line) => `$${line.total_amount}` },
            {
              id: "stock",
              header: t("orders.form.stock"),
              cell: (line) => (
                <div className="text-sm">
                  {line.available_stock_snapshot != null ? <span>{line.available_stock_snapshot}</span> : null}
                  {line.backorder_note ? <span className="block text-destructive">{line.backorder_note}</span> : null}
                </div>
              ),
            },
          ]}
          data={order.lines}
          emptyTitle={t("orders.detail.noLineItems")}
          emptyDescription={t("orders.detail.noLineItemsDescription")}
          getRowId={(line) => line.id}
        />
      </SectionCard>
    </section>
  );
}
