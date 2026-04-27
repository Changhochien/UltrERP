import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import OpportunityForm from "@/domain/crm/components/OpportunityForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import type { OpportunityCreatePayload } from "../../domain/crm/types";
import type { OpportunityFormValues } from "../../lib/schemas/opportunity.schema";
import { useToast } from "../../hooks/useToast";
import { createOpportunity } from "../../lib/api/crm";
import {
  CRM_OPPORTUNITIES_ROUTE,
  type AppRoute,
} from "../../lib/routes";

function getPrefill(search: string): Partial<OpportunityFormValues> {
  const params = new URLSearchParams(search);
  const partyType = params.get("partyType");
  const partyName = params.get("partyName");
  const partyLabel = params.get("partyLabel");
  const territory = params.get("territory");
  const utmSource = params.get("utmSource");
  const utmMedium = params.get("utmMedium");
  const utmCampaign = params.get("utmCampaign");
  const utmContent = params.get("utmContent");

  if (!partyType && !partyName && !partyLabel) {
    return {};
  }

  return {
    opportunity_from: partyType === "lead" || partyType === "customer" || partyType === "prospect"
      ? partyType
      : "prospect",
    party_name: partyName ?? partyLabel ?? "",
    opportunity_title: partyLabel ? `${partyLabel} Opportunity` : "",
    territory: territory ?? "",
    utm_source: utmSource ?? "",
    utm_medium: utmMedium ?? "",
    utm_campaign: utmCampaign ?? "",
    utm_content: utmContent ?? "",
  };
}

export interface CreateOpportunityPageProps {
  onNavigate?: (path: string) => void;
}

export default function CreateOpportunityPage({ onNavigate }: CreateOpportunityPageProps) {
  const { t } = useTranslation("crm");
const { t: tRoutes } = useTranslation("routes");
  const location = useLocation();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const initialValues = useMemo(() => getPrefill(location.search), [location.search]);

  async function handleSubmit(payload: OpportunityCreatePayload) {
    setSubmitting(true);
    setServerErrors([]);
    try {
      const result = await createOpportunity(payload);
      if (result.ok) {
        setCreatedId(result.data.id);
        showSuccessToast(
          t("opportunities.createPage.toast.successTitle"),
          t("opportunities.createPage.toast.successDescription", { name: result.data.opportunity_title }),
        );
        return;
      }
      setServerErrors(result.errors);
      showErrorToast(
        t("opportunities.createPage.toast.errorTitle"),
        result.errors[0]?.message ?? t("opportunities.createPage.toast.errorDescription"),
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
            { label: tRoutes("crmOpportunities.label"), href: CRM_OPPORTUNITIES_ROUTE as AppRoute },
            { label: tRoutes("createOpportunity.label") },
          ]}
          eyebrow={t("opportunities.createPage.eyebrow")}
          title={t("opportunities.createPage.titleCreated")}
          description={t("opportunities.createPage.descriptionCreated")}
        />
        <SectionCard
          title={t("opportunities.createPage.createdRecord")}
          description={t("opportunities.createPage.createdRecordDescription")}
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
              {t("opportunities.createPage.createAnother")}
            </Button>
            {onNavigate ? (
              <Button type="button" variant="outline" onClick={() => onNavigate(CRM_OPPORTUNITIES_ROUTE)}>
                {t("opportunities.createPage.backToPipeline")}
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
          { label: tRoutes("crmOpportunities.label"), href: CRM_OPPORTUNITIES_ROUTE as AppRoute },
          { label: tRoutes("createOpportunity.label") },
        ]}
        eyebrow={t("opportunities.createPage.eyebrow")}
        title={t("opportunities.createPage.title")}
        description={t("opportunities.createPage.description")}
      />
      <SectionCard
        title={t("opportunities.createPage.formTitle")}
        description={t("opportunities.createPage.formDescription")}
      >
        <OpportunityForm
          onSubmit={handleSubmit}
          submitting={submitting}
          serverErrors={serverErrors}
          initialValues={initialValues}
        />
      </SectionCard>
    </div>
  );
}