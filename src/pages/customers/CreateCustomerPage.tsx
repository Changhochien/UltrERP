/** Create Customer page. */

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import type { CustomerCreatePayload, CustomerResponse } from "../../domain/customers/types";
import { CUSTOMERS_ROUTE, type AppRoute } from "../../lib/routes";
import { createCustomer, type DuplicateInfo } from "../../lib/api/customers";
import CustomerForm from "@/domain/customers/components/CustomerForm";
import DuplicateCustomerWarning from "@/domain/customers/components/DuplicateCustomerWarning";
import { trackEvent, AnalyticsEvents } from "../../lib/analytics";
import { useToast } from "../../hooks/useToast";

export interface CreateCustomerPageProps {
  onNavigate?: (path: AppRoute) => void;
}

export default function CreateCustomerPage({ onNavigate }: CreateCustomerPageProps) {
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [created, setCreated] = useState<CustomerResponse | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateInfo | null>(null);

  async function handleSubmit(payload: CustomerCreatePayload) {
    setSubmitting(true);
    setServerErrors([]);
    setDuplicate(null);
    try {
      const result = await createCustomer(payload);
      if (result.ok) {
        trackEvent(AnalyticsEvents.CUSTOMER_CREATED, { source_page: "/customers" });
        showSuccessToast(
          t("customer.createPage.toast.successTitle"),
          t("customer.createPage.toast.successDescription", { name: result.data.company_name }),
        );
        setCreated(result.data);
      } else if (result.duplicate) {
        setDuplicate(result.duplicate);
      } else {
        setServerErrors(result.errors);
        showErrorToast(
          t("customer.createPage.toast.errorTitle"),
          result.errors[0]?.message ?? t("customer.createPage.toast.errorDescription"),
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={[
            { label: tRoutes("customers.label"), href: CUSTOMERS_ROUTE },
            { label: tRoutes("createCustomer.label") },
          ]}
          eyebrow={t("customer.createPage.eyebrow")}
          title={t("customer.createPage.titleCreated")}
          description={t("customer.createPage.descriptionCreated")}
        />
        <SectionCard
          title={t("customer.createPage.createdRecord")}
          description={t("customer.createPage.createdRecordDescription")}
        >
          <div className="space-y-4 text-sm">
            <p>
              <strong>{created.company_name}</strong> ({created.normalized_business_number}) has been
              created with ID <code>{created.id}</code>.
            </p>
            <Button type="button" onClick={() => setCreated(null)}>
              {t("customer.createPage.createAnother")}
            </Button>
          </div>
        </SectionCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: tRoutes("customers.label"), href: CUSTOMERS_ROUTE },
          { label: tRoutes("createCustomer.label") },
        ]}
        eyebrow={t("customer.createPage.eyebrow")}
        title={t("customer.createPage.title")}
        description={t("customer.createPage.description")}
      />
      <SectionCard
        title={t("customer.createPage.formTitle")}
        description={t("customer.createPage.formDescription")}
      >
        {duplicate ? (
          <DuplicateCustomerWarning
            duplicate={duplicate}
            onViewExisting={() => onNavigate?.(CUSTOMERS_ROUTE)}
            onCancel={() => setDuplicate(null)}
          />
        ) : (
          <CustomerForm onSubmit={handleSubmit} submitting={submitting} serverErrors={serverErrors} />
        )}
      </SectionCard>
    </div>
  );
}
