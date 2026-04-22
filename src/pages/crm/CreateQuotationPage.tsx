import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import QuotationForm from "../../components/crm/QuotationForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import type { OpportunityQuotationHandoff, QuotationCreatePayload } from "../../domain/crm/types";
import type { QuotationFormValues } from "../../lib/schemas/quotation.schema";
import { useToast } from "../../hooks/useToast";
import { createQuotation } from "../../lib/api/crm";
import { CRM_QUOTATIONS_ROUTE, type AppRoute } from "../../lib/routes";

const DEFAULT_COMPANY = "UltrERP Taiwan";

function formatDateInput(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function addDays(value: Date, days: number): Date {
  const next = new Date(value);
  next.setDate(next.getDate() + days);
  return next;
}

function getPrefill(state: unknown, search: string): Partial<QuotationFormValues> {
  const handoff = (state as { handoff?: OpportunityQuotationHandoff } | null)?.handoff;
  const today = formatDateInput(new Date());
  const validTill = formatDateInput(addDays(new Date(), 30));

  if (handoff) {
    return {
      quotation_to: handoff.opportunity_from,
      party_name: handoff.party_name,
      company: DEFAULT_COMPANY,
      transaction_date: today,
      valid_till: validTill,
      currency: handoff.currency,
      territory: handoff.territory,
      customer_group: handoff.customer_group,
      contact_person: handoff.contact_person,
      contact_email: handoff.contact_email,
      contact_mobile: handoff.contact_mobile,
      job_title: handoff.job_title,
      utm_source: handoff.utm_source,
      utm_medium: handoff.utm_medium,
      utm_campaign: handoff.utm_campaign,
      utm_content: handoff.utm_content,
      opportunity_id: handoff.opportunity_id,
      items: handoff.items.map((item) => ({
        item_name: item.item_name,
        item_code: item.item_code,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
    };
  }

  const params = new URLSearchParams(search);
  const partyType = params.get("partyType");
  const partyName = params.get("partyName");
  const territory = params.get("territory");
  const customerGroup = params.get("customerGroup");
  const contactName = params.get("contactName");
  const contactEmail = params.get("contactEmail");
  const contactMobile = params.get("contactMobile");
  const utmSource = params.get("utmSource");
  const utmMedium = params.get("utmMedium");
  const utmCampaign = params.get("utmCampaign");
  const utmContent = params.get("utmContent");

  if (!partyType && !partyName) {
    return {
      company: DEFAULT_COMPANY,
      transaction_date: today,
      valid_till: validTill,
      items: [
        {
          item_name: "",
          item_code: "",
          description: "",
          quantity: "1",
          unit_price: "",
        },
      ],
    };
  }

  return {
    quotation_to:
      partyType === "lead" || partyType === "customer" || partyType === "prospect"
        ? partyType
        : "prospect",
    party_name: partyName ?? "",
    company: DEFAULT_COMPANY,
    transaction_date: today,
    valid_till: validTill,
    territory: territory ?? "",
    customer_group: customerGroup ?? "",
    contact_person: contactName ?? "",
    contact_email: contactEmail ?? "",
    contact_mobile: contactMobile ?? "",
    utm_source: utmSource ?? "",
    utm_medium: utmMedium ?? "",
    utm_campaign: utmCampaign ?? "",
    utm_content: utmContent ?? "",
    items: [
      {
        item_name: "",
        item_code: "",
        description: "",
        quantity: "1",
        unit_price: "",
      },
    ],
  };
}

export interface CreateQuotationPageProps {
  onNavigate?: (path: string) => void;
}

export default function CreateQuotationPage({ onNavigate }: CreateQuotationPageProps) {
  const { t } = useTranslation("common");
  const location = useLocation();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const initialValues = useMemo(
    () => getPrefill(location.state, location.search),
    [location.search, location.state],
  );

  async function handleSubmit(payload: QuotationCreatePayload) {
    setSubmitting(true);
    setServerErrors([]);
    try {
      const result = await createQuotation(payload);
      if (result.ok) {
        setCreatedId(result.data.id);
        showSuccessToast(
          t("crm.quotations.createPage.toast.successTitle"),
          t("crm.quotations.createPage.toast.successDescription", { name: result.data.party_label }),
        );
        return;
      }
      setServerErrors(result.errors);
      showErrorToast(
        t("crm.quotations.createPage.toast.errorTitle"),
        result.errors[0]?.message ?? t("crm.quotations.createPage.toast.errorDescription"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (createdId) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={[
            { label: t("routes.crmQuotations.label"), href: CRM_QUOTATIONS_ROUTE as AppRoute },
            { label: t("routes.createQuotation.label") },
          ]}
          eyebrow={t("crm.quotations.createPage.eyebrow")}
          title={t("crm.quotations.createPage.titleCreated")}
          description={t("crm.quotations.createPage.descriptionCreated")}
        />
        <SectionCard
          title={t("crm.quotations.createPage.createdRecord")}
          description={t("crm.quotations.createPage.createdRecordDescription")}
        >
          <div className="space-y-4 text-sm">
            <p>
              <strong>{createdId}</strong>
            </p>
            <Button
              type="button"
              onClick={() => {
                setCreatedId(null);
                setServerErrors([]);
              }}
            >
              {t("crm.quotations.createPage.createAnother")}
            </Button>
            {onNavigate ? (
              <Button type="button" variant="outline" onClick={() => onNavigate(CRM_QUOTATIONS_ROUTE)}>
                {t("crm.quotations.createPage.backToRegistry")}
              </Button>
            ) : null}
          </div>
        </SectionCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: t("routes.crmQuotations.label"), href: CRM_QUOTATIONS_ROUTE as AppRoute },
          { label: t("routes.createQuotation.label") },
        ]}
        eyebrow={t("crm.quotations.createPage.eyebrow")}
        title={t("crm.quotations.createPage.title")}
        description={t("crm.quotations.createPage.description")}
      />
      <SectionCard
        title={t("crm.quotations.createPage.formTitle")}
        description={t("crm.quotations.createPage.formDescription")}
      >
        <QuotationForm
          onSubmit={handleSubmit}
          submitting={submitting}
          serverErrors={serverErrors}
          initialValues={initialValues}
        />
      </SectionCard>
    </div>
  );
}