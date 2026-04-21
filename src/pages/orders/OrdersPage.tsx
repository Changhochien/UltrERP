/** Orders page — list, create, and detail views. */

import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import type { QuotationOrderHandoff } from "../../domain/crm/types";
import { usePermissions } from "../../hooks/usePermissions";
import { prepareQuotationOrderHandoff } from "../../lib/api/crm";
import { ORDERS_ROUTE, ORDER_CREATE_ROUTE } from "../../lib/routes";
import { OrderForm } from "../../domain/orders/components/OrderForm";
import { OrderList } from "../../domain/orders/components/OrderList";
import { OrderDetail } from "../../domain/orders/components/OrderDetail";
import type { OrderFormValues } from "../../lib/schemas/order.schema";

interface OrderCreateLocationState {
  quotationOrderHandoff?: QuotationOrderHandoff;
}

function toOrderInitialValues(handoff: QuotationOrderHandoff): Partial<OrderFormValues> {
  return {
    customer_id: handoff.customer_id,
    source_quotation_id: handoff.source_quotation_id,
    crm_context_snapshot: handoff.crm_context_snapshot ?? null,
    notes: handoff.notes,
    lines: handoff.lines.map((line) => ({
      product_id: line.product_id,
      source_quotation_line_no: line.source_quotation_line_no,
      description: line.description,
      quantity: Number(line.quantity),
      list_unit_price: Number(line.list_unit_price),
      unit_price: Number(line.unit_price),
      discount_amount: Number(line.discount_amount),
      tax_policy_code: line.tax_policy_code,
    })),
  };
}

export function OrdersPage() {
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const location = useLocation();
  const navigate = useNavigate();
  const { orderId } = useParams<{ orderId: string }>();
  const canWriteOrders = canWrite("orders");
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const initialCustomerId = searchParams.get("customer_id") ?? undefined;
  const quotationId = searchParams.get("quotation_id") ?? undefined;
  const handoffFromState = (location.state as OrderCreateLocationState | null)?.quotationOrderHandoff ?? null;
  const [quotationHandoff, setQuotationHandoff] = useState<QuotationOrderHandoff | null>(handoffFromState);
  const [handoffLoading, setHandoffLoading] = useState(Boolean(quotationId && !handoffFromState));
  const [handoffError, setHandoffError] = useState<string | null>(null);

  useEffect(() => {
    if (location.pathname !== ORDER_CREATE_ROUTE) {
      return;
    }

    if (handoffFromState) {
      setQuotationHandoff(handoffFromState);
      setHandoffLoading(false);
      setHandoffError(null);
      return;
    }

    if (!quotationId) {
      setQuotationHandoff(null);
      setHandoffLoading(false);
      setHandoffError(null);
      return;
    }

    let cancelled = false;
    setHandoffLoading(true);
    setHandoffError(null);
    prepareQuotationOrderHandoff(quotationId)
      .then((result) => {
        if (cancelled) {
          return;
        }
        if (result.ok) {
          setQuotationHandoff(result.data);
          setHandoffError(null);
          return;
        }
        setQuotationHandoff(null);
        setHandoffError(result.errors[0]?.message ?? t("orders.form.quotationLoadError"));
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setQuotationHandoff(null);
          setHandoffError(loadError instanceof Error ? loadError.message : t("orders.form.quotationLoadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setHandoffLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [handoffFromState, location.pathname, quotationId, t]);

  if (orderId) {
    return (
      <OrderDetail
        orderId={orderId}
        onBack={() => navigate(ORDERS_ROUTE)}
      />
    );
  }

  if (location.pathname === ORDER_CREATE_ROUTE) {
    if (!canWriteOrders) {
      return (
        <div className="space-y-6">
          <SectionCard
            title={t("orders.form.newOrderTitle")}
            description={t("orders.form.newOrderDescription")}
          >
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{t("orders.form.readOnly")}</p>
              <Button type="button" variant="outline" onClick={() => navigate(ORDERS_ROUTE)}>
                {t("orders.detail.backToList")}
              </Button>
            </div>
          </SectionCard>
        </div>
      );
    }

    if (handoffLoading) {
      return (
        <SectionCard
          title={t("orders.form.newOrderTitle")}
          description={t("orders.form.quotationLoading")}
        >
          <p aria-busy="true" className="text-sm text-muted-foreground">
            {t("orders.form.loading")}
          </p>
        </SectionCard>
      );
    }

    if (handoffError) {
      return (
        <SectionCard
          title={t("orders.form.newOrderTitle")}
          description={t("orders.form.quotationLoadError")}
        >
          <div className="space-y-4">
            <p className="text-sm text-destructive">{handoffError}</p>
            <Button type="button" variant="outline" onClick={() => navigate(ORDERS_ROUTE)}>
              {t("orders.detail.backToList")}
            </Button>
          </div>
        </SectionCard>
      );
    }

    return (
      <OrderForm
        initialCustomerId={initialCustomerId}
        initialValues={quotationHandoff ? toOrderInitialValues(quotationHandoff) : undefined}
        conversionSource={quotationHandoff ? {
          quotationId: quotationHandoff.source_quotation_id,
          partyLabel:
            typeof quotationHandoff.crm_context_snapshot?.party_label === "string"
              ? quotationHandoff.crm_context_snapshot.party_label
              : quotationHandoff.source_quotation_id,
        } : undefined}
        onCreated={(id) => navigate(`/orders/${id}`)}
        onCancel={() => navigate(ORDERS_ROUTE)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Orders"
        title="Orders"
        description="Track order flow, inspect current pipeline, and jump into fulfillment details."
        actions={(
          canWriteOrders ? (
            <Button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
              New Order
            </Button>
          ) : null
        )}
      />
      <SectionCard title="Order Pipeline" description="Filter and sort the current order queue.">
        <OrderList onSelect={(id) => navigate(`/orders/${id}`)} />
      </SectionCard>
    </div>
  );
}
