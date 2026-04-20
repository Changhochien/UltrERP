/** Read-only order detail view with line items and status actions. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useToast } from "../../../hooks/useToast";
import { useOrderDetail, statusBadgeVariant, statusLabel } from "../hooks/useOrders";
import { updateOrderStatus } from "../../../lib/api/orders";
import type { OrderStatus } from "../types";

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

function buildStatusToastCopy(
  t: ReturnType<typeof useTranslation>["t"],
  targetStatus: OrderStatus,
  orderNumber: string,
  invoiceNumber: string | null,
) {
  if (targetStatus === "confirmed") {
    if (invoiceNumber) {
      return {
        title: t("orders.detail.toast.confirmedTitle"),
        description: t("orders.detail.toast.confirmedDescription", { invoiceNumber }),
      };
    }

    return {
      title: t("orders.detail.toast.confirmedTitle"),
      description: t("orders.detail.toast.confirmedDescriptionFallback", { orderNumber }),
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

export function OrderDetail({ orderId, onBack }: OrderDetailProps) {
  const { t } = useTranslation("common");
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const navigate = useNavigate();
  const { order, loading, error, reload } = useOrderDetail(orderId);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<StatusAction | null>(null);
  const [showInvoiceSuccess, setShowInvoiceSuccess] = useState<{
    invoiceId: string | null;
    invoiceNumber: string;
  } | null>(null);

  const handleStatusChange = async (targetStatus: OrderStatus) => {
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
      if (activeAction?.isConfirmOrder && result.data?.invoice_number) {
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

  const isConfirmed = order.status === "confirmed" || order.status === "shipped" || order.status === "fulfilled";
  const exec = order.execution;

  return (
    <section aria-label="Order detail" className="space-y-5">
      <Button type="button" variant="outline" onClick={onBack}>
        {t("orders.detail.backToList")}
      </Button>

      {showInvoiceSuccess ? (
        <SectionCard title={t("orders.detail.confirmed")}>
          <div className="space-y-3">
            <SurfaceMessage tone="success">
              {t("orders.detail.invoiceCreated", { number: showInvoiceSuccess.invoiceNumber })}
            </SurfaceMessage>
            <Button
              type="button"
              onClick={() => navigate(`/invoices/${showInvoiceSuccess.invoiceId}`)}
            >
              {t("orders.detail.viewInvoice", { number: showInvoiceSuccess.invoiceNumber })}
            </Button>
          </div>
        </SectionCard>
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold tracking-tight">{t("orders.detail.orderTitle")} {order.order_number}</h2>
          <Badge variant={statusBadgeVariant(order.status as OrderStatus)} className="normal-case tracking-normal">
            {statusLabel(order.status as OrderStatus)}
          </Badge>
        </div>
        {actions.length > 0 && !activeAction ? (
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <Button key={action.targetStatus} type="button" onClick={() => setActiveAction(action)}>
                {t(action.labelKey)}
              </Button>
            ))}
          </div>
        ) : null}
      </div>

      {activeAction ? (
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
                {t("orders.list.backorderRisk")}: {exec.backorder_line_count} line(s)
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
            {order.invoice_id && order.invoice_number ? (
              <p>
                <span className="font-medium">{t("orders.detail.invoice")}:</span>{" "}
                <button
                  type="button"
                  className="appearance-none border-0 bg-transparent p-0 text-foreground underline-offset-4 hover:text-foreground/80 hover:underline focus-visible:underline"
                  onClick={() => navigate(`/invoices/${order.invoice_id}`)}
                >
                  {order.invoice_number}
                </button>
              </p>
            ) : (
              <p>
                <span className="font-medium">{t("orders.detail.invoice")}:</span>{" "}
                {t("orders.list.invoiceOnConfirmation")}
              </p>
            )}
            {order.invoice_payment_status && (
              <p>
                <span className="font-medium">{t("orders.list.unpaid")}:</span>{" "}
                {order.invoice_payment_status}
              </p>
            )}
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
