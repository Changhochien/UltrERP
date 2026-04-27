import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import DuplicateLeadWarning from "@/domain/crm/components/DuplicateLeadWarning";
import LeadForm from "@/domain/crm/components/LeadForm";
import { Button } from "../../components/ui/button";
import { useToast } from "../../hooks/useToast";
import { createLead } from "../../lib/api/crm";
import {
  buildCustomerDetailPath,
  buildLeadDetailPath,
  CRM_LEADS_ROUTE,
  type AppRoute,
} from "../../lib/routes";
import type {
  DuplicateLeadCandidate,
  LeadCreatePayload,
  LeadResponse,
} from "../../domain/crm/types";
import type { LeadFormValues } from "../../lib/schemas/lead.schema";

function toDraftValues(payload: LeadCreatePayload): LeadFormValues {
  return {
    lead_name: payload.lead_name,
    company_name: payload.company_name,
    email_id: payload.email_id,
    phone: payload.phone,
    mobile_no: payload.mobile_no,
    territory: payload.territory,
    lead_owner: payload.lead_owner,
    source: payload.source,
    qualification_status: payload.qualification_status,
    qualified_by: payload.qualified_by,
    annual_revenue: payload.annual_revenue ?? "",
    no_of_employees: payload.no_of_employees != null ? String(payload.no_of_employees) : "",
    industry: payload.industry,
    market_segment: payload.market_segment,
    utm_source: payload.utm_source,
    utm_medium: payload.utm_medium,
    utm_campaign: payload.utm_campaign,
    utm_content: payload.utm_content,
    notes: payload.notes,
  };
}

export interface CreateLeadPageProps {
  onNavigate?: (path: string) => void;
}

export default function CreateLeadPage({ onNavigate }: CreateLeadPageProps) {
  const { t } = useTranslation("crm");
const { t: tRoutes } = useTranslation("routes");
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [created, setCreated] = useState<LeadResponse | null>(null);
  const [duplicate, setDuplicate] = useState<{ candidates: DuplicateLeadCandidate[] } | null>(null);
  const [draftValues, setDraftValues] = useState<LeadFormValues | undefined>(undefined);

  async function handleSubmit(payload: LeadCreatePayload) {
    setSubmitting(true);
    setServerErrors([]);
    setDuplicate(null);
    try {
      const result = await createLead(payload);
      if (result.ok) {
        showSuccessToast(
          t("createPage.toast.successTitle"),
          t("createPage.toast.successDescription", { name: result.data.lead_name }),
        );
        setCreated(result.data);
      } else if (result.duplicate) {
        setDraftValues(toDraftValues(payload));
        setDuplicate(result.duplicate);
      } else {
        setServerErrors(result.errors);
        showErrorToast(
          t("createPage.toast.errorTitle"),
          result.errors[0]?.message ?? t("createPage.toast.errorDescription"),
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleOpenCandidate(candidate: DuplicateLeadCandidate) {
    if (!onNavigate) {
      return;
    }
    if (candidate.kind === "lead") {
      onNavigate(buildLeadDetailPath(candidate.id));
      return;
    }
    onNavigate(buildCustomerDetailPath(candidate.id));
  }

  if (created) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={[
            { label: tRoutes("crmLeads.label"), href: CRM_LEADS_ROUTE as AppRoute },
            { label: tRoutes("createLead.label") },
          ]}
          eyebrow={t("createPage.eyebrow")}
          title={t("createPage.titleCreated")}
          description={t("createPage.descriptionCreated")}
        />
        <SectionCard
          title={t("createPage.createdRecord")}
          description={t("createPage.createdRecordDescription")}
        >
          <div className="space-y-4 text-sm">
            <p>
              <strong>{created.lead_name}</strong> has been created with ID <code>{created.id}</code>.
            </p>
            <Button
              type="button"
              onClick={() => {
                setCreated(null);
                setDraftValues(undefined);
                setServerErrors([]);
                setDuplicate(null);
              }}
            >
              {t("createPage.createAnother")}
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
          { label: tRoutes("crmLeads.label"), href: CRM_LEADS_ROUTE as AppRoute },
          { label: tRoutes("createLead.label") },
        ]}
        eyebrow={t("createPage.eyebrow")}
        title={t("createPage.title")}
        description={t("createPage.description")}
      />
      <SectionCard
        title={t("createPage.formTitle")}
        description={t("createPage.formDescription")}
      >
        {duplicate ? (
          <DuplicateLeadWarning
            duplicate={duplicate}
            onOpenCandidate={handleOpenCandidate}
            onCancel={() => setDuplicate(null)}
          />
        ) : (
          <LeadForm
            onSubmit={handleSubmit}
            submitting={submitting}
            serverErrors={serverErrors}
            initialValues={draftValues}
          />
        )}
      </SectionCard>
    </div>
  );
}
