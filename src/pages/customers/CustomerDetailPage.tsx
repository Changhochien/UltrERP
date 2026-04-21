/** Customer detail page — shows all customer fields and tabbed sub-views. */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { EditCustomerDialog } from "../../components/customers/EditCustomerDialog";
import { getCustomer, updateCustomer } from "../../lib/api/customers";
import type { CustomerResponse } from "../../domain/customers/types";
import { CustomerInvoicesTab } from "../../components/customers/CustomerInvoicesTab";
import { CustomerOrdersTab } from "../../components/customers/CustomerOrdersTab";
import { CustomerOutstandingTab } from "../../components/customers/CustomerOutstandingTab";
import { CustomerStatementTab } from "../../components/customers/CustomerStatementTab";
import { CUSTOMERS_ROUTE } from "../../lib/routes";
import { CustomerAnalyticsTab } from "@/components/customers/CustomerAnalyticsTab";
import { usePermissions } from "../../hooks/usePermissions";

interface CustomerDetailPageProps {
  onBack: () => void;
}

const STATUS_VARIANT: Record<string, "success" | "warning" | "outline"> = {
  active: "success",
  suspended: "warning",
  inactive: "outline",
};

const STATUS_LABEL_KEYS: Record<string, string> = {
  active: "customer.detail.statusValues.active",
  suspended: "customer.detail.statusValues.suspended",
  inactive: "customer.detail.statusValues.inactive",
  deleted: "customer.detail.statusValues.deleted",
};

export function CustomerDetailPage({ onBack }: CustomerDetailPageProps) {
  const { customerId } = useParams<{ customerId: string }>();
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getCustomer(customerId).then((data) => {
      if (cancelled) return;
      if (!data) {
        setError(t("customer.detail.notFound"));
        setLoading(false);
        return;
      }
      setCustomer(data);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [customerId, t, refreshKey]);

  const handleSuspend = useCallback(async () => {
    if (!customer) return;
    if (!window.confirm(t("customer.detail.suspendConfirm.message"))) return;

    const result = await updateCustomer(customer.id, {
      status: "suspended",
      version: customer.version,
    });
    if (result.ok) {
      setRefreshKey((k) => k + 1);
    } else {
      alert(result.errors?.[0]?.message ?? t("customer.detail.suspendConfirm.error"));
    }
  }, [customer, t]);

  const handleDelete = useCallback(async () => {
    if (!customer) return;
    if (!window.confirm(t("customer.detail.deleteConfirm.message"))) return;

    // Check outstanding balance before delete
    // Use the outstanding tab's hook via direct API call if available
    // For simplicity, attempt soft-delete; if backend rejects, show error
    const result = await updateCustomer(customer.id, {
      status: "deleted",
      version: customer.version,
    });
    if (result.ok) {
      onBack();
    } else {
      const msg = result.errors?.[0]?.message ?? t("customer.detail.deleteConfirm.error");
      // Check for outstanding balance error
      if (msg.toLowerCase().includes("outstanding") || msg.toLowerCase().includes("balance")) {
        alert(t("customer.detail.cannotDelete.message"));
      } else {
        alert(msg);
      }
    }
  }, [customer, t, onBack]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-24" />
        </div>
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="space-y-6">
        <Button type="button" variant="outline" onClick={onBack}>
          {t("customer.detail.backToList")}
        </Button>
        <div role="alert" className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error ?? t("customer.detail.notFound")}
        </div>
      </div>
    );
  }

  const statusLabel = STATUS_LABEL_KEYS[customer.status]
    ? t(STATUS_LABEL_KEYS[customer.status], { defaultValue: customer.status })
    : customer.status;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: t("routes.customers.label"), href: CUSTOMERS_ROUTE },
          { label: customer.company_name },
        ]}
        eyebrow={t("customer.detail.eyebrow")}
        title={customer.company_name}
        description={`${customer.normalized_business_number} · ${statusLabel}`}
        actions={canWrite("customers") ? (
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setEditingId(customer.id)}
            >
              {t("customer.detail.edit")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleSuspend}
              disabled={customer.status === "suspended"}
            >
              {t("customer.detail.suspend")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleDelete}
            >
              {t("customer.detail.delete")}
            </Button>
          </div>
        ) : undefined}
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">{t("customer.detail.tabs.overview")}</TabsTrigger>
          <TabsTrigger value="invoices">{t("customer.detail.tabs.invoices")}</TabsTrigger>
          <TabsTrigger value="orders">{t("customer.detail.tabs.orders")}</TabsTrigger>
          <TabsTrigger value="outstanding">{t("customer.detail.tabs.outstanding")}</TabsTrigger>
          <TabsTrigger value="statement">{t("customer.detail.tabs.statement")}</TabsTrigger>
          <TabsTrigger value="analytics">{t("customer.detail.tabs.analytics")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <SectionCard
            title={t("customer.detail.overviewTitle")}
            description={t("customer.detail.overviewDescription")}
          >
            <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.companyName")}</dt>
                <dd className="mt-1 text-sm font-medium">{customer.company_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.ban")}</dt>
                <dd className="mt-1 text-sm font-medium">{customer.normalized_business_number}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.billingAddress")}</dt>
                <dd className="mt-1 text-sm">{customer.billing_address}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.contactName")}</dt>
                <dd className="mt-1 text-sm">{customer.contact_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.phone")}</dt>
                <dd className="mt-1 text-sm">{customer.contact_phone}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.email")}</dt>
                <dd className="mt-1 text-sm">{customer.contact_email}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.creditLimit")}</dt>
                <dd className="mt-1 text-sm">${customer.credit_limit}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.status")}</dt>
                <dd className="mt-1">
                  <Badge variant={STATUS_VARIANT[customer.status] ?? "outline"} className="normal-case tracking-normal">
                    {statusLabel}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.createdAt")}</dt>
                <dd className="mt-1 text-sm">{new Date(customer.created_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t("customer.detail.updatedAt")}</dt>
                <dd className="mt-1 text-sm">{new Date(customer.updated_at).toLocaleString()}</dd>
              </div>
            </dl>
          </SectionCard>
        </TabsContent>

        <TabsContent value="invoices">
          {customerId ? <CustomerInvoicesTab customerId={customerId} /> : null}
        </TabsContent>

        <TabsContent value="orders">
          {customerId ? <CustomerOrdersTab customerId={customerId} /> : null}
        </TabsContent>

        <TabsContent value="outstanding">
          {customerId ? <CustomerOutstandingTab customerId={customerId} /> : null}
        </TabsContent>

        <TabsContent value="statement">
          {customerId ? (
            <CustomerStatementTab customerId={customerId} customerName={customer.company_name} />
          ) : null}
        </TabsContent>

        <TabsContent value="analytics">
          {customerId ? <CustomerAnalyticsTab customerId={customerId} /> : null}
        </TabsContent>
      </Tabs>

      {editingId && (
        <EditCustomerDialog
          customerId={editingId}
          onClose={() => setEditingId(null)}
          onSaved={() => {
            setEditingId(null);
            setRefreshKey((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}
